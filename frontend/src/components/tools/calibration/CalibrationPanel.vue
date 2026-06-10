<template>
  <div class="tool-section">
    <h2>Sensor Calibration</h2>
    <div class="calib-container">
      <!-- Not started yet -->
      <div v-if="!session.active" class="calib-pre-session">
        <p class="calib-desc">
          Manually calibrate sensors by capturing samples one at a time.
          Position the unit, then click Capture for each measurement.
        </p>

        <div class="calib-sensor-select">
          <label>Sensor:</label>
          <button v-for="s in ['gyro', 'accel', 'compass']" :key="s"
            :class="['btn-sensor', { selected: session.sensor === s }]" @click="session.sensor = s">
            {{ SENSOR_LABELS[s] }}
          </button>
        </div>

        <div class="calib-info">
          <template v-if="session.sensor === 'gyro'">
            Place the unit completely still on a flat surface. Click Capture, wait until the sample indicator
            confirms enough data, then click Stop Capture. One position is sufficient —
            the gyro only needs a static zero-bias measurement.
          </template>
          <template v-else-if="session.sensor === 'accel'">
            Place the unit so one face points toward the ground, click Capture, then rotate to the next face.
            Repeat for all 6 orientations (each axis ±). The cube shows which faces have been covered — green means done.
            Do not move the unit while a window is recording.
          </template>
          <template v-else-if="session.sensor === 'compass'">
            Rotate the unit, while making wide fluid movements, in all of the three spatial axes (X, Y and Z).
            A figure-8 motion works well. The sphere will show coverage as you move.<br><br>
            Click <strong>Start</strong> when you are holding the unit and ready to rotate.
            Click <strong>Stop</strong> when coverage is sufficient.
          </template>
        </div>

        <button class="btn-calib-start"
          :disabled="!session.sensor || session.starting || (sensorHealth.checked && !sensorHealth.all_ok)"
          @click="calibStart">
          {{ session.starting ? 'Starting...' : 'Select Calibration' }}
        </button>

        <div v-if="sensorHealth.checked && !sensorHealth.all_ok" class="sensor-health-warning">
          <span class="warning-icon-sm">⚠</span>
          One or more sensors are not responding:
          <ul>
            <template v-for="(info, name) in sensorHealth.sensors" :key="name">
              <li v-if="!info.ok">
                <strong>{{ SENSOR_LABELS[name] }}</strong>
                — {{ info.age_s !== null ? `last seen ${info.age_s}s ago` : 'no data' }}
              </li>
            </template>
          </ul>
          <button class="btn-restart-services" @click="restartServices" :disabled="restarting">
            {{ restarting ? 'Restarting...' : 'Restart Services' }}
          </button>
        </div>
      </div>

      <!-- Active session -->
      <div v-else>
        <div class="calib-header-row">
          <span class="calib-sensor-badge">
            {{ SENSOR_LABELS[session.sensor] }}
          </span>
        </div>

        <!-- Session timed out -->
        <div v-if="session.timedOut" class="calib-timeout">
          <div class="calib-timeout-title">Calibration session expired</div>
          <p class="calib-timeout-body">
            The session was closed because it was idle too long or the page was inactive.
            Any data collected so far has been discarded.
          </p>
          <p class="calib-timeout-body">
            Click <strong>Start Over</strong> to begin a new session. Try to complete all
            capture steps without pausing too long between them.
          </p>
          <button class="btn-calib-start-over" @click="calibCancel(true)">Start Over</button>
        </div>

        <!-- Normal active session -->
        <template v-else>
          <!-- Compass: stream mode with coverage sphere -->
          <CalibrationStream v-if="session.sensor === 'compass'" :session="session"
            @finish="calibFinish" @cancel="calibCancel" />

          <!-- Gyro / Accel: manual capture mode -->
          <CalibrationManual v-else :session="session"
            @capture="calibCapture" @finish="calibFinish" @cancel="calibCancel" />

          <div v-if="session.error" class="calib-error">
            {{ session.error }}
          </div>
        </template>
      </div>
    </div>

    <ResultModal :visible="result.visible" :title="result.title" :message="result.message"
      :success="result.success" @close="result.visible = false" />

    <CalibrationHistory ref="history" />
  </div>
</template>

<script>
import axios from 'axios'
import CalibrationStream from './CalibrationStream.vue'
import CalibrationManual from './CalibrationManual.vue'
import ResultModal from '../../ResultModal.vue'
import CalibrationHistory from './CalibrationHistory.vue'

