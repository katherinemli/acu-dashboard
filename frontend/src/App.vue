<template>
  <div id="wrap">
    <div id="header">
      <div class="header-inner">
        <router-link to="/" class="logo"></router-link>
        <div class="status">
          <div class="status-led" :class="headerLedClass"></div>
          <div class="status-info">
            <div class="info-label">Name<br />Model</div>
            <div class="info-value">
              <span>{{ header.name }}</span><br />{{ header.model }}
            </div>
          </div>
          <div class="status-indicators">
            <div class="indicator" :class="badgeClass('lan')">LAN</div>
            <div class="indicator" :class="badgeClass('transmit')">Transmit</div>
            <div class="indicator" :class="badgeClass('lock')">Lock</div>
            <div class="indicator" :class="trackingBadgeClass">
              {{ trackingLabel }}
            </div>
            <div class="indicator" :class="badgeClass('gps')">
              {{ header.gps === 'manual' ? 'Manual Location' : 'GPS' }}
            </div>
            <div class="indicator" :class="badgeClass('signal')">
              Signal{{ header.signal_value != null ? ` ${header.signal_value}` : '' }}
            </div>
            <div
              class="indicator"
              :class="compassCalibBadgeClass"
              :title="header.compass_calibration_msg || ''"
            >
              {{ compassCalibLabel }}
            </div>
            <template v-if="isPointing">
              <button class="header-stop-btn" :class="{ 'btn-busy': stopping }" :disabled="stopping" @click="stopPointing">
                {{ stopping ? 'Stopping...' : 'Stop Pointing' }}
              </button>
              <span class="header-tracking-label">{{ stopError || 'System is tracking' }}</span>
            </template>
            <template v-else-if="isStopped">
              <button class="header-stop-btn header-resume-btn" :class="{ 'btn-busy': resuming }" :disabled="resuming" @click="resumePointing">
                {{ resuming ? 'Resuming...' : 'Resume Pointing' }}
              </button>
              <span class="header-tracking-label header-stopped-label">{{ resumeError || 'Pointing stopped' }}</span>
            </template>
          </div>
        </div>
      </div>
    </div>

    <div id="content">
      <div id="sidebar">
        <div class="sidebar-header">
          <button class="sidebar-icon-btn" @click="refresh" title="Refresh">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M23 4v6h-6"/><path d="M1 20v-6h6"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/></svg>
          </button>
          <router-link to="/docs" class="sidebar-icon-btn" title="Documentation">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
          </router-link>
        </div>

        <nav class="menu">
          <router-link to="/" class="menu-item" :class="{ active: $route.path === '/' }">
            <AppIcon name="satellite" /> Overview
          </router-link>

          <!-- <router-link to="/stats" class="menu-item" :class="{ active: $route.path === '/stats' }">
            <AppIcon name="stats" /> Stats
          </router-link> -->
          
          <div class="menu-category">
            <AppIcon name="system" /> CONFIGURATION
          </div>
          <div class="menu-children">
            <router-link v-for="item in configItems" :key="item.path" :to="item.path" class="menu-item"
              :class="{ active: $route.path === item.path }">
              {{ item.label }}
            </router-link>
          </div>

          <div class="menu-category">
            <AppIcon name="tools" /> TOOLS
          </div>
          <div class="menu-children">
            <router-link v-for="item in toolsItems" :key="item.path" :to="item.path" class="menu-item"
              :class="{ active: $route.path === item.path }">
              {{ item.label }}
            </router-link>
          </div>
        </nav>
      </div>

      <div id="main">
        <router-view></router-view>
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios'
import AppIcon from './components/AppIcon.vue'
import { useAcuStore } from './stores/acu'

const API_URL = import.meta.env.VITE_API_URL || ''

