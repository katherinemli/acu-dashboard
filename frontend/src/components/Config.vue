<template>
  <div class="config">
    <h2>{{ title }}</h2>

    <div v-if="isNetworkSection && !loading" class="net-notice" :class="{ 'net-warning': networkChanged }">
      <div class="net-notice-inner">
        <AppIcon :name="networkChanged ? 'warning' : 'info'" :size="16" />
        <div>
          <span v-if="!networkChanged">Changing these settings will reconnect the network interface. Verify values before saving.</span>
          <template v-else>
            <strong>Network settings have changed.</strong> Saving will reconnect the interface and may briefly interrupt access.
            <div v-if="formData['acuIp'] && formData['acuIp'] !== originalData['acuIp'] && networkValidation.ipOk !== false" class="net-ip-note">
              New MGMT IP: <code>{{ formData['acuIp'] }}</code> — reconnect here after saving if you lose access.
            </div>
            <div class="net-checks">
              <span v-if="networkValidation.subnetOk === false" class="net-chip chip-warn">⚠ Gateway not in subnet</span>
              <span v-else-if="networkValidation.subnetOk === true" class="net-chip chip-ok">✓ Subnet OK</span>
              <span v-if="networkCheckPending" class="net-chip">Checking gateway…</span>
              <template v-else-if="networkCheck">
                <span v-if="networkCheck.gateway_reachable === false" class="net-chip chip-warn">⚠ Gateway unreachable</span>
                <span v-else-if="networkCheck.gateway_reachable === true" class="net-chip chip-ok">✓ Gateway reachable</span>
              </template>
            </div>
          </template>
        </div>
      </div>
    </div>

    <div v-if="loading" class="loading">Loading...</div>

    <form v-else @submit.prevent="save" class="config-form">
      <div v-for="field in fields" :key="field.key" class="field-row"
        :class="{ 'field-readonly': isFieldReadonly(field) }">
        <label :for="field.key">{{ field.label }}</label>

        <div class="field-input">
          <div v-if="field.type === 'button-group'" class="btn-group">
            <button v-for="opt in field.options" :key="opt.value" type="button"
              :class="{ active: formData[field.key] === opt.value }" @click="formData[field.key] = opt.value">{{
              opt.label }}</button>
          </div>

          <select v-else-if="field.type === 'select'" :id="field.key" v-model="formData[field.key]"
            :disabled="isFieldReadonly(field)">
            <option v-for="opt in field.options" :key="opt" :value="opt">{{ opt }}</option>
          </select>

          <input v-else :id="field.key" v-model="formData[field.key]" :type="field.type || 'text'"
            :placeholder="field.placeholder" :disabled="isFieldReadonly(field)" :readonly="isFieldReadonly(field)"
            :min="field.min" :max="field.max" :step="field.step" :maxlength="field.maxlength" :class="{
              'input-readonly': isFieldReadonly(field),
              'input-valid': networkFieldState(field.key) === 'valid' || (formData[field.key] && !validationErrors[field.key] && hasValidation(field)),
              'input-error': networkFieldState(field.key) === 'error' || validationErrors[field.key]
            }" @input="validateField(field, formData[field.key])" />
          <span v-if="validationErrors[field.key]" class="validation-msg">{{ validationErrors[field.key] }}</span>
        </div>

        <span class="field-range">
          {{ formatRange(field) }}
        </span>

        <span class="field-help">
          <span v-if="isFieldReadonly(field)" class="lock-icon">
            <AppIcon name="lock" :size="12" />
          </span>
          {{ field.help }}
        </span>
      </div>

      <div class="form-actions">
        <button type="submit" class="btn-save" :disabled="saving || hasErrors">
          {{ saving ? 'Saving...' : 'Save' }}
        </button>
        <button type="button" class="btn-cancel" @click="reset">Reset</button>
      </div>

      <div v-if="message" class="message" :class="messageType">
        {{ message }}
      </div>

      <template v-if="section === 'sensors'">
        <div class="section-divider"><span>System Clock</span></div>
        <div class="field-row">
          <label>Current time</label>
          <div class="field-input">
            <span class="clock-readout">{{ currentTime || '—' }}</span>
          </div>
          <span class="field-range"></span>
          <span class="field-help">Live device clock</span>
        </div>
        <div class="field-row">
          <label for="clock-input">Set time</label>
          <div class="field-input">
            <input id="clock-input" type="datetime-local" v-model="clockInput" :step="1" />
          </div>
          <span class="field-range"></span>
          <div class="clock-row-actions">
            <button type="button" class="btn-cancel" @click="setClockToNow">Now</button>
            <button type="button" class="btn-save" :disabled="clockSaving || !clockInput" @click="setClock">
              {{ clockSaving ? 'Setting...' : 'Set Clock' }}
            </button>
          </div>
        </div>
        <div v-if="clockMessage" class="message" :class="clockMessageType" style="margin: 0 20px 10px;">
          {{ clockMessage }}
        </div>
        <p class="clock-help">Sets the system clock for offline units without NTP. GPS will correct it automatically once acumon acquires a fix.</p>
      </template>
    </form>

  </div>
