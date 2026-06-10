<template>
  <div class="overview">
    <div v-if="loading" class="loading">Loading...</div>

    <template v-else>
      <!-- ROW 1: Critical operational data -->
      <div class="row row-1">

        <!-- SIGNAL & LINK -->
        <div class="card card-signal">
          <div class="card-header">
            <span><AppIcon name="modem" :size="16" /> Signal &amp; Link</span>
          </div>
          <div class="card-body signal-body">

            <div class="lock-mode-row">
              <div class="lock-indicator" :class="lockClass">
                <span class="lock-dot"></span>
                <span class="lock-text">{{ lockText }}</span>
              </div>
              <div class="ui-pill" :class="modeClass">{{ modeText }}</div>
            </div>

            <div class="signal-metric">
              <div class="signal-metric-top">
                <span class="sig-label">RF Level</span>
                <span class="sig-value">{{ modem.rf_level != null ? modem.rf_level + ' dBm' : '—' }}</span>
              </div>
              <div class="rf-bar-track">
                <div class="rf-bar-fill" :style="{ width: rfBarPct + '%', background: rfBarColor }"></div>
              </div>
            </div>

            <div class="signal-metric signal-metric-inline">
              <span class="sig-label">C/N</span>
              <span class="sig-value sig-cn">{{ modem.cn_level != null ? modem.cn_level + ' dB' : '—' }}</span>
            </div>

            <div class="signal-metric signal-metric-inline">
              <span class="sig-label">Modulator TX</span>
              <span class="ui-pill" :class="modem.tx_enabled ? 'ui-pill-green' : modem.tx_enabled === false ? 'ui-pill-red' : 'ui-pill-gray'">
                {{ modem.tx_enabled ? 'ON' : modem.tx_enabled === false ? 'OFF' : '—' }}
              </span>
            </div>

            <div class="signal-metric signal-metric-inline">
              <span class="sig-label">ESA TX</span>
              <button class="ui-pill ui-pill-btn"
                :class="txMuted ? 'ui-pill-red' : 'ui-pill-green'"
                :disabled="txMuteToggling"
                @click="toggleTxMute">
                {{ txMuted ? 'MUTED' : 'ACTIVE' }}
              </button>
            </div>

            <div class="signal-updated">Updated {{ modem.timestamp || '—' }}</div>
          </div>
        </div>

        <!-- ANTENNA POSITION -->
        <div class="card card-antpos">
          <div class="card-header" :class="{ 'card-header-manual': currentMode === 'manual_pointing' }">
            <span><AppIcon name="pointing" :size="16" /> Antenna Position</span>
            <span v-if="currentMode === 'manual_pointing'" class="ui-pill ui-pill-blue">MANUAL</span>
          </div>
          <div class="card-body antpos-body">
            <div class="antpos-cols">

              <!-- LEFT: AZIMUTH + compass -->
              <div class="antpos-col">
                <div class="antpos-kpi">
                  <span class="antpos-kpi-lbl">AZIMUTH</span>
                  <span class="antpos-kpi-val">{{ displayAzimuthText }}</span>
                </div>
                <div class="antpos-compass-view">
                  <svg viewBox="0 0 160 160" class="az-compass">
                    <defs>
                      <clipPath id="az-inner-clip">
                        <circle cx="80" cy="80" r="53"/>
                      </clipPath>
                    </defs>
                    <circle cx="80" cy="80" r="72" fill="none" stroke="#e5e7eb" stroke-width="1.5"/>
                    <circle cx="80" cy="80" r="54" fill="none" stroke="#f3f4f6" stroke-width="1"/>
                    <line v-for="i in 12" :key="'t'+i"
                      :x1="80 + 66*Math.sin((i-1)*30*Math.PI/180)"
                      :y1="80 - 66*Math.cos((i-1)*30*Math.PI/180)"
                      :x2="80 + 72*Math.sin((i-1)*30*Math.PI/180)"
                      :y2="80 - 72*Math.cos((i-1)*30*Math.PI/180)"
                      stroke="#9ca3af" stroke-width="1.5"/>
                    <template v-for="i in 36" :key="'m'+i">
                      <line v-if="(i-1) % 3 !== 0"
                        :x1="80 + 68*Math.sin((i-1)*10*Math.PI/180)"
                        :y1="80 - 68*Math.cos((i-1)*10*Math.PI/180)"
                        :x2="80 + 72*Math.sin((i-1)*10*Math.PI/180)"
                        :y2="80 - 72*Math.cos((i-1)*10*Math.PI/180)"
                        stroke="#d1d5db" stroke-width="0.8"/>
                    </template>
                    <text x="80" y="9"   text-anchor="middle" fill="#dc2626" font-size="11" font-weight="700">N</text>
                    <text x="153" y="84" text-anchor="middle" fill="#6b7280" font-size="10" font-weight="600">E</text>
                    <text x="80" y="155" text-anchor="middle" fill="#6b7280" font-size="10" font-weight="600">S</text>
                    <text x="7"  y="84"  text-anchor="middle" fill="#6b7280" font-size="10" font-weight="600">W</text>
                    <g :style="{ transform: `rotate(${panelHeadingDeg}deg)`, transformOrigin: '80px 80px', transition: 'transform 0.5s cubic-bezier(0.4,0,0.2,1)' }">
                      <rect x="72" y="42" width="16" height="46" rx="2" fill="#dce7f3" stroke="#3b82f6" stroke-width="1.5"/>
                      <line x1="74" y1="44" x2="74" y2="86" stroke="#3b82f6" stroke-width="2.5"/>
                      <line x1="72" y1="65" x2="88" y2="65" stroke="#93c5fd" stroke-width="0.8" opacity="0.6"/>
                      <line x1="80" y1="80" x2="80" y2="20" stroke="#1f2937" stroke-width="1.5"/>
                      <polygon points="80,12 76,22 84,22" fill="#1f2937"/>
                    </g>
                    <circle cx="80" cy="80" r="3" fill="#374151"/>
                    <g :style="{ transform: `rotate(${displayAzimuth}deg)`, transformOrigin: '80px 80px' }" clip-path="url(#az-inner-clip)">
                      <path d="M 80,80 L 53.5,34.1 A 53,53 0 0,1 106.5,34.1 Z" fill="#22c55e" opacity="0.22"/>
                      <line x1="80" y1="80" x2="80" y2="16" stroke="#f59e0b" stroke-width="2" stroke-dasharray="4 2"/>
                      <polygon points="80,8 75,20 85,20" fill="#f59e0b"/>
                    </g>
                  </svg>
                  <div class="az-legend">
                    <span class="az-legend-item"><span class="legend-dot" style="background:#f59e0b"></span>Beam Az</span>
                    <span class="az-legend-item"><span class="legend-rect"></span>ESA Panel</span>
                    <span class="az-legend-item"><span class="legend-mech-arrow"></span>Mech Dir</span>
                    <span class="az-legend-item"><span class="legend-roll"></span>Roll</span>
                  </div>
                </div>
              </div>

              <!-- RIGHT: ELEVATION + pitch viz -->
              <div class="antpos-col">
                <div class="antpos-kpi">
                  <span class="antpos-kpi-lbl">ELEVATION</span>
                  <span class="antpos-kpi-val">{{ displayElevationText }}</span>
                </div>
                <div class="antpos-pitch-view" v-if="pitchDeg != null">
                  <svg viewBox="0 0 200 200" class="esa-cross-view">
                    <!-- Ground reference line -->
                    <line x1="15" y1="140" x2="185" y2="140" stroke="#d1d5db" stroke-width="1.5" stroke-dasharray="4 4"/>
                    <!-- FOV cone: rotates with pitch (+pitch → left = negative SVG rotation) -->
                    <g :style="{ transform: `rotate(${-(pitchDeg ?? 0)}deg)`, transformOrigin: '100px 135px', transition: 'transform 0.5s cubic-bezier(0.4,0,0.2,1)' }">
                      <path d="M 100,135 L 35,22.4 A 130,130 0 0,1 165,22.4 Z" fill="#22c55e" opacity="0.10"/>
                      <path d="M 35,22.4 A 130,130 0 0,1 165,22.4" fill="none" stroke="#22c55e" stroke-width="1.5" stroke-dasharray="3 3" opacity="0.35"/>
                    </g>
                    <!-- Panel body + beam arrow: rotates with pitch, beam nested within -->
                    <g :style="{ transform: `rotate(${-(pitchDeg ?? 0)}deg)`, transformOrigin: '100px 135px', transition: 'transform 0.5s cubic-bezier(0.4,0,0.2,1)' }">
                      <rect x="40" y="131" width="120" height="8" rx="1" fill="#dce7f3" stroke="#3b82f6" stroke-width="1.5"/>
                      <line x1="45" y1="133" x2="155" y2="133" stroke="#93c5fd" stroke-width="1" opacity="0.3"/>
                      <!-- Beam arrow tilts off panel boresight by theta = 90 - elevation (acumon ant.c:506). Phi is azimuth (ant.c:507) and belongs to the compass view, not here. -->
                      <g :style="{ transform: `rotate(${90 - displayElevation}deg)`, transformOrigin: '100px 135px', transition: 'transform 0.5s cubic-bezier(0.4,0,0.2,1)' }">
                        <polygon points="100,135 88,20 112,20" fill="#f59e0b" opacity="0.12"/>
                        <line x1="100" y1="135" x2="100" y2="20" stroke="#f59e0b" stroke-width="2.5" stroke-linecap="round"/>
                        <polygon points="100,8 96,20 104,20" fill="#f59e0b"/>
                      </g>
                      <text x="100" y="154" fill="#9ca3af" font-size="7" font-family="monospace" font-weight="bold" text-anchor="middle" letter-spacing="0.5">COMtech ESA UT</text>
                    </g>
                    <!-- Pivot dot -->
                    <circle cx="100" cy="135" r="3" fill="#fff" stroke="#374151" stroke-width="1.5"/>
                  </svg>
                  <div class="el-legend">
                    <span class="az-legend-item"><span class="legend-dot" style="background:#f59e0b"></span>Beam El</span>
                    <span class="az-legend-item"><span class="legend-rect"></span>ESA Panel</span>
                    <span class="az-legend-item"><span class="legend-fov"></span>FOV</span>
                    <span class="az-legend-item"><span class="legend-ground"></span>Ground</span>
                  </div>
                  <div class="instr-metrics">
                    <div class="instr-metric">
                      <span class="instr-metric-lbl">PHI</span>
                      <span class="instr-metric-val" style="color:#f59e0b">{{ typeof pointingDat.phi === 'number' ? (pointingDat.phi >= 0 ? '+' : '') + pointingDat.phi.toFixed(1) + '°' : '—' }}</span>
                    </div>
                    <div class="instr-metric">
                      <span class="instr-metric-lbl">PITCH</span>
                      <span class="instr-metric-val" style="color:#3b82f6">{{ pitchDeg != null ? (pitchDeg >= 0 ? '+' : '') + pitchDeg.toFixed(1) + '°' : '—' }}</span>
                    </div>
                  </div>
                </div>
              </div>

            </div>

            <!-- Pointing-readiness criteria — shows clearly what blocks AUTO pointing -->
            <div v-if="readiness.criteria && readiness.criteria.length" class="readiness-row">
              <div v-for="c in readiness.criteria" :key="c.key" class="readiness-item" :title="c.reason">
                <span class="readiness-dot" :class="c.ok ? 'rd-ok' : 'rd-bad'"></span>
                <span class="readiness-lbl">{{ c.label }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- TARGET SATELLITE -->
        <div class="card">
          <div class="card-header">
            <span><AppIcon name="satellite" :size="16" /> Target Satellite</span>
          </div>
          <div v-if="tleWarning" class="tle-card-warning">⚠️ {{ tleWarning }}</div>
          <div v-if="!satVisible" class="sat-not-visible-banner">
            Satellite not visible or out of range
            <span v-if="satElevation != null"> (elevation {{ satElevation.toFixed(1) }}°)</span>
          </div>
          <div class="card-body">
            <template v-if="activeSat.satName">
              <div class="info-row">
                <span class="label">Name</span>
                <span class="value">{{ activeSat.satName }}</span>
              </div>
              <div class="info-row" v-if="activeSat.satLong">
                <span class="label">Position</span>
                <span class="value">{{ activeSat.satLong }}° {{ activeSat.satLongEW }}</span>
              </div>
              <div class="info-row" v-if="activeSat.satOperator">
                <span class="label">Operator</span>
                <span class="value">{{ activeSat.satOperator }}</span>
              </div>
              <div class="info-row" v-if="activeSat.satNoradId">
                <span class="label">NORAD ID</span>
                <span class="value">{{ activeSat.satNoradId }}</span>
              </div>
              <div class="info-row" v-if="activeSat.satRxPol || activeSat.satTxPol">
                <span class="label">Polarization</span>
                <span class="value">RX: {{ activeSat.satRxPol }} / TX: {{ activeSat.satTxPol }}</span>
              </div>
              <div class="info-row" v-if="activeSat.satBandMhz">
                <span class="label">Band</span>
                <span class="value">{{ activeSat.satBandMhz }} MHz</span>
              </div>
            </template>
            <div v-else class="no-data">No satellite configured</div>
          </div>
        </div>

      </div>

      <!-- ROW 2: Technical reference -->
      <div class="row row-2">

        <!-- COMPASS -->
        <div class="card card-compass">
          <div class="card-header">
            <span><AppIcon name="compass" :size="16" /> Compass</span>
            <div class="pill-group">
              <button class="ui-pill ui-pill-btn"
                :class="!manualHeadingMode ? 'ui-pill-blue' : 'ui-pill-inactive'"
                @click="setHeadingMode('auto')">
                AUTO
              </button>
              <button class="ui-pill ui-pill-btn"
                :class="manualHeadingMode ? 'ui-pill-red' : 'ui-pill-inactive'"
                @click="setHeadingMode('manual')"
                title="Fix heading at 0° N — physically align antenna to True North">
                MANUAL
              </button>
              <span class="pill-sep"></span>
              <button class="ui-pill ui-pill-btn"
                :class="compassMode === 'true_north' ? 'ui-pill-blue' : 'ui-pill-inactive'"
                @click="setCompassMode('true_north')">
                TRUE NORTH
              </button>
              <button class="ui-pill ui-pill-btn"
                :class="compassMode === 'magnetic' ? 'ui-pill-yellow' : 'ui-pill-inactive'"
                @click="setCompassMode('magnetic')">
                MAGNETIC
              </button>
            </div>
          </div>
          <div class="card-body compass-visual-body">
            <template v-if="compassHeading != null && (manualHeadingMode || compassMode === 'magnetic' || compass.available)">
              <svg viewBox="0 0 200 200" class="compass-gauge">
                <g :style="{ transform: `rotate(${compassRotationDeg}deg)`, transformOrigin: '100px 100px', transition: 'transform 0.5s cubic-bezier(0.4, 0, 0.2, 1)' }">
                  <circle cx="100" cy="100" r="88" fill="none" stroke="#dee2e6" stroke-width="1" />
                  <circle cx="100" cy="100" r="70" fill="none" stroke="#f1f3f5" stroke-width="0.5" />
                  <g v-for="deg in 72" :key="'tick-' + deg">
                    <line v-if="(deg - 1) * 5 % 10 === 0" :x1="100" :y1="14" :x2="100" :y2="24" stroke="#374151"
                      stroke-width="1.5" :transform="`rotate(${(deg - 1) * 5}, 100, 100)`" />
                    <line v-else :x1="100" :y1="16" :x2="100" :y2="22" stroke="#9ca3af" stroke-width="0.7"
                      :transform="`rotate(${(deg - 1) * 5}, 100, 100)`" />
                  </g>
                  <text v-for="deg in [30, 60, 90, 120, 150, 180, 210, 240, 270, 300, 330]" :key="'lbl-' + deg"
                    :transform="`rotate(${deg}, 100, 100)`" x="100" y="34" text-anchor="middle" fill="#9ca3af"
                    font-size="8">{{ deg }}</text>
                  <text x="100" y="44" text-anchor="middle" fill="#dc2626" font-size="14" font-weight="bold">N</text>
                  <text x="160" y="104" text-anchor="middle" fill="#6b7280" font-size="12" font-weight="600">E</text>
                  <text x="100" y="164" text-anchor="middle" fill="#6b7280" font-size="12" font-weight="600">S</text>
                  <text x="40" y="104" text-anchor="middle" fill="#6b7280" font-size="12" font-weight="600">W</text>
                  <line x1="100" y1="12" x2="100" y2="24" stroke="#dc2626" stroke-width="2.5" stroke-linecap="round" />
                </g>
                <polygon points="100,10 96,2 104,2" fill="#3b82f6" />
                <circle cx="100" cy="100" r="3" fill="#9ca3af" />
                <line x1="95" y1="100" x2="105" y2="100" stroke="#9ca3af" stroke-width="0.5" />
                <line x1="100" y1="95" x2="100" y2="105" stroke="#9ca3af" stroke-width="0.5" />
              </svg>
              <div class="compass-readout">
                <span class="compass-heading">{{ compassHeading.toFixed(0) }}° {{ compassCardinal }}</span>
                <span v-if="!manualHeadingMode && compassFieldUt != null" class="compass-field-ut">
                  {{ compassFieldUt }} µT
                </span>
              </div>
            </template>
            <div v-else-if="compass.mag_heading == null" class="no-data">Compass unavailable — calibrate first</div>
            <div v-else class="no-data">Heading unavailable — waiting for sensor data</div>
          </div>
        </div>

        <!-- POINTING DETAIL -->
        <div class="card">
          <div class="card-header" :class="{ 'card-header-manual': currentMode === 'manual_pointing' }">
            <span><AppIcon name="pointing" :size="16" /> Pointing Detail</span>
            <span v-if="manualError" class="manual-error-label">{{ manualError }}</span>
            <div v-if="isManualControlVisible" class="pill-group">
              <button class="ui-pill ui-pill-btn"
                :class="[currentMode !== 'manual_pointing' ? 'ui-pill-gray' : 'ui-pill-inactive', { 'ui-pill-busy': transitioning && expectedMode === 'auto' }]"
                :disabled="toggling || transitioning"
                @click="currentMode === 'manual_pointing' && toggleManual()">
                <span v-if="transitioning && expectedMode === 'auto'" class="btn-spinner"></span>
                <span v-else>AUTO</span>
              </button>
              <button class="ui-pill ui-pill-btn"
                :class="[currentMode === 'manual_pointing' ? 'ui-pill-blue' : 'ui-pill-inactive', { 'ui-pill-busy': transitioning && expectedMode === 'manual_pointing' }]"
                :disabled="toggling || transitioning"
                @click="currentMode !== 'manual_pointing' && toggleManual()">
                <span v-if="transitioning && expectedMode === 'manual_pointing'" class="btn-spinner"></span>
                <span v-else>MANUAL</span>
              </button>
            </div>
          </div>
          <div v-if="currentMode === 'manual_pointing'" class="card-body manual-body">
            <div class="manual-arrows">
              <div class="manual-row">
                <button class="arrow-btn" @click="nudge(0, nudgeIncrement)" title="+Elevation">▲</button>
              </div>
              <div class="manual-row">
                <button class="arrow-btn" @click="nudge(-nudgeIncrement, 0)" title="-Azimuth">◄</button>
                <div class="manual-center-dot"></div>
                <button class="arrow-btn" @click="nudge(nudgeIncrement, 0)" title="+Azimuth">►</button>
              </div>
              <div class="manual-row">
                <button class="arrow-btn" @click="nudge(0, -nudgeIncrement)" title="-Elevation">▼</button>
              </div>
            </div>
            <div class="manual-goto">
              <div class="manual-goto-row">
                <label class="goto-label">Step</label>
                <input class="goto-input goto-input-step" type="number" step="0.1" min="0.1" v-model.number="nudgeIncrement" />
                <label class="goto-label">Az</label>
                <input class="goto-input" type="number" step="0.1" v-model.number="gotoAz" @keyup.enter="gotoPosition" />
                <label class="goto-label">El</label>
                <input class="goto-input" type="number" step="0.1" v-model.number="gotoEl" @keyup.enter="gotoPosition" />
                <button class="goto-btn" @click="gotoPosition">Go</button>
              </div>
            </div>
            <div class="manual-detail">
              <div class="info-row" v-if="pointingDat.phi != null">
                <span class="label">Steering Phi</span>
                <span class="value mono">{{ pointingDat.phi }}°</span>
              </div>
              <div class="info-row" v-if="pointingDat.theta != null">
                <span class="label">Steering Theta</span>
                <span class="value mono">{{ pointingDat.theta }}°</span>
              </div>
              <div class="info-row">
                <span class="label">Pol Skew</span>
                <span class="value mono">{{ formatAngle(pointingDat.pol_skew, 1) }}</span>
              </div>
            </div>
          </div>
          <div v-else class="card-body">
            <div class="info-row" v-if="pointingDat.type">
              <span class="label">Snapshot</span>
              <span class="snap-badge" :class="'snap-' + pointingDat.type">{{ pointingDat.type.toUpperCase() }}</span>
            </div>
            <div class="info-row" v-if="pointingDat.cycle != null">
              <span class="label">Cycle</span>
              <span class="value">{{ pointingDat.cycle }}</span>
            </div>
            <div class="info-row">
              <span class="label">Azimuth</span>
              <span class="value mono">{{ formatAngle(earthFrameAz, 3) }}</span>
            </div>
            <div class="info-row">
              <span class="label">Elevation</span>
              <span class="value mono">{{ formatAngle(pointingDat.elevation, 3) }}</span>
            </div>
            <div class="info-row" v-if="pointingDat.offset_az != null">
              <span class="label">Offset Azimuth</span>
              <span class="value mono">{{ formatAngle(pointingDat.offset_az, 3) }}</span>
            </div>
            <div class="info-row" v-if="pointingDat.offset_el != null">
              <span class="label">Offset Elevation</span>
              <span class="value mono">{{ formatAngle(pointingDat.offset_el, 3) }}</span>
            </div>
            <div class="info-row">
              <span class="label">Pol Skew</span>
              <span class="value mono">{{ formatAngle(pointingDat.pol_skew, 1) }}</span>
            </div>
            <div class="info-row" v-if="pointingDat.phi != null">
              <span class="label">Steering Phi</span>
              <span class="value mono">{{ pointingDat.phi }}°</span>
            </div>
            <div class="info-row" v-if="pointingDat.theta != null">
              <span class="label">Steering Theta</span>
              <span class="value mono">{{ pointingDat.theta }}°</span>
            </div>
          </div>
        </div>

        <!-- SYSTEM + SENSORS -->
        <div class="card">
          <div class="card-header">
            <span><AppIcon name="device" :size="16" /> System</span>
          </div>
          <div class="card-body">
            <div class="info-row">
              <span class="label">Name</span>
              <span class="value">{{ deviceInfo.name }}</span>
            </div>
            <div class="info-row">
              <span class="label">Version</span>
              <span class="value">{{ deviceInfo.version }}</span>
            </div>
            <div class="info-row">
              <span class="label">Uptime</span>
              <span class="value">{{ deviceInfo.uptime }}</span>
            </div>
            <div class="info-row">
              <span class="label">CPU</span>
              <span class="value">{{ deviceInfo.cpu_pct ?? '—' }}%</span>
            </div>
            <div class="info-row">
              <span class="label">Memory</span>
              <span class="value">{{ deviceInfo.memory_pct ?? '—' }}%</span>
            </div>
            <div class="info-row">
              <span class="label">Disk</span>
              <span class="value">{{ deviceInfo.disk_pct ?? '—' }}%</span>
            </div>
            <div class="info-row">
              <span class="label">Temperature</span>
              <span class="value">{{ tempPres.temperature?.toFixed(1) ?? '—' }}°C</span>
            </div>
            <div class="info-row">
              <span class="label">Pressure</span>
              <span class="value">{{ tempPres.pressure?.toFixed(0) ?? '—' }} Pa</span>
            </div>
            <div class="info-row">
              <span class="label">Log RAM</span>
              <span v-if="'log2ram_ok' in deviceInfo" class="ui-pill"
                :class="deviceInfo.log2ram_ok ? (deviceInfo.log2ram_pct >= 85 ? 'ui-pill-yellow' : 'ui-pill-green') : 'ui-pill-red'">
                {{ !deviceInfo.log2ram_mounted ? 'NOT MOUNTED'
                  : deviceInfo.log2ram_service !== 'active' ? 'SVC DOWN'
                  : (deviceInfo.log2ram_pct ?? '?') + '%' }}
              </span>
              <span v-else class="ui-pill ui-pill-gray">—</span>
            </div>
            <div class="info-row">
              <span class="label">Logrotate</span>
              <span v-if="'logrotate_ok' in deviceInfo" class="ui-pill"
                :class="deviceInfo.logrotate_ok ? 'ui-pill-green' : (deviceInfo.logrotate_age_h != null && deviceInfo.logrotate_cron ? 'ui-pill-yellow' : 'ui-pill-red')">
                {{ !deviceInfo.logrotate_cron ? 'NO CRON'
                  : deviceInfo.logrotate_age_h == null ? 'NEVER RAN'
                  : deviceInfo.logrotate_large?.length ? deviceInfo.logrotate_large[0].name + ' ' + deviceInfo.logrotate_large[0].mb + 'MB'
                  : deviceInfo.logrotate_ok ? 'OK'
                  : deviceInfo.logrotate_age_h + 'h ago' }}
              </span>
              <span v-else class="ui-pill ui-pill-gray">—</span>
            </div>
          </div>
        </div>

      </div>

      <!-- ROW 3: Location -->
      <div class="row row-map">
        <div class="card card-map">
          <div class="card-header">
            <span><AppIcon name="gps" :size="16" /> Location</span>
            <span class="location-header-right" v-if="gps.lat">
              <span class="ui-pill ui-pill-green">GPS</span>
              <span class="location-coords">{{ gps.lat?.toFixed(6) }}°, {{ gps.lon?.toFixed(6) }}° · Sats: {{ gps.satellites }} · Alt: {{ gps.altitude }}m</span>
            </span>
            <span class="location-header-right" v-else-if="manualLat != null">
              <span class="ui-pill ui-pill-blue">MANUAL</span>
              <span class="location-coords">{{ locationConfig.latDeg }}°{{ locationConfig.latMin }}'{{ locationConfig.latSec }}" {{ locationConfig.latNS }},
              {{ locationConfig.lonDeg }}°{{ locationConfig.lonMin }}'{{ locationConfig.lonSec }}" {{ locationConfig.lonEW }}</span>
            </span>
            <span class="location-header-right" v-else-if="isSearchingGps">
              <span class="ui-pill ui-pill-yellow">SEARCHING</span>
            </span>
            <span class="location-header-right" v-else>
              <span class="ui-pill ui-pill-gray">NO GPS</span>
            </span>
          </div>
          <div class="card-body map-body">
            <div ref="mapContainer" :class="['map-container', { 'map-searching': isSearchingGps }]"></div>
            <div v-if="isSearchingGps" class="map-overlay">
              <div class="map-spinner"></div>
              <div class="map-spinner-text">Searching for GPS fix...</div>
            </div>
          </div>
        </div>
      </div>

    </template>
  </div>
</template>

<script>
import axios from 'axios'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import AppIcon from './AppIcon.vue'
import { useAcuStore } from '../stores/acu'

import markerIcon2x from 'leaflet/dist/images/marker-icon-2x.png'
import markerIcon from 'leaflet/dist/images/marker-icon.png'
import markerShadow from 'leaflet/dist/images/marker-shadow.png'

delete L.Icon.Default.prototype._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: markerIcon2x,
  iconUrl: markerIcon,
  shadowUrl: markerShadow
})

