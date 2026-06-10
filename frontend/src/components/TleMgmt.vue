<template>
  <div class="tools">
    <h2>TLE Management</h2>

    <!-- UPLOAD AREA -->
    <div class="upload-container">
      <div class="upload-header">
        <h3><AppIcon name="satellite" :size="16" /> Upload TLE Data</h3>
      </div>
      <div class="upload-body">
        <div
          class="upload-area"
          @dragover.prevent="isDragging = true"
          @dragleave="isDragging = false"
          @drop.prevent="handleDrop"
          :class="{ dragover: isDragging }"
        >
          <input type="file" ref="fileInput" @change="handleFileSelect" accept=".tle,.txt" hidden />
          <div class="upload-content" @click="$refs.fileInput.click()">
            <span class="upload-icon"><AppIcon name="satellite" :size="32" /></span>
            <p>Drag &amp; drop TLE file here<br/>or click to browse</p>
            <small class="upload-hint">.tle or .txt — supports multi-satellite files</small>
          </div>
        </div>

        <!-- Paste area -->
        <div class="paste-section">
          <div class="paste-header" @click="showPaste = !showPaste">
            <span><AppIcon name="clipboard" :size="14" /> Or paste TLE text directly</span>
            <span class="toggle-icon">{{ showPaste ? '▾' : '▸' }}</span>
          </div>
          <div v-if="showPaste" class="paste-body">
            <textarea
              v-model="pasteText"
              placeholder="ST-2
