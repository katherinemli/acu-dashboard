<template>
  <div>

    <!-- Phase 1: pre-start — user gets ready before data collection begins -->
    <div v-if="!userStarted">
      <div class="calib-info">
        Rotate the unit, while making wide fluid movements, in all of the three spatial axes (X, Y and Z). A figure-8 motions work well.<br><br>
        Press <strong>Start</strong> when you are holding the unit and ready to rotate.
      </div>
      <div v-if="session.waitingForAcumon" class="calib-waiting">
        Waiting for sensor to enter high-frequency mode...
      </div>
      <div class="calib-actions">
        <button class="btn-calib-start-now"
                :disabled="!!session.waitingForAcumon"
                @click="userStarted = true">
          Start
        </button>
        <button class="btn-calib-cancel" @click="$emit('cancel')">Cancel</button>
      </div>
    </div>

    <!-- Phase 2: active collection -->
    <div v-else>
      <div>
        <div v-if="session.waitingForAcumon" class="calib-waiting">
          Waiting for sensor to enter high-frequency mode...
        </div>
        <div v-else-if="noMovementWarning" class="calib-no-movement">
          ⚠ No movement detected — keep rotating the unit
        </div>
        <div v-else-if="session.autoStopReady" class="calib-ready">
          Coverage sufficient — you can stop now
        </div>
        <div v-else class="calib-info">
          Keep rotating in all directions.
        </div>

        <div class="calib-stream-stats">
          <div>Samples: {{ session.samples }}</div>
          <div>
            Coverage: {{ session.sectorsHit }} / {{ session.sectorsTotal }}
            ({{ (session.coverage * 100).toFixed(0) }}%)
          </div>
          <div>Elapsed: {{ session.elapsed }}s</div>
          <div v-if="session.lastReading">
            Last: x={{ session.lastReading.x }},
            y={{ session.lastReading.y }},
            z={{ session.lastReading.z }}
          </div>
        </div>

        <div class="calib-actions">
          <button class="btn-calib-finish"
                  :disabled="session.finishing"
                  @click="$emit('finish')">
            {{ session.finishing ? 'Calculating...' : 'Stop & Calculate' }}
          </button>
          <button class="btn-calib-cancel" @click="$emit('cancel')">Cancel</button>
        </div>
      </div>

    </div>

  </div>
</template>

<script>
// Total range across 3 axes over the last WINDOW readings.
// Still unit (calib-mode noise ~35 units): range ≈ 100-120 → below threshold.
// Active rotation: per-axis changes of 100s of units → well above threshold.
const MOVEMENT_THRESHOLD = 150
const MOVEMENT_WINDOW    = 5

export default {
  name: 'CalibrationStream',
  props: {
    session: { type: Object, required: true }
  },
  emits: ['finish', 'cancel'],
  data() {
    return {
      userStarted:      false,
      readingHistory:   [],
      noMovementWarning: false,
    }
  },
  watch: {
    'session.lastReading'(val) {
      if (!val || !this.userStarted) return
      this.readingHistory.push({ x: val.x, y: val.y, z: val.z })
      if (this.readingHistory.length > MOVEMENT_WINDOW) this.readingHistory.shift()
      if (this.readingHistory.length < MOVEMENT_WINDOW) return
      const xs = this.readingHistory.map(r => r.x)
      const ys = this.readingHistory.map(r => r.y)
      const zs = this.readingHistory.map(r => r.z)
      const range = (Math.max(...xs) - Math.min(...xs))
                  + (Math.max(...ys) - Math.min(...ys))
                  + (Math.max(...zs) - Math.min(...zs))
      this.noMovementWarning = range < MOVEMENT_THRESHOLD
    }
  }
}
</script>

<style scoped>
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

.calib-waiting {
  padding: 10px 14px;
  background: #fff8e6;
  border: 1px solid #fcb940;
  border-radius: 6px;
  font-size: 14px;
  color: #7a4f00;
  text-align: center;
  margin: 10px 0;
}

.calib-no-movement {
  padding: 10px 14px;
  background: #fff5f5;
  border: 1px solid #fe5e37;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 600;
  color: #991b1b;
  text-align: center;
  margin: 10px 0;
}

.calib-ready {
  color: #1b5e20;
  font-weight: 600;
  font-size: 14px;
  padding: 8px 12px;
  background: #e8f5e9;
  border-radius: 4px;
  margin: 10px 0;
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

.calib-actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  margin-top: 12px;
}

.btn-calib-start-now {
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

.btn-calib-start-now:hover:not(:disabled) {
  background: #1e88e5;
}

.btn-calib-start-now:disabled {
  background: #90caf9;
  cursor: not-allowed;
}

.btn-calib-finish {
  flex: 2;
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
</style>
