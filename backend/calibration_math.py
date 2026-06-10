"""
calibration_math.py - Pure mathematical functions for calibration.

This module has NO state and NO side effects on calibration sessions. It only:
    - writes sensors_cal.json (the actual calibration output, persisted)

The ellipsoid fit implements Freescale's 10-parameter eigen-decomposition
method as described in AN4246 sections 4-5 and implemented in magcal.c
(fUpdateCalibration10EIG). The key steps are:

    1. Build 10x10 measurement matrix (quadratic + linear terms)
    2. Eigen-decomposition -> smallest eigenvalue -> ellipsoid solution
    3. Extract hard-iron V, ellipsoid matrix A
    4. Normalize A to unit determinant, compute B (geomagnetic field)
    5. W^-1 = A^(1/2) via eigen-decomposition of A (symmetric, AN4246 Eq. 20)
    6. Validate B in [22, 67] uT, fit error percentage
    7. Write sensors_cal.json with coefficients + quality metrics

Public API:
    run_ellipsoid_calibration(sensor, samples) -> str summary, writes sensors_cal.json
    run_gyro_calibration(samples)             -> str summary, writes sensors_cal.json
    compute_coverage(samples, centroid=None)   -> (n, coverage_fraction, sectors_hit)
    classify_sector(x, y, z)                   -> int 0..N-1 or -1
    CENTROIDS_NP                               -> (N, 3) ndarray of face centroids

Constants exported:
    COVERAGE_TOTAL_SECTORS  = 320  (icosahedron, subdivision=2 → 20×4×4 faces)
    RAW_SAMPLE_LIMIT        = 2000 (rejects driver-glitch outliers; raised for high-G accel)
"""

import math
import json
import os
import time

import numpy as np

from shared import (
    log_event,
    SENSORS_CAL_FILE,
)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

RAW_SAMPLE_LIMIT = 2000

# Physical validity range for geomagnetic field (AN4246 / magcal.c)
MIN_GEOMAGNETIC_FIELD_UT = 22.0
MAX_GEOMAGNETIC_FIELD_UT = 67.0

# Minimum samples for 10-parameter eigen-decomposition
MIN_SAMPLES_10EIG = 150

# Default geomagnetic field used for numerical scaling (magcal.c)
DEFAULT_B_UT = 50.0

# Calibration expires after this many days
CALIBRATION_VALIDITY_DAYS = 30

# µT per raw LSB — AK09916 16-bit mode (datasheet). MUST stay equal to
# MAG_SENSITIVITY_UT in ant.c: the hard-iron offset is estimated here in this
# scale and subtracted there. If they differ, the offset is removed in the
# wrong scale -> residual hard-iron -> heading bias.
UT_PER_COUNT = 0.15


# ---------------------------------------------------------------------------
# Coverage (icosahedron-based, 320 sectors)
# ---------------------------------------------------------------------------