const API_URL = import.meta.env.VITE_API_URL || ''

export default {
  name: 'Overview',
  components: { AppIcon },
  setup() {
    const store = useAcuStore()
    return { store }
  },
  data() {
    return {
      loading: true,
      toggling: false,
      transitioning: false,
      expectedMode: null,
      manualError: '',
      gotoAz: 0,
      gotoEl: 0,
      nudgeIncrement: 0.5,
      activeSat: {},
      pointingDat: {},
      readiness: {},
      modem: {},
      tempPres: {},
      compass: {},
      compassMode: localStorage.getItem('compassMode') || 'true_north',
      manualHeadingMode: localStorage.getItem('manualHeadingMode') === 'true',
      compassRotationDeg: 0,
      panelHeadingDeg: 0,
      gps: {},
      locationConfig: {},
      deviceInfo: {},
      map: null,
      marker: null,
      fastInterval: null,
      slowInterval: null,
      compassInterval: null,
      txMuted: false,
      txMuteToggling: false,
    }
  },
  watch: {
    'store.status.tracking'(mode) {
      if (!this.transitioning || this.expectedMode === null) return
      const m = (mode || '').toLowerCase()
      const reached = this.expectedMode === 'manual_pointing'
        ? m === 'manual_pointing'
        : m !== 'manual_pointing'
      if (reached) { this.transitioning = false; this.expectedMode = null }
    },
    compassHeading(newVal) {
      if (newVal == null) return
      const target = -newVal
      let delta = target - this.compassRotationDeg
      delta = ((delta + 180) % 360 + 360) % 360 - 180
      this.compassRotationDeg += delta
    },
    panelHeading(newVal) {
      if (newVal == null) return
      const target = newVal
      let delta = target - this.panelHeadingDeg
      delta = ((delta + 180) % 360 + 360) % 360 - 180
      this.panelHeadingDeg += delta
    }
  },
  computed: {
    // --- Lock / Mode ---
    lockClass() {
      const lock = this.modem.demod_lock
      if (lock === true)  return 'lock-locked'
      if (lock === false) return 'lock-unlocked'
      return 'lock-unknown'
    },
    lockText() {
      const lock = this.modem.demod_lock
      if (lock === true)  return 'LOCKED'
      if (lock === false) return 'UNLOCKED'
      return 'NO DATA'
    },
    tleWarning() {
      return this.store.tleWarning
    },
    modeText() {
      const m = (this.store.status.tracking || '').toUpperCase()
      const labels = {
        'AUTO_POINTING':   'SCANNING',
        'TRACKING':        'TRACKING',
        'MANUAL_POINTING': 'MANUAL',
        'IDLE':            'IDLE',
        'READY':           'READY',
        'FAULT':           'FAULT',
        'CALIBRATING':     'CALIBRATING',
        'INIT':            'INIT',
      }
      return labels[m] || m || '—'
    },
    modeClass() {
      const map = {
        'tracking':        'ui-pill-green',
        'auto_pointing':   'ui-pill-blue',
        'manual_pointing': 'ui-pill-blue',
        'ready':           'ui-pill-yellow',
        'idle':            'ui-pill-gray',
        'fault':           'ui-pill-red',
        'calibrating':     'ui-pill-purple',
        'init':            'ui-pill-gray',
      }
      return map[(this.store.status.tracking || '').toLowerCase()] || 'ui-pill-gray'
    },

    // --- RF bar ---
    rfBarPct() {
      if (this.modem.rf_level == null) return 0
      // Map -90 dBm (0%) to -20 dBm (100%)
      return Math.max(0, Math.min(100, (this.modem.rf_level + 90) / 70 * 100))
    },
    rfBarColor() {
      if (this.modem.rf_level == null) return '#9ca3af'
      if (this.modem.rf_level >= -50) return '#22c55e'
      if (this.modem.rf_level >= -65) return '#f59e0b'
      return '#ef4444'
    },

    // --- Compass ---
    compassHeading() {
      if (this.manualHeadingMode) return 0
      if (this.compassMode === 'magnetic') {
        return typeof this.compass.mag_heading === 'number' ? this.compass.mag_heading : null
      }
      return typeof this.compass.heading === 'number' ? this.compass.heading : null
    },
    compassCardinal() {
      if (this.compassHeading == null) return ''
      const dirs = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW']
      return dirs[Math.round(this.compassHeading / 45) % 8]
    },
    compassFieldUt() {
      return typeof this.compass.field_ut === 'number' ? this.compass.field_ut : null
    },

    // --- Panel orientation (from compass/IMU) ---
    panelHeading() {
      return this.compassHeadingTrueNorth ?? 0
    },
    // True-north heading used for Earth-frame azimuth conversion (always true north,
    // independent of the user's magnetic/true compass display toggle).
    compassHeadingTrueNorth() {
      if (this.manualHeadingMode) return 0
      return typeof this.compass.heading === 'number' ? this.compass.heading : null
    },
    // pitch/roll arrive in radians from acumon's orientation file.
    pitchDeg() {
      const p = this.compass.pitch
      if (p == null) return null
      return Math.round((p * 180 / Math.PI) * 10) / 10
    },
    rollDeg() {
      const r = this.compass.roll
      if (r == null) return null
      return Math.round((r * 180 / Math.PI) * 10) / 10
    },
    pitchVizArcPath() {
      const p = this.pitchDeg
      if (p == null || Math.abs(p) < 1) return ''
      const absp = Math.abs(p)
      const r = 42, cx = 35, cy = 120
      const angle = Math.min(absp, 89) * Math.PI / 180
      const ex = cx + r * Math.cos(angle)
      const ey = cy - r * Math.sin(angle)
      return `M ${cx + r} ${cy} A ${r} ${r} 0 0 0 ${ex.toFixed(1)} ${ey.toFixed(1)}`
    },
    elevTrajectoryArcPath() {
      const el = typeof this.displayElevation === 'number' ? this.displayElevation : 0
      if (el < 1) return ''
      const r = 145, cx = 35, cy = 120
      const angle = Math.min(el, 90) * Math.PI / 180
      const ex = cx + r * Math.cos(angle)
      const ey = cy - r * Math.sin(angle)
      return `M ${cx + r} ${cy} A ${r} ${r} 0 0 0 ${ex.toFixed(1)} ${ey.toFixed(1)}`
    },
    elevArrowData() {
      const el = typeof this.displayElevation === 'number' ? this.displayElevation : 0
      if (el < 1) return null
      const rad = Math.min(el, 90) * Math.PI / 180
      const cx = 35, cy = 120, len = 130
      const ex = cx + len * Math.cos(rad)
      const ey = cy - len * Math.sin(rad)
      const dx = Math.cos(rad), dy = -Math.sin(rad)
      const nx = Math.sin(rad), ny = Math.cos(rad)
      const hL = 10, hW = 5
      const bx = ex - dx * hL, by = ey - dy * hL
      return {
        x1: cx, y1: cy,
        x2: ex.toFixed(1), y2: ey.toFixed(1),
        head: `${ex.toFixed(1)},${ey.toFixed(1)} ${(bx + nx * hW).toFixed(1)},${(by + ny * hW).toFixed(1)} ${(bx - nx * hW).toFixed(1)},${(by - ny * hW).toFixed(1)}`
      }
    },

    // --- Pointing (Earth-frame az = panel_az + heading; Earth-frame el = commanded el) ---
    displayElevation() {
      return typeof this.pointingDat.elevation === 'number' ? this.pointingDat.elevation : 0
    },
    earthFrameAz() {
      const az = this.pointingDat.azimuth
      const h = this.compassHeadingTrueNorth
      if (typeof az !== 'number') return 0
      if (h == null) return az
      return ((az + h) % 360 + 360) % 360
    },
    displayAzimuth() {
      if (this.currentMode === 'manual_pointing') {
        const az = this.pointingDat.azimuth
        return typeof az === 'number' ? az : 0
      }
      return this.earthFrameAz
    },
    displayElevationText() {
      return this.formatAngle(this.displayElevation, 1)
    },

    displayAzimuthText() {
      if (this.currentMode === 'manual_pointing') {
        const az = this.pointingDat.azimuth
        return this.formatAngle(typeof az === 'number' ? az : 0, 1)
      }
      return this.formatAngle(this.earthFrameAz, 1)
    },

    // --- Manual pointing ---
    currentMode() {
      return (this.store.status.tracking || '').toLowerCase()
    },
    isManualControlVisible() {
      return ['ready', 'auto_pointing', 'tracking', 'manual_pointing'].includes(this.currentMode)
    },

    // --- Satellite visibility ---
    satLonDeg() {
      const lon = this.activeSat.satLong
      if (lon == null) return null
      return this.activeSat.satLongEW === 'W' ? -Math.abs(lon) : Math.abs(lon)
    },
    satElevation() {
      const lat = this.gps.lat || this.manualLat
      const lon = this.gps.lon || this.manualLon
      if (lat == null || lon == null || this.satLonDeg == null) return null
      const lat_r  = lat * Math.PI / 180
      const dlon_r = (this.satLonDeg - lon) * Math.PI / 180
      const cos_el = Math.cos(lat_r) * Math.cos(dlon_r)
      const num    = cos_el - 0.15127
      const den    = Math.sqrt(Math.max(0, 1 - cos_el * cos_el))
      if (den < 1e-9) return 0
      return Math.atan2(num, den) * 180 / Math.PI
    },
    satVisible() {
      if (this.pointingDat.type === 'not_visible') return false
      return this.satElevation == null || this.satElevation > 0
    },

    // --- Location ---
    isManualMode() {
      return this.store.status.facts?.gps_override_enabled === true
    },
    isSearchingGps() {
      return !this.isManualMode && !this.gps.lat
    },
    manualLat() {
      const c = this.locationConfig
      if (!c.latDeg) return null
      const deg = parseFloat(c.latDeg) + parseFloat(c.latMin || 0) / 60 + parseFloat(c.latSec || 0) / 3600
      return c.latNS === 'South' ? -deg : deg
    },
    manualLon() {
      const c = this.locationConfig
      if (!c.lonDeg) return null
      const deg = parseFloat(c.lonDeg) + parseFloat(c.lonMin || 0) / 60 + parseFloat(c.lonSec || 0) / 3600
      return c.lonEW === 'West' ? -deg : deg
    }
  },
  mounted() {
    this.loadFast()
    this.loadSlow()
    this.refreshCompass()
    this.fastInterval    = setInterval(this.loadFast, 1000)
    this.slowInterval    = setInterval(this.loadSlow, 5000)
    this.compassInterval = setInterval(this.refreshCompass, 500)
  },
  beforeUnmount() {
    clearInterval(this.fastInterval)
    clearInterval(this.slowInterval)
    clearInterval(this.compassInterval)
    if (this.map) { this.map.remove(); this.map = null }
  },
  methods: {
    async toggleManual() {
      if (this.toggling || this.transitioning) return
      const enteringManual = this.currentMode !== 'manual_pointing'
      this.toggling = true
      this.transitioning = true
      this.expectedMode = enteringManual ? 'manual_pointing' : 'auto'
      setTimeout(() => { this.transitioning = false; this.expectedMode = null }, 8000)
      if (enteringManual) {
        this.gotoAz = parseFloat(this.earthFrameAz.toFixed(1))
        this.gotoEl = typeof this.pointingDat.elevation === 'number' ? parseFloat(this.pointingDat.elevation.toFixed(1)) : 0
      }
      try {
        this.manualError = ''
        if (!enteringManual) {
          await axios.post(`${API_URL}/api/actions/manual-exit`)
        } else {
          await axios.post(`${API_URL}/api/actions/manual-mode`)
        }
      } catch (e) {
        this.manualError = e.response?.data?.error || 'Command failed'
        this.transitioning = false
        this.expectedMode = null
      } finally {
        this.toggling = false
      }
    },
    async nudge(daz, del) {
      try {
        await axios.post(`${API_URL}/api/actions/manual-nudge`, { az: daz, el: del })
        this.gotoAz = parseFloat((this.gotoAz + daz).toFixed(1))
        this.gotoEl = parseFloat((this.gotoEl + del).toFixed(1))
      } catch (e) {
        console.error('Nudge failed:', e)
      }
    },
    async toggleTxMute() {
      if (this.txMuteToggling) return
      this.txMuteToggling = true
      try {
        await axios.post(`${API_URL}/api/actions/tx-mute`)
        this.txMuted = !this.txMuted
      } catch (e) {
        console.error('TX mute toggle failed:', e)
      } finally {
        this.txMuteToggling = false
      }
    },
    async gotoPosition() {
      const h = this.compassHeadingTrueNorth
      const panelAz = h != null ? ((this.gotoAz - h) % 360 + 360) % 360 : this.gotoAz
      try {
        await axios.post(`${API_URL}/api/actions/manual-goto`, { az: panelAz, el: this.gotoEl })
      } catch (e) {
        console.error('Goto failed:', e)
      }
    },
    setCompassMode(mode) {
      this.compassMode = mode
      localStorage.setItem('compassMode', mode)
    },
    setHeadingMode(mode) {
      this.manualHeadingMode = mode === 'manual'
      localStorage.setItem('manualHeadingMode', this.manualHeadingMode)
    },
    formatAngle(value, digits = 1) {
      return typeof value === 'number' ? `${value.toFixed(digits)}°` : '—'
    },
    async loadFast() {
      try {
        const res = await axios.get(`${API_URL}/api/telemetry/overview`)
        this.pointingDat = res.data.pointing_dat || {}
        this.modem       = res.data.modem        || {}
        this.loading = false
        axios.get(`${API_URL}/api/readiness`)
          .then(r => { this.readiness = r.data || {} })
          .catch(() => {})
      } catch (e) {
        console.error('Error loading fast telemetry:', e)
        this.loading = false
      }
    },
    async loadSlow() {
      try {
        const [tempRes, gpsRes, deviceRes, activeSatRes, locationRes] = await Promise.all([
          axios.get(`${API_URL}/api/telemetry/temp-pres`).catch(() => ({ data: {} })),
          axios.get(`${API_URL}/api/telemetry/gps`).catch(() => ({ data: {} })),
          axios.get(`${API_URL}/api/system/device-info`).catch(() => ({ data: {} })),
          axios.get(`${API_URL}/api/satellites/active`).catch(() => ({ data: {} })),
          axios.get(`${API_URL}/api/config/location`).catch(() => ({ data: {} })),
        ])
        this.tempPres       = tempRes.data           || {}
        this.gps            = gpsRes.data            || {}
        this.deviceInfo     = deviceRes.data         || {}
        this.activeSat      = activeSatRes.data      || {}
        this.locationConfig = locationRes.data?.data || {}

        await this.$nextTick()
        if (!this.map) this.loadMap()
        else           this.updateMap()
      } catch (e) {
        console.error('Error loading slow telemetry:', e)
      }
    },
    async refreshCompass() {
      try {
        const res = await axios.get(`${API_URL}/api/telemetry/compass`)
        this.compass = res.data || {}
      } catch {
        // keep last known value on error
      }
    },
    loadMap() {
      if (!this.$refs.mapContainer) return
      const lat = this.gps.lat || this.manualLat
      const lon = this.gps.lon || this.manualLon
      const centerLat = lat || 20
      const centerLon = lon || 0
      const zoom = lat ? 8 : 2
      const isGps = !!this.gps.lat
      const popupContent = isGps
        ? `<b>ACU Position (GPS)</b><br>Lat: ${this.gps.lat.toFixed(6)}°<br>Lon: ${this.gps.lon.toFixed(6)}°<br>Alt: ${this.gps.altitude || 0}m<br>Satellites: ${this.gps.satellites || 0}<br>Quality: ${this.gps.quality || 0}`
        : `<b>ACU Position (Manual)</b><br>Lat: ${lat?.toFixed(6)}°<br>Lon: ${lon?.toFixed(6)}°<br>Alt: ${this.locationConfig.altitude || 0}m`

      this.map = L.map(this.$refs.mapContainer, {
        zoomControl: true, attributionControl: false
      }).setView([centerLat, centerLon], zoom)

      L.tileLayer('/api/tiles/{z}/{x}/{y}.png', { maxZoom: 8 }).addTo(this.map)

      const antennaIcon = L.divIcon({
        className: '',
        html: `<svg viewBox="-14 -14 36 42" width="40" height="46">
          <line x1="-2" y1="18" x2="-7" y2="26" stroke="#374151" stroke-width="2.2" stroke-linecap="round"/>
          <line x1="2"  y1="18" x2="7"  y2="26" stroke="#374151" stroke-width="2.2" stroke-linecap="round"/>
          <line x1="-8" y1="26" x2="8"  y2="26" stroke="#374151" stroke-width="2.2" stroke-linecap="round"/>
          <line x1="0" y1="8" x2="0" y2="18" stroke="#374151" stroke-width="2.2" stroke-linecap="round"/>
          <path d="M-9,2 Q0,14 9,2" fill="none" stroke="#1e3a5f" stroke-width="2.4" stroke-linecap="round"/>
          <line x1="-9" y1="2" x2="9" y2="2" stroke="#1e3a5f" stroke-width="1.4" stroke-linecap="round" opacity="0.4"/>
          <line x1="0" y1="8" x2="7" y2="-2" stroke="#374151" stroke-width="1.6" stroke-linecap="round"/>
          <path d="M10,-5 Q13,-1 10,4"  fill="none" stroke="#42a5f5" stroke-width="1.8" stroke-linecap="round" opacity="0.9"/>
          <path d="M13,-8 Q17,-1 13,6" fill="none" stroke="#42a5f5" stroke-width="1.6" stroke-linecap="round" opacity="0.55"/>
          <circle cx="7" cy="-2" r="2" fill="#42a5f5"/>
        </svg>`,
        iconSize: [40, 46],
        iconAnchor: [20, 46]
      })

      if (lat && lon) {
        this.marker = L.marker([lat, lon], { icon: antennaIcon }).addTo(this.map)
        this.marker.bindPopup(popupContent)
      }

      setTimeout(() => this.map.invalidateSize(), 200)
    },
    updateMap() {
      if (!this.map || !this.marker || !this.gps.lat || !this.gps.lon) return
      const popupContent = `<b>ACU Position</b><br>Lat: ${this.gps.lat.toFixed(6)}°<br>Lon: ${this.gps.lon.toFixed(6)}°<br>Alt: ${this.gps.altitude || 0}m<br>Satellites: ${this.gps.satellites || 0}<br>Quality: ${this.gps.quality || 0}`
      this.marker.setLatLng([this.gps.lat, this.gps.lon])
      this.marker.setPopupContent(popupContent)
    }
  }
}
</script>

