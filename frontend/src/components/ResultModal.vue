<template>
  <div v-if="visible" class="modal-overlay" @click.self="$emit('close')">
    <div class="modal modal-confirm">
      <div class="modal-header">
        <h3>{{ title }}</h3>
        <button class="btn-close" @click="$emit('close')">×</button>
      </div>
      <div class="modal-body">
        <p :class="{ 'result-success': success, 'result-error': !success }">{{ message }}</p>
      </div>
      <div class="modal-actions">
        <button class="btn-save" @click="$emit('close')">OK</button>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'ResultModal',
  props: {
    visible: { type: Boolean, default: false },
    title: { type: String, default: '' },
    message: { type: String, default: '' },
    success: { type: Boolean, default: true }
  },
  emits: ['close']
}
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal {
  background: white;
  border-radius: 8px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
  max-width: 90vw;
}

.modal-confirm {
  width: 420px;
}

.modal-header {
  padding: 16px 20px;
  border-bottom: 1px solid #eee;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.modal-header h3 {
  margin: 0;
  font-size: 16px;
  color: #333;
}

.btn-close {
  background: none;
  border: none;
  font-size: 24px;
  cursor: pointer;
  color: #999;
  padding: 0;
  line-height: 1;
}

.modal-body {
  padding: 20px;
}

.modal-actions {
  padding: 12px 20px;
  border-top: 1px solid #eee;
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.btn-save {
  padding: 8px 20px;
  background: #4a90a4;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.result-success {
  color: #166534;
  font-weight: 500;
}

.result-error {
  color: #991b1b;
  font-weight: 500;
}
</style>