def _build_icosahedron_faces():
    """Return list of face centroids (normalized) for an icosahedron with
    subdivision=2 (320 face centroids)."""
    t = (1 + math.sqrt(5)) / 2
    verts = [
        [-1, t, 0], [1, t, 0], [-1, -t, 0], [1, -t, 0],
        [0, -1, t], [0, 1, t], [0, -1, -t], [0, 1, -t],
        [t, 0, -1], [t, 0, 1], [-t, 0, -1], [-t, 0, 1],
    ]
    for i in range(len(verts)):
        v = verts[i]
        norm = math.sqrt(v[0]**2 + v[1]**2 + v[2]**2)
        verts[i] = [v[0]/norm, v[1]/norm, v[2]/norm]

    faces = [
        [0,11,5],[0,5,1],[0,1,7],[0,7,10],[0,10,11],
        [1,5,9],[5,11,4],[11,10,2],[10,7,6],[7,1,8],
        [3,9,4],[3,4,2],[3,2,6],[3,6,8],[3,8,9],
        [4,9,5],[2,4,11],[6,2,10],[8,6,7],[9,8,1],
    ]

    for _ in range(2):
        new_faces = []
        mid_cache = {}
        def get_mid(a, b):
            key = (min(a,b), max(a,b))
            if key not in mid_cache:
                va, vb = verts[a], verts[b]
                mid = [
                    (va[0]+vb[0])/2, (va[1]+vb[1])/2, (va[2]+vb[2])/2
                ]
                norm = math.sqrt(mid[0]**2 + mid[1]**2 + mid[2]**2)
                mid_cache[key] = len(verts)
                verts.append([mid[0]/norm, mid[1]/norm, mid[2]/norm])
            return mid_cache[key]
        for a, b, c in faces:
            ab = get_mid(a, b)
            bc = get_mid(b, c)
            ca = get_mid(c, a)
            new_faces.extend([[a, ab, ca], [b, bc, ab], [c, ca, bc], [ab, bc, ca]])
        faces = new_faces

    centroids = []
    for a, b, c in faces:
        va, vb, vc = verts[a], verts[b], verts[c]
        cx = (va[0] + vb[0] + vc[0]) / 3
        cy = (va[1] + vb[1] + vc[1]) / 3
        cz = (va[2] + vb[2] + vc[2]) / 3
        norm = math.sqrt(cx**2 + cy**2 + cz**2)
        centroids.append((cx/norm, cy/norm, cz/norm))

    return centroids


_ICOSAHEDRON_CENTROIDS = _build_icosahedron_faces()
COVERAGE_TOTAL_SECTORS = len(_ICOSAHEDRON_CENTROIDS)
CENTROIDS_NP = np.array(_ICOSAHEDRON_CENTROIDS, dtype=np.float64)


def classify_sector(x, y, z):
    """Classify a single (x, y, z) point into the nearest face index."""
    norm_sq = x * x + y * y + z * z
    if norm_sq < 1e-18:
        return -1
    inv_norm = 1.0 / math.sqrt(norm_sq)
    nx = x * inv_norm
    ny = y * inv_norm
    nz = z * inv_norm
    dots = CENTROIDS_NP @ np.array([nx, ny, nz], dtype=np.float64)
    return int(np.argmax(dots))


def compute_coverage(samples, centroid=None):
    """Return (sample_count, coverage_fraction, distinct_faces_hit)."""
    if samples is None or len(samples) == 0:
        return 0, 0.0, 0

    arr = np.asarray(samples, dtype=np.float64)
    if arr.ndim != 2 or arr.shape[1] != 3:
        return 0, 0.0, 0

    n = arr.shape[0]

    if centroid is None:
        centroid = (arr.max(axis=0) + arr.min(axis=0)) / 2.0
    centroid = np.asarray(centroid, dtype=np.float64)

    centered = arr - centroid
    norms = np.linalg.norm(centered, axis=1, keepdims=True)
    safe_norms = np.where(norms < 1e-9, 1.0, norms)
    normed = centered / safe_norms

    dots = normed @ CENTROIDS_NP.T
    nearest = np.argmax(dots, axis=1)

    valid_mask = (norms.squeeze(-1) >= 1e-9)
    if valid_mask.any():
        hit = np.unique(nearest[valid_mask])
        faces_hit = int(hit.size)
    else:
        faces_hit = 0

    coverage = faces_hit / COVERAGE_TOTAL_SECTORS
    return n, coverage, faces_hit


# ---------------------------------------------------------------------------
# Determinant helper
# ---------------------------------------------------------------------------

def _f3x3_det(A):
    """Determinant of a 3x3 matrix."""
    return (
        A[0, 0] * (A[1, 1] * A[2, 2] - A[1, 2] * A[2, 1])
        - A[0, 1] * (A[1, 0] * A[2, 2] - A[1, 2] * A[2, 0])
        + A[0, 2] * (A[1, 0] * A[2, 1] - A[1, 1] * A[2, 0])
    )


