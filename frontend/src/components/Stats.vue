<template>
  <div class="stats">
    <h2>Sensor Statistics</h2>
    
    <div class="stats-controls">
      <label>
        Time range:
        <select v-model="limit" @change="loadData">
          <option :value="20">Last 20 readings</option>
          <option :value="50">Last 50 readings</option>
          <option :value="100">Last 100 readings</option>
        </select>
      </label>
    </div>
    
    <div v-if="loading" class="loading">Loading...</div>
    
    <div v-else class="charts">
      <!-- Temperature Chart -->
      <div class="chart-container">
        <h3>Temperature</h3>
        <div class="chart-info">
          <span>Current: <strong>{{ currentTemp }}°C</strong></span>
          <span>Min: {{ minTemp }}°C</span>
          <span>Max: {{ maxTemp }}°C</span>
        </div>
        <svg :viewBox="`0 0 ${width} ${height}`" class="chart">
          <line v-for="i in 5" :key="'tg'+i"
                :x1="padding" 
                :x2="width - padding" 
                :y1="padding + (i-1) * (chartHeight/4)"
                :y2="padding + (i-1) * (chartHeight/4)"
                class="grid-line"/>
          
          <text v-for="(label, i) in tempYLabels" :key="'tl'+i"
                :x="padding - 5" 
                :y="padding + i * (chartHeight/4) + 4"
                class="axis-label">{{ label }}</text>
          
          <polyline :points="tempPoints" class="chart-line temp-line"/>
          
          <circle v-for="(point, i) in data" :key="'tp'+i"
                  :cx="getX(i)" 
                  :cy="getTempY(point.temperature)"
                  r="3" 
                  class="data-point temp-point"/>
        </svg>
      </div>
      
      <!-- Pressure Chart -->
      <div class="chart-container">
        <h3>Pressure</h3>
        <div class="chart-info">
          <span>Current: <strong>{{ currentPressure }} Pa</strong></span>
          <span>Min: {{ minPressure }} Pa</span>
          <span>Max: {{ maxPressure }} Pa</span>
        </div>
        <svg :viewBox="`0 0 ${width} ${height}`" class="chart">
          <line v-for="i in 5" :key="'pg'+i"
                :x1="padding" 
                :x2="width - padding" 
                :y1="padding + (i-1) * (chartHeight/4)"
                :y2="padding + (i-1) * (chartHeight/4)"
                class="grid-line"/>
          
          <text v-for="(label, i) in pressureYLabels" :key="'pl'+i"
                :x="padding - 5" 
                :y="padding + i * (chartHeight/4) + 4"
                class="axis-label">{{ label }}</text>
          
          <polyline :points="pressurePoints" class="chart-line pressure-line"/>
          
          <circle v-for="(point, i) in data" :key="'pp'+i"
                  :cx="getX(i)" 
                  :cy="getPressureY(point.pressure)"
                  r="3" 
                  class="data-point pressure-point"/>
        </svg>
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || ''
  
