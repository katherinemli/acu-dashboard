<template>
  <div class="satellite-manager">
    <div class="header">
      <h2>Satellites Configuration</h2>
      <button class="btn-new" @click="openNew">+ New Satellite</button>
    </div>

    <!-- TLE Match Warning (global) -->
    <div v-if="globalTleWarning" class="tle-warning">
      ⚠️ {{ globalTleWarning }}
      <router-link to="/tools/tle-mgmt" class="warning-link">Go to TLE Management →</router-link>
    </div>
    
    <div v-if="loading" class="loading">Loading...</div>
    
    <div v-else class="satellite-grid">
      <div 
        v-for="sat in satellites" 
        :key="sat.id" 
        class="satellite-card"
        :class="{ 
          'active': sat.active && sat.tle_status !== 'missing',
          'warning': sat.active && sat.tle_status === 'missing'
        }"
      >
        <div class="card-header">
          <span class="sat-name">{{ sat.satName }}</span>
          <div class="header-badges">
            <span class="tle-led" :class="'led-' + sat.tle_status" :title="tleLedTitle(sat)"></span>
            <span v-if="sat.active && sat.tle_status !== 'missing'" class="badge-active">ACTIVE</span>
            <span v-if="sat.active && sat.tle_status === 'missing'" class="badge-active badge-warning">NO TLE</span>
          </div>
        </div>
        
        <div class="card-body">
          <div class="info-row">
            <span class="label">NORAD ID</span>
            <span class="value">{{ sat.satNoradId }}</span>
          </div>
          <div class="info-row">
            <span class="label">Operator</span>
            <span class="value">{{ sat.satOperator }}</span>
          </div>
          <div class="info-row">
            <span class="label">Position</span>
            <span class="value">{{ sat.satLong }}° {{ sat.satLongEW }}</span>
          </div>
          <div class="info-row">
            <span class="label">Polarization</span>
            <span class="value">RX: {{ sat.satRxPol }} / TX: {{ sat.satTxPol }}</span>
          </div>
          <div class="info-row">
            <span class="label">Band</span>
            <span class="value">{{ sat.satBandMhz }} MHz</span>
          </div>
          <div class="info-row" v-if="sat.tle_age_days !== null">
            <span class="label">TLE Age</span>
            <span class="value" :class="'tle-age-' + sat.tle_status">
              {{ sat.tle_age_days === 0 ? 'Today' : sat.tle_age_days + ' days' }}
            </span>
          </div>
          <div class="info-row" v-else>
            <span class="label">TLE</span>
            <span class="value tle-age-missing">Not available</span>
          </div>
        </div>
        
        <div class="card-actions">
          <button 
            v-if="!sat.active" 
            class="btn-activate" 
            @click="activate(sat)"
            title="Set as active satellite"
          >
            Activate
          </button>
          <button 
            class="btn-tle" 
            @click="openTleModal(sat)"
            title="View/edit TLE data"
          >
            TLE
          </button>
          <button 
            class="btn-edit" 
            @click="openEdit(sat)"
            title="Edit satellite"
          >
            Edit
          </button>
          <button 
            v-if="!sat.active" 
            class="btn-delete" 
            @click="confirmDelete(sat)"
            title="Delete satellite"
          >
            Delete
          </button>
        </div>
      </div>
    </div>
    
    <div v-if="showModal" class="modal-overlay" @click.self="closeModal">
      <div class="modal">
        <div class="modal-header">
          <h3>{{ editingSatellite ? 'Edit Satellite' : 'New Satellite' }}</h3>
          <button class="btn-close" @click="closeModal">×</button>
        </div>
        
        <form @submit.prevent="save" class="modal-body">
          <div v-for="field in fields" :key="field.key" class="field-row">
            <label :for="field.key">{{ field.label }}</label>
            
            <div class="field-input">
              <select 
                v-if="field.type === 'select'"
                :id="field.key"
                v-model="formData[field.key]"
              >
                <option v-for="opt in field.options" :key="opt" :value="opt">{{ opt }}</option>
              </select>
              
              <input 
                v-else
                :id="field.key"
                v-model="formData[field.key]" 
                :type="field.type || 'text'"
                :placeholder="field.placeholder"
                :min="field.min"
                :max="field.max"
                :step="field.step"
                :required="field.required"
              />
            </div>
            
            <span class="field-help">{{ field.help }}</span>
          </div>
          
          <div class="modal-actions">
            <button type="submit" class="btn-save" :disabled="saving">
              {{ saving ? 'Saving...' : 'Save' }}
            </button>
            <button type="button" class="btn-cancel" @click="closeModal">Cancel</button>
          </div>
        </form>
        
        <div v-if="error" class="error-msg">{{ error }}</div>
      </div>
    </div>
    
    <div v-if="showDeleteConfirm" class="modal-overlay" @click.self="showDeleteConfirm = false">
      <div class="modal modal-confirm">
        <div class="modal-header">
          <h3>Delete Satellite</h3>
        </div>
        <div class="modal-body">
          <p>Are you sure you want to delete <strong>{{ deletingSatellite?.satName }}</strong>?</p>
          <p class="warning">This action cannot be undone.</p>
        </div>
        <div class="modal-actions">
          <button class="btn-delete" @click="doDelete">Delete</button>
          <button class="btn-cancel" @click="showDeleteConfirm = false">Cancel</button>
        </div>
      </div>
    </div>

    <!-- TLE Quick Edit Modal -->
    <div v-if="showTleModal" class="modal-overlay" @click.self="closeTleModal">
      <div class="modal modal-tle">
        <div class="modal-header">
          <h3>TLE — {{ tleSatellite?.satName }}</h3>
          <button class="btn-close" @click="closeTleModal">×</button>
        </div>
        <div class="modal-body">
          <div class="tle-modal-info">
            <span class="tle-modal-norad">NORAD {{ tleSatellite?.satNoradId }}</span>
            <span v-if="tleCurrentAge !== null" class="tle-modal-age" :class="tleCurrentAgeClass">
              Current: {{ tleCurrentAge === 0 ? 'Today' : tleCurrentAge + ' days old' }}
            </span>
            <span v-else class="tle-modal-age tle-age-missing">No TLE in library</span>
          </div>

          <div v-if="tleCurrentRaw" class="tle-current-block">
            <label>Current TLE</label>
            <pre class="tle-raw-display">{{ tleCurrentRaw }}</pre>
          </div>

          <div class="tle-edit-block">
            <label>{{ tleCurrentRaw ? 'Paste new TLE to update' : 'Paste TLE data (3 lines)' }}</label>
            <textarea
              v-model="tleEditText"
              :placeholder="tlePlaceholder"
              rows="4"
              class="tle-edit-textarea"
            ></textarea>
          </div>

          <div v-if="tleEditError" class="error-msg">{{ tleEditError }}</div>
          <div v-if="tleEditSuccess" class="success-msg">{{ tleEditSuccess }}</div>
        </div>
        <div class="modal-actions">
          <button 
            class="btn-save" 
            @click="saveTleEdit" 
            :disabled="!tleEditText.trim() || tleSaving"
          >
            {{ tleSaving ? 'Saving...' : 'Save TLE' }}
          </button>
          <button class="btn-cancel" @click="closeTleModal">Close</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios'