1 37606U 11022B   26090.36086191 -.00000225  00000-0  00000+0 0  9998
2 37606   0.0205 120.0852 0001945 261.6711  24.8792  1.00270603 54495"
              rows="6"
            ></textarea>
            <button class="btn-primary" @click="uploadPasted" :disabled="!pasteText.trim() || uploading">
              {{ uploading ? 'Uploading...' : 'Upload Pasted TLE' }}
            </button>
          </div>
        </div>

        <div v-if="uploading" class="upload-status">Uploading...</div>
      </div>
    </div>

    <!-- UPLOAD SUMMARY -->
    <div v-if="uploadSummary" class="upload-summary" :class="messageType">
      <div class="summary-header">
        {{ uploadSummary.total }} satellite{{ uploadSummary.total !== 1 ? 's' : '' }} processed
        <span v-if="uploadSummary.auto_activated" class="auto-activated"><AppIcon name="check" :size="12" /> Active TLE updated</span>
      </div>
      <div class="summary-items" v-if="uploadSummary.new.length || uploadSummary.updated.length">
        <span v-for="item in uploadSummary.new" :key="'n-' + item.norad_id" class="summary-chip new">
          {{ item.name }} <small>NEW</small>
        </span>
        <span v-for="item in uploadSummary.updated" :key="'u-' + item.norad_id" class="summary-chip updated">
          {{ item.name }} <small>UPDATED</small>
        </span>
      </div>
    </div>

    <!-- MESSAGE (simple) -->
    <div v-if="message && !uploadSummary" class="message" :class="messageType">
      {{ message }}
    </div>

    <!-- TLE INVENTORY (Library) -->
    <div class="file-manager">
      <div class="fm-header">
        <h3>Satellite TLE Inventory</h3>
        <button class="btn-refresh" @click="loadInventory">Refresh</button>
      </div>

      <div v-if="loadingInventory" class="loading">Loading...</div>

      <div v-else-if="inventory.length === 0" class="no-data">
        No TLEs in library. Upload a TLE file above.
      </div>

      <div v-else class="inv-table">
        <div class="inv-header-row">
          <span>Satellite</span>
          <span>NORAD ID</span>
          <span>Epoch</span>
          <span>Age</span>
          <span>Status</span>
          <span></span>
        </div>
        <div v-for="item in inventory" :key="item.norad_id" class="inv-row" :class="{ 'inv-active': item.is_active }">
          <span class="inv-name">
            {{ item.name }}
            <small v-if="item.satellite_name && item.satellite_name !== item.name" class="inv-config-name">
              ({{ item.satellite_name }})
            </small>
          </span>
          <span class="inv-norad">{{ item.norad_id }}</span>
          <span class="inv-epoch">{{ item.epoch?.split(' ')[0] }}</span>
          <span class="inv-age" :class="ageClassForDays(item.age_days)">
            {{ item.age_days === 0 ? 'Today' : item.age_days + 'd' }}
          </span>
          <span class="inv-status">
            <span v-if="item.is_active" class="status-chip active">Active</span>
            <span v-else-if="item.has_config" class="status-chip configured">Configured</span>
            <span v-else class="status-chip unmatched">No config</span>
          </span>
          <span class="inv-actions">
            <button
              class="btn-sm edit"
              @click="openEditTle(item)"
            >Edit</button>
            <button
              v-if="!item.is_active"
              class="btn-sm delete"
              @click="deleteFromLibrary(item.norad_id, item.name)"
            >Delete</button>
          </span>
        </div>
      </div>
    </div>

    <!-- ACTIVE TLE DETAIL -->
    <div class="tle-active" v-if="activeTle">
      <div class="fm-header">
        <h3>Active TLE Detail</h3>
        <span class="tle-age" :class="ageClass">{{ ageLabel }}</span>
      </div>
      <div v-if="tleWarning" class="tle-mismatch-warning">
        <AppIcon name="warning" :size="14" /> {{ tleWarning }}
      </div>
      <div class="tle-detail">
        <div class="tle-parsed">
          <div class="tle-field">
            <label>Satellite</label>
            <span>{{ activeTle.name }}</span>
          </div>
          <div class="tle-field">
            <label>NORAD ID</label>
            <span>{{ activeTle.norad_id }}</span>
          </div>
          <div class="tle-field">
            <label>Int'l Designator</label>
            <span>{{ activeTle.intl_designator }}</span>
          </div>
          <div class="tle-field">
            <label>Epoch</label>
            <span>{{ activeTle.epoch }}</span>
          </div>
          <div class="tle-field">
            <label>Inclination</label>
            <span>{{ activeTle.inclination }}°</span>
          </div>
          <div class="tle-field">
            <label>RAAN</label>
            <span>{{ activeTle.raan }}°</span>
          </div>
          <div class="tle-field">
            <label>Eccentricity</label>
            <span>{{ activeTle.eccentricity }}</span>
          </div>
          <div class="tle-field">
            <label>Arg of Perigee</label>
            <span>{{ activeTle.arg_perigee }}°</span>
          </div>
          <div class="tle-field">
            <label>Mean Anomaly</label>
            <span>{{ activeTle.mean_anomaly }}°</span>
          </div>
          <div class="tle-field">
            <label>Mean Motion</label>
            <span>{{ activeTle.mean_motion }} rev/day</span>
          </div>
          <div class="tle-field">
            <label>Rev Number</label>
            <span>{{ activeTle.rev_number }}</span>
          </div>
        </div>
        <div class="tle-raw-section">
          <div class="tle-raw-header" @click="showRaw = !showRaw">
            <span>Raw TLE</span>
            <span class="toggle-icon">{{ showRaw ? '▾' : '▸' }}</span>
          </div>
          <pre v-if="showRaw" class="tle-raw">{{ activeTle.raw }}</pre>
        </div>
      </div>
    </div>

    <!-- TLE HISTORY (uploaded files) -->
    <div class="file-manager">
      <div class="fm-header">
        <h3>Upload History</h3>
        <button class="btn-refresh" @click="loadHistory">Refresh</button>
      </div>

      <div v-if="loadingHistory" class="loading">Loading...</div>

      <div v-else-if="historyFiles.length === 0" class="no-data">
        No TLE files uploaded yet.
      </div>

      <div v-else class="fm-table">
        <div v-for="item in historyFiles" :key="item.filename" class="fm-row">
          <span class="fm-name">{{ item.filename }}</span>
          <span class="fm-sat-count">{{ item.satellite_count }} sat{{ item.satellite_count !== 1 ? 's' : '' }}</span>
          <span class="fm-date">{{ item.uploaded_at }}</span>
          <span class="fm-actions">
            <a :href="downloadTleUrl(item.filename)" class="btn-sm download">Download</a>
            <button
              class="btn-sm delete"
              @click="deleteHistory(item.filename)"
            >Delete</button>
          </span>
        </div>
      </div>
    </div>

    <!-- TLE Edit Modal -->
    <div v-if="showEditModal" class="modal-overlay" @click.self="closeEditModal">
      <div class="modal modal-tle-edit">
        <div class="modal-header">
          <h3>Edit TLE — {{ editingTle?.name }}</h3>
          <button class="btn-close" @click="closeEditModal">×</button>
        </div>
        <div class="modal-body">
          <div class="tle-edit-info">
            <span class="tle-edit-norad">NORAD {{ editingTle?.norad_id }}</span>
            <span v-if="editingTle?.age_days !== null" class="tle-edit-age" :class="ageClassForDays(editingTle?.age_days)">
              {{ editingTle?.age_days === 0 ? 'Today' : editingTle?.age_days + ' days old' }}
            </span>
          </div>

          <div class="tle-edit-block">
            <label>TLE Data (3 lines)</label>
            <textarea
              v-model="editTleText"
              rows="5"
              class="tle-edit-textarea"
            ></textarea>
          </div>

          <div v-if="editTleError" class="edit-error">{{ editTleError }}</div>
          <div v-if="editTleSuccess" class="edit-success">{{ editTleSuccess }}</div>
        </div>
        <div class="modal-actions">
          <button class="btn-save" @click="saveEditTle" :disabled="!editTleText.trim() || editTleSaving">
            {{ editTleSaving ? 'Saving...' : 'Save' }}
          </button>
          <button class="btn-cancel" @click="closeEditModal">Cancel</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || ''