export default {
  name: 'App',
  components: {
    AppIcon
  },
  setup() {
    const store = useAcuStore()
    return { store }
  },
  data() {
    return {
      stopping: false,
      stopError: '',
      resuming: false,
      resumeError: '',
      configItems: [
        { label: 'System', path: '/config/system' },
        { label: 'Network', path: '/config/network' },
        { label: 'Satellites', path: '/config/satellite' },
        { label: 'ESA', path: '/config/esa' },
        { label: 'Location', path: '/config/location' },
        { label: 'Advanced', path: '/config/sensors' },
        { label: 'Pointing', path: '/config/advanced' },
      ],
      toolsItems: [
        { label: 'Network', path: '/tools/network' },
        { label: 'Save / Load Config', path: '/tools/config-mgmt' },
        { label: 'TLE Management', path: '/tools/tle-mgmt' },
        { label: 'Calibration', path: '/tools/calibration' },
        { label: 'Events', path: '/tools/events' },
        { label: 'Logs', path: '/tools/logs' },
        { label: 'Upgrade', path: '/tools/upgrade' },
        { label: 'Reboot', path: '/tools/reboot' }
      ]
    }
  },
  computed: {
    header() {
      return this.store.status
    },
    isPointing() {
      const t = this.store.status.tracking
      return t === 'tracking' || t === 'auto_pointing'
    },
    isStopped() {
      return this.store.status.tracking === 'stopped'
    },
    headerLedClass() {
      if (this.store.status.lan === 'up') return 'cg'
      if (this.store.status.lan === 'down') return 'cr'
      return 'cw'
    },
    trackingBadgeClass() {
      const t = this.store.status.tracking
      if (t === 'calibration') return 'cy'
      if (t === 'tracking') return 'cg'
      if (t === 'searching') return 'cy'
      if (t === 'fault') return 'cr'
      if (t === 'ready') return 'cb'
      if (t === 'auto_pointing') return 'cy'
      if (t === 'manual_pointing') return 'cb'
      if (t === 'stopped') return 'cr'
      return 'cw'
    },
    trackingLabel() {
      const t = this.store.status.tracking
      if (t === 'calibration') return 'CALIBRATING...'
      if (t === 'tracking') return 'Tracking'
      if (t === 'searching') return 'Searching'
      if (t === 'fault') return 'Fault'
      if (t === 'ready') return 'Ready'
      if (t === 'auto_pointing') return 'Auto Pointing'
      if (t === 'manual_pointing') return 'Manual Pointing'
      if (t === 'stopped') return 'Stopped'
      if (t === 'unknown') return 'Unknown'
      return 'Idle'
    },
    compassCalibBadgeClass() {
      const s = this.store.status.compass_calibration
      if (s === 'good') return 'cg'
      if (s === 'poor') return 'cy'
      if (s === 'not_calibrated') return 'cr'
      return 'cw'
    },
    compassCalibLabel() {
      const s = this.store.status.compass_calibration
      if (s === 'good') return 'COMPASS'
      if (s === 'poor') return 'COMPASS: POOR'
      if (s === 'not_calibrated') return 'NO CAL'
      return 'COMPASS: ?'
    }
  },
  methods: {
    badgeClass(key) {
      const val = this.store.status[key]
      if (['up', 'on', 'locked', 'good', 'tracking'].includes(val)) return 'cg'
      if (['low', 'searching', 'auto_pointing'].includes(val)) return 'cy'
      if (['down', 'off', 'unlocked', 'bad', 'no_lock'].includes(val)) return 'cr'
      if (['manual', 'ready'].includes(val)) return 'cb'
      return 'cw'
    },
    refresh() {
      this.$router.go(0)
    },
    async stopPointing() {
      this.stopping = true
      this.stopError = ''
      try {
        await axios.post(`${API_URL}/api/actions/stop-pointing`)
        // Poll until acumon confirms the transition — API returns ok as soon
        // as the command is written, but acumon processes it asynchronously.
        const poll = setInterval(async () => {
          await this.store.fetchStatus()
          if (!this.isPointing) {
            clearInterval(poll)
            this.stopping = false
          }
        }, 500)
        setTimeout(() => { clearInterval(poll); this.stopping = false }, 8000)
      } catch (e) {
        this.stopping = false
        this.stopError = e.response?.data?.error || 'Stop failed'
      }
    },
    async resumePointing() {
      this.resuming = true
      this.resumeError = ''
      try {
        await axios.post(`${API_URL}/api/actions/resume-pointing`)
        const poll = setInterval(async () => {
          await this.store.fetchStatus()
          if (this.isPointing) {
            clearInterval(poll)
            this.resuming = false
          }
        }, 500)
        setTimeout(() => { clearInterval(poll); this.resuming = false }, 8000)
      } catch (e) {
        this.resuming = false
        this.resumeError = e.response?.data?.error || 'Resume failed'
      }
    }
  },
  mounted() {
    this.store.start()
  },
  beforeUnmount() {
    this.store.stop()
  }
}
</script>

