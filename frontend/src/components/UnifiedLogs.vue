<template>
  <div class="tool-section">
    <div class="section-head">
      <h2>Logs &amp; Events</h2>
      <span v-if="unitTime" class="unit-clock">
        <span class="unit-clock-label">Unit time</span>
        {{ unitTime }}
      </span>
    </div>
    <div class="logs-container">
      <div class="logs-toolbar">
        <!-- Source pills — segmented toggle, same .ui-pill system as the Compass card.
             v1 just swaps the source; correlation/merged timeline is a later iteration. -->
        <div class="pill-group">
          <button
            v-for="s in sources"
            :key="s.key"
            class="ui-pill ui-pill-btn"
            :class="source === s.key ? 'ui-pill-blue' : 'ui-pill-gray'"
            @click="setSource(s.key)"
          >{{ s.label }}</button>
        </div>

        <span class="tb-spacer"></span>

        <button class="sort-btn" @click="toggleSort">
          {{ sortDir === 'desc' ? 'Newest first ↓' : 'Oldest first ↑' }}
        </button>
        <select v-if="isLog" v-model.number="logsLimit" @change="loadData">
          <option :value="50">Last 50 lines</option>
          <option :value="100">Last 100 lines</option>
          <option :value="200">Last 200 lines</option>
        </select>
        <button @click="loadData">Refresh</button>
        <button @click="downloadLogs">Download All</button>
        <button class="danger" @click="purgeLogs">Purge All Logs</button>
      </div>

      <div v-if="loading" class="loading">Loading…</div>
      <div v-else-if="rows.length === 0" class="no-data">No entries.</div>
      <div v-else class="logs-list">
        <div v-for="(r, i) in sortedRows" :key="i" class="log-item" :class="r.cls">
          <span class="log-time">{{ r.time }}</span>
          <span class="log-origin" :class="'org-' + r.origin">{{ r.origin }}</span>
          <span class="log-level">{{ r.level }}</span>
          <span class="log-message">
            <span v-if="r.tag" class="log-tag">{{ r.tag }}</span>{{ r.body }}
          </span>
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
import ConfirmModal from './ConfirmModal.vue'
import ResultModal from './ResultModal.vue'

const API_URL = import.meta.env.VITE_API_URL || ''

// Map any level string (INF/ERR/WRN/DBG or info/error/warning) to a css class.
function levelClass(level) {
  const l = (level || '').toLowerCase()
  if (l.startsWith('err')) return 'lv-err'
  if (l.startsWith('wrn') || l.startsWith('warn')) return 'lv-wrn'
  if (l.startsWith('dbg') || l.startsWith('debug')) return 'lv-dbg'
  return 'lv-inf'
}

// Parse the two timestamp formats to epoch ms for sorting.
//   events: "2026-06-05 14:22:50"   acumon: "2026 Jun 05 09:17:22"
// Unparseable / empty → 0 so it sinks to the bottom on newest-first.
function toEpoch(ts) {
  if (!ts) return 0
  if (/^\d{4}-\d{2}-\d{2}/.test(ts)) {
    return Date.parse(ts.replace(' ', 'T')) || 0
  }
  const m = ts.match(/^(\d{4})\s+(\w{3})\s+(\d{2})\s+(\d{2}):(\d{2}):(\d{2})/)
  if (m) {
    const [, y, mon, d, hh, mm, ss] = m
    return Date.parse(`${mon} ${d} ${y} ${hh}:${mm}:${ss}`) || 0
  }
  return 0
}

// Pull a leading subsystem tag out of a message so it can be emphasised:
//   "AMIP: modem connected"        -> { tag: "AMIP:", body: "modem connected" }
//   "esa ok: mode=IDLE ..."        -> { tag: "esa ok:", body: "mode=IDLE ..." }
//   "[tle] TLE upload rejected"    -> { tag: "[tle]",  body: "TLE upload rejected" }
//   "Connection 'eth0' ..."        -> { tag: "",       body: "Connection 'eth0' ..." }
// Only short 1-2 word prefixes count, so mid-sentence colons aren't mistaken.
function splitTag(message) {
  const msg = message || ''
  const ev = msg.match(/^(\[[^\]]+\])\s*(.*)$/s)
  if (ev) return { tag: ev[1], body: ev[2] }
  const log = msg.match(/^([A-Za-z]{2,}(?: [A-Za-z]{2,})?):\s+(.*)$/s)
  if (log) return { tag: log[1] + ':', body: log[2] }
  return { tag: '', body: msg }
}