import { useAcuStore } from '../stores/acu'

const API_URL = import.meta.env.VITE_API_URL || ''

export default {
  name: 'SatelliteList',
  setup() {
    const store = useAcuStore()
    return { store }
  },
  computed: {
    globalTleWarning() {
      return this.store.tleWarning
    }
  },
  data() {
    return {
      loading: true,
      saving: false,
      satellites: [],
      fields: [],
      formData: {},
      showModal: false,
      showDeleteConfirm: false,
      editingSatellite: null,
      deletingSatellite: null,
      error: '',
      // TLE quick-edit modal
      showTleModal: false,
      tleSatellite: null,
      tleCurrentRaw: '',
      tleCurrentAge: null,
      tleEditText: '',
      tleEditError: '',
      tleEditSuccess: '',
      tleSaving: false,
    }
  },
  mounted() {
    this.loadSatellites()
    this.loadFields()
    this._poll = setInterval(this.loadSatellites, 10000)
  },
  beforeUnmount() {
    if (this._poll) clearInterval(this._poll)
  },
  methods: {
    async loadSatellites() {
      try {
        const res = await axios.get(`${API_URL}/api/satellites`)
        this.satellites = res.data
      } catch (e) {
        console.error('Error loading satellites:', e)
      }
      this.loading = false
    },
    
    async loadFields() {
      try {
        const res = await axios.get(`${API_URL}/api/satellites/fields`)
        this.fields = res.data.fields
      } catch (e) {
        console.error('Error loading fields:', e)
      }
    },
    
    openNew() {
      this.editingSatellite = null
      this.formData = { satLongEW: 'E', satRxPol: 'V', satTxPol: 'H', satSearchPat: 'spiral' }
      this.error = ''
      this.showModal = true
    },
    
    openEdit(sat) {
      this.editingSatellite = sat
      this.formData = { ...sat }
      this.error = ''
      this.showModal = true
    },
    
    closeModal() {
      this.showModal = false
      this.editingSatellite = null
      this.error = ''
    },
    
    async save() {
      this.saving = true
      this.error = ''
      
      try {
        if (this.editingSatellite) {
          await axios.put(`${API_URL}/api/satellites/${this.editingSatellite.id}`, this.formData)
        } else {
          await axios.post(`${API_URL}/api/satellites`, this.formData)
        }
        
        this.closeModal()
        this.loadSatellites()
      } catch (e) {
        this.error = e.response?.data?.error || 'Error saving satellite'
      }
      
      this.saving = false
    },
    
    async activate(sat) {
      try {
        const res = await axios.post(`${API_URL}/api/satellites/${sat.id}/activate`)
        if (res.data.tle_warning) {
          alert(res.data.tle_warning)
        }
        this.loadSatellites()
      } catch (e) {
        alert(e.response?.data?.error || 'Error activating satellite')
      }
    },
    
    confirmDelete(sat) {
      this.deletingSatellite = sat
      this.showDeleteConfirm = true
    },
    
    async doDelete() {
      if (!this.deletingSatellite) return
      
      try {
        await axios.delete(`${API_URL}/api/satellites/${this.deletingSatellite.id}`)
        this.showDeleteConfirm = false
        this.deletingSatellite = null
        this.loadSatellites()
      } catch (e) {
        alert(e.response?.data?.error || 'Error deleting satellite')
        this.showDeleteConfirm = false
      }
    },

    tleLedTitle(sat) {
      if (sat.tle_status === 'ready') return `TLE available (${sat.tle_age_days} days old)`
      if (sat.tle_status === 'stale') return `TLE is stale (${sat.tle_age_days} days old)`
      return 'No TLE in library for this NORAD ID'
    },

    // ============ TLE QUICK-EDIT ============
    async openTleModal(sat) {
      this.tleSatellite = sat
      this.tleEditText = ''
      this.tleEditError = ''
      this.tleEditSuccess = ''
      this.tleCurrentRaw = ''
      this.tleCurrentAge = null
      this.showTleModal = true

      // Load current TLE from library
      const norad = sat.satNoradId
      if (norad) {
        try {
          const res = await axios.get(`${API_URL}/api/tle/library/${norad}`)
          if (res.data) {
            this.tleCurrentRaw = res.data.raw || ''
            this.tleCurrentAge = res.data.age_days
          }
        } catch {
          // No TLE exists — that's ok
        }
      }
    },

    closeTleModal() {
      this.showTleModal = false
      this.tleSatellite = null
    },

    async saveTleEdit() {
      const norad = this.tleSatellite?.satNoradId
      if (!norad || !this.tleEditText.trim()) return

      this.tleSaving = true
      this.tleEditError = ''
      this.tleEditSuccess = ''

      try {
        const res = await axios.put(`${API_URL}/api/tle/library/${norad}`, {
          text: this.tleEditText.trim()
        })
        this.tleEditSuccess = `TLE updated for ${res.data.parsed?.name || 'satellite'}`
        this.tleCurrentRaw = res.data.parsed?.raw || this.tleEditText.trim()
        this.tleCurrentAge = res.data.parsed?.age_days ?? null
        this.tleEditText = ''
        // Refresh card data
        this.loadSatellites()
      } catch (e) {
        this.tleEditError = e.response?.data?.error || 'Failed to save TLE'
      }

      this.tleSaving = false
    },
  },
  computed: {
    tlePlaceholder() {
      const name = this.tleSatellite?.satName || 'SATELLITE'
      return `${name}\n1 ${this.tleSatellite?.satNoradId || '99999'}U ...\n2 ${this.tleSatellite?.satNoradId || '99999'} ...`
    },
    tleCurrentAgeClass() {
      const d = this.tleCurrentAge
      if (d === null) return ''
      if (d <= 3) return 'tle-age-ready'
      if (d <= 14) return 'tle-age-stale'
      return 'tle-age-missing'
    },
  }
}
</script>

