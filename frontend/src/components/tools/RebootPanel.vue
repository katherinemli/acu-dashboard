<template>
  <div class="tool-section">
    <h2>System Reboot</h2>
    <div class="reboot-container">
      <div class="warning-box">
        <span class="warning-icon">
          <AppIcon name="warning" :size="16" />
        </span>
        <p>Rebooting the system will temporarily interrupt all services.</p>
      </div>

      <div class="reboot-options">
        <button @click="confirmReboot('soft')" class="btn-reboot soft" :disabled="rebooting">
          Restart
          <small>Restart services only</small>
        </button>
        <button @click="confirmReboot('hard')" class="btn-reboot hard" :disabled="rebooting">
          Reboot
          <small>Full system restart</small>
        </button>
      </div>

      <div v-if="rebooting" class="reboot-status">
        <div class="spinner"></div>
        <p>System is rebooting... Please wait.</p>
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
  name: 'RebootPanel',
  components: { AppIcon, ConfirmModal, ResultModal },
  data() {
    return {
      rebooting: false,
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
  methods: {
    confirmReboot(type) {
      const label = type === 'soft' ? 'Restart' : 'Reboot'
      const desc = type === 'soft' ? 'restart services only' : 'full system restart'
      this.confirm = {
        visible: true,
        title: label,
        message: `Perform a ${label.toLowerCase()} (${desc})?`,
        warning: 'All services will be temporarily interrupted.',
        btnText: label,
        btnClass: type === 'hard' ? 'btn-danger' : 'btn-primary',
        action: () => this.doReboot(type)
      }
    },

    async doReboot(type) {
      this.rebooting = true
      try {
        await axios.post(`${API_URL}/api/actions/reboot`, { type })
        setTimeout(() => {
          this.rebooting = false
          const label = type === 'soft' ? 'Restart' : 'Reboot'
          this.showResult(`${label} Command Sent`, `${label} command acknowledged. Verify recovery from status or logs.`, true)
        }, 3000)
      } catch (e) {
        this.showResult('Reboot Failed', e.response?.data?.error || 'Error sending reboot command', false)
        this.rebooting = false
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

.reboot-container {
  max-width: 500px;
}

.warning-box {
  background: #fff8e6;
  border: 1px solid #fcb940;
  border-radius: 8px;
  padding: 15px;
  display: flex;
  gap: 15px;
  align-items: flex-start;
  margin-bottom: 20px;
}

.warning-icon {
  font-size: 24px;
}

.warning-box p {
  margin: 0;
  color: #666;
  font-size: 13px;
  line-height: 1.5;
}

.reboot-options {
  display: flex;
  gap: 15px;
}

.btn-reboot {
  flex: 1;
  padding: 20px;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 5px;
  font-size: 14px;
  font-weight: 600;
  transition: transform 0.2s;
}

.btn-reboot:hover:not(:disabled) {
  transform: scale(1.02);
}

.btn-reboot:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-reboot small {
  font-weight: normal;
  font-size: 11px;
  opacity: 0.8;
}

.btn-reboot.soft {
  background: #42a5f5;
  color: white;
}

.btn-reboot.hard {
  background: #fe5e37;
  color: white;
}

.reboot-status {
  margin-top: 30px;
  text-align: center;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 4px solid #f0f0f0;
  border-top-color: #369;
  border-radius: 50%;
  margin: 0 auto 15px;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.reboot-status p {
  color: #666;
}
</style>