# ---------------------------------------------------------------------------
# Outlier filter
# ---------------------------------------------------------------------------

def _filter_raw_outliers(samples, sensor):
    """Drop driver-glitch outliers."""
    arr = np.asarray(samples, dtype=np.float64)
    if arr.ndim != 2 or arr.shape[1] != 3 or arr.shape[0] == 0:
        return np.array([])
    mask = np.all(np.abs(arr) <= RAW_SAMPLE_LIMIT, axis=1)
    rejected = int((~mask).sum())
    if rejected > 0:
        pct = rejected / arr.shape[0] * 100
        log_event(
            'info',
            f'{sensor} calibration: filtered {rejected}/{arr.shape[0]} outliers ({pct:.1f}%)',
            'calibration',
        )
    return arr[mask]


# ---------------------------------------------------------------------------
# Cal-file I/O helper
# ---------------------------------------------------------------------------

_SENSOR_KEYS = ('compass', 'accel', 'gyro')


def _load_cal_file():
    """Load sensors_cal.json and return a per-sensor dict.

    Handles the legacy flat format where compass data was written at the root
    level (predating the per-sensor structure). Migrates it on read so callers
    always see {"compass": {...}, "accel": {...}, ...}."""
    if not os.path.exists(SENSORS_CAL_FILE):
        return {}
    with open(SENSORS_CAL_FILE, 'r') as f:
        raw = json.load(f)
    # Old format: compass fields at root, no sensor-type sub-keys
    if 'valid' in raw and not any(k in raw for k in _SENSOR_KEYS):
        return {'compass': raw}
    return raw


# ---------------------------------------------------------------------------
# 10-parameter ellipsoid fit -- AN4246 / magcal.c fUpdateCalibration10EIG
# ---------------------------------------------------------------------------

def run_accel_calibration(samples):
    """CANDIDATE: solver propio de accel (6 posiciones, elipsoide DIAGONAL).

    El 10-EIG del magnetometro es un elipsoide general (10 params, con cross-terms)
    y necesita una esfera densa; con 6 caras sostenidas alineadas a ejes queda
    degenerado -> 'Singular / non-positive eigenvalues / negative B^2'.
    Aqui ajustamos solo bias + escala por eje (modelo diagonal, 6 params utiles),
    bien condicionado con poses sobre los 3 ejes. Trabaja en counts crudos.
    """
    data = _filter_raw_outliers(samples, 'accel')
    n = len(data)
    if n < MIN_SAMPLES_10EIG:
        raise ValueError(
            f'Only {n} valid accel samples. Need at least {MIN_SAMPLES_10EIG}. '
            f'Hold each face still for longer.'
        )

    x, y, z = data[:, 0], data[:, 1], data[:, 2]
    # Elipsoide diagonal: A x^2 + B y^2 + C z^2 + D x + E y + F z + G = 0
    Dmat = np.column_stack([x*x, y*y, z*z, x, y, z, np.ones(n)])
    _, sv, Vt = np.linalg.svd(Dmat, full_matrices=False)
    coef = Vt[-1]
    A, B, C, Dc, E, F, G = coef

    # Para una esfera/elipsoide real A,B,C deben tener el mismo signo y no anularse.
    if A < 0:  # normaliza a coeficientes cuadraticos positivos
        A, B, C, Dc, E, F, G = -A, -B, -C, -Dc, -E, -F, -G
    if not (A > 1e-12 and B > 1e-12 and C > 1e-12):
        raise ValueError(
            'accel calibration: degenerate fit (un eje sin variacion). '
            'Sostener la unidad quieta sobre las 6 caras (ambos signos de X, Y, Z).'
        )

    bias = np.array([-Dc/(2*A), -E/(2*B), -F/(2*C)])
    K = A*bias[0]**2 + B*bias[1]**2 + C*bias[2]**2 - G  # A(x-bx)^2+... = K
    if K <= 0:
        raise ValueError(
            'accel calibration: ajuste no fisico (K<=0). Cobertura de caras insuficiente.'
        )

    axes = np.sqrt(K / np.array([A, B, C]))   # semieje (radio) por eje, en counts
    g_counts = float(axes.mean())             # radio objetivo de la esfera
    scale = g_counts / axes                    # (a-bias)*scale -> esfera radio g_counts

    corr = (data - bias) * scale
    mag = np.linalg.norm(corr, axis=1)
    fit_error_pct = float(100.0 * np.std(mag) / g_counts)

    now_ts = time.time()
    calibrated_at = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(now_ts))
    expires_at = time.strftime('%Y-%m-%dT%H:%M:%SZ',
                               time.gmtime(now_ts + CALIBRATION_VALIDITY_DAYS * 86400))
    _, coverage, sectors_hit = compute_coverage(data)

    output = {
        'valid': True,
        'calibrated_at': calibrated_at,
        'expires_at': expires_at,
        'solver': '6pos-diag',
        'sample_count': n,
        'coverage': round(coverage, 3),
        'sectors_hit': sectors_hit,
        'sectors_total': COVERAGE_TOTAL_SECTORS,
        'bias': [round(bias[0], 2), round(bias[1], 2), round(bias[2], 2)],
        'scale': [round(scale[0], 6), round(scale[1], 6), round(scale[2], 6)],
        'g_counts': round(g_counts, 1),
        'fit_error_pct': round(fit_error_pct, 4),
    }
    cal = _load_cal_file()
    cal['accel'] = output
    with open(SENSORS_CAL_FILE, 'w') as f:
        json.dump(cal, f, indent=2)

    return (
        f'Accel calibration applied ({n} samples)\n'
        f'  Bias(counts): [{bias[0]:.1f}, {bias[1]:.1f}, {bias[2]:.1f}]\n'
        f'  Scale: [{scale[0]:.4f}, {scale[1]:.4f}, {scale[2]:.4f}]\n'
        f'  g~{g_counts:.0f} counts   Fit error: {fit_error_pct:.2f}%'
    )