import AppIcon from './AppIcon.vue'


import { useAcuStore } from '../stores/acu'

export default {
  name: 'TleMgmt',
  components: {
    AppIcon
  },
  setup() {
    const store = useAcuStore()
    return { store }
  },
  data() {
    return {
      isDragging: false,
      uploading: false,
      message: '',
      messageType: 'success',
      uploadSummary: null,
      showPaste: false,
      pasteText: '',
      showRaw: false,

      activeTle: null,

      inventory: [],
      loadingInventory: true,

      historyFiles: [],
      loadingHistory: false,

      // Edit TLE modal
      showEditModal: false,
      editingTle: null,
      editTleText: '',
      editTleError: '',
      editTleSuccess: '',
      editTleSaving: false,
    }
  },
  computed: {
    tleWarning() {
      return this.store.tleWarning
    },
    ageLabel() {
      if (!this.activeTle?.epoch) return ''
      try {
        const epoch = new Date(this.activeTle.epoch)
        const now = new Date()
        const diffDays = Math.floor((now - epoch) / (1000 * 60 * 60 * 24))
        if (diffDays === 0) return 'Today'
        if (diffDays === 1) return '1 day old'
        return `${diffDays} days old`
      } catch {
        return ''
      }
    },
    ageClass() {
      if (!this.activeTle?.epoch) return ''
      try {
        const epoch = new Date(this.activeTle.epoch)
        const diffDays = Math.floor((new Date() - epoch) / (1000 * 60 * 60 * 24))
        if (diffDays <= 3) return 'age-fresh'
        if (diffDays <= 7) return 'age-ok'
        if (diffDays <= 14) return 'age-warn'
        return 'age-stale'
      } catch {
        return ''
      }
    }
  },
  mounted() {
    this.loadActiveTle()
    this.loadInventory()
    this.loadHistory()
    this._poll = setInterval(() => {
      this.loadActiveTle()
      this.loadInventory()
    }, 10000)
  },
  beforeUnmount() {
    if (this._poll) clearInterval(this._poll)
  },
  methods: {
    ageClassForDays(days) {
      if (days === null || days === undefined) return ''
      if (days <= 3) return 'age-fresh'
      if (days <= 7) return 'age-ok'
      if (days <= 14) return 'age-warn'
      return 'age-stale'
    },

    // ============ UPLOAD ============
    handleFileSelect(e) {
      const file = e.target.files[0]
      if (file) this.uploadFile(file)
      e.target.value = ''
    },

    handleDrop(e) {
      this.isDragging = false
      const file = e.dataTransfer.files[0]
      if (file) this.uploadFile(file)
    },

    async uploadFile(file) {
      this.uploading = true
      this.clearMessage()

      const formData = new FormData()
      formData.append('file', file)

      try {
        const res = await axios.post(`${API_URL}/api/tle/upload`, formData, {
          headers: { 'Content-Type': 'multipart/form-data' }
        })
        this.uploadSummary = res.data.summary || null
        this.messageType = 'success'
        if (!this.uploadSummary) {
          this.message = res.data.message
        }
        this.refreshAll()
      } catch (e) {
        this.showMsg('error', e.response?.data?.error || 'Upload failed')
      }

      this.uploading = false
    },

    async uploadPasted() {
      if (!this.pasteText.trim()) return
      this.uploading = true
      this.clearMessage()

      try {
        const res = await axios.post(`${API_URL}/api/tle/upload-text`, {
          text: this.pasteText.trim()
        })
        this.uploadSummary = res.data.summary || null
        this.messageType = 'success'
        if (!this.uploadSummary) {
          this.message = res.data.message
        }
        this.pasteText = ''
        this.showPaste = false
        this.refreshAll()
      } catch (e) {
        this.showMsg('error', e.response?.data?.error || 'Upload failed')
      }

      this.uploading = false
    },

    refreshAll() {
      this.loadActiveTle()
      this.loadInventory()
      this.loadHistory()
    },

    // ============ LOAD DATA ============
    async loadActiveTle() {
      try {
        const res = await axios.get(`${API_URL}/api/tle/active`)
        this.activeTle = res.data || null
      } catch {
        this.activeTle = null
      }
    },

    async loadInventory() {
      try {
        const res = await axios.get(`${API_URL}/api/tle/inventory`)
        this.inventory = res.data || []
      } catch {
        this.inventory = []
      }
      this.loadingInventory = false
    },

    async loadHistory() {
      this.loadingHistory = true
      try {
        const res = await axios.get(`${API_URL}/api/tle/history`)
        this.historyFiles = res.data || []
      } catch {
        this.historyFiles = []
      }
      this.loadingHistory = false
    },

    // ============ ACTIONS ============
    async deleteFromLibrary(noradId, name) {
      if (!confirm(`Delete TLE for ${name} (NORAD ${noradId}) from library?`)) return
      try {
        await axios.delete(`${API_URL}/api/tle/library/${noradId}`)
        this.showMsg('success', `TLE for ${name} deleted`)
        this.refreshAll()
      } catch (e) {
        this.showMsg('error', e.response?.data?.error || 'Delete failed')
      }
    },

    async deleteHistory(filename) {
      if (!confirm(`Delete history file "${filename}"?`)) return
      try {
        await axios.delete(`${API_URL}/api/tle/files/${filename}`)
        this.showMsg('success', `"${filename}" deleted`)
        this.loadHistory()
      } catch (e) {
        this.showMsg('error', e.response?.data?.error || 'Delete failed')
      }
    },

    downloadTleUrl(filename) {
      return `${API_URL}/api/tle/download/${filename}`
    },

    // ============ EDIT TLE MODAL ============
    async openEditTle(item) {
      this.editingTle = item
      this.editTleError = ''
      this.editTleSuccess = ''
      this.showEditModal = true

      // Load current raw TLE
      try {
        const res = await axios.get(`${API_URL}/api/tle/library/${item.norad_id}`)
        this.editTleText = res.data.raw || ''
      } catch {
        this.editTleText = ''
      }
    },

    closeEditModal() {
      this.showEditModal = false
      this.editingTle = null
    },

    async saveEditTle() {
      if (!this.editingTle || !this.editTleText.trim()) return

      this.editTleSaving = true
      this.editTleError = ''
      this.editTleSuccess = ''

      try {
        const res = await axios.put(`${API_URL}/api/tle/library/${this.editingTle.norad_id}`, {
          text: this.editTleText.trim()
        })
        this.editTleSuccess = `TLE updated for ${res.data.parsed?.name || 'satellite'}`
        this.refreshAll()
      } catch (e) {
        this.editTleError = e.response?.data?.error || 'Failed to save TLE'
      }

      this.editTleSaving = false
    },

    // ============ HELPERS ============
    showMsg(type, text) {
      this.uploadSummary = null
      this.messageType = type
      this.message = text
      setTimeout(() => { this.message = '' }, 5000)
    },

    clearMessage() {
      this.message = ''
      this.uploadSummary = null
    }
  }
}
</script>