</template>

<script>
import axios from 'axios'
import AppIcon from './AppIcon.vue'

const API_URL = import.meta.env.VITE_API_URL || ''

function _ipToInt(ip) {
  const parts = ip.split('.').map(Number)
  if (parts.length !== 4 || parts.some(p => isNaN(p) || p < 0 || p > 255)) return null
  return ((parts[0] << 24) | (parts[1] << 16) | (parts[2] << 8) | parts[3]) >>> 0
}

function _isValidIp(ip) {
  return _ipToInt(ip) !== null
}

function _isValidMask(mask) {
  const n = _ipToInt(mask)
  if (!n) return false
  const inv = (~n >>> 0)
  return inv === 0 || (inv & (inv + 1)) === 0
}

function _sameSubnet(ip, mask, gw) {
  const i = _ipToInt(ip), m = _ipToInt(mask), g = _ipToInt(gw)
  if (i === null || m === null || g === null) return null
  return (i & m) === (g & m)
}

export default {
  name: 'Config',
  components: {
    AppIcon
  },
  props: {
    section: {
      type: String,
      required: true
    }
  },
  data() {
    return {
      loading: false,
      saving: false,
      title: 'Configuration',
      fields: [],
      formData: {},
      originalData: {},
      validationErrors: {},
      message: '',
      messageType: 'success',
      networkChanged: false,
      networkCheck: null,
      networkCheckPending: false,
      // System Clock (Advanced section only)
      currentTime: '',
      clockInput: '',
      clockSaving: false,
      clockMessage: '',
      clockMessageType: 'success',
      clockTimer: null,
    }
  },
  computed: {
    hasErrors() {
      return Object.keys(this.validationErrors).length > 0
    },
    isNetworkSection() {
      return this.section === 'network'
    },
    networkValidation() {
      if (!this.isNetworkSection) return { ipOk: null, maskOk: null, gwOk: null, subnetOk: null }
      const ip   = this.formData['acuIp']      || ''
      const mask = this.formData['acuMask']    || ''
      const gw   = this.formData['acuGateway'] || ''
      const ipOk   = ip   ? _isValidIp(ip)   : null
      const maskOk = mask ? _isValidMask(mask) : null
      const gwOk   = gw   ? _isValidIp(gw)   : null
      const subnetOk = (ipOk && maskOk && gwOk) ? _sameSubnet(ip, mask, gw) : null
      return { ipOk, maskOk, gwOk, subnetOk }
    },
  },
  watch: {
    section: {
      immediate: true,
      handler(newSection) {
        this.loadConfig(newSection)
        if (newSection === 'sensors') {
          this.startClockTick()
        } else {
          this.stopClockTick()
        }
      }
    }
  },
  beforeUnmount() {
    this.stopClockTick()
  },
  methods: {
    formatRange(field) {
      if (field.min !== undefined && field.max !== undefined) {
        return `${field.min} - ${field.max}`
      } else if (field.min !== undefined) {
        return `min: ${field.min}`
      } else if (field.max !== undefined) {
        return `max: ${field.max}`
      }
      return ''
    },

    isFieldReadonly(field) {
      if (field.readonly) return true
      // Location section: coordinate fields are readonly when GPS mode is active (SiteLocOverride === '0')
      if (this.section === 'location' && field.key !== 'SiteLocOverride') {
        return this.formData['SiteLocOverride'] === '0'
      }
      return false
    },

    hasValidation(field) {
      return !!field.pattern
    },

    validateField(field, value) {
      if (field.pattern) {
        const regex = new RegExp(field.pattern)
        if (value && !regex.test(value)) {
          this.validationErrors = { ...this.validationErrors, [field.key]: field.help || 'Invalid value' }
        } else {
          const { [field.key]: _, ...rest } = this.validationErrors
          this.validationErrors = rest
        }
      }
      if (this.isNetworkSection && ['acuIp', 'acuMask', 'acuGateway', 'acuDns'].includes(field.key)) {
        const keys = ['acuIp', 'acuMask', 'acuGateway', 'acuDns']
        this.networkChanged = keys.some(k => this.formData[k] !== this.originalData[k])
        this._scheduleNetworkCheck()
      }
    },

    networkFieldState(key) {
      if (!this.isNetworkSection) return null
      const v = this.networkValidation
      if (key === 'acuIp')      return v.ipOk   === true ? 'valid' : v.ipOk   === false ? 'error' : null
      if (key === 'acuMask')    return v.maskOk  === true ? 'valid' : v.maskOk  === false ? 'error' : null
      if (key === 'acuGateway') {
        if (v.gwOk === false)                     return 'error'
        if (v.subnetOk === false)                 return 'error'
        if (v.subnetOk === true)                  return 'valid'
        return null
      }
      if (key === 'acuDns') {
        const dns = this.formData['acuDns'] || ''
        if (!dns) return null
        return _isValidIp(dns) ? 'valid' : 'error'
      }
      return null
    },

    _scheduleNetworkCheck() {
      clearTimeout(this._netCheckTimer)
      if (!this.networkChanged) return
      if (this.networkValidation.subnetOk === false) return
      this._netCheckTimer = setTimeout(() => this.checkNetwork(), 900)
    },

    async checkNetwork() {
      const ip = this.formData['acuIp'] || ''
      const mask = this.formData['acuMask'] || ''
      const gateway = this.formData['acuGateway'] || ''
      this.networkCheckPending = true
      this.networkCheck = null
      try {
        const res = await axios.post(`${API_URL}/api/network/check`, { ip, mask, gateway })
        this.networkCheck = res.data
      } catch {
        this.networkCheck = null
      }
      this.networkCheckPending = false
    },

    async loadConfig(section) {
      this.loading = true
      this.message = ''
      this.formData = {}
      this.fields = []
      this.validationErrors = {}
      this.networkChanged = false
      this.networkCheck = null
      this.networkCheckPending = false

      try {
        const res = await axios.get(`${API_URL}/api/config/${section}`)

        this.title = res.data.title || 'Configuration'
        this.fields = res.data.fields || []

        this.fields.forEach(field => {
          const value = res.data.data?.[field.key]
          this.formData[field.key] = value !== undefined ? value : ''
        })

        this.originalData = { ...this.formData }

      } catch (e) {
        console.error('Error loading config:', e)
        this.message = 'Error loading configuration'
        this.messageType = 'error'
      }

      this.loading = false
    },

    async save() {
      this.saving = true
      this.message = ''

      if (this.hasErrors) {
        this.message = 'Fix validation errors before saving'
        this.messageType = 'error'
        this.saving = false
        return
      }

      try {
        await axios.post(`${API_URL}/api/config/${this.section}`, this.formData)
        this.messageType = 'success'
        if (this.isNetworkSection) {
          const newIp = this.formData['acuIp']
          const ipChanged = newIp && newIp !== this.originalData['acuIp']
          this.message = ipChanged
            ? `Network settings saved. Interface reconnecting — connect to ${newIp} if access is lost.`
            : 'Network settings saved. Interface is reconnecting.'
        } else {
          this.message = 'Configuration saved successfully!'
        }
        this.originalData = { ...this.formData }
        this.networkChanged = false
        this.networkCheck = null

      } catch (e) {
        console.error('Error saving config:', e)
        this.message = e.response?.data?.error || 'Error saving configuration'
        this.messageType = 'error'
      }

      this.saving = false

      setTimeout(() => {
        this.message = ''
      }, 3000)
    },

    reset() {
      this.formData = { ...this.originalData }
      this.validationErrors = {}
      this.message = ''
      this.networkChanged = false
      this.networkCheck = null
    },

    async startClockTick() {
      await this.syncClockOffset()
      this.tickClock()
      this.clockTimer = setInterval(this.tickClock, 1000)
      this._clockSyncTimer = setInterval(this.syncClockOffset, 60000)
    },
    stopClockTick() {
      if (this.clockTimer) { clearInterval(this.clockTimer); this.clockTimer = null }
      if (this._clockSyncTimer) { clearInterval(this._clockSyncTimer); this._clockSyncTimer = null }
    },
    async syncClockOffset() {
      try {
        const before = Date.now()
        const res = await axios.get(`${API_URL}/api/system/time`)
        const rtt = Date.now() - before
        this._clockOffset = res.data.unix_ms - before - rtt / 2
      } catch {
        // keep existing offset on error
      }
    },
    tickClock() {
      const piNow = new Date(Date.now() + (this._clockOffset || 0))
      this.currentTime = piNow.toLocaleString('en-CA', { hour12: false })
    },
    setClockToNow() {
      const pad = n => String(n).padStart(2, '0')
      const now = new Date()
      this.clockInput = `${now.getFullYear()}-${pad(now.getMonth()+1)}-${pad(now.getDate())}T${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())}`
    },
    async setClock() {
      if (!this.clockInput) return
      this.clockSaving = true
      this.clockMessage = ''
      try {
        await axios.post(`${API_URL}/api/system/set-time`, { datetime: this.clockInput })
        this.clockMessage = `Clock set to ${this.clockInput.replace('T', ' ')}`
        this.clockMessageType = 'success'
      } catch (e) {
        this.clockMessage = e.response?.data?.error || 'Failed to set clock'
        this.clockMessageType = 'error'
      } finally {
        this.clockSaving = false
        setTimeout(() => { this.clockMessage = '' }, 4000)
      }
    }
  }
}
</script>