<style>
* {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

body {
  font-family: Arial, sans-serif;
  background: #f5f5f5;
}

#wrap {
  display: flex;
  flex-direction: column;
  height: 100vh;
  overflow: hidden;
}

/* HEADER */
#header {
  background: #369;
  height: 60px;
}

.header-inner {
  display: flex;
  align-items: center;
  height: 100%;
}

.logo {
  width: 200px;
  height: 60px;
  background: #369;
  border-right: 1px solid rgba(255, 255, 255, 0.2);
  display: flex;
  align-items: center;
  justify-content: center;
  background-image: url('./assets/nms_logo.png');
  background-size: contain;
  background-repeat: no-repeat;
  background-position: center;
}

.status {
  flex: 1;
  display: flex;
  align-items: center;
  padding: 0 20px;
  gap: 20px;
}

.status-led {
  width: 12px;
  height: 12px;
  border-radius: 50%;
}

.status-info {
  display: flex;
  gap: 10px;
  color: white;
  font-size: 12px;
}

.info-label {
  color: #aaa;
  line-height: 1.4;
}

.info-value {
  line-height: 1.4;
}

.status-indicators {
  display: flex;
  align-items: center;
  gap: 8px;
}

.header-stop-btn {
  padding: 4px 14px;
  background: #fe5e37;
  color: white;
  border: none;
  border-radius: 3px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
}

.header-stop-btn:hover:not(:disabled) {
  background: #e04e28;
}

.header-stop-btn:disabled {
  opacity: 0.6;
  cursor: default;
}

.btn-busy {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.btn-busy::after {
  content: '';
  width: 10px;
  height: 10px;
  border: 2px solid rgba(255,255,255,0.35);
  border-top-color: white;
  border-radius: 50%;
  animation: btn-spin 0.7s linear infinite;
  flex-shrink: 0;
}
@keyframes btn-spin {
  to { transform: rotate(360deg); }
}

.header-resume-btn {
  background: #2aab6c !important;
}

.header-resume-btn:hover:not(:disabled) {
  background: #1e8c57 !important;
}

.header-tracking-label {
  color: #7dd228;
  font-size: 12px;
  font-weight: 600;
  white-space: nowrap;
}

.header-stopped-label {
  color: #fcb940;
}

.indicator {
  padding: 4px 10px;
  border-radius: 3px;
  font-size: 11px;
  font-weight: bold;
}

.cw { background: #f0f0f0; color: #666; }
.cy { background: #fcb940; color: #333; }
.cr { background: #fe5e37; color: white; }
.cg { background: #7dd228; color: #333; }
.cb { background: #4a9fd9; color: white; }

/* CONTENT */
#content {
  display: flex;
  flex: 1;
  overflow: hidden;
}

/* SIDEBAR */
#sidebar {
  width: 200px;
  background: #369;
  overflow-y: auto;
}

.sidebar-header {
  padding: 10px 12px;
  display: flex;
  gap: 8px;
}

.sidebar-icon-btn {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 7px;
  background: rgba(255,255,255,0.08);
  border: none;
  border-radius: 4px;
  cursor: pointer;
  color: #cdd8e6;
  text-decoration: none;
  transition: background 0.15s, color 0.15s;
}

.sidebar-icon-btn:hover {
  background: rgba(255,255,255,0.16);
  color: #fff;
}

.sidebar-icon-btn svg {
  width: 16px;
  height: 16px;
}

.menu { padding: 10px 0; }

.menu-category {
  padding: 12px 15px;
  color: white;
  font-weight: bold;
  font-size: 12px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 8px;
}

.menu-category:hover { background: rgba(255, 255, 255, 0.1); }


.menu-children { background: rgba(0, 0, 0, 0.1); }

.menu-item {
  display: flex;
  align-items: center;
  padding: 10px 15px 10px 30px;
  color: white;
  font-size: 13px;
  cursor: pointer;
  transition: background 0.2s;
  text-decoration: none;
}

.menu-item:hover { background: rgba(255, 255, 255, 0.1); }

.menu-item.active {
  background: #162d47;
  border-left: 3px solid #7dd228;
}

.menu-item .app-icon {
  margin-right: 10px;
}

.menu > .menu-item {
  padding-left: 15px;
}

/* MAIN */
#main {
  flex: 1;
  overflow-y: auto;
  background: #f5f5f5;
}
</style>
