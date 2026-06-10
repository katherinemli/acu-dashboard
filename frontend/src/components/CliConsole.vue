<template>
  <div class="cli">
    <div class="cli-bar">
      <span class="cli-title">⌁ ACU Debug Console</span>
      <span class="cli-hint">read-only · dev tool · #/debug/cli</span>
    </div>

    <div class="cli-body">
      <!-- Controls -->
      <div class="cli-controls">
        <div class="cli-send-row">
          <input v-model="cmd" class="cli-input" placeholder="e.g. 2 4" @keyup.enter="send(cmd)" />
          <button class="cli-send" :disabled="loading" @click="send(cmd)">SEND</button>
        </div>

        <div class="cli-refresh">
          <label v-for="r in REFRESH" :key="r.s" class="cli-radio">
            <input type="radio" :value="r.s" v-model="refresh" @change="setRefresh" /> {{ r.label }}
          </label>
        </div>

        <div class="cli-group">Configs</div>
        <div class="cli-btns">
          <button v-for="c in CONFIGS" :key="c.cmd" class="cli-btn"
            :class="{ active: lastCmd === c.cmd }" @click="send(c.cmd)">{{ c.label }}</button>
        </div>

        <div class="cli-group">Stats</div>
        <div class="cli-btns">
          <button v-for="c in STATS" :key="c.cmd" class="cli-btn"
            :class="{ active: lastCmd === c.cmd }" @click="send(c.cmd)">{{ c.label }}</button>
        </div>
      </div>

      <!-- Terminal -->
      <pre class="cli-out" :class="{ err: !!error }">{{ error || output || 'Ready — pick a command or type one (e.g. 2 4).' }}</pre>
    </div>
  </div>
</template>

<script>
import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || ''

export default {
  name: 'CliConsole',
  data() {
    return {
      cmd: '',
      output: '',
      error: '',
      lastCmd: '',
      loading: false,
      refresh: 0,
      timer: null,
      REFRESH: [
        { s: 0, label: 'Off' }, { s: 0.5, label: '0.5s' },
        { s: 1, label: '1s' }, { s: 3, label: '3s' },
      ],
      CONFIGS: [
        { label: 'System', cmd: '1 1' }, { label: 'Network', cmd: '1 2' },
        { label: 'Sensors', cmd: '1 3' }, { label: 'ESA', cmd: '1 4' },
        { label: 'Site', cmd: '1 5' }, { label: 'Satellite', cmd: '1 6' },
        { label: 'Server', cmd: '1 7' }, { label: 'Storage', cmd: '1 8' },
        { label: 'Advanced', cmd: '1 9' }, { label: 'All', cmd: '1 10' },
      ],
      STATS: [
        { label: 'Local', cmd: '2 1' }, { label: 'Pointing', cmd: '2 4' },
        { label: 'AMIP State', cmd: '2 5' }, { label: 'Antenna Ctrl', cmd: '2 6' },
        { label: 'Satellite', cmd: '2 7' },
      ],
    }
  },
  beforeUnmount() {
    if (this.timer) clearInterval(this.timer)
  },
  methods: {
    async send(cmd) {
      cmd = (cmd || '').trim()
      if (!cmd || this.loading) return
      this.cmd = cmd
      this.lastCmd = cmd
      this.loading = true
      try {
        const res = await axios.post(`${API_URL}/api/debug/cli`, { cmd })
        this.output = res.data.output || '(no output)'
        this.error = ''
      } catch (e) {
        this.error = e.response?.data?.error || 'Command failed'
      } finally {
        this.loading = false
      }
    },
    setRefresh() {
      if (this.timer) { clearInterval(this.timer); this.timer = null }
      if (this.refresh > 0) {
        this.timer = setInterval(() => {
          if (this.lastCmd && !this.loading) this.send(this.lastCmd)
        }, this.refresh * 1000)
      }
    },
  },
}
</script>

<style scoped>
.cli { padding: 16px; background: #f5f5f5; min-height: 100%; }
.cli-bar {
  display: flex; align-items: baseline; gap: 12px;
  background: #1e3a5f; color: #fff; padding: 10px 15px;
  border-radius: 4px 4px 0 0; font-size: 14px; font-weight: 600;
}
.cli-hint { font-size: 11px; color: #9bbcd6; font-weight: 400; }
.cli-body { display: flex; border: 1px solid #e0e0e0; border-top: none; border-radius: 0 0 4px 4px; }
.cli-controls {
  width: 232px; flex-shrink: 0; padding: 14px;
  background: #fff; border-right: 1px solid #e0e0e0;
  display: flex; flex-direction: column; gap: 10px;
}
.cli-send-row { display: flex; gap: 6px; }
.cli-input {
  flex: 1; min-width: 0; padding: 6px 8px; border: 1px solid #cbd5e1;
  border-radius: 4px; font-family: monospace; font-size: 13px;
}
.cli-input:focus { outline: none; border-color: #2563eb; }
.cli-send {
  background: #1e3a5f; color: #fff; border: none; border-radius: 4px;
  padding: 6px 12px; font-weight: 600; cursor: pointer; font-size: 12px;
}
.cli-send:hover:not(:disabled) { background: #2563eb; }
.cli-send:disabled { opacity: 0.5; cursor: wait; }
.cli-refresh { display: flex; gap: 10px; font-size: 11px; color: #555; }
.cli-radio { display: flex; align-items: center; gap: 3px; cursor: pointer; }
.cli-group {
  font-size: 10px; font-weight: 700; text-transform: uppercase;
  letter-spacing: 0.06em; color: #6b7280; margin-top: 6px;
}
.cli-btns { display: grid; grid-template-columns: 1fr 1fr; gap: 5px; }
.cli-btn {
  background: #eef2f7; color: #334155; border: 1px solid #d6dee8;
  border-radius: 4px; padding: 6px 4px; font-size: 11px; cursor: pointer;
}
.cli-btn:hover { background: #dbe6f3; }
.cli-btn.active { background: #1e3a5f; color: #fff; border-color: #1e3a5f; }
.cli-out {
  flex: 1; margin: 0; padding: 14px;
  background: #0b1220; color: #7CFC9B;
  font-family: 'Courier New', monospace; font-size: 12.5px; line-height: 1.45;
  white-space: pre-wrap; word-break: break-word;
  min-height: 460px; max-height: 72vh; overflow: auto;
}
.cli-out.err { color: #ff6b6b; }
</style>
