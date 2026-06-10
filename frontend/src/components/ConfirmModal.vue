<template>
  <div v-if="visible" class="modal-overlay" @click.self="$emit('cancel')">
    <div class="modal modal-confirm">
      <div class="modal-header">
        <h3>{{ title }}</h3>
        <button class="btn-close" @click="$emit('cancel')">×</button>
      </div>
      <div class="modal-body">
        <p>{{ message }}</p>
        <p v-if="warning" class="warning">{{ warning }}</p>
      </div>
      <div class="modal-actions">
        <button class="btn-confirm" :class="btnClass" @click="$emit('confirm')">{{ btnText }}</button>
        <button class="btn-cancel" @click="$emit('cancel')">Cancel</button>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'ConfirmModal',
  props: {
    visible: { type: Boolean, default: false },
    title: { type: String, default: 'Confirm' },
    message: { type: String, default: '' },
    warning: { type: String, default: '' },
    btnText: { type: String, default: 'Confirm' },
    btnClass: { type: String, default: 'btn-primary' } // 'btn-primary' | 'btn-danger'
  },
  emits: ['confirm', 'cancel']
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

.modal-body p {
  margin: 0 0 8px;
  color: #555;
  font-size: 14px;
}

.modal-body .warning {
  color: #991b1b;
  font-size: 13px;
}

.modal-actions {
  padding: 12px 20px;
  border-top: 1px solid #eee;
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.btn-confirm,
.btn-cancel {
  padding: 8px 16px;
  border-radius: 4px;
  font-size: 13px;
  cursor: pointer;
  border: none;
}

.btn-primary {
  background: #4a90a4;
  color: white;
}

.btn-primary:hover {
  background: #3d7a8c;
}

.btn-danger {
  background: #fe5e37;
  color: white;
}

.btn-danger:hover {
  background: #e5502f;
}

.btn-cancel {
  background: #e0e0e0;
  color: #333;
}
</style>