def run_ellipsoid_calibration(sensor, samples):
    """Run 10-parameter ellipsoid fit on `samples` and write sensors_cal.json."""
    if sensor == 'accel':
        return run_accel_calibration(samples)   # CANDIDATE: accel usa solver propio
    data = _filter_raw_outliers(samples, sensor)
    n_samples = len(data)

    if n_samples < MIN_SAMPLES_10EIG:
        raise ValueError(
            f'Only {n_samples} valid samples. Need at least {MIN_SAMPLES_10EIG}. '
            f'Keep rotating the unit to cover more orientations.'
        )

    mx = data[:, 0] * UT_PER_COUNT
    my = data[:, 1] * UT_PER_COUNT
    mz = data[:, 2] * UT_PER_COUNT

    # CANDIDATE CHANGE: se quita el pre-filtro [22,67] uT.
    # Corría sobre |mag| crudo (con offset de hierro duro incluido), que en banco
    # se sienta en 62-97 uT -> descartaba 56-100% de muestras BUENAS y sesgaba el
    # fit hacia el subconjunto de campo bajo. El offset lo RESUELVE el propio fit;
    # la validez fisica del campo se sigue chequeando POST-fit sobre B (abajo).

    if n_samples < MIN_SAMPLES_10EIG:
        raise ValueError(
            f'Only {n_samples} valid samples after filtering. Need at least {MIN_SAMPLES_10EIG}. '
            f'Keep rotating the unit to cover more orientations.'
        )

    i_offset_x = np.mean(mx)
    i_offset_y = np.mean(my)
    i_offset_z = np.mean(mz)

    x = mx - i_offset_x
    y = my - i_offset_y
    z = mz - i_offset_z

    v0 = x * x
    v1 = 2.0 * x * y
    v2 = 2.0 * x * z
    v3 = y * y
    v4 = 2.0 * y * z
    v5 = z * z
    v6 = 2.0 * x
    v7 = 2.0 * y
    v8 = 2.0 * z
    v9 = np.ones(n_samples)

    vecA = np.column_stack([v0, v1, v2, v3, v4, v5, v6, v7, v8, v9])
    matA = vecA.T @ vecA

    eigenvalues, eigenvectors = np.linalg.eigh(matA)
    j_min = np.argmin(eigenvalues)
    lambda_min = eigenvalues[j_min]
    v_solution = eigenvectors[:, j_min]

    A = np.zeros((3, 3), dtype=np.float64)
    A[0, 0] = v_solution[0]
    A[0, 1] = v_solution[1]
    A[0, 2] = v_solution[2]
    A[1, 0] = A[0, 1]
    A[1, 1] = v_solution[3]
    A[1, 2] = v_solution[4]
    A[2, 0] = A[0, 2]
    A[2, 1] = A[1, 2]
    A[2, 2] = v_solution[5]

    det_A = _f3x3_det(A)
    if det_A < 0.0:
        A = -A
        v_solution[6] = -v_solution[6]
        v_solution[7] = -v_solution[7]
        v_solution[8] = -v_solution[8]
        v_solution[9] = -v_solution[9]
        det_A = -det_A

    invA = np.linalg.inv(A)
    b_vec = np.array([v_solution[6], v_solution[7], v_solution[8]])
    V_offset = -0.5 * invA @ b_vec

    B_sq_offset = (
        A[0, 0] * V_offset[0] * V_offset[0]
        + 2.0 * A[0, 1] * V_offset[0] * V_offset[1]
        + 2.0 * A[0, 2] * V_offset[0] * V_offset[2]
        + A[1, 1] * V_offset[1] * V_offset[1]
        + 2.0 * A[1, 2] * V_offset[1] * V_offset[2]
        + A[2, 2] * V_offset[2] * V_offset[2]
        - v_solution[9]
    )
    if B_sq_offset < 0:
        raise ValueError(
            f'{sensor} calibration produced negative B^2={B_sq_offset:.2f}. '
            f'Data may be degenerate or cover insufficient orientations.'
        )
    B_offset = math.sqrt(abs(B_sq_offset))

    det_factor = det_A ** (-1.0 / 3.0)
    A_normalized = A * det_factor
    B_offset *= det_A ** (-1.0 / 6.0)

    eigvals_A, eigvecs_A = np.linalg.eigh(A_normalized)
    if np.any(eigvals_A <= 0):
        raise ValueError(
            f'{sensor} calibration: A matrix has non-positive eigenvalues. '
            f'Data insufficient or degenerate.'
        )
    sqrt_eigvals = np.sqrt(eigvals_A)
    W_inv = eigvecs_A @ np.diag(sqrt_eigvals) @ eigvecs_A.T

    V_ut = V_offset + np.array([i_offset_x, i_offset_y, i_offset_z])
    B_ut = B_offset

    fit_error_pct = (
        50.0 * math.sqrt(abs(lambda_min) / n_samples) / (B_offset * B_offset)
    )

    if sensor == 'compass':
        if B_ut < MIN_GEOMAGNETIC_FIELD_UT or B_ut > MAX_GEOMAGNETIC_FIELD_UT:
            raise ValueError(
                f'{sensor} calibration produced B={B_ut:.1f} uT, outside valid range '
                f'[{MIN_GEOMAGNETIC_FIELD_UT}, {MAX_GEOMAGNETIC_FIELD_UT}] uT. '
                f'Possible magnetic interference during calibration.'
            )

    samples_for_coverage = np.column_stack([mx, my, mz])
    _, coverage, sectors_hit = compute_coverage(samples_for_coverage)

    now_ts = time.time()
    calibrated_at = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(now_ts))
    expires_at = time.strftime(
        '%Y-%m-%dT%H:%M:%SZ',
        time.gmtime(now_ts + CALIBRATION_VALIDITY_DAYS * 86400)
    )

    output = {
        'valid': True,
        'calibrated_at': calibrated_at,
        'expires_at': expires_at,
        'solver': '10-EIG',
        'sample_count': n_samples,
        'coverage': round(coverage, 3),
        'sectors_hit': sectors_hit,
        'sectors_total': COVERAGE_TOTAL_SECTORS,
        'hard_iron_ut': [round(V_ut[0], 2), round(V_ut[1], 2), round(V_ut[2], 2)],
        'inv_soft_iron': [
            [round(W_inv[0, 0], 6), round(W_inv[0, 1], 6), round(W_inv[0, 2], 6)],
            [round(W_inv[1, 0], 6), round(W_inv[1, 1], 6), round(W_inv[1, 2], 6)],
            [round(W_inv[2, 0], 6), round(W_inv[2, 1], 6), round(W_inv[2, 2], 6)],
        ],
        'field_strength_ut': round(B_ut, 2),
        'fit_error_pct': round(fit_error_pct, 4),
    }

    cal = _load_cal_file()
    cal[sensor] = output
    with open(SENSORS_CAL_FILE, 'w') as f:
        json.dump(cal, f, indent=2)

    log_event(
        'info',
        f'{sensor.capitalize()} calibration written to {SENSORS_CAL_FILE} '
        f'(B={B_ut:.1f}, fit_error={fit_error_pct:.2f}%, '
        f'hard_iron=[{V_ut[0]:.0f}, {V_ut[1]:.0f}, {V_ut[2]:.0f}])',
        'calibration',
    )

    summary = (
        f'{sensor.capitalize()} calibration applied ({n_samples} samples)\n'
        f'  Offset: [{V_ut[0]:.1f}, {V_ut[1]:.1f}, {V_ut[2]:.1f}]\n'
        f'  Field strength: {B_ut:.1f}\n'
        f'  Fit error: {fit_error_pct:.2f}%'
    )
    return summary


