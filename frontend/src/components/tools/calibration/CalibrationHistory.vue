<template>
  <div class="calib-history">
    <div class="ch-header">
      <h3>Calibration History</h3>
      <button class="ch-refresh" @click="load" :disabled="loading" title="Reload">
        ↻ Refresh
      </button>
    </div>

    <div v-if="loading" class="ch-empty">Loading…</div>
    <div v-else-if="error" class="ch-empty ch-error">{{ error }}</div>
    <div v-else-if="sessions.length === 0" class="ch-empty">
      No calibration history yet — past sessions will appear here.
    </div>

    <table v-else class="ch-table">
      <thead>
        <tr>
          <th>Date</th>
          <th>Sensor</th>
          <th>Status</th>
          <th>Coverage</th>
          <th>Quality</th>
          <th class="ch-col-x"></th>
        </tr>
      </thead>
      <tbody>
        <template v-for="(s, i) in sessions" :key="s.file || i">
          <tr class="ch-row" :class="{ 'ch-open': expanded === i }" @click="toggle(i)">
            <td class="ch-date">{{ fmtDate(s.timestamp) }}</td>
            <td>{{ (s.sensor || '—').toUpperCase() }}</td>
            <td>
              <span class="ch-badge" :class="badgeClass(s.status)">{{ s.status || '—' }}</span>
            </td>
            <td>{{ s.coverage != null ? Math.round(s.coverage * 100) + '%' : '—' }}</td>
            <td>
              <span v-if="s.quality_score != null" class="ch-quality">
                <span class="ch-quality-bar">
                  <span class="ch-quality-fill"
                    :style="{ width: (s.quality_score * 100) + '%', background: qualityColor(s.quality_score) }"></span>
                </span>
                {{ s.quality_score.toFixed(2) }}
              </span>
              <span v-else>—</span>
            </td>
            <td class="ch-expand">{{ expanded === i ? '▾' : '▸' }}</td>
          </tr>

          <tr v-if="expanded === i" class="ch-detail-row">
            <td colspan="6">
              <div class="ch-detail">
                <div class="ch-metrics">
                  <span v-if="s.samples">
                    <b>Samples</b>
                    {{ s.samples.kept ?? '?' }} kept / {{ s.samples.captured ?? '?' }} captured
                    <em v-if="s.samples.rejected != null">({{ s.samples.rejected }} rejected)</em>
                  </span>
                  <span v-if="s.sectors_hit != null">
                    <b>Sectors</b> {{ s.sectors_hit }}/{{ s.sectors_total ?? 320 }}
                  </span>
                  <span v-if="s.field_strength_ut != null">
                    <b>Field</b> {{ s.field_strength_ut }} µT
                    <em v-if="diagWmm(s) != null">(WMM ~{{ diagWmm(s) }})</em>
                  </span>
                  <span v-if="s.fit_error_pct != null"><b>Fit err</b> {{ s.fit_error_pct }}%</span>
                  <span v-if="s.duration_s != null"><b>Duration</b> {{ s.duration_s }}s</span>
                </div>

                <div v-if="hasEntries(s.rejection_reasons)" class="ch-block ch-reject">
                  <div class="ch-block-title">Rejection reasons</div>
                  <ul><li v-for="(v, k) in s.rejection_reasons" :key="k">{{ prettyKey(k) }}: {{ v }}</li></ul>
                </div>

                <div v-if="hasEntries(s.diagnostics)" class="ch-block">
                  <div class="ch-block-title">Diagnostics</div>
                  <ul><li v-for="(v, k) in s.diagnostics" :key="k">{{ prettyKey(k) }}: {{ v }}</li></ul>
                </div>

                <div v-if="s.recommendations && s.recommendations.length" class="ch-block ch-reco">
                  <div class="ch-block-title">Recommendations</div>
                  <ul><li v-for="(r, ri) in s.recommendations" :key="ri">{{ r }}</li></ul>
                </div>

                <div class="ch-file">{{ s.file }}</div>
              </div>
            </td>
          </tr>
        </template>
      </tbody>
    </table>
  </div>
</template>

<script>
import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || ''