<style scoped>
.tools {
  padding: 20px;
}

h2 {
  margin-bottom: 20px;
  color: #333;
}

h3 {
  margin: 0;
  font-size: 14px;
  color: #333;
}

.loading {
  text-align: center;
  padding: 20px;
  color: #666;
}

.no-data {
  text-align: center;
  padding: 20px;
  color: #999;
  font-size: 13px;
}

/* UPLOAD */
.upload-container {
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  margin-bottom: 15px;
  overflow: hidden;
}

.upload-header {
  padding: 15px 20px;
  background: #f5f5f5;
  border-bottom: 1px solid #eee;
}

.upload-body {
  padding: 20px;
}

.upload-area {
  border: 2px dashed #ddd;
  border-radius: 8px;
  padding: 30px;
  text-align: center;
  cursor: pointer;
  transition: border-color 0.2s, background 0.2s;
}

.upload-area:hover {
  border-color: #aaa;
  background: #fafafa;
}

.upload-area.dragover {
  border-color: #42a5f5;
  background: #e3f2fd;
}

.upload-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
}

.upload-icon {
  font-size: 32px;
}

.upload-content p {
  color: #666;
  font-size: 13px;
  margin: 0;
}

.upload-hint {
  color: #999;
  font-size: 11px;
}

.upload-status {
  text-align: center;
  padding: 10px;
  color: #42a5f5;
  font-size: 13px;
}

