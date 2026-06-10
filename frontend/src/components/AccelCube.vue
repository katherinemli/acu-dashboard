<template>
  <div class="face-map-container">
    <div class="face-map">
      <div
        v-for="cell in FACE_CELLS"
        :key="cell.label"
        class="face-cell"
        :class="cellClass(cell.index)"
        :style="{ gridColumn: cell.col, gridRow: cell.row }"
      >
        {{ cell.label }}
      </div>
    </div>
    <div class="face-legend">
      <span class="legend-item"><span class="swatch swatch-captured"></span>Captured</span>
      <span class="legend-item"><span class="swatch swatch-active"></span>Current</span>
      <span class="legend-item"><span class="swatch swatch-recording"></span>Recording</span>
      <span class="legend-item"><span class="swatch swatch-empty"></span>Pending</span>
    </div>
  </div>
</template>

<script>
const FACE_CELLS = [
  { label: 'Z+', index: 4, col: 2, row: 1 },
  { label: 'X-', index: 1, col: 1, row: 2 },
  { label: 'Y+', index: 2, col: 2, row: 2 },
  { label: 'X+', index: 0, col: 3, row: 2 },
  { label: 'Z-', index: 5, col: 2, row: 3 },
  { label: 'Y-', index: 3, col: 2, row: 4 },
]

export default {
  name: 'AccelCube',
  props: {
    faceHits:    { type: Array,   default: () => [0, 0, 0, 0, 0, 0] },
    currentFace: { type: Number,  default: -1 },
    capturing:   { type: Boolean, default: false }
  },
  data() {
    return { FACE_CELLS }
  },
  methods: {
    cellClass(index) {
      if (this.faceHits[index] > 0)                            return 'face-captured'
      if (index === this.currentFace && this.capturing)        return 'face-recording'
      if (index === this.currentFace)                          return 'face-active'
      return 'face-empty'
    }
  }
}
</script>

<style scoped>
.face-map-container {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  padding: 8px 0;
}

.face-map {
  display: grid;
  grid-template-columns: repeat(3, 76px);
  grid-template-rows: repeat(4, 76px);
  gap: 5px;
}

.face-cell {
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: monospace;
  font-size: 16px;
  font-weight: 700;
  border-radius: 6px;
  border: 2px solid rgba(0, 0, 0, 0.12);
  transition: background-color 0.25s, color 0.25s;
  user-select: none;
}

.face-empty {
  background: #dde8f0;
  color: #7a8fa0;
  border-color: #c0d0dc;
}

.face-active {
  background: #42a5f5;
  color: white;
  border-color: #1a87e0;
}

.face-recording {
  background: #f08820;
  color: white;
  border-color: #c96800;
  animation: pulse 0.8s ease-in-out infinite;
}

.face-captured {
  background: #2ecc40;
  color: white;
  border-color: #1aaa2e;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50%       { opacity: 0.65; }
}

.face-legend {
  display: flex;
  gap: 14px;
  justify-content: flex-start;
  margin-top: 12px;
  flex-wrap: wrap;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 12px;
  color: #555;
  font-family: monospace;
}

.swatch {
  width: 14px;
  height: 14px;
  border-radius: 3px;
  border: 1px solid rgba(0,0,0,0.15);
  flex-shrink: 0;
}

.swatch-captured  { background: #2ecc40; }
.swatch-active    { background: #42a5f5; }
.swatch-recording { background: #f08820; }
.swatch-empty     { background: #dde8f0; }
</style>
