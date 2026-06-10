<template>
  <div class="config-mgmt">
    <div class="top-bar">
      <h2>Save / Load Configuration</h2>
      <div class="quick-actions">
        <button class="btn-action backup" @click="openLoadBackup" :disabled="busy">
          <AppIcon name="clock" :size="14" /> Load Auto-Backup
        </button>
        <button class="btn-action factory" @click="showFactoryReset = true" :disabled="busy">
          <AppIcon name="warning" :size="14" /> Factory Reset
        </button>
      </div>
    </div>

    <!-- Single upload zone -->
    <div class="upload-zone"
         @dragover.prevent="isDragging = true"
         @dragleave="isDragging = false"
         @drop.prevent="onDrop"
         :class="{ dragging: isDragging }">
      <input type="file" ref="fileInput" @change="onFileSelect" accept=".ini" hidden />
      <div class="upload-inner" @click="$refs.fileInput.click()">
        <AppIcon name="file" :size="32" />
        <div class="upload-text">
          <span>Drag &amp; drop a <strong>.ini</strong> file here</span>
          <small>or click to browse — config.ini / satellites.ini</small>
        </div>
        <span v-if="uploading" class="chip-uploading">Uploading…</span>
      </div>
    </div>

    <!-- Message -->
    <div v-if="message" class="message" :class="messageType">{{ message }}</div>

    <!-- Two panels -->
    <div class="panels">

      <!-- config.ini panel -->
      <div class="panel">
        <div class="panel-title">
          <code>config.ini</code>
          <span class="badge-active">active</span>
          <a class="btn-download-active" :href="downloadUrl('active', 'config.ini')" download="config.ini">
            <AppIcon name="download" :size="13" /> Download
          </a>
        </div>

        <div v-if="loadingPreviews" class="panel-loading">Loading…</div>
        <div v-else class="preview-block">
          <div class="preview-group-label">Network</div>
          <div v-for="f in networkFields" :key="f.key" class="pr-row">
            <span class="pr-key">{{ f.label }}</span>
            <span class="pr-val">{{ activeNetwork[f.key] || '—' }}</span>
          </div>

          <template v-if="configExpanded">
            <div class="preview-group-label" style="margin-top:10px">System</div>
            <div class="pr-row">
              <span class="pr-key">Name</span>
              <span class="pr-val">{{ activeSystem.acuName || '—' }}</span>
            </div>
            <div class="pr-row">
              <span class="pr-key">Modem</span>
              <span class="pr-val">{{ activeSystem.modemType || '—' }}<template v-if="activeSystem.modemIp"> @ {{ activeSystem.modemIp }}</template></span>
            </div>
            <div class="pr-row">
              <span class="pr-key">Modem port</span>
              <span class="pr-val">{{ activeSystem.modemPort || '—' }}</span>
            </div>
          </template>

          <button class="btn-expand" @click="configExpanded = !configExpanded">
            {{ configExpanded ? '▲ Show less' : '▼ Show more' }}
          </button>
        </div>

        <!-- Pending config -->
        <div v-if="pendingConfig" class="pending-block">
          <div class="pending-header">
            <span class="pending-label">PENDING</span>
            <span class="pending-fname">{{ pendingConfig.filename }}</span>
            <span class="recognized-chip">config</span>
          </div>

          <div class="preview-group-label">Network</div>
          <div v-for="f in networkFields" :key="f.key"
               class="pr-row"
               :class="{ 'pr-changed': diffConfig(f.key) }">
            <span class="pr-key">{{ f.label }}</span>
            <span class="pr-val">{{ pendingVal(pendingConfig, 'Network', f.key) }}</span>
            <span v-if="diffConfig(f.key)" class="diff-old">← {{ activeNetwork[f.key] || '—' }}</span>
          </div>

          <template v-if="pendingConfigExpanded">
            <template v-for="(fields, section) in pendingConfig.parsed" :key="section">
              <template v-if="section !== 'Network' && section !== 'Storage'">
                <div class="preview-group-label" style="margin-top:8px">{{ section }}</div>
                <div v-for="(val, key) in fields" :key="key" class="pr-row">
                  <span class="pr-key">{{ key }}</span>
                  <span class="pr-val">{{ val }}</span>
                </div>
              </template>
            </template>
          </template>

          <button class="btn-expand" @click="pendingConfigExpanded = !pendingConfigExpanded">
            {{ pendingConfigExpanded ? '▲ Show less' : '▼ Show more' }}
          </button>

          <div class="pending-actions">
            <button class="btn-apply" @click="applyPending('config')" :disabled="busy">
              {{ busy ? '…' : 'Apply' }}
            </button>
            <button class="btn-discard" @click="discardPending('config')" :disabled="busy">Discard</button>
          </div>
        </div>
      </div>

      <!-- satellites.ini panel -->
      <div class="panel">
        <div class="panel-title">
          <code>satellites.ini</code>
          <span class="badge-active">active</span>
          <a class="btn-download-active" :href="downloadUrl('active', 'satellites.ini')" download="satellites.ini">
            <AppIcon name="download" :size="13" /> Download
          </a>
        </div>

        <div v-if="loadingPreviews" class="panel-loading">Loading…</div>
        <div v-else class="preview-block">
          <div class="preview-group-label">Satellites ({{ activeSatellites.length }})</div>
          <div v-if="activeSatellites.length === 0" class="pr-empty">No satellites configured</div>
          <div v-for="sat in (satsExpanded ? activeSatellites : activeSatellites.slice(0, 4))"
               :key="sat.satId" class="pr-row">
            <span class="pr-key sat-name">{{ sat.satName || '—' }}</span>
            <span class="pr-val pr-norad">NORAD {{ sat.satNoradId || '—' }}</span>
            <span v-if="sat.active == 1" class="sat-active-dot" title="Active satellite">●</span>
          </div>
          <button v-if="activeSatellites.length > 4" class="btn-expand" @click="satsExpanded = !satsExpanded">
            {{ satsExpanded ? '▲ Show less' : `▼ Show more (${activeSatellites.length - 4} more)` }}
          </button>
        </div>

        <!-- Pending satellite -->
        <div v-if="pendingSatellite" class="pending-block">
          <div class="pending-header">
            <span class="pending-label">PENDING</span>
            <span class="pending-fname">{{ pendingSatellite.filename }}</span>
            <span class="recognized-chip">satellites</span>
          </div>

          <div class="preview-group-label">Satellites</div>
          <template v-for="(fields, section) in pendingSatellite.parsed" :key="section">
            <div v-if="/^Satellite\d*/i.test(section)" class="pr-row">
              <span class="pr-key sat-name">{{ fields.satName || section }}</span>
              <span class="pr-val pr-norad">NORAD {{ fields.satNoradId || '—' }}</span>
            </div>
          </template>

          <div class="pending-actions">
            <button class="btn-apply" @click="applyPending('satellite')" :disabled="busy">
              {{ busy ? '…' : 'Apply' }}
            </button>
            <button class="btn-discard" @click="discardPending('satellite')" :disabled="busy">Discard</button>
          </div>
        </div>
      </div>

    </div><!-- /panels -->

    <!-- History -->
    <div class="history">
      <div class="history-header">
        <h3>History</h3>
        <button class="btn-refresh" @click="loadFiles">Refresh</button>
      </div>
      <div v-if="loadingFiles" class="loading">Loading…</div>
      <table v-else class="history-table">
        <thead>
          <tr>
            <th>File</th>
            <th>Type</th>
            <th>Date</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in visibleHistory" :key="item._key">
            <td class="mono">{{ item.name }}</td>
            <td><span :class="item.catClass">{{ item.cat }}</span></td>
            <td class="col-date">{{ item.modified }}</td>
            <td class="col-actions">
              <a :href="downloadUrl(item.dlCategory, item.name)" class="btn-sm btn-dl">Download</a>
              <button class="btn-sm btn-del" @click="item.onDelete()">Delete</button>
            </td>
          </tr>
          <tr v-if="allHistory.length === 0">
            <td colspan="4" class="no-data">No history yet</td>
          </tr>
          <tr v-if="allHistory.length > historyLimit">
            <td colspan="4" class="history-more">
              <button class="btn-load-more" @click="historyLimit += 10">
                Load more ({{ allHistory.length - historyLimit }} remaining)
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- FACTORY RESET MODAL -->
    <div v-if="showFactoryReset" class="modal-overlay" @click.self="showFactoryReset = false">
      <div class="modal">
        <h3><AppIcon name="warning" :size="15" /> Factory Reset</h3>
        <div class="modal-body">
          <p style="color:#d32f2f;font-weight:500">This will restore all configuration to factory defaults. All current settings will be lost.</p>
          <p>A backup of your current configuration will be created automatically before resetting.</p>
          <p style="margin-top:12px"><strong>Are you sure you want to continue?</strong></p>
        </div>
        <div class="modal-actions">
          <button class="btn-danger" @click="doFactoryReset" :disabled="busy">
            {{ busy ? 'Resetting…' : 'Reset to Factory Defaults' }}
          </button>
          <button class="btn-secondary" @click="showFactoryReset = false">Cancel</button>
        </div>
      </div>
    </div>

    <!-- LOAD BACKUP MODAL -->
    <div v-if="showLoadBackup" class="modal-overlay" @click.self="showLoadBackup = false">
      <div class="modal modal-wide">
        <h3>Load Auto-Backup</h3>
        <p class="modal-hint">
          Restores both config.ini and satellites.ini — including network settings (IP / Gateway).
          Ensure the backup was made in the same network environment.
        </p>
        <div class="modal-body">
          <div v-if="loadingBackups" class="loading">Loading…</div>
          <div v-else-if="backupList.length === 0" class="no-data">No auto-backups found</div>
          <div v-else class="file-list">
            <div v-for="item in backupList" :key="item.name"
                 class="file-item" :class="{ selected: selectedBackup === item.name }"
                 @click="selectedBackup = item.name">
              <span class="file-name">{{ formatTimestamp(item.name) }}</span>
              <span class="file-meta">{{ item.files.length }} files · {{ formatSize(item.size) }}</span>
              <span class="file-date">{{ item.modified }}</span>
            </div>
          </div>
        </div>
        <div class="modal-actions">
          <button class="btn-primary" @click="doLoadBackup" :disabled="!selectedBackup || busy">
            {{ busy ? 'Loading…' : 'Load Selected' }}
          </button>
          <button class="btn-secondary" @click="showLoadBackup = false">Cancel</button>
        </div>
      </div>
    </div>

  </div>