<style scoped>
.overview {
  padding: 20px;
  background: #f5f5f5;
  min-height: 100%;
}

.loading {
  text-align: center;
  padding: 40px;
  color: #888;
}

/* ── Grid rows ── */
.row {
  display: grid;
  gap: 15px;
  margin-bottom: 15px;
}

.row-1 {
  grid-template-columns: 1.1fr 1.4fr 1fr;
}

.row-2 {
  grid-template-columns: 1fr 1.2fr 1fr;
}

.instr-metrics {
  margin-top: 8px;
  display: flex;
  gap: 20px;
}
.instr-metric {
  display: flex;
  flex-direction: column;
  align-items: center;
}
.instr-metric-lbl {
  font-size: 9px;
  font-weight: 700;
  color: #9ca3af;
  letter-spacing: 0.06em;
}
.instr-metric-val {
  font-family: monospace;
  font-size: 14px;
  font-weight: 700;
}

.row-map {
  grid-template-columns: 1fr;
}

/* ── Card base ── */
.card {
  background: #fff;
  border-radius: 4px;
  overflow: hidden;
  border: 1px solid #e0e0e0;
  box-shadow: 0 2px 4px rgba(0,0,0,0.08);
}

.card-header {
  background: #1e3a5f;
  color: #fff;
  padding: 10px 15px;
  font-size: 13px;
  font-weight: 600;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
}