/* PASTE */
.paste-section {
  margin-top: 12px;
  border: 1px solid #eee;
  border-radius: 6px;
  overflow: hidden;
}

.paste-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  background: #fafafa;
  cursor: pointer;
  font-size: 13px;
  color: #555;
  user-select: none;
}

.paste-header:hover {
  background: #f0f0f0;
}

.toggle-icon {
  font-size: 11px;
  color: #999;
}

.paste-body {
  padding: 14px;
  border-top: 1px solid #eee;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.paste-body textarea {
  width: 100%;
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  padding: 10px;
  resize: vertical;
  line-height: 1.5;
  box-sizing: border-box;
}

.paste-body textarea:focus {
  outline: none;
  border-color: #999;
}

.paste-body .btn-primary {
  align-self: flex-end;
}

/* MESSAGE */
.message {
  padding: 10px 15px;
  border-radius: 6px;
  margin-bottom: 15px;
  font-size: 13px;
}

.message.success {
  background: #e8f5e9;
  color: #2e7d32;
  border: 1px solid #c8e6c9;
}

.message.error {
  background: #ffebee;
  color: #c62828;
  border: 1px solid #ffcdd2;
}

/* ACTIVE TLE */
.tle-active {
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  margin-bottom: 15px;
  overflow: hidden;
}

.tle-mismatch-warning {
  background: #fff3e0;
  border-bottom: 1px solid #ffcc80;
  color: #e65100;
  padding: 10px 20px;
  font-size: 13px;
}

.tle-detail {
  padding: 20px;
}

.tle-parsed {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 12px;
  margin-bottom: 15px;
}