export default {
  name: 'Stats',
  data() {
    return {
      loading: true,
      limit: 50,
      data: [],
      width: 600,
      height: 200,
      padding: 50,
      refreshInterval: null
    }
  },
  computed: {
    chartHeight() {
      return this.height - this.padding * 2
    },
    chartWidth() {
      return this.width - this.padding * 2
    },
    
    currentTemp() {
      const last = this.data[this.data.length - 1]
      return last ? last.temperature.toFixed(2) : '--'
    },
    currentPressure() {
      const last = this.data[this.data.length - 1]
      return last ? Math.round(last.pressure) : '--'
    },
    
    minTemp() {
      if (!this.data.length) return '--'
      return Math.min(...this.data.map(d => d.temperature)).toFixed(2)
    },
    maxTemp() {
      if (!this.data.length) return '--'
      return Math.max(...this.data.map(d => d.temperature)).toFixed(2)
    },
    
    minPressure() {
      if (!this.data.length) return '--'
      return Math.round(Math.min(...this.data.map(d => d.pressure)))
    },
    maxPressure() {
      if (!this.data.length) return '--'
      return Math.round(Math.max(...this.data.map(d => d.pressure)))
    },
    
    tempRange() {
      if (!this.data.length) return { min: 25, max: 30 }
      const min = Math.min(...this.data.map(d => d.temperature))
      const max = Math.max(...this.data.map(d => d.temperature))
      const pad = (max - min) * 0.1 || 0.5
      return { min: min - pad, max: max + pad }
    },
    
    pressureRange() {
      if (!this.data.length) return { min: 100000, max: 101000 }
      const min = Math.min(...this.data.map(d => d.pressure))
      const max = Math.max(...this.data.map(d => d.pressure))
      const pad = (max - min) * 0.1 || 5
      return { min: min - pad, max: max + pad }
    },
    
    tempYLabels() {
      const { min, max } = this.tempRange
      const step = (max - min) / 4
      return [max, max - step, max - step*2, max - step*3, min].map(v => v.toFixed(1))
    },
    pressureYLabels() {
      const { min, max } = this.pressureRange
      const step = (max - min) / 4
      return [max, max - step, max - step*2, max - step*3, min].map(v => Math.round(v))
    },
    
    tempPoints() {
      return this.data
        .map((d, i) => `${this.getX(i)},${this.getTempY(d.temperature)}`)
        .join(' ')
    },
    pressurePoints() {
      return this.data
        .map((d, i) => `${this.getX(i)},${this.getPressureY(d.pressure)}`)
        .join(' ')
    }
  },
  methods: {
    getX(index) {
      const count = Math.max(this.data.length - 1, 1)
      return this.padding + (index / count) * this.chartWidth
    },
    getTempY(value) {
      const { min, max } = this.tempRange
      const ratio = (value - min) / (max - min)
      return this.padding + (1 - ratio) * this.chartHeight
    },
    getPressureY(value) {
      const { min, max } = this.pressureRange
      const ratio = (value - min) / (max - min)
      return this.padding + (1 - ratio) * this.chartHeight
    },
    
    async loadData() {
      try {
        const res = await axios.get(`${API_URL}/api/telemetry/temp-pres/history?limit=${this.limit}`)
        this.data = res.data || []
      } catch (e) {
        console.error('Error loading stats:', e)
      }
      this.loading = false
    }
  },
  mounted() {
    this.loadData()
    this.refreshInterval = setInterval(this.loadData, 10000)
  },
  beforeUnmount() {
    if (this.refreshInterval) {
      clearInterval(this.refreshInterval)
    }
  }
}
</script>

<style scoped>
.stats {
  padding: 20px;
}

h2 {
  margin-bottom: 20px;
  color: #333;
  font-size: 18px;
  font-weight: 500;
}

.stats-controls {
  margin-bottom: 20px;
}

.stats-controls label {
  font-size: 13px;
  color: #555;
}

.stats-controls select {
  margin-left: 10px;
  padding: 6px 10px;
  border: 1px solid #ddd;
  border-radius: 3px;
  font-size: 13px;
}

.loading {
  text-align: center;
  padding: 40px;
  color: #666;
}

.charts {
  display: flex;
  flex-direction: column;
  gap: 30px;
}

.chart-container {
  background: white;
  border-radius: 4px;
  padding: 15px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}

.chart-container h3 {
  margin: 0 0 10px 0;
  font-size: 14px;
  font-weight: 500;
  color: #333;
}

.chart-info {
  display: flex;
  gap: 20px;
  margin-bottom: 10px;
  font-size: 12px;
  color: #666;
}

.chart-info strong {
  color: #333;
}

.chart {
  width: 100%;
  height: auto;
  max-height: 200px;
}

.grid-line {
  stroke: #eee;
  stroke-width: 1;
}

.axis-label {
  font-size: 10px;
  fill: #888;
  text-anchor: end;
}

.chart-line {
  fill: none;
  stroke-width: 2;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.temp-line {
  stroke: #e57373;
}

.pressure-line {
  stroke: #64b5f6;
}

.data-point {
  fill: white;
  stroke-width: 2;
}

.temp-point {
  stroke: #e57373;
}

.pressure-point {
  stroke: #64b5f6;
}
</style>