export default {
  name: 'CalibrationHistory',
  data() {
    return { sessions: [], loading: true, error: '', expanded: null }
  },
  mounted() {
    this.load()
  },
  methods: {
    async load() {
      this.loading = true
      this.error = ''
      try {
        const res = await axios.get(`${API_URL}/api/calibration/history`)
        this.sessions = res.data.sessions || []
      } catch (e) {
        this.error = e.response?.data?.error || 'Could not load calibration history'
        this.sessions = []
      } finally {
        this.loading = false
      }
    },
    toggle(i) {
      this.expanded = this.expanded === i ? null : i
    },
    hasEntries(obj) {
      return obj && typeof obj === 'object' && Object.keys(obj).length > 0
    },
    diagWmm(s) {
      return s.diagnostics ? s.diagnostics.wmm_expected_ut : null
    },
    fmtDate(ts) {
      if (!ts) return '—'
      const d = new Date(ts)
      if (isNaN(d.getTime())) return ts
      return d.toLocaleString([], {
        year: 'numeric', month: 'short', day: '2-digit',
        hour: '2-digit', minute: '2-digit',
      })
    },
    badgeClass(status) {
      const m = {
        APPLIED: 'ch-badge-green', DONE: 'ch-badge-green',
        INCOMPLETE: 'ch-badge-yellow', CANCELLED: 'ch-badge-gray',
        FAILED: 'ch-badge-red', UNREADABLE: 'ch-badge-red',
      }
      return m[(status || '').toUpperCase()] || 'ch-badge-gray'
    },
    qualityColor(q) {
      if (q >= 0.8) return '#22c55e'
      if (q >= 0.5) return '#f59e0b'
      return '#ef4444'
    },
    prettyKey(k) {
      return String(k).replace(/_/g, ' ')
    },
  },
}
</script>

<style scoped>
.calib-history {
  margin-top: 24px;
  background: #fff;
  border: 1px solid #e0e0e0;
  border-radius: 6px;
  overflow: hidden;
}
.ch-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #1e3a5f;
  color: #fff;
  padding: 10px 15px;
}
.ch-header h3 {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
}
.ch-refresh {
  background: rgba(255, 255, 255, 0.15);
  color: #fff;
  border: none;
  border-radius: 4px;
  padding: 4px 10px;
  font-size: 12px;
  cursor: pointer;
}
.ch-refresh:hover:not(:disabled) { background: rgba(255, 255, 255, 0.28); }
.ch-refresh:disabled { opacity: 0.5; cursor: default; }

.ch-empty {
  padding: 20px 15px;
  color: #888;
  font-size: 13px;
  font-style: italic;
}
.ch-error { color: #b91c1c; }

.ch-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
.ch-table th {
  text-align: left;
  color: #6b7280;
  font-weight: 600;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  padding: 8px 12px;
  border-bottom: 1px solid #eee;
  background: #fafbfc;
}
.ch-col-x { width: 28px; }
.ch-row { cursor: pointer; }
.ch-row td {
  padding: 9px 12px;
  border-bottom: 1px solid #f1f3f5;
  color: #333;
}
.ch-row:hover td { background: #fafcff; }
.ch-row.ch-open td { background: #f3f8ff; }
.ch-date { white-space: nowrap; color: #555; }
.ch-expand { color: #9ca3af; text-align: center; }

.ch-badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 3px;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.03em;
}
.ch-badge-green  { background: #dcfce7; color: #15803d; }
.ch-badge-yellow { background: #fef3c7; color: #92400e; }
.ch-badge-gray   { background: #f0f0f0; color: #666; }
.ch-badge-red    { background: #fee2e2; color: #b91c1c; }

.ch-quality {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-family: monospace;
  font-size: 12px;
}
.ch-quality-bar {
  width: 46px;
  height: 6px;
  background: #eceff1;
  border-radius: 3px;
  overflow: hidden;
}
.ch-quality-fill { display: block; height: 100%; border-radius: 3px; }

.ch-detail-row td { padding: 0; background: #f8fafc; border-bottom: 1px solid #e5e7eb; }
.ch-detail { padding: 12px 16px; }
.ch-metrics {
  display: flex;
  flex-wrap: wrap;
  gap: 6px 20px;
  font-size: 12px;
  color: #374151;
  margin-bottom: 8px;
}
.ch-metrics b { color: #6b7280; font-weight: 600; margin-right: 3px; }
.ch-metrics em { color: #9ca3af; font-style: normal; }

.ch-block { margin-top: 8px; }
.ch-block-title {
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: #6b7280;
  margin-bottom: 2px;
}
.ch-block ul { margin: 0; padding-left: 18px; font-size: 12px; color: #374151; }
.ch-block li { padding: 1px 0; }
.ch-reject .ch-block-title { color: #b45309; }
.ch-reco .ch-block-title { color: #1d4ed8; }
.ch-reco ul li { color: #1e40af; }

.ch-file {
  margin-top: 8px;
  font-family: monospace;
  font-size: 10px;
  color: #9ca3af;
}
</style>