const API_URL = import.meta.env.VITE_API_URL || ''

// Map a raw accel reading to one of 6 cube faces (±X=0/1, ±Y=2/3, ±Z=4/5).
// The axis with the largest absolute value is dominant (gravity direction).
function classifyFace(x, y, z) {
  const ax = Math.abs(x), ay = Math.abs(y), az = Math.abs(z)
  if (ax >= ay && ax >= az) return x >= 0 ? 0 : 1
  if (ay >= ax && ay >= az) return y >= 0 ? 2 : 3
  return z >= 0 ? 4 : 5
}

const SENSOR_LABELS = {
  gyro: 'Gyroscope',
  accel: 'Accelerometer',
  compass: 'Magnetometer'
}

export default {
  name: 'CalibrationPanel',
  components: { CalibrationStream, CalibrationManual, ResultModal, CalibrationHistory },
  data() {
    return {
      pollInterval: null,
      pollErrorCount: 0,
      SENSOR_LABELS,
      sensorHealth: {
        checked: false,
        all_ok: true,
        sensors: {}
      },
      restarting: false,
      session: {
        active: false,
        sensor: 'compass',
        samples: 0,
        lastReading: null,
        log: [],
        coverage: 0,
        sectorsHit: 0,
        sectorsTotal: 320,
        elapsed: 0,
        autoStopReady: false,
        isStable: false,
        captures: 0,
        starting: false,
        captureBusy: false,
        capturingWindow: false,
        finishing: false,
        timedOut: false,
        error: '',
        waitingForAcumon: false,
        accelFaceHits: [0, 0, 0, 0, 0, 0],
        accelCurrentFace: -1,
        accelWindowStartSamples: 0
      },
      result: {
        visible: false,
        title: '',
        message: '',
        success: true
      }
    }
  },
  watch: {
    'session.elapsed'(val) {
      if (this.session.active && val >= 300 && !this.session.finishing) {
        this.calibFinish()
      }
    }
  },
  mounted() {
    this.checkSensorHealth()
  },
  beforeUnmount() {
    this.stopPolling()
  },
  methods: {
    async checkSensorHealth() {
      try {
        const res = await axios.get(`${API_URL}/api/acu/sensor-health`)
        this.sensorHealth = { checked: true, ...res.data }
      } catch (e) {
        this.sensorHealth = { checked: false, all_ok: true, sensors: {} }
      }
    },

    async restartServices() {
      this.restarting = true
      try {
        await axios.post(`${API_URL}/api/actions/reboot`, { type: 'soft' })
        await new Promise(r => setTimeout(r, 4000))
        await this.checkSensorHealth()
      } catch (e) {
        console.error('Restart failed:', e)
      }
      this.restarting = false
    },

    async calibStart() {
      this.session.starting = true
      this.session.error = ''
      const sensor = this.session.sensor
      const endpoint = `/api/calibration/${sensor}/start`

      try {
        const res = await axios.post(`${API_URL}${endpoint}`, { sensor })
        if (res.data.status === 'ok') {
          this.session.active = true
          this.session.timedOut = false
          this.pollErrorCount = 0
          this.session.samples = 0
          this.session.lastReading = sensor === 'compass' ? null : ''
          this.session.log = []
          this.session.coverage = 0
          this.session.sectorsHit = 0
          this.session.elapsed = 0
          this.session.autoStopReady = false
          this.session.isStable = false
          this.session.captures = 0
          this.session.captureBusy = false
          this.session.capturingWindow = false
          this.session.waitingForAcumon = false
          this.session.accelFaceHits = [0, 0, 0, 0, 0, 0]
          this.session.accelCurrentFace = -1
          this.session.accelWindowStartSamples = 0

          this.startPolling()
        } else {
          this.session.error = res.data.error || 'Failed to start'
        }
      } catch (e) {
        this.session.error = e.response?.data?.error || e.message
      }
      this.session.starting = false
    },

    startPolling() {
      this.stopPolling()
      const sensor = this.session.sensor

      this.session.pollInterval = setInterval(async () => {
        try {
          const res = await axios.get(`${API_URL}/api/calibration/${sensor}/progress`)
          if (res.data.status === 'ok') {
            this.pollErrorCount = 0
            this.session.samples = res.data.samples
            this.session.coverage = res.data.coverage
            this.session.sectorsHit = res.data.sectors_hit
            this.session.sectorsTotal = res.data.sectors_total
            this.session.elapsed = res.data.elapsed_seconds
            this.session.autoStopReady = res.data.auto_stop_ready || false
            this.session.lastReading = res.data.last_reading
            this.session.isStable = res.data.is_stable || false
            this.session.captures = res.data.captures || 0
            this.session.capturingWindow = res.data.capturing || false
            this.session.waitingForAcumon = res.data.waiting_for_acumon || false

            if (sensor === 'accel' && res.data.last_reading) {
              const { x, y, z } = res.data.last_reading
              this.session.accelCurrentFace = classifyFace(x, y, z)
            }
          } else {
            this.pollErrorCount++
            if (this.pollErrorCount >= 2) this._markTimedOut()
          }
        } catch (e) {
          this.pollErrorCount++
          if (this.pollErrorCount >= 2) this._markTimedOut()
          console.debug('Progress poll failed:', e.message)
        }
      }, 1000)
    },

    stopPolling() {
      if (this.session.pollInterval) {
        clearInterval(this.session.pollInterval)
        this.session.pollInterval = null
      }
    },

    _markTimedOut() {
      if (!this.session.timedOut) {
        this.session.timedOut = true
        this.stopPolling()
      }
    },

    async calibCapture() {
      const sensor = this.session.sensor
      this.session.captureBusy = true
      this.session.error = ''
      try {
        const res = await axios.post(`${API_URL}/api/calibration/${sensor}/capture`)
        if (res.data.status === 'ok') {
          this.session.captures = res.data.captures
          this.session.capturingWindow = res.data.state === 'capturing'
          if (res.data.state === 'capturing') {
            this.session.accelWindowStartSamples = this.session.samples
          }
          // Window just closed — permanently mark whichever face was dominant
          if (res.data.state === 'idle' && this.session.accelCurrentFace >= 0) {
            const hits = [...this.session.accelFaceHits]
            hits[this.session.accelCurrentFace]++
            this.session.accelFaceHits = hits
          }
        } else {
          const errMsg = res.data.error || 'Capture failed'
          if (errMsg.toLowerCase().includes('calibration in progress')) {
            this._markTimedOut()
          } else {
            this.session.error = errMsg
          }
        }
      } catch (e) {
        const errMsg = e.response?.data?.error || e.message
        if (errMsg && errMsg.toLowerCase().includes('calibration in progress')) {
          this._markTimedOut()
        } else {
          this.session.error = errMsg
        }
      }
      this.session.captureBusy = false
    },

    async calibFinish() {
      this.session.finishing = true
      this.session.error = ''
      const sensor = this.session.sensor
      const endpoint = `/api/calibration/${sensor}/stop`

      this.stopPolling()

      try {
        const stopRes = await axios.post(`${API_URL}${endpoint}`)

        if (stopRes.data.status !== 'ok') {
          const errMsg = stopRes.data.error || 'Stop failed'
          if (errMsg.toLowerCase().includes('calibration in progress')) {
            this._markTimedOut()
          } else {
            this.session.error = errMsg
          }
          this.session.finishing = false
          return
        }

        if (stopRes.data.state === 'calculating') {
          const result = await this._pollFitResult(sensor)
          if (result.status === 'ok') {
            this.session.active = false
            this.showResult(
              'Calibration Complete',
              `${result.sensor} calibration finished with ${result.samples} samples.` +
              (result.calib_output ? '\n' + result.calib_output : ''),
              true
            )
          } else {
            if (result.reset) {
              this.session.active = false
              this.showResult('Calibration Failed', result.error || 'Fit failed', false)
            } else {
              this.session.error = result.error || 'Fit failed'
            }
          }
        } else {
          this.session.active = false
          this.showResult(
            'Calibration Complete',
            `${stopRes.data.sensor} calibration finished with ${stopRes.data.samples} samples.` +
            (stopRes.data.calib_output ? '\n' + stopRes.data.calib_output : ''),
            true
          )
        }
      } catch (e) {
        const errMsg = e.response?.data?.error || e.message
        if (errMsg && errMsg.toLowerCase().includes('calibration in progress')) {
          this._markTimedOut()
        } else {
          this.session.error = errMsg
        }
      }
      // A finished run (applied or failed) writes a history record — refresh
      // the table once, event-driven. No polling clock added on purpose.
      this.$refs.history?.load()
      this.session.finishing = false
    },

    async _pollFitResult(sensor, timeoutMs = 30000) {
      const start = Date.now()
      while (Date.now() - start < timeoutMs) {
        try {
          const res = await axios.get(`${API_URL}/api/calibration/${sensor}/result`)
          if (res.data.state === 'done') {
            return res.data
          }
        } catch (e) {
          // endpoint may not exist yet for gyro/accel — skip
        }
        await new Promise(r => setTimeout(r, 500))
      }
      return { status: 'error', error: 'Calibration timed out. Please try again.', reset: true }
    },

    async calibCancel(silent = false) {
      if (!silent && !confirm('Cancel calibration? Sensor data will be lost.')) return

      this.stopPolling()
      const sensor = this.session.sensor

      try {
        await axios.post(`${API_URL}/api/calibration/${sensor}/cancel`)
      } catch (e) {
        console.error('Cancel error:', e)
      }
      this.session.active = false
      this.session.timedOut = false
      this.pollErrorCount = 0
      this.session.samples = 0
      this.session.log = []
      this.session.accelFaceHits = [0, 0, 0, 0, 0, 0]
      this.session.accelCurrentFace = -1
      this.session.accelWindowStartSamples = 0
      this.session.captureBusy = false
      this.session.capturingWindow = false
      this.session.error = ''
    },

    showResult(title, message, success) {
      this.result = { visible: true, title, message, success }
    }
  }
}
</script>