# ---------------------------------------------------------------------------
# Gyro zero-bias calibration
# ---------------------------------------------------------------------------

def run_gyro_calibration(samples):
    """Estimate gyro zero-bias as the arithmetic mean of all static samples.

    The ellipsoid fit is not applicable to angular-rate data. This function
    computes the simple mean (X, Y, Z) across all supplied raw samples,
    writes the result to sensors_cal.json, and returns a human-readable
    summary string."""
    arr = np.asarray(samples, dtype=np.float64)
    if arr.ndim != 2 or arr.shape[1] != 3 or arr.shape[0] == 0:
        raise ValueError(
            f'Gyro calibration received {len(samples)} samples. '
            f'Need at least 1 valid sample.'
        )

    n_samples = arr.shape[0]
    bias_x = float(arr[:, 0].mean())
    bias_y = float(arr[:, 1].mean())
    bias_z = float(arr[:, 2].mean())

    now_ts = time.time()
    calibrated_at = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(now_ts))
    expires_at = time.strftime(
        '%Y-%m-%dT%H:%M:%SZ',
        time.gmtime(now_ts + CALIBRATION_VALIDITY_DAYS * 86400)
    )

    output = {
        'valid': True,
        'calibrated_at': calibrated_at,
        'expires_at': expires_at,
        'solver': 'zero-bias',
        'sample_count': n_samples,
        'bias': [round(bias_x, 4), round(bias_y, 4), round(bias_z, 4)],
    }

    cal = _load_cal_file()
    cal['gyro'] = output
    with open(SENSORS_CAL_FILE, 'w') as f:
        json.dump(cal, f, indent=2)

    log_event(
        'info',
        f'Gyro calibration written to {SENSORS_CAL_FILE} '
        f'(bias=[{bias_x:.2f}, {bias_y:.2f}, {bias_z:.2f}], '
        f'n={n_samples})',
        'calibration',
    )

    return (
        f'Gyro calibration applied ({n_samples} samples)\n'
        f'  Bias: [{bias_x:.2f}, {bias_y:.2f}, {bias_z:.2f}]'
    )