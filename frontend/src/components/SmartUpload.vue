<template>
  <div class="su">
    <div class="su-bar">
      <span class="su-title">⇪ Smart Upload</span>
      <span class="su-hint">demo · dev tool · #/debug/upload</span>
      <span class="su-spacer"></span>
      <button class="su-act backup" :disabled="busy" @click="openLoadBackup">⟲ Load Auto-Backup</button>
      <button class="su-act danger" :disabled="busy" @click="showFactoryReset = true">⚠ Factory Reset</button>
    </div>

    <div class="su-body">
      <!-- Dropzone (multi-file) -->
      <div
        class="su-drop"
        :class="{ over: dragging, busy: detecting }"
        @dragover.prevent="dragging = true"
        @dragleave.prevent="dragging = false"
        @drop.prevent="onDrop"
        @click="$refs.picker.click()"
      >
        <input ref="picker" type="file" class="su-file" multiple @change="onPick" />
        <div class="su-drop-icon">⇪</div>
        <div class="su-drop-text">
          {{ detecting ? 'Detecting…' : 'Drop files here, or click to choose' }}
        </div>
        <div class="su-drop-sub">TLE · config.ini · satellites.ini — detected by content, drop several at once</div>
      </div>

      <!-- Files upload + validate on drop; activation is the explicit step.
           "Activate all" only applies to staged config/satellites .ini files. -->
      <div v-if="items.length" class="su-toolbar">
        <button v-if="stagedItems.length" class="su-apply" :disabled="busy" @click="activateAll">
          Activate all ({{ stagedItems.length }})
        </button>
        <button class="su-cancel" :disabled="busy" @click="clearAll">Clear</button>
      </div>

      <!-- 3 columns by file type -->
      <div class="su-cols">

        <!-- ── TLE ── -->
        <div class="su-col col-tle" :class="{ active: byType('tle').length > 0 }">
          <div class="su-col-head">TLE</div>
          <div class="su-col-body">
            <div v-for="it in byType('tle')" :key="it.id" class="su-item" :class="'st-' + it.status">
              <div class="su-item-top">
                <span class="su-fname">{{ it.filename }}</span>
                <button class="su-x" :disabled="it.status === 'applying'" @click="remove(it)">×</button>
              </div>
              <p class="su-summary">{{ it.summary }}</p>
              <div class="su-item-status" :class="'tag-' + it.status">{{ statusLabel(it) }}</div>
              <div v-if="it.message" class="su-msg" :class="{ err: it.status === 'error' }">{{ it.message }}</div>
              <div class="su-actions" v-if="it.status === 'staged'">
                <button class="su-apply sm" :disabled="busy" @click="activateItem(it)">Activate</button>
                <button class="su-cancel sm" :disabled="busy" @click="remove(it)">Discard</button>
              </div>
              <div class="su-actions" v-else-if="it.status === 'error'">
                <button class="su-apply sm" :disabled="busy" @click="retryItem(it)">Retry</button>
                <button class="su-cancel sm" :disabled="busy" @click="remove(it)">Discard</button>
              </div>
              <div v-else-if="it.status === 'detecting' || it.status === 'uploading'" class="su-applying">
                {{ it.status === 'detecting' ? 'Validating…' : 'Uploading…' }}
              </div>
              <div v-else-if="it.status === 'activating'" class="su-applying">Activating…</div>
            </div>

            <div class="su-state">
              <div class="su-state-head">
                <span class="su-state-label">TLE catalog ({{ invTle.length }})</span>
              </div>
              <input v-model="tleQuery" class="su-search" placeholder="Search satellite or NORAD…" />

              <div v-if="invTle.length === 0" class="su-col-empty">No TLEs in the catalog yet</div>
              <template v-else>
                <div v-if="tleVisible.length === 0" class="su-col-empty">
                  {{ tleQuery.trim() ? `No match for “${tleQuery}”` : 'Nothing active or configured yet' }}
                </div>
                <div v-else class="su-inv">
                  <div
                    v-for="i in tleVisible"
                    :key="i.norad_id"
                    class="su-inv-row"
                    :class="{ act: i.is_active, recent: isRecent(i) }"
                  >
                    <span class="su-inv-name">
                      {{ i.name }}
                      <span v-if="isRecent(i)" class="su-chip recent">just added</span>
                    </span>
                    <span class="su-inv-norad mono">{{ i.norad_id }}</span>
                    <span class="su-inv-age" :class="ageClassForDays(i.age_days)">
                      {{ i.age_days === 0 ? 'Today' : i.age_days + 'd' }}
                    </span>
                    <span class="su-chip" :class="i.is_active ? 'active' : (i.has_config ? 'configured' : 'unmatched')">
                      {{ i.is_active ? 'Active' : (i.has_config ? 'Configured' : 'No config') }}
                    </span>
                    <button v-if="!i.is_active" class="su-mini" :disabled="busy" @click="activateNorad(i.norad_id, i.name)">Activate</button>
                    <span v-else class="su-mini-spacer"></span>
                  </div>
                </div>
                <button v-if="!tleQuery.trim() && tleRestCount > 0" class="su-link" @click="showCatalog = !showCatalog">
                  {{ showCatalog ? '▲ Hide full catalog' : `▼ Show full catalog (${tleRestCount})` }}
                </button>
              </template>
            </div>
          </div>
        </div>

        <!-- ── config.ini ── -->
        <div class="su-col col-config" :class="{ active: byType('config').length > 0 }">
          <div class="su-col-head">config.ini</div>
          <div class="su-col-body">
            <div v-for="it in byType('config')" :key="it.id" class="su-item" :class="'st-' + it.status">
              <div class="su-item-top">
                <span class="su-fname">{{ it.filename }}</span>
                <button class="su-x" :disabled="it.status === 'applying'" @click="remove(it)">×</button>
              </div>
              <p class="su-summary">{{ it.summary }}</p>
              <div class="su-item-status" :class="'tag-' + it.status">{{ statusLabel(it) }}</div>
              <div v-if="it.message" class="su-msg" :class="{ err: it.status === 'error' }">{{ it.message }}</div>
              <div class="su-actions" v-if="it.status === 'staged'">
                <button class="su-apply sm" :disabled="busy" @click="activateItem(it)">Activate</button>
                <button class="su-cancel sm" :disabled="busy" @click="remove(it)">Discard</button>
              </div>
              <div class="su-actions" v-else-if="it.status === 'error'">
                <button class="su-apply sm" :disabled="busy" @click="retryItem(it)">Retry</button>
                <button class="su-cancel sm" :disabled="busy" @click="remove(it)">Discard</button>
              </div>
              <div v-else-if="it.status === 'detecting' || it.status === 'uploading'" class="su-applying">
                {{ it.status === 'detecting' ? 'Validating…' : 'Uploading…' }}
              </div>
              <div v-else-if="it.status === 'activating'" class="su-applying">Activating…</div>
            </div>

            <div class="su-state">
              <div class="su-state-head">
                <span class="su-state-label">Network <span class="su-badge-active">active</span></span>
                <a class="su-dl" :href="downloadUrl('active', 'config.ini')" download="config.ini">⤓ Download</a>
              </div>
              <div v-for="f in networkFields" :key="f.key" class="su-kv">
                <span class="su-kv-k">{{ f.label }}</span>
                <span class="su-kv-v mono">{{ activeNetwork[f.key] || '—' }}</span>
              </div>
              <button class="su-link" @click="showMoreConfig = !showMoreConfig">
                {{ showMoreConfig ? '▲ Show less' : '▼ Show more' }}
              </button>
              <template v-if="showMoreConfig">
                <div class="su-state-label sub">System</div>
                <div v-for="(v, k) in activeSystem" :key="k" class="su-kv">
                  <span class="su-kv-k">{{ k }}</span>
                  <span class="su-kv-v mono">{{ v }}</span>
                </div>
              </template>
            </div>
          </div>
        </div>

        <!-- ── satellites.ini ── -->
        <div class="su-col col-satellite" :class="{ active: byType('satellite').length > 0 }">
          <div class="su-col-head">satellites.ini</div>
          <div class="su-col-body">
            <div v-for="it in byType('satellite')" :key="it.id" class="su-item" :class="'st-' + it.status">
              <div class="su-item-top">
                <span class="su-fname">{{ it.filename }}</span>
                <button class="su-x" :disabled="it.status === 'applying'" @click="remove(it)">×</button>
              </div>
              <p class="su-summary">{{ it.summary }}</p>
              <div class="su-item-status" :class="'tag-' + it.status">{{ statusLabel(it) }}</div>
              <div v-if="it.message" class="su-msg" :class="{ err: it.status === 'error' }">{{ it.message }}</div>
              <div class="su-actions" v-if="it.status === 'staged'">
                <button class="su-apply sm" :disabled="busy" @click="activateItem(it)">Activate</button>
                <button class="su-cancel sm" :disabled="busy" @click="remove(it)">Discard</button>
              </div>
              <div class="su-actions" v-else-if="it.status === 'error'">
                <button class="su-apply sm" :disabled="busy" @click="retryItem(it)">Retry</button>
                <button class="su-cancel sm" :disabled="busy" @click="remove(it)">Discard</button>
              </div>
              <div v-else-if="it.status === 'detecting' || it.status === 'uploading'" class="su-applying">
                {{ it.status === 'detecting' ? 'Validating…' : 'Uploading…' }}
              </div>
              <div v-else-if="it.status === 'activating'" class="su-applying">Activating…</div>
            </div>

            <div class="su-state">
              <div class="su-state-head">
                <span class="su-state-label">Satellites ({{ activeSats.length }}) <span class="su-badge-active">active</span></span>
                <a class="su-dl" :href="downloadUrl('active', 'satellites.ini')" download="satellites.ini">⤓ Download</a>
              </div>
              <div v-if="activeSats.length === 0" class="su-col-empty">No satellites configured</div>
              <div v-for="s in (showMoreSats ? activeSats : activeSats.slice(0, 4))" :key="s.satId" class="su-kv">
                <span class="su-kv-k">{{ s.satName || '—' }}</span>
                <span class="su-kv-v mono">NORAD {{ s.satNoradId || '—' }}</span>
                <span v-if="s.active == 1" class="su-sat-dot" title="Active satellite">●</span>
              </div>
              <button v-if="activeSats.length > 4" class="su-link" @click="showMoreSats = !showMoreSats">
                {{ showMoreSats ? '▲ Show less' : `▼ Show more (${activeSats.length - 4} more)` }}
              </button>
            </div>
          </div>
        </div>

      </div>

      <!-- Unrecognized files -->
      <div v-if="byType('unknown').length" class="su-unknown">
        <div v-for="it in byType('unknown')" :key="it.id" class="su-unknown-row">
          <span class="su-fname">{{ it.filename }}</span>
          <span class="su-unknown-msg">{{ it.summary }}</span>
          <button class="su-x" @click="remove(it)">×</button>
        </div>
      </div>

      <!-- History -->
      <div class="su-history">
        <div class="su-history-head">
          <span class="su-state-label">History</span>
          <button class="su-link" @click="loadFiles">Refresh</button>
        </div>
        <table class="su-htable">
          <thead>
            <tr><th>File</th><th>Type</th><th>Date</th><th></th></tr>
          </thead>
          <tbody>
            <tr v-for="row in visibleHistory" :key="row._key">
              <td class="mono">{{ row.name }}</td>
              <td><span class="su-cat" :class="row.catClass">{{ row.cat }}</span></td>
              <td class="su-date">{{ row.modified }}</td>
              <td class="su-htable-act">
                <a :href="downloadUrl(row.dlCategory, row.name)" class="su-link">Download</a>
                <button class="su-link del" @click="row.onDelete()">Delete</button>
              </td>
            </tr>
            <tr v-if="allHistory.length === 0">
              <td colspan="4" class="su-col-empty">No history yet</td>
            </tr>
            <tr v-if="allHistory.length > historyLimit">
              <td colspan="4" class="su-more">
                <button class="su-link" @click="historyLimit += 10">
                  Load more ({{ allHistory.length - historyLimit }} remaining)
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Factory Reset modal -->
    <div v-if="showFactoryReset" class="su-overlay" @click.self="showFactoryReset = false">
      <div class="su-modal">
        <h3>⚠ Factory Reset</h3>
        <p class="danger-txt">This restores all configuration to factory defaults. Current settings will be lost.</p>
        <p>A backup of the current configuration is created automatically first.</p>
        <div class="su-modal-act">
          <button class="su-act danger" :disabled="busy" @click="doFactoryReset">
            {{ busy ? 'Resetting…' : 'Reset to Factory Defaults' }}
          </button>
          <button class="su-cancel" :disabled="busy" @click="showFactoryReset = false">Cancel</button>
        </div>
      </div>
    </div>

    <!-- Load Auto-Backup modal -->
    <div v-if="showLoadBackup" class="su-overlay" @click.self="showLoadBackup = false">
      <div class="su-modal wide">
        <h3>Load Auto-Backup</h3>
        <p class="su-hint dark">Restores both config.ini and satellites.ini — including network settings. Ensure the backup was made in the same network environment.</p>
        <div v-if="loadingBackups" class="su-col-empty">Loading…</div>
        <div v-else-if="backupList.length === 0" class="su-col-empty">No auto-backups found</div>
        <div v-else class="su-bk-list">
          <div
            v-for="b in backupList"
            :key="b.name"
            class="su-bk-item"
            :class="{ selected: selectedBackup === b.name }"
            @click="selectedBackup = b.name"
          >
            <span class="su-bk-name">{{ formatTimestamp(b.name) }}</span>
            <span class="su-bk-meta">{{ (b.files ? b.files.length : 0) }} files · {{ formatSize(b.size) }}</span>
            <span class="su-date">{{ b.modified }}</span>
          </div>
        </div>
        <div class="su-modal-act">
          <button class="su-apply" :disabled="!selectedBackup || busy" @click="doLoadBackup">
            {{ busy ? 'Loading…' : 'Load Selected' }}
          </button>
          <button class="su-cancel" :disabled="busy" @click="showLoadBackup = false">Cancel</button>
        </div>
      </div>
    </div>

    <!-- Toast -->
    <div v-if="message" class="su-toast" :class="messageType">{{ message }}</div>
  </div>