<style scoped>
.satellite-manager {
  padding: 20px;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.header h2 {
  margin: 0;
  color: #333;
  font-size: 18px;
}

.btn-new {
  padding: 8px 16px;
  background: #4a90a4;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
}

.btn-new:hover {
  background: #3d7a8c;
}

.loading {
  text-align: center;
  padding: 40px;
  color: #888;
}

.satellite-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 20px;
}

/* Card */
/* Card Base */
.satellite-card {
  background: white;
  border-radius: 6px;
  border: 2px solid #e0e0e0;
  overflow: hidden;
  transition: border-color 0.2s;
}

/* Header Base */
.satellite-card .card-header {
  background: #1e3a5f;
  color: white;
  padding: 12px 15px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.satellite-card.active {
  border-color: #4ade80;
}

.satellite-card.active .card-header {
  background: #166534;
  color: white;
}

.satellite-card.active .badge-active {
  background: #4ade80;
  color: #166534;
}

.satellite-card.warning {
  border-color: #f8c674;
}

.satellite-card.warning .card-header {
  background: #fff3e0;
  color: #854d0e;
}

.satellite-card.warning .badge-active {
  background: #f8c674;
  color: #78350f;
}

.sat-name {
  font-weight: 600;
  font-size: 16px;
}

.badge-active {
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
}

.badge-warning {
  background: #f8c674 !important;
  color: #78350f !important;
}

.header-badges {
  display: flex;
  align-items: center;
  gap: 8px;
}

.tle-led {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  display: inline-block;
  flex-shrink: 0;
}

.led-ready {
  background: #4ade80;
  box-shadow: 0 0 4px rgba(74, 222, 128, 0.5);
}

.led-stale {
  background: #fbbf24;
  box-shadow: 0 0 4px rgba(251, 191, 36, 0.5);
}

.led-missing {
  background: #f87171;
  box-shadow: 0 0 4px rgba(248, 113, 113, 0.5);
}

.tle-age-ready {
  color: #16a34a;
}

.tle-age-stale {
  color: #d97706;
}

.tle-age-missing {
  color: #dc2626;
  font-style: italic;
}

.satellite-card .card-body {
  padding: 15px;
}

.satellite-card .info-row {
  display: flex;
  justify-content: space-between;
  padding: 6px 0;
  border-bottom: 1px solid #f0f0f0;
  font-size: 13px;
}

.satellite-card .info-row:last-child {
  border-bottom: none;
}

.satellite-card .label {
  color: #666;
}

.satellite-card .value {
  color: #333;
  font-weight: 500;
}
/* Card actions */
.card-actions {
  padding: 10px 15px;
  background: #f9f9f9;
  border-top: 1px solid #eee;
  display: flex;
  gap: 8px;
}

.card-actions button {
  padding: 6px 12px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
  transition: background 0.2s;
}

.btn-activate {
  background: #dcfce7;
  color: #166534;
}

.btn-activate:hover {
  background: #bbf7d0;
}

.btn-edit {
  background: #e0e0e0;
  color: #333;
}

.btn-edit:hover {
  background: #d0d0d0;
}

.btn-tle {
  background: #e3f2fd;
  color: #1565c0;
}

.btn-tle:hover {
  background: #bbdefb;
}

.btn-delete {
  background: #fee2e2;
  color: #991b1b;
}

.btn-delete:hover {
  background: #fecaca;
}

/* Modal */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0,0,0,0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}