<style scoped>
.tool-section {
  padding: 20px;
}

h2 {
  margin-bottom: 20px;
  color: #333;
}

.calib-container {
  max-width: 960px;
}

.calib-pre-session {
  max-width: 560px;
}

.calib-desc {
  color: #666;
  font-size: 13px;
  line-height: 1.5;
  margin-bottom: 20px;
}

.calib-sensor-select {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 15px;
}

.calib-sensor-select label {
  color: #666;
  font-size: 13px;
  font-weight: 600;
}

.btn-sensor {
  padding: 8px 16px;
  border: 1px solid #ddd;
  border-radius: 4px;
  background: white;
  cursor: pointer;
  font-size: 13px;
  transition: all 0.15s;
}

.btn-sensor:hover {
  border-color: #42a5f5;
}

.btn-sensor.selected {
  background: #42a5f5;
  color: white;
  border-color: #42a5f5;
}

.calib-info {
  padding: 10px 12px;
  background: #f0f7ff;
  border-left: 3px solid #42a5f5;
  border-radius: 4px;
  font-size: 13px;
  color: #555;
  margin-bottom: 20px;
}

.btn-calib-start {
  width: 100%;
  padding: 12px;
  background: #7dd228;
  color: white;
  border: none;
  border-radius: 4px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
}

