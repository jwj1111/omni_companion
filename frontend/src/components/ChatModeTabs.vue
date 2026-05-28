<template>
  <nav class="mode-tabs">
    <div class="tab-list">
      <router-link to="/chat" class="tab" :class="{ active: active === 'non-immersive' }">
        <span class="tab-label">文字对话</span>
      </router-link>
      <router-link to="/immersive" class="tab" :class="{ active: active === 'immersive' }">
        <span class="tab-label">语音对话</span>
      </router-link>
    </div>
    <div v-if="$slots.actions" class="tab-actions">
      <slot name="actions" />
    </div>
  </nav>
</template>

<script setup>
defineProps({
  active: { type: String, required: true }
})
</script>

<style scoped>
.mode-tabs {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 16px;
  gap: 12px;
  background: var(--bg-panel);
  border-bottom: 1px solid var(--border);
}

.tab-list {
  display: flex;
  align-items: center;
  gap: 2px;
  min-width: 0;
}

.tab-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  flex-shrink: 0;
}

.tab {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 10px 16px;
  text-decoration: none;
  color: var(--text-muted);
  font-size: var(--type-label);
  font-weight: 500;
  line-height: var(--leading-tight);
  letter-spacing: var(--tracking-label);
  transition: color var(--transition-fast);
}

.tab::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 16px;
  right: 16px;
  height: 2px;
  background: transparent;
  border-radius: 1px 1px 0 0;
  transition: background var(--transition-fast);
}

.tab:hover {
  color: var(--text-secondary);
}

.tab.active {
  color: var(--accent-light);
}

.tab.active::after {
  background: var(--accent);
}
</style>
