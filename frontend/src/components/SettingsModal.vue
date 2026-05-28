<template>
  <div class="settings-overlay" @click.self="$emit('close')">
    <div class="settings-panel">
      <header class="settings-header">
        <h2>设置</h2>
        <button class="btn-close" @click="$emit('close')">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
          </svg>
        </button>
      </header>

      <nav class="settings-nav">
        <button v-for="t in tabs" :key="t.id" :class="{ active: tab === t.id }" @click="tab = t.id">
          {{ t.label }}
        </button>
      </nav>

      <section class="settings-content">
        <!-- API 配置 -->
        <div v-if="tab === 'api'" class="tab-content">
          <div class="form-group">
            <label>API Key</label>
            <input type="password" v-model="form.apiKey" placeholder="sk-xxx" />
            <p class="hint">阿里云百炼 API Key</p>
          </div>
          <div class="form-group">
            <label>区域</label>
            <select v-model="form.region">
              <option value="beijing">北京</option>
              <option value="singapore">新加坡</option>
            </select>
          </div>
        </div>

        <!-- 角色管理 -->
        <div v-if="tab === 'persona'" class="tab-content">
          <div class="form-group">
            <label>角色名称</label>
            <input v-model="form.personaName" placeholder="角色名" />
          </div>
          <div class="form-group">
            <label>音色</label>
            <select v-model="form.voice">
              <option v-for="v in voices" :key="v.id" :value="v.id">
                {{ v.name }} - {{ v.desc }}
              </option>
            </select>
          </div>
          <div class="form-group">
            <label>性格</label>
            <textarea v-model="form.personality" rows="3"></textarea>
          </div>
          <div class="form-group">
            <label>背景身份</label>
            <textarea v-model="form.background" rows="2"></textarea>
          </div>
          <div class="form-group">
            <label>说话风格</label>
            <textarea v-model="form.speakingStyle" rows="3"></textarea>
          </div>
          <div class="form-group">
            <label>与用户关系</label>
            <textarea v-model="form.relationship" rows="2"></textarea>
          </div>
        </div>

        <!-- 功能开关 -->
        <div v-if="tab === 'features'" class="tab-content">
          <div class="form-group row">
            <label>非实时联网搜索</label>
            <input type="checkbox" v-model="form.nonRealtimeSearch" />
          </div>
          <div class="form-group row">
            <label>实时联网搜索</label>
            <input type="checkbox" v-model="form.realtimeSearch" />
          </div>
          <div class="form-group row">
            <label>输出音频</label>
            <input type="checkbox" v-model="form.outputAudio" />
          </div>
        </div>

        <!-- 实时模式 -->
        <div v-if="tab === 'realtime'" class="tab-content">
          <div class="form-group">
            <label>VAD 类型</label>
            <select v-model="form.vadType">
              <option value="semantic_vad">Semantic VAD（推荐）</option>
              <option value="server_vad">Server VAD</option>
            </select>
          </div>
          <div class="form-group">
            <label>静默时长 (ms)</label>
            <input type="number" v-model.number="form.silenceDuration" min="300" max="2000" step="100" />
          </div>
          <div class="form-group">
            <label>截屏频率 (ms)</label>
            <input type="number" v-model.number="form.screenshotInterval" min="500" max="10000" step="500" />
          </div>
        </div>
      </section>

      <footer class="settings-footer">
        <button class="btn-save" @click="save">保存</button>
      </footer>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getSettings, getVoices } from '@/services/api'

defineEmits(['close'])

const tabs = [
  { id: 'api', label: 'API' },
  { id: 'persona', label: '角色' },
  { id: 'features', label: '功能' },
  { id: 'realtime', label: '实时模式' },
]
const tab = ref('api')
const voices = ref([])

const form = ref({
  apiKey: '',
  region: 'beijing',
  personaName: '',
  voice: 'Tina',
  personality: '',
  background: '',
  speakingStyle: '',
  relationship: '',
  nonRealtimeSearch: false,
  realtimeSearch: false,
  outputAudio: true,
  vadType: 'semantic_vad',
  silenceDuration: 800,
  screenshotInterval: 1000,
})

onMounted(async () => {
  try {
    const [settingsResp, voicesResp] = await Promise.all([getSettings(), getVoices()])
    voices.value = voicesResp.voices || []

    // 填充表单
    const { settings, persona, env } = settingsResp
    form.value.region = env?.region || 'beijing'
    form.value.personaName = persona?.name || ''
    form.value.voice = persona?.voice || settings?.voice || 'Tina'
    form.value.personality = persona?.personality || ''
    form.value.background = persona?.background || ''
    form.value.speakingStyle = persona?.speaking_style || ''
    form.value.relationship = persona?.relationship || ''
    form.value.nonRealtimeSearch = settings?.non_realtime?.enable_search || false
    form.value.realtimeSearch = settings?.realtime?.enable_search || false
    form.value.outputAudio = settings?.output?.modalities?.includes('audio') ?? true
    form.value.vadType = settings?.realtime?.vad_type || 'semantic_vad'
    form.value.silenceDuration = settings?.realtime?.silence_duration_ms || 800
    form.value.screenshotInterval = settings?.screen_capture?.interval_ms || 1000
  } catch (e) {
    console.error('加载设置失败:', e)
  }
})

async function save() {
  // TODO: 调用后端 PUT /api/settings/update 和 /api/settings/env
  // 暂时只打印
  console.log('保存设置:', form.value)
  alert('设置已保存（当前为前端演示，需后端配合）')
}
</script>

<style scoped>
.settings-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  backdrop-filter: blur(4px);
}

.settings-panel {
  background: var(--bg-panel);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  width: 600px;
  max-height: 80vh;
  display: flex;
  flex-direction: column;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
}

.settings-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid var(--border);
}

.settings-header h2 {
  font-size: 16px;
  font-weight: 600;
}

.btn-close {
  color: var(--text-muted);
  padding: 4px;
  border-radius: 4px;
  transition: all var(--transition-fast);
}

.btn-close:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}

.settings-nav {
  display: flex;
  gap: 2px;
  padding: 10px 20px;
  border-bottom: 1px solid var(--border);
}

.settings-nav button {
  padding: 6px 14px;
  border-radius: var(--radius-sm);
  font-size: 13px;
  color: var(--text-secondary);
  transition: all var(--transition-fast);
}

.settings-nav button:hover {
  background: var(--bg-hover);
}

.settings-nav button.active {
  background: var(--accent-dark);
  color: #fff;
}

.settings-content {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
}

.tab-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-group.row {
  flex-direction: row;
  align-items: center;
  justify-content: space-between;
}

.form-group label {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-secondary);
}

.form-group input[type="text"],
.form-group input[type="password"],
.form-group input[type="number"],
.form-group textarea,
.form-group select {
  width: 100%;
}

.form-group select {
  padding: 8px 12px;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  color: var(--text-primary);
}

.form-group input[type="checkbox"] {
  width: 18px;
  height: 18px;
  accent-color: var(--accent);
}

.hint {
  font-size: 11px;
  color: var(--text-muted);
}

.settings-footer {
  padding: 12px 20px;
  border-top: 1px solid var(--border);
  display: flex;
  justify-content: flex-end;
}

.btn-save {
  padding: 8px 20px;
  background: var(--accent);
  color: #fff;
  border-radius: var(--radius-sm);
  font-size: 13px;
  font-weight: 500;
  transition: background var(--transition-fast);
}

.btn-save:hover {
  background: var(--accent-light);
}
</style>