.modal {
  background: white;
  border-radius: 8px;
  width: 90%;
  max-width: 600px;
  max-height: 90vh;
  overflow-y: auto;
}

.modal-header {
  padding: 15px 20px;
  border-bottom: 1px solid #eee;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.modal-header h3 {
  margin: 0;
  font-size: 16px;
}

.btn-close {
  background: none;
  border: none;
  font-size: 24px;
  cursor: pointer;
  color: #666;
}

.modal-body {
  padding: 20px;
}

.modal-confirm .modal-body {
  text-align: center;
}

.modal-confirm .warning {
  color: #991b1b;
  font-size: 13px;
}

/* Form en modal */
.modal .field-row {
  display: grid;
  grid-template-columns: 120px 1fr 1fr;
  gap: 10px;
  align-items: center;
  margin-bottom: 12px;
}

.modal .field-row label {
  font-size: 13px;
  color: #555;
}

.modal .field-input input,
.modal .field-input select {
  width: 100%;
  padding: 8px 10px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
}

.modal .field-help {
  font-size: 11px;
  color: #888;
}

.modal .field-input input::placeholder {
  color: #aaa;
  font-weight: 300;
}

.modal-actions {
  padding: 15px 20px;
  border-top: 1px solid #eee;
  display: flex;
  gap: 10px;
  justify-content: flex-end;
}