<style scoped>
.config {
  padding: 20px;
}

h2 {
  margin-bottom: 20px;
  color: #333;
  font-size: 18px;
  font-weight: 500;
}

.loading {
  text-align: center;
  padding: 40px;
  color: #666;
}

/* FORM - table-like layout */
.config-form {
  background: white;
  border-radius: 4px;
  padding: 10px 0;
}

.field-row {
  display: grid;
  grid-template-columns: 150px 200px 100px 1fr;
  align-items: center;
  gap: 15px;
  padding: 12px 20px;
  border-bottom: 1px solid #f0f0f0;
}

.field-row:last-of-type {
  border-bottom: none;
}

.field-row label {
  font-size: 13px;
  color: #555;
  font-weight: 400;
}

.field-input input,
.field-input select {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 3px;
  font-size: 14px;
  background: #fafafa;
  box-sizing: border-box;
  transition: border-color 0.2s;
}

.field-input input:focus,
.field-input select:focus {
  outline: none;
  border-color: #999;
  background: #fff;
}

.field-input input::placeholder {
  color: #aaa;
  font-weight: 300;
}

.field-input input:disabled,
.field-input select:disabled {
  background: #f5f5f5;
  color: #999;
}

/* Validation styles */
.input-valid {
  border-color: #4ade80 !important;
}