.card-body {
  padding: 15px;
}

.tle-card-warning {
  background: #fff3e0;
  color: #e65100;
  padding: 6px 15px;
  font-size: 11px;
  border-bottom: 1px solid #ffcc80;
}

.sat-not-visible-banner {
  background: #fef2f2;
  color: #b91c1c;
  padding: 6px 15px;
  font-size: 11px;
  font-weight: 600;
  border-bottom: 1px solid #fecaca;
}

/* ── Info rows (shared) ── */
.info-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 6px 0;
  border-bottom: 1px solid #eee;
  font-size: 12px;
}
.info-row:last-child { border-bottom: none; }

.label { color: #666; }
.value { color: #333; font-weight: 500; }
.value.small { font-size: 10px; color: #999; }
.value.mono { font-family: monospace; }
.mono { font-family: monospace; }

.no-data { color: #999; font-size: 12px; font-style: italic; padding: 10px 0; }

/* ── Signal & Link card ── */
.signal-body {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.lock-mode-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.lock-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 14px;
  border-radius: 6px;
  flex: 1;
}
.lock-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  flex-shrink: 0;
}
.lock-text {
  font-size: 15px;
  font-weight: 700;
  letter-spacing: 0.05em;
}
.lock-locked   { background: #f0fdf4; }
.lock-locked .lock-dot  { background: #22c55e; box-shadow: 0 0 6px #22c55e99; }
.lock-locked .lock-text { color: #15803d; }
.lock-unlocked { background: #fef2f2; }
.lock-unlocked .lock-dot  { background: #ef4444; box-shadow: 0 0 6px #ef444499; }
.lock-unlocked .lock-text { color: #b91c1c; }
.lock-unknown  { background: #f9fafb; }
.lock-unknown .lock-dot  { background: #9ca3af; }
.lock-unknown .lock-text { color: #6b7280; }

/* ── Unified pill — matches header .indicator style ── */
.ui-pill {
  display: inline-block;
  padding: 4px 10px;
  border-radius: 3px;
  font-size: 11px;
  font-weight: bold;
  white-space: nowrap;
  letter-spacing: 0.04em;
}
.ui-pill-green  { background: #7dd228; color: #333; }
.ui-pill-blue   { background: #4a9fd9; color: #fff; }
.ui-pill-red    { background: #fe5e37; color: #fff; }
.ui-pill-yellow { background: #fcb940; color: #333; }
.ui-pill-gray   { background: #f0f0f0; color: #666; }
.ui-pill-purple { background: #9333ea; color: #fff; }
.ui-pill-btn {
  border: none;
  cursor: pointer;
  transition: filter 0.15s;
}
.ui-pill-btn:hover:not(:disabled) { filter: brightness(1.12); }
.ui-pill-btn:disabled { opacity: 0.6; cursor: not-allowed; }
.ui-pill-busy { opacity: 0.75; cursor: wait; }

/* Segmented control (two-option toggle) */
.pill-group {
  display: flex;
  gap: 2px;
  align-items: center;
}
.pill-sep {
  width: 1px;
  height: 14px;
  background: rgba(255,255,255,0.25);
  margin: 0 4px;
}
/* Keep the ACTIVE pill at full opacity when both pills are disabled (transitioning) */
.pill-group .ui-pill-btn:disabled:not(.ui-pill-inactive) {
  opacity: 1;
  cursor: default;
}
/* Unselected/inactive pill — dimmed ghost on the dark card header */
.ui-pill-inactive {
  background: rgba(255,255,255,0.1);
  color: rgba(255,255,255,0.45);
}
.ui-pill-inactive:hover:not(:disabled) {
  background: rgba(255,255,255,0.2);
  color: rgba(255,255,255,0.8);
  filter: none;
}
.btn-spinner {
  display: inline-block;
  width: 10px;
  height: 10px;
  border: 2px solid rgba(255,255,255,0.35);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}

.card-header-manual {
  background: #0369a1 !important;
}
.manual-error-label {
  font-size: 11px;
  color: #fca5a5;
  font-weight: 500;
  flex: 1;
  text-align: center;
}
.manual-body {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 16px;
}
.manual-arrows {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}
.manual-row {
  display: flex;
  align-items: center;
  gap: 4px;
}
.manual-center-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: #d1d5db;
}
.arrow-btn {
  width: 52px;
  height: 52px;
  font-size: 20px;
  background: #1e3a5f;
  color: #fff;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.15s;
  display: flex;
  align-items: center;
  justify-content: center;
}
.arrow-btn:hover  { background: #2563eb; }
.arrow-btn:active { background: #1d4ed8; transform: scale(0.95); }

.manual-goto { margin-top: 12px; width: 100%; }
.manual-detail {
  margin-top: 10px;
  width: 100%;
  border-top: 1px solid #e5e7eb;
  padding-top: 8px;
}
.manual-goto-row {
  display: flex;
  align-items: center;
  gap: 6px;
  justify-content: center;
}
.goto-label {
  font-size: 11px;
  font-weight: 600;
  color: #6b7280;
  min-width: 14px;
}
.goto-input {
  width: 64px;
  padding: 5px 6px;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  font-size: 12px;
  font-family: monospace;
  text-align: center;
  background: #f9fafb;
}
.goto-input:focus { outline: none; border-color: #3b82f6; background: #fff; }
.goto-input-step { width: 50px; border-color: #a5b4fc; }
.goto-btn {
  padding: 5px 14px;
  background: #1e3a5f;
  color: #fff;
  border: none;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
}
.goto-btn:hover { background: #2563eb; }

.signal-metric {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.signal-metric-inline {
  flex-direction: row;
  align-items: center;
  justify-content: space-between;
}
.signal-metric-top {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
}
.sig-label {
  font-size: 11px;
  color: #6b7280;
  font-weight: 500;
}
.sig-value {
  font-size: 16px;
  font-weight: 700;
  color: #111827;
  font-family: monospace;
}
.sig-cn {
  font-size: 18px;
}
.rf-bar-track {
  height: 6px;
  background: #e5e7eb;
  border-radius: 3px;
  overflow: hidden;
}
.rf-bar-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.5s ease, background 0.5s ease;
}

/* tx-pill removed — uses .ui-pill system */

.signal-updated {
  font-size: 10px;
  color: #9ca3af;
  margin-top: 2px;
}

/* ── Antenna Position card ── */
.antpos-body {
  padding: 12px 15px;
}
.antpos-cols {
  display: flex;
  gap: 8px;
  align-items: flex-start;
}
.antpos-col {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}
.antpos-kpi {
  display: flex;
  flex-direction: column;
  align-items: center;
  line-height: 1.1;
}
.antpos-kpi-lbl {
  font-size: 10px;
  color: #6b7280;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.06em;
}
.antpos-kpi-val {
  font-size: 28px;
  font-weight: 700;
  color: #111827;
  font-family: monospace;
  letter-spacing: -0.5px;
}
.antpos-lbl {
  font-size: 10px;
  color: #6b7280;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.06em;
}
.antpos-pitch-view {
  display: flex;
  flex-direction: column;
  align-items: center;
}
.esa-cross-view {
  width: 175px;
  height: 175px;
  display: block;
}
.antpos-compass-view {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
}
.az-compass {
  width: 195px;
  height: 195px;
}
.az-legend {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: center;
  font-size: 10px;
  color: #6b7280;
}
.az-legend-item {
  display: flex;
  align-items: center;
  gap: 4px;
}
.legend-dot {
  width: 8px;
  height: 4px;
  border-radius: 2px;
  display: inline-block;
}
.legend-rect {
  width: 10px;
  height: 14px;
  border-radius: 1px;
  background: #dce7f3;
  border: 1px solid #3b82f6;
  display: inline-block;
}
.legend-mech-arrow {
  width: 2px;
  height: 12px;
  background: #1f2937;
  display: inline-block;
  position: relative;
  top: 1px;
}
.legend-roll {
  width: 12px;
  height: 8px;
  background: linear-gradient(to bottom, #22c55e55 50%, #9ca3af55 50%);
  border: 1px solid #d1d5db;
  border-radius: 1px;
  display: inline-block;
}
.el-legend {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: center;
  font-size: 10px;
  color: #6b7280;
  margin-top: 4px;
}
.legend-fov {
  width: 12px;
  height: 10px;
  background: #22c55e22;
  border: 1px solid #22c55e88;
  border-radius: 1px;
  display: inline-block;
}
.legend-ground {
  width: 14px;
  height: 0;
  border-bottom: 2px dashed #d1d5db;
  display: inline-block;
  position: relative;
  top: -3px;
}

/* ── Snapshot badge — uses .ui-pill base, colors override ── */
.snap-scan   { background: #4a9fd9; color: #fff; }
.snap-peak   { background: #7dd228; color: #333; }
.snap-base   { background: #f0f0f0; color: #666; }
.snap-manual { background: #4a9fd9; color: #fff; }

/* ── Compass card ── */
.card-compass {
  min-width: 180px;
  display: flex;
  flex-direction: column;
}

.compass-visual-body {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  flex: 1;
  padding: 12px 10px;
}
.compass-gauge {
  width: clamp(130px, 70%, 210px);
  aspect-ratio: 1;
}
.compass-readout {
  display: flex;
  flex-direction: column;
  align-items: center;
  margin-top: 4px;
}
.compass-heading {
  font-size: 18px;
  font-weight: bold;
  color: #15803d;
}
/* compass-mode-toggle removed — uses .ui-pill system */
.compass-manual-tag {
  font-size: 12px;
  font-weight: normal;
  color: #fe5e37;
}
.compass-field-ut {
  display: block;
  font-size: 11px;
  color: #9ca3af;
  font-family: monospace;
  margin-top: 2px;
}

.location-header-right {
  display: flex;
  align-items: center;
  gap: 8px;
}
.location-coords {
  font-size: 11px;
  color: #ccc;
  white-space: nowrap;
}

/* ── Map card ── */
.card-map { min-height: 300px; }
.map-body {
  padding: 0 !important;
  height: 280px;
  position: relative;
}
.map-container { width: 100%; height: 100%; }
.map-searching { opacity: 0.35; filter: grayscale(40%); }
.map-overlay {
  position: absolute;
  top: 0; left: 0; right: 0; bottom: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  pointer-events: none;
  gap: 12px;
}
.map-spinner {
  width: 36px;
  height: 36px;
  border: 3px solid rgba(66,165,245,0.25);
  border-top-color: #42a5f5;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}
.map-spinner-text {
  font-size: 13px;
  color: #374151;
  font-weight: 500;
  background: rgba(255,255,255,0.85);
  padding: 4px 12px;
  border-radius: 12px;
}

.readiness-row {
  display: flex;
  justify-content: center;
  flex-wrap: wrap;
  gap: 14px;
  margin-top: 6px;
  padding-top: 10px;
  border-top: 1px solid #eee;
}
.readiness-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 3px;
  cursor: help;
}
.readiness-dot { width: 13px; height: 13px; border-radius: 50%; }
.rd-ok  { background: #22c55e; box-shadow: 0 0 5px #22c55e99; }
.rd-bad { background: #ef4444; box-shadow: 0 0 5px #ef444499; }
.readiness-lbl { font-size: 10px; font-weight: 600; color: #6b7280; }

@keyframes spin { to { transform: rotate(360deg); } }
</style>