.btn-calib-start:disabled {
  background: #ccc;
  cursor: not-allowed;
}

.calib-header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
}

.calib-sensor-badge {
  padding: 4px 12px;
  background: #42a5f5;
  color: white;
  border-radius: 12px;
  font-size: 13px;
  font-weight: 600;
}


.calib-error {
  margin-top: 10px;
  padding: 8px 12px;
  background: #fff5f5;
  border-left: 3px solid #fe5e37;
  border-radius: 4px;
  font-size: 13px;
  color: #991b1b;
}

.calib-timeout {
  padding: 20px 24px;
  background: #fff8e6;
  border: 1px solid #fcb940;
  border-radius: 6px;
  max-width: 480px;
}

.calib-timeout-title {
  font-size: 15px;
  font-weight: 600;
  color: #7a4f00;
  margin-bottom: 8px;
}

.calib-timeout-body {
  font-size: 13px;
  color: #5a3a00;
  margin: 0 0 16px 0;
  line-height: 1.5;
}

.btn-calib-start-over {
  padding: 10px 24px;
  background: #42a5f5;
  color: white;
  border: none;
  border-radius: 4px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}

.btn-calib-start-over:hover {
  background: #1e88e5;
}

.sensor-health-warning {
  margin-top: 12px;
  padding: 10px 14px;
  background: #fff8e6;
  border: 1px solid #fcb940;
  border-radius: 6px;
  font-size: 13px;
  color: #7a4f00;
}

.sensor-health-warning ul {
  margin: 6px 0 8px 16px;
  padding: 0;
}

.sensor-health-warning li {
  margin-bottom: 2px;
}

.warning-icon-sm {
  margin-right: 4px;
}

.btn-restart-services {
  margin-top: 4px;
  padding: 6px 14px;
  background: #42a5f5;
  color: white;
  border: none;
  border-radius: 4px;
  font-size: 12px;
  cursor: pointer;
}

.btn-restart-services:disabled {
  background: #ccc;
  cursor: not-allowed;
}
</style>