</template>

<script>
import axios from 'axios'
import AppIcon from './AppIcon.vue'

const API_URL = import.meta.env.VITE_API_URL || ''

export default {
  name: 'ConfigMgmt',
  components: { AppIcon },
  data() {
    return {
      busy: false,
      message: '',
      messageType: 'success',
      uploading: false,
      isDragging: false,

      // Active previews
      loadingPreviews: false,
      activeNetwork: {},
      activeSystem: {},
      activeSatellites: [],

      // Accordion
      configExpanded: false,
      satsExpanded: false,
      pendingConfigExpanded: false,

      // Pending uploads (one per type)
      pendingConfig: null,     // { filename, uploadedFilename, parsed }
      pendingSatellite: null,  // { filename, uploadedFilename, parsed }

      // History
      loadingFiles: false,
      backupList: [],
      uploadsList: [],
      historyLimit: 10,

      // Modals
      showFactoryReset: false,
      showLoadBackup: false,
      loadingBackups: false,
      selectedBackup: null,
    }
  },
  computed: {
    networkFields() {
      return [
        { key: 'acuIp',      label: 'MGMT IP'  },
        { key: 'acuGateway', label: 'Gateway'   },
        { key: 'acuMask',    label: 'Mask'      },
      ]
    },
    allHistory() {
      const rows = []
      for (const item of this.uploadsList) {
        rows.push({
          _key: 'up-' + item.name,
          name: item.name,
          cat: 'upload',
          catClass: 'cat-upload',
          modified: item.modified,
          dlCategory: 'uploads',
          onDelete: () => this.deleteUpload(item.name),
        })
      }
      for (const item of this.backupList) {
        for (const file of item.files) {
          rows.push({
            _key: 'bk-' + file,
            name: file,
            cat: 'backup',
            catClass: 'cat-backup',
            modified: item.modified,
            dlCategory: 'backup',
            onDelete: () => this.deleteBackup(item.name),
          })
        }
      }
      rows.sort((a, b) => b.modified.localeCompare(a.modified))
      return rows
    },
    visibleHistory() {
      return this.allHistory.slice(0, this.historyLimit)
    },
  },
  mounted() {
    this.loadFiles()
    this.fetchActivePreviews()
  },
  methods: {

    // ── Active previews ──────────────────────────────────────────────

    async fetchActivePreviews() {
      this.loadingPreviews = true
      const [netRes, sysRes, satRes] = await Promise.all([
        axios.get(`${API_URL}/api/config/network`).catch(() => null),
        axios.get(`${API_URL}/api/config/system`).catch(() => null),
        axios.get(`${API_URL}/api/satellites`).catch(() => null),
      ])
      if (netRes) this.activeNetwork = netRes.data.data || {}
      if (sysRes) this.activeSystem  = sysRes.data.data || {}
      if (satRes) this.activeSatellites = satRes.data || []
      this.loadingPreviews = false
    },

    // ── Upload ───────────────────────────────────────────────────────

    onFileSelect(e) {
      const file = e.target.files[0]
      if (file) this.handleNewFile(file)
      e.target.value = ''
    },

    onDrop(e) {
      this.isDragging = false
      const file = e.dataTransfer.files[0]
      if (file) this.handleNewFile(file)
    },

    async handleNewFile(file) {
      if (!file.name.endsWith('.ini')) {
        this.showMsg('error', 'Only .ini files are allowed')
        return
      }

      let text = ''
      try { text = await file.text() } catch {}

      const type   = this.detectFileType(text)
      const parsed = this.parseIni(text)

      this.uploading = true
      const formData = new FormData()
      formData.append('file', file)

      try {
        const res = await axios.post(`${API_URL}/api/config-mgmt/upload`, formData, {
          headers: { 'Content-Type': 'multipart/form-data' },
        })
        const uploadedFilename = res.data.filename

        if (type === 'satellite') {
          this.pendingSatellite = { filename: file.name, uploadedFilename, parsed }
        } else {
          this.pendingConfig = { filename: file.name, uploadedFilename, parsed }
          this.pendingConfigExpanded = false
        }

        this.loadFiles()
      } catch (e) {
        this.showMsg('error', e.response?.data?.error || 'Upload failed')
      }

      this.uploading = false
    },

    // ── Pending actions ──────────────────────────────────────────────

    async applyPending(type) {
      const pending = type === 'config' ? this.pendingConfig : this.pendingSatellite
      if (!pending) return

      this.busy = true
      try {
        await axios.post(`${API_URL}/api/config-mgmt/load-upload`, {
          filename: pending.uploadedFilename,
          type,
        })
        this.showMsg('success', `${pending.uploadedFilename} applied successfully`)

        if (type === 'config') {
          // Reactive optimistic update — data already parsed, no round-trip needed
          this.activeNetwork = { ...this.activeNetwork, ...(pending.parsed['Network'] || {}) }
          this.activeSystem  = { ...this.activeSystem,  ...(pending.parsed['System']  || {}) }
          this.pendingConfig = null
        } else {
          this.pendingSatellite = null
          const satRes = await axios.get(`${API_URL}/api/satellites`).catch(() => null)
          if (satRes) this.activeSatellites = satRes.data || []
        }

        this.loadFiles()
      } catch (e) {
        this.showMsg('error', e.response?.data?.error || 'Apply failed')
      }
      this.busy = false
    },

    discardPending(type) {
      if (type === 'config') this.pendingConfig = null
      else this.pendingSatellite = null
    },

    // ── INI utils ────────────────────────────────────────────────────

    detectFileType(text) {
      if (/^\[Satellite\d+\]/mi.test(text)) return 'satellite'
      if (/^\[Network\]/m.test(text) || /^\[System\]/m.test(text)) return 'config'
      return 'config'
    },

    parseIni(text) {
      const sections = {}
      let current = null
      for (const line of text.split(/\r?\n/)) {
        const trimmed = line.trim()
        if (!trimmed || trimmed.startsWith(';') || trimmed.startsWith('#')) continue
        if (trimmed.startsWith('[') && trimmed.endsWith(']')) {
          current = trimmed.slice(1, -1)
          sections[current] = {}
        } else if (current && trimmed.includes('=')) {
          const eqIdx = trimmed.indexOf('=')
          const rawKey = trimmed.slice(0, eqIdx).trim()
          const key    = rawKey.replace(/^[_*]/, '')
          const val    = trimmed.slice(eqIdx + 1).trim()
          sections[current][key] = val
        }
      }
      return sections
    },

    pendingVal(pending, section, key) {
      return pending?.parsed?.[section]?.[key] || '—'
    },

    diffConfig(key) {
      const pendingV = this.pendingConfig?.parsed?.Network?.[key]
      if (pendingV === undefined) return false
      return pendingV !== (this.activeNetwork[key] || '')
    },

    // ── Factory reset ────────────────────────────────────────────────

    async doFactoryReset() {
      this.busy = true
      try {
        const res = await axios.post(`${API_URL}/api/config-mgmt/factory-reset`)
        this.showMsg('success', res.data.message)
        this.showFactoryReset = false
        this.loadFiles()
        await this.fetchActivePreviews()
      } catch (e) {
        this.showMsg('error', e.response?.data?.error || 'Factory reset failed')
      }
      this.busy = false
    },

    // ── Load backup ──────────────────────────────────────────────────

    async openLoadBackup() {
      this.showLoadBackup = true
      this.selectedBackup = null
      this.loadingBackups = true
      try {
        const res = await axios.get(`${API_URL}/api/config-mgmt/files/backups`)
        this.backupList = res.data || []
      } catch { this.backupList = [] }
      this.loadingBackups = false
    },

    async doLoadBackup() {
      if (!this.selectedBackup) return
      if (!confirm(`Load backup "${this.formatTimestamp(this.selectedBackup)}"? Current config will be backed up automatically.`)) return
      this.busy = true
      try {
        const res = await axios.post(`${API_URL}/api/config-mgmt/load-backup`, { timestamp: this.selectedBackup })
        this.showMsg('success', res.data.message)
        this.showLoadBackup = false
        this.selectedBackup = null
        this.loadFiles()
        await this.fetchActivePreviews()
      } catch (e) {
        this.showMsg('error', e.response?.data?.error || 'Load failed')
      }
      this.busy = false
    },

    // ── File manager ─────────────────────────────────────────────────

    async loadFiles() {
      this.loadingFiles = true
      this.historyLimit = 10
      try {
        const res = await axios.get(`${API_URL}/api/config-mgmt/files`)
        this.backupList  = res.data.backups  || []
        this.uploadsList = res.data.uploads  || []
      } catch {
        this.backupList  = []
        this.uploadsList = []
      }
      this.loadingFiles = false
    },

    async deleteBackup(timestamp) {
      if (!confirm(`Delete backup "${this.formatTimestamp(timestamp)}"?`)) return
      try {
        await axios.delete(`${API_URL}/api/config-mgmt/files/backups/${timestamp}`)
        this.loadFiles()
      } catch (e) {
        this.showMsg('error', e.response?.data?.error || 'Delete failed')
      }
    },

    async deleteUpload(filename) {
      if (!confirm(`Delete uploaded file "${filename}"?`)) return
      try {
        await axios.delete(`${API_URL}/api/config-mgmt/files/uploads/${filename}`)
        this.loadFiles()
      } catch (e) {
        this.showMsg('error', e.response?.data?.error || 'Delete failed')
      }
    },

    downloadUrl(category, filename) {
      return `${API_URL}/api/config-mgmt/download/${category}/${filename}`
    },

    // ── Helpers ──────────────────────────────────────────────────────

    formatTimestamp(ts) {
      if (!ts || ts.length < 15) return ts
      return `${ts.slice(0,4)}-${ts.slice(4,6)}-${ts.slice(6,8)} ${ts.slice(9,11)}:${ts.slice(11,13)}:${ts.slice(13,15)}`
    },

    formatSize(bytes) {
      if (!bytes) return '0 B'
      if (bytes < 1024) return bytes + ' B'
      return (bytes / 1024).toFixed(1) + ' KB'
    },

    showMsg(type, text) {
      this.messageType = type
      this.message = text
      setTimeout(() => { this.message = '' }, 4000)
    },
  },
}
</script>

