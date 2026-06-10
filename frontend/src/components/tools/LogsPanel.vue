<template>
  <div class="tool-section">
    <h2>ACU Logs</h2>
    <div class="logs-container">
      <div class="logs-toolbar">
        <select v-model="logFile" @change="loadLogs">
          <option value="msg">Messages (acu_msg.log)</option>
          <option value="err">Errors (acu_err.log)</option>
        </select>
        <select v-model="logsLimit" @change="loadLogs">
          <option :value="50">Last 50 lines</option>
          <option :value="100">Last 100 lines</option>
          <option :value="200">Last 200 lines</option>
        </select>
        <button @click="loadLogs">Refresh</button>
        <button @click="downloadLogs">Download</button>
        <button @click="purgeLogs">Purge All Logs</button>
      </div>
      <div v-if="loading" class="loading">Loading...</div>
      <div v-else class="logs-list">
        <div v-for="(log, i) in logs" :key="i" class="log-item" :class="log.level">
          <span class="log-time">{{ log.timestamp }}</span>
          <span class="log-level">{{ log.level }}</span>
          <span class="log-message">{{ log.message }}</span>
        </div>
      </div>
    </div>

    <ConfirmModal
      :visible="confirm.visible"
      :title="confirm.title"
      :message="confirm.message"
      :warning="confirm.warning"
      :btn-text="confirm.btnText"
      :btn-class="confirm.btnClass"
      @confirm="onConfirm"
      @cancel="confirm.visible = false"
    />

    <ResultModal
      :visible="result.visible"
      :title="result.title"
      :message="result.message"
      :success="result.success"
      @close="result.visible = false"
    />
  </div>
</template>

<script>
import axios from 'axios'
import ConfirmModal from '../ConfirmModal.vue'
import ResultModal from '../ResultModal.vue'

const API_URL = import.meta.env.VITE_API_URL || ''

export default {
  name: 'LogsPanel',
  components: { ConfirmModal, ResultModal },
  data() {
    return {
      logs: [],
      logFile: 'msg',
      logsLimit: 100,
      loading: false,
      confirm: {
        visible: false,
        title: '',
        message: '',
        warning: '',
        btnText: 'Confirm',
        btnClass: 'btn-primary',
        action: null
      },
      result: {
        visible: false,
        title: '',
        message: '',
        success: true
      }
    }
  },
  mounted() {
    this.loadLogs()
  },
  methods: {
    async loadLogs() {
      this.loading = true
      try {
        const res = await axios.get(`${API_URL}/api/logs?limit=${this.logsLimit}&file=${this.logFile}`)
        this.logs = res.data || []
      } catch (e) {
        console.error('Error loading logs:', e)
        this.logs = []
      }
      this.loading = false
    },

    downloadLogs() {
      window.location.href = `${API_URL}/api/logs/download`
    },

    purgeLogs() {
      this.confirm = {
        visible: true,
        title: 'Purge Logs',
        message: 'Delete all log files from ACU, Eureka, and journalctl?',
        warning: 'This cannot be undone.',
        btnText: 'Purge All',
        btnClass: 'btn-danger',
        action: this.doPurge
      }
    },

    async doPurge() {
      try {
        const res = await axios.post(`${API_URL}/api/logs/purge`)
        const data = res.data
        this.showResult(
          'Logs Purged',
          data.errors.length
            ? `${data.purged} items purged. Errors: ${data.errors.join(', ')}`
            : `${data.purged} items purged successfully.`,
          data.errors.length === 0
        )
        this.loadLogs()
      } catch (e) {
        this.showResult('Purge Failed', 'Could not purge logs: ' + e.message, false)
      }
    },

    onConfirm() {
      this.confirm.visible = false
      if (this.confirm.action) this.confirm.action()
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

.loading {
  text-align: center;
  padding: 20px;
  color: #666;
}

.logs-container {
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  overflow: hidden;
}

.logs-toolbar {
  padding: 15px;
  background: #f5f5f5;
  display: flex;
  gap: 10px;
}

.logs-toolbar select,
.logs-toolbar button {
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 13px;
}

.logs-toolbar button {
  background: #369;
  color: white;
  border: none;
  cursor: pointer;
}

.logs-list {
  max-height: 500px;
  overflow-y: auto;
  background: #1e1e1e;
  padding: 10px;
}

.log-item {
  display: flex;
  gap: 10px;
  padding: 4px 8px;
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 12px;
  color: #d4d4d4;
}

.log-item.ERR {
  color: #f87171;
}

.log-item.WRN {
  color: #fbbf24;
}

.log-item.DBG {
  color: #888;
}

.log-time {
  color: #888;
  min-width: 120px;
}

.log-level {
  min-width: 40px;
  font-weight: 600;
}

.log-message {
  flex: 1;
}
</style>
