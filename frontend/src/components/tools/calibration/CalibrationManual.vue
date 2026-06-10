<template>
  <div class="calib-two-col">

    <!-- Left column: instructions + face map -->
    <div class="calib-col-visual">
      <div class="calib-info">
        <template v-if="session.sensor === 'gyro'">
          Place the unit completely still on a flat surface. Click Capture, wait until the sample indicator
          confirms enough data, then click Stop Capture. One position is sufficient —
          the gyro only needs a static zero-bias measurement.
          <br><br>
          Button sequence: <strong>Capture</strong> → wait → <strong>Stop Capture</strong> → <strong>Calculate</strong>
        </template>
        <template v-else-if="session.sensor === 'accel'">
          Place the unit so one face points toward the ground, click Capture, then rotate to the next face.
          Repeat for all 6 orientations (each axis ±). The cube shows which faces have been covered — green means done.
          Do not move the unit while a window is recording.
          <br><br>
          Button sequence: <strong>Capture</strong> → wait → <strong>Stop Capture</strong> → rotate to next face → repeat × 6 → <strong>Calculate</strong>
        </template>
      </div>

      <AccelCube v-if="session.sensor === 'accel'"
        :faceHits="session.accelFaceHits"
        :currentFace="session.accelCurrentFace"
        :capturing="session.capturingWindow"
      />
    </div>

    <!-- Right column: stats + buttons -->
    <div class="calib-col-controls">
      <div class="calib-stream-stats">
        <div>Samples: {{ session.samples }}</div>
        <div>Elapsed: {{ session.elapsed }}s</div>
        <div v-if="session.lastReading">
          Last: x={{ session.lastReading.x }},
          y={{ session.lastReading.y }},
          z={{ session.lastReading.z }}
        </div>
        <div v-if="session.capturingWindow" class="calib-capturing-banner">
          <span v-if="windowSamples >= WINDOW_SAMPLES_OK"
                class="calib-window-ready">
            ✓ Enough data ({{ windowSamples }} samples) — stop when ready
          </span>
          <span v-else>
            🔴 Recording — {{ windowSamples }} / {{ WINDOW_SAMPLES_OK }} samples...
            click Stop Capture when done
          </span>
        </div>
        <div v-else class="calib-idle-banner">
          <template v-if="session.sensor === 'accel'">
            <span v-if="uniqueCaptures === 0">
              Place one face down, hold the unit still, then click Capture
            </span>
            <span v-else-if="uniqueCaptures < 6">
              {{ uniqueCaptures }}/6 unique faces done — rotate to the next face, hold still, then click Capture
            </span>
            <span v-else>
              All 6 faces captured — click Calculate
            </span>
          </template>
          <template v-else-if="session.sensor === 'gyro'">
            <span v-if="session.captures === 0">
              Hold the unit completely still, then click Capture
            </span>
            <span v-else>
              Capture complete — click Calculate
            </span>
          </template>
        </div>
      </div>

      <div class="calib-actions">
        <button v-if="!session.capturingWindow"
          class="btn-capture"
          :disabled="session.captureBusy"
          @click="$emit('capture')">
          {{ session.captureBusy ? '...' : 'Capture' }}
        </button>
        <button v-else
          class="btn-stop-capture"
          :disabled="session.captureBusy"
          @click="$emit('capture')">
          {{ session.captureBusy ? '...' : 'Stop Capture' }}
        </button>

        <button
          class="btn-calib-finish"
          :disabled="session.capturingWindow || uniqueCaptures < minCaptures || session.finishing"
          @click="$emit('finish')"
        >
          {{ session.finishing ? 'Calculating...' : 'Calculate' }}
        </button>

        <button class="btn-calib-cancel" @click="$emit('cancel')">
          Cancel
        </button>
      </div>

      <div class="calib-capture-hint" v-if="uniqueCaptures < minCaptures">
        Need at least {{ minCaptures }} unique faces. You have {{ uniqueCaptures }}.
      </div>
      <div class="calib-capture-hint" v-else-if="session.capturingWindow">
        Stop the current capture before calculating.
      </div>
    </div>

  </div>
</template>

<script>
import AccelCube from '../../AccelCube.vue'

const WINDOW_SAMPLES_OK = 200

export default {
  name: 'CalibrationManual',
  components: { AccelCube },
  props: {
    session: { type: Object, required: true }
  },
  data() {
    return { WINDOW_SAMPLES_OK }
  },
  computed: {
    minCaptures() { return this.session.sensor === 'gyro' ? 1 : 6 },
    uniqueCaptures() {
      if (this.session.sensor === 'accel') {
        return this.session.accelFaceHits.filter(h => h > 0).length
      }
      return this.session.captures
    },
    windowSamples() {
      return Math.max(0, this.session.samples - (this.session.accelWindowStartSamples || 0))
    }
  },
  emits: ['capture', 'finish', 'cancel']
}
</script>

<style scoped>
.calib-two-col {
  display: flex;
  gap: 32px;
  align-items: flex-start;
}

.calib-col-visual {
  flex: 0 0 320px;
}

.calib-col-controls {
  flex: 1 1 0;
  min-width: 280px;
}

.calib-info {
  padding: 10px 12px;
  background: #f0f7ff;
  border-left: 3px solid #42a5f5;
  border-radius: 4px;
  font-size: 13px;
  color: #555;
  margin-bottom: 12px;
  line-height: 1.6;
}

.calib-stream-stats {
  background: #f5f5f5;
  padding: 12px;
  border-radius: 4px;
  margin: 12px 0;
  font-family: monospace;
  font-size: 14px;
  line-height: 1.8;
}

.calib-capturing-banner {
  margin-top: 8px;
  padding: 6px 10px;
  border-radius: 4px;
  font-weight: 600;
  font-size: 13px;
  background: #fff3e0;
  color: #e65100;
}

.calib-idle-banner {
  margin-top: 8px;
  padding: 6px 10px;
  border-radius: 4px;
  font-weight: 600;
  font-size: 13px;
  background: #f0f7ff;
  color: #1565c0;
}

.calib-window-ready {
  color: #1b5e20;
  font-weight: 700;
}

.calib-actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.btn-capture {
  flex: 2;
  padding: 14px;
  background: #42a5f5;
  color: white;
  border: none;
  border-radius: 4px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
}

.btn-capture:hover:not(:disabled) {
  background: #1e88e5;
}

.btn-capture:disabled {
  background: #90caf9;
  cursor: not-allowed;
}

.btn-stop-capture {
  flex: 2;
  padding: 14px;
  background: #fe5e37;
  color: white;
  border: none;
  border-radius: 4px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  animation: pulse 1.5s infinite;
}

.btn-stop-capture:hover:not(:disabled) {
  background: #d32f2f;
}

.btn-stop-capture:disabled {
  background: #ef9a9a;
  cursor: not-allowed;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.7; }
}

.btn-calib-finish {
  flex: 1;
  padding: 14px;
  background: #7dd228;
  color: white;
  border: none;
  border-radius: 4px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
}

.btn-calib-finish:disabled {
  background: #ccc;
  cursor: not-allowed;
}

.btn-calib-cancel {
  flex: 1;
  padding: 14px;
  background: #e0e0e0;
  color: #333;
  border: none;
  border-radius: 4px;
  font-size: 14px;
  cursor: pointer;
}

.calib-capture-hint {
  margin-top: 8px;
  font-size: 12px;
  color: #888;
  text-align: center;
}
</style>