.tle-field {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.tle-field label {
  font-size: 11px;
  color: #888;
  text-transform: uppercase;
  font-weight: 600;
}

.tle-field span {
  font-size: 14px;
  color: #333;
  font-weight: 500;
}

/* Age indicator */
.tle-age {
  font-size: 11px;
  font-weight: 600;
  padding: 3px 8px;
  border-radius: 3px;
}

.age-fresh {
  background: #e8f5e9;
  color: #2e7d32;
}

.age-ok {
  background: #e3f2fd;
  color: #1565c0;
}

.age-warn {
  background: #fff3e0;
  color: #e65100;
}

.age-stale {
  background: #ffebee;
  color: #c62828;
}

/* Raw TLE */
.tle-raw-section {
  border: 1px solid #eee;
  border-radius: 4px;
  overflow: hidden;
}

.tle-raw-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  background: #fafafa;
  cursor: pointer;
  font-size: 12px;
  color: #666;
  user-select: none;
}

.tle-raw-header:hover {
  background: #f0f0f0;
}

.tle-raw {
  margin: 0;
  padding: 12px;
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 12px;
  line-height: 1.6;
  background: #f8f9fa;
  border-top: 1px solid #eee;
  white-space: pre;
  overflow-x: auto;
}

/* FILE MANAGER (reuse existing style) */
.file-manager {
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  overflow: hidden;
}

.fm-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 15px 20px;
  background: #f5f5f5;
  border-bottom: 1px solid #eee;
}

.btn-refresh {
  padding: 6px 14px;
  background: #369;
  color: white;
  border: none;
  border-radius: 4px;
  font-size: 12px;
  cursor: pointer;
}