</template>

<script>
import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || ''

export default {
  name: 'SmartUpload',
  data() {
    return {
      dragging: false,
      detecting: false,
      working: false,
      seq: 0,
      items: [],   // { id, file, type, filename, summary, status, message }

      // Active state on the unit
      invTle: [],
      tleQuery: '',
      showCatalog: false,
      recentNorads: [],   // NORADs added/updated this session — pinned + highlighted
      activeNetwork: {},
      activeSystem: {},
      activeSats: [],
      showMoreConfig: false,
      showMoreSats: false,

      // History
      uploadsList: [],
      backupList: [],
      historyLimit: 10,

      // Modals
      showFactoryReset: false,
      showLoadBackup: false,
      loadingBackups: false,
      selectedBackup: null,

      message: '',
      messageType: 'success',
    }
  },
  computed: {
    busy() {
      return this.detecting || this.working ||
        this.items.some(i => i.status === 'uploading' || i.status === 'activating')
    },
    stagedItems() {
      return this.items.filter(i => i.status === 'staged')
    },
    // TLE catalog views: rank Active → just-added → Configured → rest, then name.
    tleSorted() {
      return [...this.invTle].sort((a, b) => {
        const r = this._tleRank(a) - this._tleRank(b)
        return r !== 0 ? r : String(a.name).localeCompare(String(b.name))
      })
    },
    // A bulk import (hundreds of TLEs) is a catalog load, not "find my sat", so
    // we don't pin every just-added row — that floods the view. Small, targeted
    // adds (a curated set) still pin + highlight. Either way the chip shows on
    // search/expand so they stay findable.
    pinRecent() {
      return this.recentNorads.length <= 25
    },
    tlePinned() {
      return this.tleSorted.filter(i =>
        i.is_active || i.has_config || (this.pinRecent && this.isRecent(i)))
    },
    tleRestCount() {
      return this.tleSorted.length - this.tlePinned.length
    },
    tleFiltered() {
      const q = this.tleQuery.trim().toLowerCase()
      if (!q) return this.tleSorted
      return this.tleSorted.filter(i =>
        String(i.name).toLowerCase().includes(q) ||
        String(i.satellite_name || '').toLowerCase().includes(q) ||
        String(i.norad_id).includes(q))
    },
    tleVisible() {
      if (this.tleQuery.trim()) return this.tleFiltered
      return this.showCatalog ? this.tleSorted : this.tlePinned
    },
    networkFields() {
      return [
        { key: 'acuIp', label: 'MGMT IP' },
        { key: 'acuGateway', label: 'Gateway' },
        { key: 'acuMask', label: 'Mask' },
      ]
    },
    allHistory() {
      const rows = []
      for (const u of this.uploadsList) {
        rows.push({
          _key: 'up-' + u.name, name: u.name, cat: 'upload', catClass: 'cat-upload',
          modified: u.modified, dlCategory: 'uploads', onDelete: () => this.deleteUpload(u.name),
        })
      }
      for (const b of this.backupList) {
        for (const file of (b.files || [])) {
          rows.push({
            _key: 'bk-' + file, name: file, cat: 'backup', catClass: 'cat-backup',
            modified: b.modified, dlCategory: 'backup', onDelete: () => this.deleteBackup(b.name),
          })
        }
      }
      rows.sort((a, b) => String(b.modified).localeCompare(String(a.modified)))
      return rows
    },
    visibleHistory() {
      return this.allHistory.slice(0, this.historyLimit)
    },
  },
  mounted() {
    this.fetchState()
    this.loadFiles()
  },
  methods: {
    byType(t) { return this.items.filter(i => i.type === t) },

    isRecent(i) { return this.recentNorads.includes(String(i.norad_id)) },
    _tleRank(i) {
      if (i.is_active) return 0
      if (this.isRecent(i)) return 1
      if (i.has_config) return 2
      return 3
    },

    // Activate one TLE from the catalog → points active.tle at that satellite.
    // Only one can be active at a time (a single symlink), so the inventory
    // refresh shows exactly one Active afterwards.
    async activateNorad(norad, name) {
      this.working = true
      try {
        const res = await axios.post(`${API_URL}/api/tle/activate`, { norad_id: String(norad) })
        this.showMsg('success', res.data.message || `Activated ${name} (${norad})`)
        await this.fetchState()
      } catch (e) {
        this.showMsg('error', this.errMsg(e, 'Activate failed'))
      }
      this.working = false
    },

    // ── Detection ──────────────────────────────────────────────────
    onDrop(e) { this.dragging = false; this.detectFiles(e.dataTransfer.files) },
    onPick(e) { this.detectFiles(e.target.files); if (this.$refs.picker) this.$refs.picker.value = '' },

    async detectFiles(fileList) {
      const files = Array.from(fileList || [])
      if (!files.length) return
      this.detecting = true
      try {
        for (const file of files) await this.detectOne(file)
      } finally {
        this.detecting = false
      }
    },

    async detectOne(file) {
      const item = {
        id: ++this.seq, file, type: 'unknown', filename: file.name, summary: '',
        status: 'detecting', message: '', step: '', historyFile: '', uploadedName: '',
      }
      this.items.push(item)
      // 1) Validate by content
      try {
        const fd = new FormData()
        fd.append('file', file)
        const res = await axios.post(`${API_URL}/api/debug/upload-detect`, fd)
        item.type = res.data.type
        item.summary = res.data.summary
        item.filename = res.data.filename || file.name
      } catch (e) {
        item.type = 'unknown'
        item.summary = this.errMsg(e, 'Detection failed')
      }
      if (item.type === 'unknown') return   // shown in the unrecognized banner
      // 2) Stage (upload) automatically — still NOT live; Activate is explicit
      await this.stageItem(item)
    },

    // ── Two-step apply: upload (stage) → activate ──────────────────
    // These are config-critical files, so nothing goes live on upload: the
    // file is validated (on drop) + staged, and only activated on an explicit
    // second action.
    statusLabel(it) {
      return {
        added: 'Added to catalog',
        staged: 'Uploaded · validated — not active',
        active: 'Active',
        error: 'Error',
      }[it.status] || ''
    },

    async activateAll() { for (const it of this.stagedItems) await this.activateItem(it) },

    // Stage = save to the server (uploads/ for ini, library for TLE) WITHOUT
    // going live. Runs automatically on drop — the file is already "uploaded".
    async stageItem(it) {
      if (it.type === 'unknown') return
      it.status = 'uploading'
      it.message = ''
      try {
        if (it.type === 'tle') {
          // TLE: add to the catalog only (activate=false). There is just ONE
          // active TLE (the configured satellite's), chosen per-row in the
          // catalog below — never bulk-activated here.
          const fd = new FormData()
          fd.append('file', it.file)
          fd.append('activate', 'false')
          const res = await axios.post(`${API_URL}/api/tle/upload`, fd)
          const s = res.data.summary || {}
          const norads = [...(s.new || []), ...(s.updated || [])].map(x => String(x.norad_id))
          if (norads.length) this.recentNorads = [...new Set([...this.recentNorads, ...norads])]
          it.message = `Added ${s.total || norads.length} satellite(s) to the catalog ` +
                       `(${(s.new || []).length} new, ${(s.updated || []).length} updated). ` +
                       `Find & activate one below.`
          it.status = 'added'
          await this.fetchState()   // refresh catalog so recent ones pin to top
          return
        }
        // config.ini / satellites.ini: stage to uploads/, NOT live yet.
        const canonical = it.type === 'config' ? 'config.ini' : 'satellites.ini'
        // Force a canonical .ini name so the backend's .ini-only check passes
        // regardless of the dropped file's actual name.
        const renamed = new File([it.file], canonical, { type: 'text/plain' })
        const fd = new FormData()
        fd.append('file', renamed)
        const up = await axios.post(`${API_URL}/api/config-mgmt/upload`, fd)
        it.uploadedName = up.data.filename || canonical
        it.message = 'Uploaded — not active yet'
        it.status = 'staged'
        await this.loadFiles()    // show the staged file in History
      } catch (e) {
        it.status = 'error'; it.step = 'upload'
        it.message = this.errMsg(e, 'Upload failed')
      }
    },

    async activateItem(it) {
      it.status = 'activating'
      it.message = ''
      try {
        if (it.type === 'tle') {
          const res = await axios.post(`${API_URL}/api/tle/activate`, { filename: it.historyFile })
          it.message = res.data.message || 'TLE activated.'
        } else {
          const res = await axios.post(`${API_URL}/api/config-mgmt/load-upload`, { filename: it.uploadedName, type: it.type })
          it.message = res.data.message || 'Activated (a backup was taken).'
        }
        it.status = 'active'
        await this.refreshAfterChange()
      } catch (e) {
        it.status = 'error'; it.step = 'activate'
        it.message = this.errMsg(e, 'Activate failed')
      }
    },

    retryItem(it) {
      if (it.step === 'activate') this.activateItem(it)
      else this.stageItem(it)
    },

    remove(it) { this.items = this.items.filter(i => i.id !== it.id) },
    clearAll() { this.items = [] },

    // ── Active state ───────────────────────────────────────────────
    async fetchState() {
      const [inv, net, sys, sat] = await Promise.all([
        axios.get(`${API_URL}/api/tle/inventory`).catch(() => null),
        axios.get(`${API_URL}/api/config/network`).catch(() => null),
        axios.get(`${API_URL}/api/config/system`).catch(() => null),
        axios.get(`${API_URL}/api/satellites`).catch(() => null),
      ])
      if (inv) this.invTle = inv.data || []
      if (net) this.activeNetwork = net.data.data || {}
      if (sys) this.activeSystem = sys.data.data || {}
      if (sat) this.activeSats = sat.data || []
    },

    async loadFiles() {
      try {
        const res = await axios.get(`${API_URL}/api/config-mgmt/files`)
        this.backupList = res.data.backups || []
        this.uploadsList = res.data.uploads || []
      } catch {
        this.backupList = []
        this.uploadsList = []
      }
    },

    async refreshAfterChange() {
      await Promise.all([this.fetchState(), this.loadFiles()])
    },

    // ── Backup / factory reset ─────────────────────────────────────
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
      this.working = true
      try {
        const res = await axios.post(`${API_URL}/api/config-mgmt/load-backup`, { timestamp: this.selectedBackup })
        this.showMsg('success', res.data.message || 'Backup loaded.')
        this.showLoadBackup = false
        this.selectedBackup = null
        await this.refreshAfterChange()
      } catch (e) {
        this.showMsg('error', this.errMsg(e, 'Load failed'))
      }
      this.working = false
    },

    async doFactoryReset() {
      this.working = true
      try {
        const res = await axios.post(`${API_URL}/api/config-mgmt/factory-reset`)
        this.showMsg('success', res.data.message || 'Factory reset done.')
        this.showFactoryReset = false
        await this.refreshAfterChange()
      } catch (e) {
        this.showMsg('error', this.errMsg(e, 'Factory reset failed'))
      }
      this.working = false
    },

    async deleteUpload(filename) {
      if (!confirm(`Delete uploaded file "${filename}"?`)) return
      try { await axios.delete(`${API_URL}/api/config-mgmt/files/uploads/${filename}`); this.loadFiles() }
      catch (e) { this.showMsg('error', this.errMsg(e, 'Delete failed')) }
    },
    async deleteBackup(timestamp) {
      if (!confirm(`Delete backup "${this.formatTimestamp(timestamp)}"?`)) return
      try { await axios.delete(`${API_URL}/api/config-mgmt/files/backups/${timestamp}`); this.loadFiles() }
      catch (e) { this.showMsg('error', this.errMsg(e, 'Delete failed')) }
    },

    // ── Helpers ────────────────────────────────────────────────────
    downloadUrl(category, filename) {
      return `${API_URL}/api/config-mgmt/download/${category}/${filename}`
    },
    ageClassForDays(days) {
      if (days === null || days === undefined) return ''
      if (days <= 3) return 'age-fresh'
      if (days <= 7) return 'age-ok'
      if (days <= 14) return 'age-warn'
      return 'age-stale'
    },
    formatTimestamp(ts) {
      if (!ts || ts.length < 15) return ts
      return `${ts.slice(0, 4)}-${ts.slice(4, 6)}-${ts.slice(6, 8)} ${ts.slice(9, 11)}:${ts.slice(11, 13)}:${ts.slice(13, 15)}`
    },
    formatSize(bytes) {
      if (!bytes) return '0 B'
      if (bytes < 1024) return bytes + ' B'
      return (bytes / 1024).toFixed(1) + ' KB'
    },
    errMsg(e, fallback) { return e.response?.data?.error || e.message || fallback },
    showMsg(type, text) {
      this.messageType = type
      this.message = text
      setTimeout(() => { this.message = '' }, 4000)
    },
  },
}
</script>