// Format epoch ms as "Fri Jun 5 2026 · 12:59:18" — shared by clock and rows.
function formatStamp(ms) {
  if (!ms) return ''
  const d = new Date(ms)
  const pad = n => String(n).padStart(2, '0')
  const days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
  const mons = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
  return `${days[d.getDay()]} ${mons[d.getMonth()]} ${d.getDate()} ${d.getFullYear()} · ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
}

export default {
  name: 'UnifiedLogs',
  components: { ConfirmModal, ResultModal },
  data() {
    return {
      source: 'msg',
      sources: [
        { key: 'msg', label: 'Messages' },
        { key: 'err', label: 'Errors' },
        { key: 'ev:all', label: 'All events' },
        { key: 'ev:error', label: 'Event errors' },
        { key: 'ev:warning', label: 'Event warnings' },
        { key: 'ev:info', label: 'Event info' }
      ],
      logsLimit: 100,
      sortDir: 'desc', // 'desc' = newest first
      rows: [],
      loading: false,
      unitTime: '',
      clockBaseUnit: 0,  // unit epoch ms at last fetch
      clockBaseLocal: 0, // local epoch ms at that fetch
      clockTimer: null,
      refreshSecs: 10, // table auto-refreshes on its own; no toggle
      refreshTimer: null,
      confirm: {
        visible: false, title: '', message: '', warning: '',
        btnText: 'Confirm', btnClass: 'btn-primary', action: null
      },
      result: { visible: false, title: '', message: '', success: true }
    }
  },
  computed: {
    isLog() {
      return this.source === 'msg' || this.source === 'err'
    },
    sortedRows() {
      const dir = this.sortDir === 'desc' ? -1 : 1
      // copy before sort; stable on equal epochs keeps source order
      return [...this.rows].sort((a, b) => (a.epoch - b.epoch) * dir)
    }
  },
  mounted() {
    this.loadData()
    this.syncClock()
    // fetched once on load; just tick locally after that (re-sync only on F5)
    this.clockTimer = setInterval(() => this.renderClock(), 1000)
    // table refreshes itself silently (no spinner flash); no button
    this.refreshTimer = setInterval(() => this.loadData(true), this.refreshSecs * 1000)
  },
  beforeUnmount() {
    if (this.clockTimer) clearInterval(this.clockTimer)
    if (this.refreshTimer) clearInterval(this.refreshTimer)
  },
  methods: {
    async syncClock() {
      try {
        const res = await axios.get(`${API_URL}/api/system/time`)
        this.clockBaseUnit = res.data.unix_ms
        this.clockBaseLocal = Date.now()
        this.renderClock()
      } catch (e) {
        // leave last known value; don't spam
      }
    },

    renderClock() {
      if (!this.clockBaseUnit) return
      this.unitTime = formatStamp(this.clockBaseUnit + (Date.now() - this.clockBaseLocal))
    },

    setSource(key) {
      this.source = key
      this.loadData()
    },

    toggleSort() {
      this.sortDir = this.sortDir === 'desc' ? 'asc' : 'desc'
    },

    // silent = background auto-refresh: keep the current list on screen and just
    // swap the data in when it arrives, so there's no "Loading…" flash.
    async loadData(silent = false) {
      if (!silent) this.loading = true
      try {
        const data = this.isLog ? await this.fetchLogs() : await this.fetchEvents()
        this.rows = data
      } catch (e) {
        console.error('Error loading data:', e)
        if (!silent) this.rows = []
      }
      this.loading = false
    },

    async fetchLogs() {
      const res = await axios.get(`${API_URL}/api/logs?limit=${this.logsLimit}&file=${this.source}`)
      // Logs arrive in file order (chronological). Some acumon lines carry no
      // timestamp — they continue the previous entry, so forward-fill the epoch
      // to keep them next to their predecessor instead of sinking to an extreme.
      let prevEpoch = 0
      return (res.data || []).map(log => {
        const e = toEpoch(log.timestamp)
        if (e) prevEpoch = e
        return {
          time: formatStamp(e), // own timestamp only; blank stays blank
          epoch: e || prevEpoch,
          origin: 'acumon',
          level: log.level,
          ...splitTag(log.message),
          cls: levelClass(log.level)
        }
      })
    },

    async fetchEvents() {
      const level = this.source.slice(3) // strip "ev:"
      const params = level !== 'all' ? `?level=${level}` : ''
      const res = await axios.get(`${API_URL}/api/events${params}`)
      return (res.data || []).map(ev => {
        const norm = (ev.timestamp || '').replace('T', ' ').substring(0, 19)
        const epoch = toEpoch(norm)
        return {
          time: formatStamp(epoch),
          epoch,
          origin: 'eureka',
          level: (ev.level || '').toUpperCase(),
          ...splitTag(`[${ev.source}] ${ev.message}`),
          cls: levelClass(ev.level)
        }
      })
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
        this.loadData()
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

.section-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin-bottom: 20px;
  gap: 16px;
}

h2 {
  margin: 0;
  color: #333;
}

/* Live clock of the unit — anchors timestamps to the device's own time. */
.unit-clock {
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 14px;
  color: #333;
  white-space: nowrap;
}

.unit-clock-label {
  font-family: inherit;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: #999;
  margin-right: 8px;
}

.loading,
.no-data {
  text-align: center;
  padding: 24px;
  color: #888;
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
  align-items: center;
  gap: 10px;
}

.tb-spacer {
  flex: 1;
}

/* Segmented control — same pattern as the Compass AUTO/MANUAL toggle. */
.pill-group {
  display: flex;
  gap: 4px;
  align-items: center;
  flex-wrap: wrap;
}

.ui-pill {
  display: inline-block;
  padding: 5px 12px;
  border-radius: 3px;
  font-size: 11px;
  font-weight: bold;
  white-space: nowrap;
  letter-spacing: 0.04em;
}

.ui-pill-blue { background: #4a9fd9; color: #fff; }
.ui-pill-gray { background: #f0f0f0; color: #666; }

.ui-pill-btn {
  border: none;
  cursor: pointer;
  transition: filter 0.15s;
}

.ui-pill-btn:hover { filter: brightness(1.08); }

.logs-toolbar select,
.logs-toolbar > button {
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 13px;
}

.logs-toolbar > button {
  background: #369;
  color: white;
  border: none;
  cursor: pointer;
}

.logs-toolbar > button.danger {
  background: #fe5e37;
}

.logs-toolbar > button.sort-btn {
  background: #fff;
  color: #369;
  border: 1px solid #369;
  font-weight: 600;
}


/* White list, black text, colour-coded levels — readable for older eyes.
   Larger type, taller rows; fewer lines on screen is an acceptable trade. */
.logs-list {
  max-height: 600px;
  overflow-y: auto;
  background: #fff;
}

.log-item {
  display: flex;
  gap: 14px;
  padding: 11px 16px;
  border-bottom: 1px solid #f0f0f0;
  font-size: 15px;
  line-height: 1.4;
  color: #222;
  align-items: baseline;
}

/* Subtle row tint for severity — same cue as the Events page. */
.log-item.lv-err { background: #fff5f5; }
.log-item.lv-wrn { background: #fffbf0; }

.log-time {
  color: #888;
  min-width: 215px;
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 13px;
  flex-shrink: 0;
}

/* Origin badge — distinguishes acumon vs eureka at a glance. */
.log-origin {
  min-width: 70px;
  text-align: center;
  font-size: 12px;
  font-weight: 600;
  border-radius: 3px;
  padding: 2px 6px;
  flex-shrink: 0;
}

.log-origin.org-acumon {
  background: #e3edf7;
  color: #2c6fb3;
}

.log-origin.org-eureka {
  background: #fdf3da;
  color: #a6791a;
}

.log-level {
  min-width: 52px;
  font-weight: 700;
  flex-shrink: 0;
  color: #42a5f5;
}

.log-item.lv-err .log-level { color: #fe5e37; }
.log-item.lv-wrn .log-level { color: #e6a700; }
.log-item.lv-dbg .log-level { color: #999; }

.log-message {
  flex: 1;
  white-space: pre-wrap;
  word-break: break-word;
}

/* Subsystem anchor — gives the eye something to latch onto when scanning. */
.log-tag {
  font-weight: 700;
  color: #2c5777;
  margin-right: 6px;
}

.log-item.lv-err .log-tag { color: #c0392b; }
.log-item.lv-wrn .log-tag { color: #b07d10; }
</style>