.btn-refresh:hover { background: #2a547e; }

.fm-table {
  /* table rows */
}

.fm-row {
  display: grid;
  grid-template-columns: 1fr 60px 150px 120px;
  align-items: center;
  gap: 10px;
  padding: 8px 20px;
  border-bottom: 1px solid #f5f5f5;
  font-size: 13px;
}

.fm-row:last-child { border-bottom: none; }

.fm-name {
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 12px;
  color: #333;
}

.fm-category {
  font-size: 10px;
  font-weight: 600;
  padding: 2px 6px;
  border-radius: 3px;
  text-align: center;
}

.cat-active { background: #e8f5e9; color: #2e7d32; }
.cat-backup { background: #f5f5f5; color: #666; }

.fm-sat-name {
  font-size: 12px;
  color: #555;
}

.fm-date {
  font-size: 12px;
  color: #999;
}

.fm-actions {
  display: flex;
  gap: 6px;
  justify-content: flex-end;
}

.btn-sm {
  padding: 4px 10px;
  border: none;
  border-radius: 3px;
  font-size: 11px;
  cursor: pointer;
  text-decoration: none;
  display: inline-block;
}

.btn-sm.download {
  background: #e3f2fd;
  color: #1976d2;
}

.btn-sm.download:hover { background: #bbdefb; }

.btn-sm.activate {
  background: #e8f5e9;
  color: #2e7d32;
}

.btn-sm.activate:hover { background: #c8e6c9; }

.btn-sm.delete {
  background: #ffebee;
  color: #c62828;
}

.btn-sm.delete:hover { background: #ffcdd2; }

.btn-sm.edit {
  background: #e3f2fd;
  color: #1565c0;
}

.btn-sm.edit:hover { background: #bbdefb; }

/* TLE Edit Modal */
.modal-overlay {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0,0,0,0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}

.modal-tle-edit {
  background: white;
  border-radius: 8px;
  width: 90%;
  max-width: 650px;
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

.btn-save:disabled { background: #999; cursor: not-allowed; }

.btn-cancel {
  padding: 8px 20px;
  background: #e0e0e0;
  color: #333;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.tle-edit-info {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.tle-edit-norad {
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 13px;
  color: #555;
  background: #f0f0f0;
  padding: 3px 10px;
  border-radius: 3px;
}

.tle-edit-age {
  font-size: 12px;
  font-weight: 500;
}

.tle-edit-block label {
  display: block;
  font-size: 12px;
  font-weight: 600;
  color: #666;
  text-transform: uppercase;
  margin-bottom: 6px;
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

.edit-error {
  padding: 8px 12px;
  background: #ffebee;
  color: #c62828;
  font-size: 13px;
  border-radius: 4px;
  margin-top: 8px;
}

.edit-success {
  padding: 8px 12px;
  background: #e8f5e9;
  color: #2e7d32;
  font-size: 13px;
  border-radius: 4px;
  margin-top: 8px;
}

.btn-primary {
  padding: 8px 20px;
  background: #4a90a4;
  color: white;
  border: none;
  border-radius: 4px;
  font-size: 13px;
  cursor: pointer;
}

.btn-primary:hover:not(:disabled) { background: #3d7a8c; }
.btn-primary:disabled { background: #999; cursor: not-allowed; }

/* UPLOAD SUMMARY */
.upload-summary {
  padding: 12px 16px;
  border-radius: 6px;
  margin-bottom: 15px;
  font-size: 13px;
  border: 1px solid #c8e6c9;
  background: #e8f5e9;
  color: #2e7d32;
}

.upload-summary.error {
  background: #ffebee;
  color: #c62828;
  border-color: #ffcdd2;
}

.summary-header {
  font-weight: 600;
  margin-bottom: 8px;
  display: flex;
  align-items: center;
  gap: 10px;
}

.auto-activated {
  font-size: 11px;
  background: #c8e6c9;
  padding: 2px 8px;
  border-radius: 3px;
  color: #1b5e20;
}

.summary-items {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.summary-chip {
  font-size: 12px;
  padding: 3px 10px;
  border-radius: 12px;
  display: inline-flex;
  align-items: center;
  gap: 5px;
}

.summary-chip small {
  font-size: 9px;
  font-weight: 700;
  text-transform: uppercase;
  opacity: 0.7;
}

.summary-chip.new {
  background: #e3f2fd;
  color: #1565c0;
}

.summary-chip.updated {
  background: #f3e5f5;
  color: #7b1fa2;
}

/* INVENTORY TABLE */
.inv-table {
  font-size: 13px;
}

.inv-header-row {
  display: grid;
  grid-template-columns: 1.5fr 80px 100px 60px 90px 120px;
  gap: 10px;
  padding: 8px 20px;
  background: #fafafa;
  border-bottom: 1px solid #eee;
  font-size: 11px;
  font-weight: 600;
  color: #888;
  text-transform: uppercase;
}

.inv-row {
  display: grid;
  grid-template-columns: 1.5fr 80px 100px 60px 90px 120px;
  gap: 10px;
  padding: 10px 20px;
  border-bottom: 1px solid #f5f5f5;
  align-items: center;
}

.inv-row:last-child { border-bottom: none; }

.inv-row.inv-active {
  background: #f0fdf4;
}

.inv-name {
  font-weight: 500;
  color: #333;
}

.inv-config-name {
  color: #888;
  font-weight: 400;
}

.inv-norad {
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 12px;
  color: #555;
}

.inv-epoch {
  font-size: 12px;
  color: #666;
}

.inv-age {
  font-size: 12px;
  font-weight: 600;
}

.inv-actions {
  display: flex;
  gap: 6px;
  justify-content: flex-end;
}

.status-chip {
  font-size: 10px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 3px;
  text-align: center;
  display: inline-block;
}

.status-chip.active {
  background: #e8f5e9;
  color: #2e7d32;
}

.status-chip.configured {
  background: #e3f2fd;
  color: #1565c0;
}

.status-chip.unmatched {
  background: #f5f5f5;
  color: #999;
}

.fm-sat-count {
  font-size: 11px;
  color: #666;
  background: #f0f0f0;
  padding: 2px 8px;
  border-radius: 3px;
}

/* Responsive */
@media (max-width: 900px) {
  .tle-parsed {
    grid-template-columns: repeat(2, 1fr);
  }

  .fm-row {
    grid-template-columns: 1fr auto auto;
  }

  .fm-date { display: none; }

  .inv-header-row,
  .inv-row {
    grid-template-columns: 1fr 70px 60px 80px;
  }

  .inv-epoch, .inv-actions { display: none; }
}
</style>