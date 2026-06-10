import { defineStore } from 'pinia'
import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || ''

export const useAcuStore = defineStore('acu', {
    state: () => ({
        status: {},
        tleWarning: '',
        _statusTimer: null,
        _tleTimer: null,
    }),

    actions: {
        async fetchStatus() {
            try {
                const res = await axios.get(`${API_URL}/api/status`)
                this.status = res.data || {}
            } catch {
                // keep last known state
            }
        },

        async fetchTleWarning() {
            try {
                const res = await axios.get(`${API_URL}/api/tle/match-status`)
                this.tleWarning = res.data.warning || ''
            } catch {
                this.tleWarning = ''
            }
        },

        start() {
            if (this._statusTimer) return
            this.fetchStatus()
            this.fetchTleWarning()
            this._statusTimer = setInterval(this.fetchStatus, 2000)
            this._tleTimer    = setInterval(this.fetchTleWarning, 30000)
        },

        stop() {
            clearInterval(this._statusTimer)
            clearInterval(this._tleTimer)
            this._statusTimer = null
            this._tleTimer    = null
        },
    },
})