.btn-save {
  padding: 8px 20px;
  background: #4a90a4;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.btn-save:disabled {
  background: #999;
}

.btn-cancel {
  padding: 8px 20px;
  background: #e0e0e0;
  color: #333;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.error-msg {
  padding: 10px 20px;
  background: #fee2e2;
  color: #991b1b;
  font-size: 13px;
}

.tle-warning {
  background: #fff3e0;
  border: 1px solid #ffcc80;
  color: #e65100;
  padding: 12px 16px;
  border-radius: 6px;
  font-size: 13px;
  margin-bottom: 16px;
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.warning-link {
  color: #1565c0;
  font-size: 12px;
  text-decoration: none;
  margin-left: auto;
}

.warning-link:hover {
  text-decoration: underline;
}

/* TLE Quick-Edit Modal */
.modal-tle {
  max-width: 650px;
}

.tle-modal-info {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.tle-modal-norad {
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 13px;
  color: #555;
  background: #f0f0f0;
  padding: 3px 10px;
  border-radius: 3px;
}

.tle-modal-age {
  font-size: 12px;
  font-weight: 500;
}

.tle-current-block {
  margin-bottom: 16px;
}

.tle-current-block label,
.tle-edit-block label {
  display: block;
  font-size: 12px;
  font-weight: 600;
  color: #666;
  text-transform: uppercase;
  margin-bottom: 6px;
}

.tle-raw-display {
  margin: 0;
  padding: 10px 12px;
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 12px;
  line-height: 1.6;
  background: #f8f9fa;
  border: 1px solid #e0e0e0;
  border-radius: 4px;
  white-space: pre;
  overflow-x: auto;
}

.tle-edit-textarea {
  width: 100%;
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 12px;
  line-height: 1.6;
  border: 1px solid #ddd;
  border-radius: 4px;
  padding: 10px 12px;
  resize: vertical;
  box-sizing: border-box;
}

.tle-edit-textarea:focus {
  outline: none;
  border-color: #999;
}

.success-msg {
  padding: 8px 12px;
  background: #e8f5e9;
  color: #2e7d32;
  font-size: 13px;
  border-radius: 4px;
  margin-top: 8px;
}

@media (max-width: 600px) {
  .modal .field-row {
    grid-template-columns: 1fr;
  }
}
</style>