<style scoped>
.config-mgmt { padding: 20px; }

h2 { margin: 0; color: #333; font-size: 18px; font-weight: 500; }
h3 { margin: 0; font-size: 14px; color: #333; }

/* ── Top bar ── */
.top-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

/* ── Quick actions ── */
.quick-actions {
  display: flex;
  gap: 8px;
}

.btn-action {
  padding: 7px 14px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  font-weight: 600;
  color: white;
  transition: opacity 0.15s;
  white-space: nowrap;
}

.btn-action:hover:not(:disabled) { opacity: 0.88; }
.btn-action:disabled { opacity: 0.55; cursor: not-allowed; }
.btn-action.backup  { background: #78909c; }
.btn-action.factory { background: #d32f2f; }

/* ── Upload zone ── */
.upload-zone {
  border: 2px dashed #ccc;
  border-radius: 8px;
  margin-bottom: 14px;
  transition: border-color 0.2s, background 0.2s;
  cursor: pointer;
}

.upload-zone:hover, .upload-zone.dragging {
  border-color: #42a5f5;
  background: #f5faff;
}

.upload-inner {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 28px 32px;
  color: #666;
  font-size: 13px;
}

.upload-text {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.upload-text small {
  font-size: 11px;
  color: #aaa;
}

.chip-uploading {
  margin-left: auto;
  font-size: 12px;
  color: #42a5f5;
  background: #e3f2fd;
  padding: 2px 8px;
  border-radius: 10px;
}

/* ── Message ── */
.message {
  margin-bottom: 14px;
  padding: 10px 14px;
  border-radius: 4px;
  font-size: 13px;
}
.message.success { background: #e8f5e9; color: #2e7d32; }
.message.error   { background: #ffebee; color: #c62828; }

/* ── Panels ── */
.panels {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
  margin-bottom: 20px;
}

.panel {
  background: white;
  border: 1px solid #e0e0e0;
  border-radius: 6px;
  overflow: hidden;
}

.panel-title {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  background: #f5f5f5;
  border-bottom: 1px solid #e0e0e0;
  font-size: 13px;
}

.panel-title code {
  font-size: 13px;
  font-weight: 600;
  color: #1a2e4a;
}

.badge-active {
  font-size: 10px;
  font-weight: 600;
  padding: 1px 6px;
  border-radius: 10px;
  background: #e8f5e9;
  color: #2e7d32;
  margin-left: auto;
}

.btn-download-active {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  font-weight: 500;
  padding: 2px 8px;
  border-radius: 4px;
  background: #e3f2fd;
  color: #1976d2;
  text-decoration: none;
  cursor: pointer;
}

.btn-download-active:hover {
  background: #bbdefb;
}

.panel-loading {
  padding: 20px;
  text-align: center;
  color: #999;
  font-size: 13px;
}

/* ── Preview block (active) ── */
.preview-block {
  padding: 12px 16px;
}

.preview-group-label {
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: #999;
  margin-bottom: 5px;
}

.pr-row {
  display: flex;
  align-items: baseline;
  gap: 8px;
  padding: 3px 0;
  font-size: 13px;
  border-radius: 3px;
}

.pr-row.pr-changed {
  background: #fff8e1;
  margin: 0 -4px;
  padding: 3px 4px;
}

.pr-key {
  color: #777;
  min-width: 80px;
  flex-shrink: 0;
  font-size: 12px;
}

.pr-key.sat-name { min-width: 120px; color: #333; font-weight: 500; }

.pr-val { color: #222; font-family: monospace; font-size: 12px; }
.pr-val.pr-norad { color: #888; }

.diff-old {
  font-size: 11px;
  color: #bf360c;
  font-family: monospace;
}

.pr-empty { font-size: 12px; color: #aaa; padding: 4px 0; }

.sat-active-dot { color: #4a90a4; font-size: 10px; margin-left: auto; }

.btn-expand {
  margin-top: 8px;
  background: none;
  border: none;
  color: #4a90a4;
  font-size: 11px;
  cursor: pointer;
  padding: 0;
}

.btn-expand:hover { text-decoration: underline; }

/* ── Pending block ── */
.pending-block {
  padding: 12px 16px;
  background: #fafafa;
  border-top: 2px solid #ffe082;
}

.pending-header {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 8px;
  flex-wrap: wrap;
}

.pending-label {
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.06em;
  color: #856404;
}

.pending-fname {
  font-size: 12px;
  font-family: monospace;
  color: #444;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.recognized-chip {
  font-size: 10px;
  padding: 1px 6px;
  border-radius: 10px;
  background: #e3f2fd;
  color: #1565c0;
  font-weight: 600;
}

.pending-actions {
  display: flex;
  gap: 8px;
  margin-top: 10px;
}

.btn-apply {
  padding: 5px 14px;
  background: #4a90a4;
  color: white;
  border: none;
  border-radius: 4px;
  font-size: 12px;
  cursor: pointer;
  font-weight: 500;
}

.btn-apply:hover:not(:disabled) { background: #3d7a8c; }
.btn-apply:disabled { background: #aaa; cursor: not-allowed; }

.btn-discard {
  padding: 5px 14px;
  background: #f0f0f0;
  color: #555;
  border: none;
  border-radius: 4px;
  font-size: 12px;
  cursor: pointer;
}

.btn-discard:hover:not(:disabled) { background: #e0e0e0; }
.btn-discard:disabled { opacity: 0.5; cursor: not-allowed; }

/* ── History ── */
.history {
  background: white;
  border: 1px solid #e0e0e0;
  border-radius: 6px;
  overflow: hidden;
}

.history-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 16px;
  background: #f5f5f5;
  border-bottom: 1px solid #e0e0e0;
}

.btn-refresh {
  padding: 4px 12px;
  background: #369;
  color: white;
  border: none;
  border-radius: 4px;
  font-size: 12px;
  cursor: pointer;
}

.btn-refresh:hover { background: #2a547e; }

.history-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}

.history-table th {
  padding: 7px 14px;
  text-align: left;
  background: #fafafa;
  color: #888;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  border-bottom: 1px solid #eee;
}

.history-table td {
  padding: 7px 14px;
  border-bottom: 1px solid #f5f5f5;
  color: #333;
  vertical-align: middle;
}

.history-table tr:last-child td { border-bottom: none; }
.history-table tr:hover td { background: #fafcff; }

.mono { font-family: monospace; }

.col-date { color: #999; white-space: nowrap; }

.col-actions { display: flex; gap: 6px; justify-content: flex-end; }

.cat-upload { font-size: 10px; font-weight: 600; padding: 1px 5px; border-radius: 3px; background: #e3f2fd; color: #1565c0; }
.cat-backup { font-size: 10px; font-weight: 600; padding: 1px 5px; border-radius: 3px; background: #f5f5f5; color: #666; }

.btn-sm {
  padding: 3px 9px;
  border: none;
  border-radius: 3px;
  font-size: 11px;
  cursor: pointer;
  text-decoration: none;
  display: inline-block;
}

.btn-sm.btn-dl  { background: #e3f2fd; color: #1976d2; }
.btn-sm.btn-dl:hover { background: #bbdefb; }
.btn-sm.btn-del { background: #ffebee; color: #c62828; }
.btn-sm.btn-del:hover { background: #ffcdd2; }

.no-data { text-align: center; padding: 20px; color: #aaa; font-size: 13px; }
.loading  { text-align: center; padding: 20px; color: #999; font-size: 13px; }

.history-more { text-align: center; padding: 8px; }

.btn-load-more {
  background: none;
  border: 1px solid #ddd;
  border-radius: 4px;
  color: #4a90a4;
  font-size: 12px;
  padding: 5px 16px;
  cursor: pointer;
  transition: background 0.15s;
}
.btn-load-more:hover { background: #f0f9ff; border-color: #4a90a4; }

/* ── Modals ── */
.modal-overlay {
  position: fixed; top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0,0,0,0.45);
  display: flex; align-items: center; justify-content: center;
  z-index: 1000;
}

.modal {
  background: white;
  border-radius: 8px;
  box-shadow: 0 8px 32px rgba(0,0,0,0.2);
  width: 420px;
  max-height: 80vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.modal-wide { width: 560px; }

.modal h3 { padding: 14px 20px; border-bottom: 1px solid #eee; font-size: 14px; }

.modal-hint {
  padding: 8px 20px;
  font-size: 12px;
  color: #666;
  background: #f9f9f9;
  margin: 0;
  border-bottom: 1px solid #eee;
  line-height: 1.5;
}

.modal-body { padding: 16px 20px; overflow-y: auto; flex: 1; }

.modal-actions {
  padding: 12px 20px;
  border-top: 1px solid #eee;
  display: flex;
  gap: 10px;
  justify-content: flex-end;
}

.btn-primary {
  padding: 7px 18px; background: #4a90a4; color: white;
  border: none; border-radius: 4px; font-size: 13px; cursor: pointer;
}
.btn-primary:hover:not(:disabled) { background: #3d7a8c; }
.btn-primary:disabled { background: #aaa; cursor: not-allowed; }

.btn-secondary {
  padding: 7px 18px; background: #f0f0f0; color: #555;
  border: none; border-radius: 4px; font-size: 13px; cursor: pointer;
}
.btn-secondary:hover { background: #e0e0e0; }

.btn-danger {
  padding: 7px 18px; background: #d32f2f; color: white;
  border: none; border-radius: 4px; font-size: 13px; cursor: pointer; font-weight: 500;
}
.btn-danger:hover:not(:disabled) { background: #b71c1c; }
.btn-danger:disabled { opacity: 0.55; cursor: not-allowed; }

.file-list { max-height: 280px; overflow-y: auto; border: 1px solid #eee; border-radius: 4px; }

.file-item {
  display: flex; align-items: center; gap: 10px;
  padding: 9px 12px; border-bottom: 1px solid #f0f0f0;
  cursor: pointer; font-size: 13px; transition: background 0.12s;
}
.file-item:last-child { border-bottom: none; }
.file-item:hover { background: #f5f9ff; }
.file-item.selected { background: #e3f0ff; border-left: 3px solid #42a5f5; }

.file-name { font-weight: 500; color: #333; flex: 1; }
.file-meta { color: #aaa; font-size: 11px; }
.file-date { color: #aaa; font-size: 11px; min-width: 130px; text-align: right; }

/* ── Responsive ── */
@media (max-width: 860px) {
  .panels { grid-template-columns: 1fr; }
}
</style>