<style scoped>
.su { padding: 16px; background: #f5f5f5; min-height: 100%; }
.su-bar {
  display: flex; align-items: center; gap: 12px;
  background: #1e3a5f; color: #fff; padding: 10px 15px;
  border-radius: 4px 4px 0 0; font-size: 14px; font-weight: 600;
}
.su-hint { font-size: 11px; color: #9bbcd6; font-weight: 400; }
.su-hint.dark { color: #64748b; }
.su-spacer { flex: 1; }
.su-act {
  padding: 7px 13px; border: none; border-radius: 6px; cursor: pointer;
  font-size: 12px; font-weight: 600; color: #fff; white-space: nowrap;
}
.su-act:hover:not(:disabled) { opacity: 0.88; }
.su-act:disabled { opacity: 0.5; cursor: not-allowed; }
.su-act.backup { background: #78909c; }
.su-act.danger { background: #d32f2f; }

.su-body {
  border: 1px solid #e0e0e0; border-top: none; border-radius: 0 0 4px 4px;
  background: #fff; padding: 20px; display: flex; flex-direction: column; gap: 16px;
}
.su-drop {
  border: 2px dashed #cbd5e1; border-radius: 8px; padding: 32px 20px;
  text-align: center; cursor: pointer; transition: all 0.15s; background: #fafbfc;
}
.su-drop:hover { border-color: #2563eb; background: #f4f8ff; }
.su-drop.over { border-color: #2563eb; background: #eaf2ff; }
.su-drop.busy { opacity: 0.6; cursor: wait; }
.su-file { display: none; }
.su-drop-icon { font-size: 30px; color: #1e3a5f; }
.su-drop-text { font-size: 15px; font-weight: 600; color: #334155; margin-top: 6px; }
.su-drop-sub { font-size: 12px; color: #94a3b8; margin-top: 4px; }

.su-toolbar { display: flex; gap: 8px; align-items: center; }

/* 3 columns — colours match the system palette (.cb / .cg / .cy) */
.su-cols { display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; align-items: start; }
.su-col { border: 1px solid #e0e0e0; border-radius: 8px; overflow: hidden; background: #fff; }
.su-col-head { padding: 9px 13px; font-weight: 700; font-size: 13px; color: #fff; letter-spacing: 0.02em; }
.col-tle .su-col-head { background: #4a9fd9; }
.col-config .su-col-head { background: #2aab6c; }
.col-satellite .su-col-head { background: #fcb940; color: #333; }
.su-col-body { padding: 14px; display: flex; flex-direction: column; gap: 12px; }
.su-col-empty { color: #b6c0cc; font-size: 12.5px; text-align: center; padding: 14px 0; }
.su-col.active.col-tle { box-shadow: inset 0 0 0 2px #4a9fd9; }
.su-col.active.col-config { box-shadow: inset 0 0 0 2px #2aab6c; }
.su-col.active.col-satellite { box-shadow: inset 0 0 0 2px #fcb940; }

/* pending item cards */
.su-item { border: 1px solid #e6eaef; border-radius: 6px; padding: 10px 11px; background: #fbfcfd; }
.su-item.st-staged { background: #eff6ff; border-color: #bfdbfe; }
.su-item.st-added { background: #f0f9ff; border-color: #bae6fd; }
.su-item.st-active { background: #ecfdf3; border-color: #b7e4c7; }
.su-item.st-error { background: #fef2f2; border-color: #f3c4c4; }
.su-item-status { margin-top: 7px; font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.04em; }
.tag-added { color: #0369a1; }
.tag-staged { color: #1d4ed8; }
.tag-active { color: #047857; }
.tag-error { color: #b91c1c; }
.su-cancel.sm { padding: 5px 12px; font-size: 12px; }

/* TLE catalog: search + activate-per-row + highlight recent */
.su-search {
  width: 100%; box-sizing: border-box; padding: 6px 9px; margin-bottom: 8px;
  border: 1px solid #cbd5e1; border-radius: 5px; font-size: 12.5px;
}
.su-search:focus { outline: none; border-color: #4a9fd9; }
.su-mini {
  background: #4a9fd9; color: #fff; border: none; border-radius: 4px;
  padding: 3px 9px; font-size: 11px; font-weight: 600; cursor: pointer;
}
.su-mini:hover:not(:disabled) { background: #2f86c2; }
.su-mini:disabled { opacity: 0.5; cursor: wait; }
.su-mini-spacer { display: inline-block; }
.su-inv-row.recent { background: #fffbeb; box-shadow: inset 2px 0 0 #fcb940; }
.su-chip.recent { background: #fef3c7; color: #b45309; margin-left: 6px; }
.su-item-top { display: flex; align-items: center; justify-content: space-between; gap: 6px; }
.su-fname { font-family: monospace; font-size: 12.5px; color: #475569; word-break: break-all; }
.su-summary { margin: 7px 0 0; font-size: 12.5px; color: #334155; }
.su-msg { margin-top: 7px; font-size: 12px; color: #15803d; }
.su-msg.err { color: #b91c1c; }
.su-applying { margin-top: 8px; font-size: 12px; color: #64748b; font-style: italic; }
.su-actions { display: flex; gap: 8px; margin-top: 9px; }
.su-x { background: none; border: none; color: #94a3b8; font-size: 18px; line-height: 1; cursor: pointer; padding: 0 2px; }
.su-x:hover:not(:disabled) { color: #ef4444; }
.su-x:disabled { opacity: 0.4; cursor: wait; }

/* current state block */
.su-state { border-top: 1px dashed #e2e8f0; padding-top: 12px; }
.su-state-head { display: flex; align-items: center; justify-content: space-between; gap: 8px; margin-bottom: 8px; }
.su-state-label {
  font-size: 10.5px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em; color: #6b7280;
}
.su-state-label.sub { margin-top: 10px; display: block; }
.su-badge-active {
  font-size: 9px; font-weight: 700; background: #d1fae5; color: #047857;
  padding: 1px 6px; border-radius: 8px; text-transform: none; letter-spacing: 0; margin-left: 4px;
}
.su-dl { font-size: 11px; color: #2563eb; text-decoration: none; }
.su-dl:hover { text-decoration: underline; }
.su-kv { display: flex; align-items: center; gap: 8px; font-size: 12.5px; padding: 2px 0; }
.su-kv-k { color: #64748b; min-width: 78px; }
.su-kv-v { color: #1f2937; }
.su-sat-dot { color: #2aab6c; font-size: 10px; }
.mono { font-family: monospace; }
.su-link { background: none; border: none; color: #2563eb; cursor: pointer; font-size: 12px; padding: 2px 0; text-decoration: none; }
.su-link:hover { text-decoration: underline; }
.su-link.del { color: #b91c1c; margin-left: 10px; }

/* inventory mini-table */
.su-inv { display: flex; flex-direction: column; gap: 4px; }
.su-inv-row {
  display: grid; grid-template-columns: 1fr auto auto auto auto; gap: 8px; align-items: center;
  font-size: 12px; padding: 4px 6px; border-radius: 4px;
}
.su-inv-row.act { background: #ecfdf3; }
.su-inv-name { color: #1f2937; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.su-inv-norad { color: #64748b; }
.su-inv-age { font-weight: 600; }
.age-fresh { color: #15803d; } .age-ok { color: #65a30d; } .age-warn { color: #d97706; } .age-stale { color: #dc2626; }
.su-chip { font-size: 9.5px; font-weight: 700; padding: 1px 6px; border-radius: 8px; }
.su-chip.active { background: #d1fae5; color: #047857; }
.su-chip.configured { background: #dbeafe; color: #1d4ed8; }
.su-chip.unmatched { background: #f1f5f9; color: #94a3b8; }

/* unknown */
.su-unknown { border: 1px solid #f3c4c4; border-radius: 6px; background: #fef2f2; padding: 8px 12px; display: flex; flex-direction: column; gap: 6px; }
.su-unknown-row { display: flex; align-items: center; gap: 10px; font-size: 12.5px; }
.su-unknown-msg { color: #b91c1c; flex: 1; }

/* history */
.su-history { border: 1px solid #e0e0e0; border-radius: 8px; overflow: hidden; }
.su-history-head { display: flex; align-items: center; justify-content: space-between; padding: 10px 13px; background: #f8fafc; border-bottom: 1px solid #e0e0e0; }
.su-htable { width: 100%; border-collapse: collapse; font-size: 12.5px; }
.su-htable th { text-align: left; padding: 8px 13px; color: #6b7280; font-size: 10.5px; text-transform: uppercase; letter-spacing: 0.05em; border-bottom: 1px solid #eef2f7; }
.su-htable td { padding: 8px 13px; border-bottom: 1px solid #f1f5f9; color: #334155; }
.su-htable tr:last-child td { border-bottom: none; }
.su-date { color: #64748b; white-space: nowrap; }
.su-htable-act { white-space: nowrap; }
.su-cat { font-size: 10px; font-weight: 700; padding: 1px 7px; border-radius: 8px; text-transform: uppercase; }
.cat-upload { background: #dbeafe; color: #1d4ed8; }
.cat-backup { background: #fef3c7; color: #b45309; }
.su-more { text-align: center; }

/* modals */
.su-overlay { position: fixed; inset: 0; background: rgba(15, 23, 42, 0.45); display: flex; align-items: center; justify-content: center; z-index: 1000; }
.su-modal { background: #fff; border-radius: 8px; padding: 22px; width: 420px; max-width: 92vw; box-shadow: 0 12px 40px rgba(0,0,0,0.25); }
.su-modal.wide { width: 540px; }
.su-modal h3 { margin: 0 0 12px; font-size: 16px; color: #1f2937; }
.su-modal p { font-size: 13px; color: #475569; margin: 6px 0; }
.danger-txt { color: #d32f2f; font-weight: 500; }
.su-modal-act { display: flex; gap: 8px; margin-top: 16px; }
.su-bk-list { max-height: 320px; overflow: auto; display: flex; flex-direction: column; gap: 6px; margin-top: 8px; }
.su-bk-item { display: grid; grid-template-columns: 1fr auto auto; gap: 10px; align-items: center; padding: 8px 10px; border: 1px solid #e6eaef; border-radius: 6px; cursor: pointer; font-size: 12.5px; }
.su-bk-item:hover { background: #f4f8ff; }
.su-bk-item.selected { border-color: #2563eb; background: #eaf2ff; }
.su-bk-name { font-weight: 600; color: #1f2937; }
.su-bk-meta { color: #64748b; }

.su-apply { background: #1e3a5f; color: #fff; border: none; border-radius: 4px; padding: 7px 18px; font-weight: 600; cursor: pointer; font-size: 13px; }
.su-apply.sm { padding: 5px 14px; font-size: 12px; }
.su-apply:hover:not(:disabled) { background: #2563eb; }
.su-apply:disabled { opacity: 0.5; cursor: wait; }
.su-cancel { background: #eef2f7; color: #334155; border: 1px solid #d6dee8; border-radius: 4px; padding: 7px 14px; cursor: pointer; font-size: 13px; }
.su-cancel:hover:not(:disabled) { background: #e2e8f0; }
.su-cancel:disabled { opacity: 0.5; }

/* toast */
.su-toast { position: fixed; bottom: 22px; right: 22px; padding: 12px 18px; border-radius: 6px; font-size: 13px; font-weight: 500; color: #fff; z-index: 1100; box-shadow: 0 6px 20px rgba(0,0,0,0.2); }
.su-toast.success { background: #16a34a; }
.su-toast.error { background: #dc2626; }
</style>
