<template>
  <div class="tool-section">
    <h2>Events</h2>
    <div class="events-container">
      <div class="events-toolbar">
        <select v-model="eventsFilter" @change="loadEvents">
          <option value="all">All Events</option>
          <option value="error">Errors</option>
          <option value="warning">Warnings</option>
          <option value="info">Info</option>
        </select>
        <button @click="loadEvents">Refresh</button>
      </div>
      <div v-if="loading" class="loading">Loading...</div>
      <div v-else class="events-list">
        <div v-if="events.length === 0" class="no-data">No events found</div>
        <div v-for="event in events" :key="event.id" class="event-item" :class="event.level">
          <span class="event-time">{{ formatDate(event.timestamp) }}</span>
          <span class="event-level">{{ event.level.toUpperCase() }}</span>
          <span class="event-source">[{{ event.source }}]</span>
          <span class="event-message">{{ event.message }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || ''

export default {
  name: 'EventsPanel',
  data() {
    return {
      eventsFilter: 'all',
      events: [],
      loading: false
    }
  },
  mounted() {
    this.loadEvents()
  },
  methods: {
    async loadEvents() {
      this.loading = true
      try {
        const params = this.eventsFilter !== 'all' ? `?level=${this.eventsFilter}` : ''
        const res = await axios.get(`${API_URL}/api/events${params}`)
        this.events = res.data
      } catch (e) {
        console.error('Error loading events:', e)
        this.events = []
      }
      this.loading = false
    },

    formatDate(timestamp) {
      if (!timestamp) return ''
      return timestamp.replace('T', ' ').substring(0, 19)
    }
  }
}
</script>

<style scoped>
.tool-section {
  padding: 20px;
}

h2 {
  margin-bottom: 20px;
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
}

.events-container {
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  overflow: hidden;
}

.events-toolbar {
  padding: 15px;
  background: #f5f5f5;
  display: flex;
  gap: 10px;
}

.events-toolbar select,
.events-toolbar button {
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 13px;
}

.events-toolbar button {
  background: #369;
  color: white;
  border: none;
  cursor: pointer;
}

.events-list {
  max-height: 400px;
  overflow-y: auto;
}

.event-item {
  display: flex;
  gap: 10px;
  padding: 12px 15px;
  border-bottom: 1px solid #f0f0f0;
  font-size: 13px;
  align-items: center;
}

.event-item.error {
  background: #fff5f5;
}

.event-item.warning {
  background: #fffbf0;
}

.event-time {
  color: #999;
  min-width: 140px;
  font-family: monospace;
  font-size: 12px;
}

.event-level {
  font-weight: 600;
  min-width: 60px;
}

.event-item.error .event-level {
  color: #fe5e37;
}

.event-item.warning .event-level {
  color: #e6a700;
}

.event-item.info .event-level {
  color: #42a5f5;
}

.event-source {
  color: #888;
  font-size: 12px;
}

.event-message {
  flex: 1;
  color: #333;
}
</style>
