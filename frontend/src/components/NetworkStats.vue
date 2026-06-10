<template>
  <div class="network-stats">
    <h2>Network Statistics</h2>

    <!-- Ethernet Stats -->
    <div class="card">
      <div class="card-header">
        <span class="card-icon">
          <AppIcon name="ethernet" :size="16" />
        </span>
        <span class="card-title">Ethernet (eth0)</span>
        <button class="btn-refresh" @click="fetchStats">
          <AppIcon name="refresh" :size="12" />
        </button>
      </div>
      <div v-if="loading" class="loading">Loading...</div>
      <div v-else-if="error" class="error">{{ error }}</div>
      <div v-else class="stats-grid">
        <div class="stats-column">
          <h4>RX (Receive)</h4>
          <div class="stat-row">
            <span class="stat-label">Packets</span>
            <span class="stat-value">{{ fmt(stats.rx_packets) }}</span>
          </div>
          <div class="stat-row">
            <span class="stat-label">Bytes</span>
            <span class="stat-value">{{ fmtBytes(stats.rx_bytes) }}</span>
          </div>
          <div class="stat-row">
            <span class="stat-label">Errors</span>
            <span class="stat-value" :class="{ 'val-error': stats.rx_errors > 0 }">{{ fmt(stats.rx_errors) }}</span>
          </div>
          <div class="stat-row">
            <span class="stat-label">Dropped</span>
            <span class="stat-value" :class="{ 'val-warn': stats.rx_dropped > 0 }">{{ fmt(stats.rx_dropped) }}</span>
          </div>
          <div class="stat-row">
            <span class="stat-label">Overruns</span>
            <span class="stat-value" :class="{ 'val-error': stats.rx_over_errors > 0 }">{{ fmt(stats.rx_over_errors)
              }}</span>
          </div>
        </div>

        <div class="stats-column">
          <h4>TX (Transmit)</h4>
          <div class="stat-row">
            <span class="stat-label">Packets</span>
            <span class="stat-value">{{ fmt(stats.tx_packets) }}</span>
          </div>
          <div class="stat-row">
            <span class="stat-label">Bytes</span>
            <span class="stat-value">{{ fmtBytes(stats.tx_bytes) }}</span>
          </div>
          <div class="stat-row">
            <span class="stat-label">Errors</span>
            <span class="stat-value" :class="{ 'val-error': stats.tx_errors > 0 }">{{ fmt(stats.tx_errors) }}</span>
          </div>
          <div class="stat-row">
            <span class="stat-label">Dropped</span>
            <span class="stat-value" :class="{ 'val-warn': stats.tx_dropped > 0 }">{{ fmt(stats.tx_dropped) }}</span>
          </div>
          <div class="stat-row">
            <span class="stat-label">Overruns</span>
            <span class="stat-value" :class="{ 'val-error': stats.tx_over_errors > 0 }">{{ fmt(stats.tx_over_errors)
              }}</span>
          </div>
        </div>
      </div>
      <div v-if="!loading && !error" class="stats-footer">
        <div class="stat-row">
          <span class="stat-label">Collisions</span>
          <span class="stat-value" :class="{ 'val-warn': stats.collisions > 0 }">{{ fmt(stats.collisions) }}</span>
        </div>
        <div class="updated">Updated {{ updatedAt }}</div>
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || ''
import AppIcon from './AppIcon.vue'

export default {
  name: 'NetworkStats',
  components: {
    AppIcon
  },
  data() {
    return {
      stats: {},
      loading: true,
      error: '',
      updatedAt: '',
      pollTimer: null
    }
  },
  methods: {
    async fetchStats() {
      try {
        const res = await axios.get(`${API_URL}/api/network/eth0/stats`)
        this.stats = res.data
        this.error = ''
        const now = new Date()
        this.updatedAt = now.toLocaleString('en-US', { month: 'short', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false })
      } catch (e) {
        this.error = 'Failed to load network stats'
      }
      this.loading = false
    },
    fmt(val) {
      if (val == null) return '-'
      return val.toLocaleString()
    },
    fmtBytes(val) {
      if (val == null) return '-'
      if (val < 1024) return val + ' B'
      if (val < 1048576) return (val / 1024).toFixed(1) + ' KB'
      if (val < 1073741824) return (val / 1048576).toFixed(1) + ' MB'
      return (val / 1073741824).toFixed(2) + ' GB'
    }
  },
  mounted() {
    this.fetchStats()
    this.pollTimer = setInterval(this.fetchStats, 5000)
  },
  beforeUnmount() {
    if (this.pollTimer) clearInterval(this.pollTimer)
  }
}
</script>

<style scoped>
.network-stats {
  padding: 20px;
}

h2 {
  margin-bottom: 20px;
  color: #333;
  font-size: 18px;
}

.card {
  background: white;
  border-radius: 6px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  max-width: 600px;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  border-bottom: 1px solid #eee;
  font-weight: 600;
  font-size: 14px;
  color: #333;
}

.card-icon {
  font-size: 16px;
}

.card-title {
  flex: 1;
}

.btn-refresh {
  background: none;
  border: 1px solid #ddd;
  border-radius: 4px;
  padding: 2px 8px;
  cursor: pointer;
  font-size: 14px;
  color: #666;
}

.btn-refresh:hover {
  background: #f5f5f5;
}

.stats-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0;
}

.stats-column {
  padding: 12px 16px;
}

.stats-column:first-child {
  border-right: 1px solid #eee;
}

.stats-column h4 {
  font-size: 12px;
  color: #888;
  text-transform: uppercase;
  margin-bottom: 10px;
}

.stat-row {
  display: flex;
  justify-content: space-between;
  padding: 4px 0;
  font-size: 13px;
}

.stat-label {
  color: #666;
}

.stat-value {
  font-weight: 600;
  color: #333;
  font-variant-numeric: tabular-nums;
}

.val-error {
  color: #fe5e37;
}

.val-warn {
  color: #fcb940;
}

.stats-footer {
  padding: 8px 16px 12px;
  border-top: 1px solid #eee;
}

.updated {
  text-align: right;
  font-size: 11px;
  color: #aaa;
  margin-top: 6px;
}

.loading,
.error {
  padding: 20px;
  text-align: center;
  color: #888;
  font-size: 13px;
}

.error {
  color: #fe5e37;
}
</style>