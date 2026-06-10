<template>
  <div class="tools">
    <component v-if="currentComponent" :is="currentComponent" />
    <div v-else class="tool-section">
      <h2>Tool Unavailable</h2>
      <p class="tool-note">The requested tools section is not available in this build.</p>
    </div>
  </div>
</template>

<script>
import EventsPanel from './tools/EventsPanel.vue'
import LogsPanel from './tools/LogsPanel.vue'
import UpgradePanel from './tools/UpgradePanel.vue'
import RebootPanel from './tools/RebootPanel.vue'
import CalibrationPanel from './tools/calibration/CalibrationPanel.vue'

export default {
  name: 'Tools',
  components: {
    EventsPanel,
    LogsPanel,
    UpgradePanel,
    RebootPanel,
    CalibrationPanel
  },
  props: {
    section: {
      type: String,
      required: true
    }
  },
  computed: {
    currentComponent() {
      const sectionMap = {
        events: 'EventsPanel',
        logs: 'LogsPanel',
        upgrade: 'UpgradePanel',
        reboot: 'RebootPanel',
        calibration: 'CalibrationPanel'
      }
      return sectionMap[this.section] || null
    }
  }
}
</script>

<style scoped>
.tool-section {
  padding: 20px;
}

.tool-note {
  color: #666;
  font-size: 13px;
}
</style>