.input-error {
  border-color: #f87171 !important;
  background: #fff5f5 !important;
}

.validation-msg {
  display: block;
  font-size: 11px;
  color: #f87171;
  margin-top: 4px;
}

/* Readonly field styling */
.field-readonly {
  background: #f5f5f5;
}

.input-readonly {
  background: #e8e8e8 !important;
  color: #333 !important;
  cursor: not-allowed;
  border: 1px solid #ccc !important;
  font-weight: 500;
}

.field-range {
  font-size: 12px;
  color: #888;
  white-space: nowrap;
}

.field-help {
  font-size: 12px;
  color: #666;
}

/* BUTTONS */
.form-actions {
  display: flex;
  gap: 10px;
  padding: 20px;
  border-top: 1px solid #eee;
  margin-top: 10px;
}

.btn-save {
  padding: 8px 20px;
  background: #4a90a4;
  color: white;
  border: none;
  border-radius: 3px;
  font-size: 13px;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-save:hover {
  background: #3d7a8c;
}

.btn-save:disabled {
  background: #999;
  cursor: not-allowed;
}

.btn-cancel {
  padding: 8px 20px;
  background: #f0f0f0;
  color: #666;
  border: none;
  border-radius: 3px;
  font-size: 13px;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-cancel:hover {
  background: #e0e0e0;
}

/* MESSAGE */
.message {
  margin: 15px 20px;
  padding: 10px 15px;
  border-radius: 3px;
  font-size: 13px;
}

.message.success {
  background: #e8f5e9;
  color: #2e7d32;
}

.message.error {
  background: #ffebee;
  color: #c62828;
}

.btn-group {
  display: inline-flex;
  border: 1px solid #ddd;
  border-radius: 3px;
  overflow: hidden;
}

.btn-group button {
  padding: 8px 20px;
  font-size: 13px;
  font-weight: 500;
  border: none;
  border-left: 1px solid #ddd;
  cursor: pointer;
  background: #f5f5f5;
  color: #999;
  transition: background 0.15s, color 0.15s;
}

.btn-group button:first-child {
  border-left: none;
}

.btn-group button.active {
  background: #4a90a4;
  color: white;
}

/* Responsive */
@media (max-width: 900px) {
  .field-row {
    grid-template-columns: 1fr;
    gap: 5px;
  }

  .field-range {
    order: 3;
  }

  .field-help {
    order: 4;
    padding-bottom: 10px;
  }
}

/* Network awareness panel */
.net-notice {
  margin-bottom: 16px;
  padding: 10px 14px;
  border-radius: 4px;
  background: #e8f4fd;
  border-left: 3px solid #42a5f5;
  font-size: 13px;
  color: #1565c0;
  transition: background 0.2s, border-color 0.2s;
}

.net-notice.net-warning {
  background: #fff8e1;
  border-color: #ffc107;
  color: #6d4c00;
}

.net-notice-inner {
  display: flex;
  gap: 10px;
  align-items: flex-start;
}

.net-icon {
  font-size: 15px;
  flex-shrink: 0;
  margin-top: 1px;
}

.net-ip-note {
  margin-top: 5px;
  font-size: 12px;
}

.net-ip-note code {
  font-family: monospace;
  background: rgba(0,0,0,0.08);
  padding: 1px 5px;
  border-radius: 3px;
}

.net-checks {
  display: flex;
  gap: 8px;
  margin-top: 6px;
  flex-wrap: wrap;
}

.net-chip {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 10px;
  background: rgba(0,0,0,0.07);
  color: #555;
}

.chip-ok { background: #e8f5e9; color: #2e7d32; }
.chip-warn { background: #fff3e0; color: #bf360c; font-weight: 500; }

/* System Clock — integrated into form as extra field rows */
.section-divider {
  padding: 12px 20px 4px;
  border-top: 1px solid #e8e8e8;
  margin-top: 8px;
}
.section-divider span {
  font-size: 11px;
  font-weight: 600;
  color: #999;
  text-transform: uppercase;
  letter-spacing: 0.06em;
}
.clock-readout {
  display: block;
  width: 100%;
  padding: 8px 12px;
  background: #f5f5f5;
  border: 1px solid #e0e0e0;
  border-radius: 3px;
  font-family: monospace;
  font-size: 13px;
  color: #333;
  box-sizing: border-box;
}
.clock-row-actions {
  display: flex;
  gap: 8px;
  align-items: center;
}
.clock-help {
  padding: 4px 20px 14px;
  font-size: 11px;
  color: #aaa;
  line-height: 1.5;
  margin: 0;
}
</style>