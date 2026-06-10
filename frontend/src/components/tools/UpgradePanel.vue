<template>
  <div class="tool-section">
    <h2>Firmware Upgrade</h2>
    <div class="upgrade-container">
      <div class="current-version">
        <span class="label">Current Version:</span>
        <span class="value">{{ currentVersion }}</span>
      </div>

      <div class="upload-section">
        <h3>Upload Firmware File</h3>
        <div
          class="upload-area"
          @dragover.prevent="isDragging = true"
          @dragleave="isDragging = false"
          @drop.prevent="handleDrop"
          :class="{ dragover: isDragging }"
        >
          <input type="file" ref="fileInput" @change="handleFileSelect" accept=".deb" hidden />
          <div class="upload-content" @click="$refs.fileInput.click()">
            <span class="upload-icon">
              <AppIcon name="folder" :size="32" />
            </span>
            <p>Drag & drop firmware file here<br />or click to browse</p>
          </div>
        </div>
        <div v-if="selectedFile" class="selected-file">
          Selected: {{ selectedFile.name }} ({{ formatSize(selectedFile.size) }})
        </div>
        <button v-if="selectedFile" @click="startUpgrade" class="btn-upgrade" :disabled="upgrading">
          {{ upgrading ? 'Upgrading...' : 'Start Upgrade' }}
        </button>
        <div v-if="upgradeState" class="upgrade-state" :class="upgradeStateClass">
          {{ upgradeState }}
        </div>
        <div v-if="upgradeMessage" class="upgrade-message">{{ upgradeMessage }}</div>
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
import AppIcon from '../AppIcon.vue'
import ConfirmModal from '../ConfirmModal.vue'
import ResultModal from '../ResultModal.vue'

const API_URL = import.meta.env.VITE_API_URL || ''

export default {
  name: 'UpgradePanel',
  components: { AppIcon, ConfirmModal, ResultModal },
  data() {
    return {
      currentVersion: 'Loading...',
      selectedFile: null,
      isDragging: false,
      upgrading: false,
      upgradeState: '',
      upgradeMessage: '',
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
  computed: {
    upgradeStateClass() {
      if (!this.upgradeState) return ''
      if (this.upgradeState.includes('failed')) return 'error'
      if (this.upgradeState.includes('complete')) return 'success'
      return 'pending'
    }
  },
  mounted() {
    this.loadVersion()
  },
  methods: {
    async loadVersion() {
      try {
        const res = await axios.get(`${API_URL}/api/system/version`)
        this.currentVersion = res.data.version
      } catch (e) {
        this.currentVersion = 'Unknown'
      }
    },

    handleFileSelect(e) {
      this.selectedFile = e.target.files[0]
    },

    handleDrop(e) {
      this.isDragging = false
      this.selectedFile = e.dataTransfer.files[0]
    },

    formatSize(bytes) {
      if (bytes < 1024) return bytes + ' B'
      if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
      return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
    },

    startUpgrade() {
      if (!this.selectedFile) return
      if (!this.selectedFile.name.endsWith('.deb')) {
        this.showResult('Invalid File', 'Only .deb files are accepted', false)
        return
      }

      this.confirm = {
        visible: true,
        title: 'Firmware Upgrade',
        message: `Upgrade firmware using ${this.selectedFile.name}?`,
        warning: 'The system will restart during this process.',
        btnText: 'Start Upgrade',
        btnClass: 'btn-primary',
        action: this.doUpgrade
      }
    },

    async doUpgrade() {
      this.upgrading = true
      this.upgradeState = 'uploading package'
      this.upgradeMessage = 'Uploading...'

      try {
        const formData = new FormData()
        formData.append('file', this.selectedFile)

        await axios.post(`${API_URL}/api/actions/upgrade`, formData, {
          headers: { 'Content-Type': 'multipart/form-data' }
        })

        this.pollUpgradeStatus()
      } catch (e) {
        this.showResult('Upgrade Failed', e.response?.data?.error || e.message, false)
        this.upgrading = false
        this.upgradeState = 'failed to start'
      }
    },

    pollUpgradeStatus() {
      let wasDown = false
      this.upgradeState = 'waiting for service interruption'
      this.upgradeMessage = 'Upgrade triggered. Waiting for backend/service restart.'
      const interval = setInterval(async () => {
        try {
          await axios.get(`${API_URL}/api/actions/upgrade/status`, { timeout: 2000 })

          if (wasDown) {
            this.upgradeState = 'service reachable again'
            this.upgradeMessage = 'Upgrade flow finished. Confirm the installed version below.'
            clearInterval(interval)
            setTimeout(() => {
              this.upgrading = false
              this.upgradeState = 'complete'
              this.selectedFile = null
              this.loadVersion()
              this.showResult('Upgrade Flow Complete', 'The service is reachable again. Confirm version and system health.', true)
            }, 1000)
          } else {
            this.upgradeState = 'waiting for restart'
            this.upgradeMessage = 'Package uploaded. Waiting for service restart.'
          }
        } catch (e) {
          wasDown = true
          this.upgradeState = 'service restarting'
          this.upgradeMessage = 'Service became unreachable. Waiting for it to return.'
        }
      }, 2000)
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

h3 {
  margin: 0 0 15px 0;
  font-size: 14px;
  color: #333;
}

.upgrade-container {
  max-width: 500px;
}

.current-version {
  background: white;
  padding: 15px;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  margin-bottom: 20px;
}

.current-version .label {
  color: #666;
  margin-right: 10px;
}

.current-version .value {
  font-weight: 600;
  color: #333;
}

.upload-section {
  background: white;
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.upload-area {
  border: 2px dashed #ddd;
  border-radius: 8px;
  padding: 40px;
  text-align: center;
  cursor: pointer;
  transition: all 0.2s;
}

.upload-area:hover,
.upload-area.dragover {
  border-color: #42a5f5;
  background: #f5faff;
}

.upload-icon {
  font-size: 40px;
  display: block;
  margin-bottom: 10px;
}

.upload-content p {
  color: #666;
  margin: 0;
}

.selected-file {
  margin-top: 15px;
  padding: 10px;
  background: #f0f0f0;
  border-radius: 4px;
  font-size: 13px;
}

.btn-upgrade {
  margin-top: 15px;
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

.btn-upgrade:disabled {
  background: #ccc;
  cursor: not-allowed;
}

.upgrade-message {
  margin-top: 10px;
  padding: 8px 12px;
  background: #f0f7ff;
  border-left: 3px solid #42a5f5;
  border-radius: 4px;
  font-size: 13px;
  color: #333;
}

.upgrade-state {
  margin-top: 15px;
  padding: 8px 12px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 600;
}

.upgrade-state.pending {
  background: #fff8e6;
  color: #8a6d00;
}

.upgrade-state.success {
  background: #ecfdf3;
  color: #166534;
}

.upgrade-state.error {
  background: #fef2f2;
  color: #991b1b;
}
</style>
