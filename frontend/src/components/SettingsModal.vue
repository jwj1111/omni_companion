<template>
  <div class="settings-overlay" @click.self="$emit('close')">
    <div class="settings-panel" role="dialog" aria-modal="true" aria-labelledby="settings-title">
      <header class="settings-header">
        <h2 id="settings-title">设置</h2>
        <button type="button" class="btn-close" @click="$emit('close')" aria-label="关闭设置">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
          </svg>
        </button>
      </header>

      <nav class="settings-nav">
        <button type="button" v-for="t in tabs" :key="t.id" :class="{ active: tab === t.id }" @click="tab = t.id">
          {{ t.label }}
        </button>
      </nav>

      <section class="settings-content">
        <!-- API 配置 -->
        <div v-if="tab === 'api'" class="tab-content">
          <div class="form-group">
            <label for="settings-api-key">API Key</label>
            <input id="settings-api-key" type="password" v-model="form.apiKey" placeholder="sk-xxx" autocomplete="off" />
            <p class="hint">阿里云百炼 API Key</p>
          </div>
          <div class="form-group">
            <label for="settings-region">区域</label>
            <select id="settings-region" v-model="form.region">
              <option value="beijing">北京</option>
              <option value="singapore">新加坡</option>
            </select>
          </div>
        </div>

        <!-- 角色管理 -->
        <div v-if="tab === 'persona'" class="tab-content">
          <div class="form-group">
            <label for="settings-persona-name">角色名称</label>
            <input id="settings-persona-name" v-model="form.personaName" placeholder="角色名" />
          </div>
          <div class="form-group">
            <label for="settings-voice">音色</label>
            <select id="settings-voice" v-model="form.voice">
              <option v-for="v in voices" :key="v.id" :value="v.id">
                {{ v.name }} - {{ v.desc }}
              </option>
            </select>
          </div>
          <div class="form-group">
            <label for="settings-personality">性格</label>
            <textarea id="settings-personality" v-model="form.personality" rows="3"></textarea>
          </div>
          <div class="form-group">
            <label for="settings-background">背景身份</label>
            <textarea id="settings-background" v-model="form.background" rows="2"></textarea>
          </div>
          <div class="form-group">
            <label for="settings-speaking-style">说话风格</label>
            <textarea id="settings-speaking-style" v-model="form.speakingStyle" rows="3"></textarea>
          </div>
          <div class="form-group">
            <label for="settings-relationship">与用户关系</label>
            <textarea id="settings-relationship" v-model="form.relationship" rows="2"></textarea>
          </div>
          <div class="form-group">
            <label for="settings-quirks">口癖（选填）</label>
            <textarea id="settings-quirks" v-model="form.quirks" rows="2" placeholder="例如常用语气词、习惯句式，可留空"></textarea>
            <p class="hint">留空则不额外限制角色口癖</p>
          </div>
        </div>

        <!-- 功能开关 -->
        <div v-if="tab === 'features'" class="tab-content">
          <div class="form-group row">
            <label>文字对话联网搜索</label>
            <input type="checkbox" v-model="form.nonRealtimeSearch" />
          </div>
          <div class="form-group row">
            <label for="settings-realtime-search">语音对话联网搜索</label>
            <input id="settings-realtime-search" type="checkbox" v-model="form.realtimeSearch" />
          </div>
          <div class="form-group row">
            <label>语音回复</label>
            <input type="checkbox" v-model="form.outputAudio" />
          </div>
        </div>

        <!-- 实时模式 -->
        <div v-if="tab === 'realtime'" class="tab-content">
          <div class="form-group">
            <label>语音检测方式</label>
            <select v-model="form.vadType">
              <option value="semantic_vad">语义检测（推荐）</option>
              <option value="server_vad">静音检测</option>
            </select>
          </div>
          <div class="form-group">
            <label>停顿判定时长</label>
            <input type="number" v-model.number="form.silenceDuration" min="300" max="2000" step="100" />
            <p class="hint">停顿多久后认为你说完了（毫秒）</p>
          </div>
          <div class="form-group">
            <label>画面采集间隔</label>
            <input type="number" v-model.number="form.screenshotInterval" min="500" max="10000" step="500" />
            <p class="hint">多久截一次屏发给 AI（毫秒）</p>
          </div>
        </div>

        <!-- 行为规范 -->
        <div v-if="tab === 'prompt'" class="tab-content">
          <div class="form-group">
            <label for="settings-interaction-rules">行为规范</label>
            <textarea
              id="settings-interaction-rules"
              v-model="form.interactionRules"
              rows="16"
              class="rules-textarea"
              placeholder="定义 AI 的性格、说话方式和行为边界..."
            ></textarea>
            <p class="hint">定义 AI 的说话方式和行为边界，应用后本次会话生效，刷新后恢复默认值</p>
          </div>
        </div>
      </section>

      <!-- Toast 消息 -->
      <div v-if="toast" class="settings-toast" :class="toast.type" role="alert">
        {{ toast.message }}
      </div>

      <footer class="settings-footer">
        <button type="button" class="btn-save" @click="save" :disabled="saving">
          {{ saving ? '保存中...' : '保存' }}
        </button>
      </footer>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getSettings, getVoices, updateRules, updateSettings, updateEnv, updatePersona } from '@/services/api'

defineEmits(['close'])

const tabs = [
  { id: 'api', label: '接口' },
  { id: 'persona', label: '角色' },
  { id: 'features', label: '功能' },
  { id: 'realtime', label: '语音模式' },
  { id: 'prompt', label: '行为规范' },
]
const tab = ref('api')
const voices = ref([])
const saving = ref(false)
const toast = ref(null)

function showToast(message, type = 'success') {
  toast.value = { message, type }
  setTimeout(() => { toast.value = null }, 3000)
}

const form = ref({
  apiKey: '',
  region: 'beijing',
  personaName: '',
  voice: 'Tina',
  personality: '',
  background: '',
  speakingStyle: '',
  relationship: '',
  quirks: '',
  nonRealtimeSearch: false,
  realtimeSearch: false,
  outputAudio: true,
  vadType: 'semantic_vad',
  silenceDuration: 800,
  screenshotInterval: 1000,
  interactionRules: '',
})

let activePersonaId = 'a001'

onMounted(async () => {
  try {
    const [settingsResp, voicesResp] = await Promise.all([getSettings(), getVoices()])
    voices.value = voicesResp.voices || []

    // 填充表单
    const { settings, persona, env, interaction_rules } = settingsResp
    activePersonaId = settings?.active_persona || 'a001'
    form.value.region = env?.region || 'beijing'
    form.value.personaName = persona?.name || ''
    form.value.voice = persona?.voice || settings?.voice || 'Tina'
    form.value.personality = persona?.personality || ''
    form.value.background = persona?.background || ''
    form.value.speakingStyle = persona?.speaking_style || ''
    form.value.relationship = persona?.relationship || ''
    form.value.quirks = persona?.quirks || ''
    form.value.nonRealtimeSearch = settings?.non_realtime?.enable_search || false
    form.value.realtimeSearch = settings?.realtime?.enable_search || false
    form.value.outputAudio = settings?.output?.modalities?.includes('audio') ?? true
    form.value.vadType = settings?.realtime?.vad_type || 'semantic_vad'
    form.value.silenceDuration = settings?.realtime?.silence_duration_ms || 800
    form.value.screenshotInterval = settings?.screen_capture?.interval_ms || 1000
    form.value.interactionRules = interaction_rules || ''
  } catch (e) {
    showToast('加载设置失败，请刷新重试', 'error')
  }
})

async function save() {
  saving.value = true
  try {
    const f = form.value

    // 1. 保存 API Key / Region（仅在有值时）
    if (f.apiKey) {
      await updateEnv('DASHSCOPE_API_KEY', f.apiKey)
    }
    await updateEnv('API_REGION', f.region)

    // 2. 保存角色
    await updatePersona(activePersonaId, {
      name: f.personaName,
      voice: f.voice,
      personality: f.personality,
      background: f.background,
      speaking_style: f.speakingStyle,
      relationship: f.relationship,
      quirks: f.quirks,
    })

    // 3. 保存 settings
    await updateSettings({
      active_persona: activePersonaId,
      voice: f.voice,
      output: {
        modalities: f.outputAudio ? ['text', 'audio'] : ['text'],
      },
      realtime: {
        vad_type: f.vadType,
        silence_duration_ms: f.silenceDuration,
        enable_search: f.realtimeSearch,
      },
      non_realtime: {
        enable_search: f.nonRealtimeSearch,
      },
      screen_capture: {
        interval_ms: f.screenshotInterval,
      },
    })

    // 4. 保存行为规范 prompt
    await updateRules(f.interactionRules)

    showToast('已应用，本次会话生效；刷新后恢复默认值')
  } catch (e) {
    showToast('保存失败，请检查网络后重试', 'error')
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.settings-overlay {
  position: fixed;
  inset: 0;
  background: var(--overlay-scrim);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  backdrop-filter: blur(6px);
  animation: overlay-in 0.15s ease-out;
}

@keyframes overlay-in {
  from { opacity: 0; }
  to { opacity: 1; }
}

.settings-panel {
  background: var(--bg-panel);
  border: 1px solid var(--border-light);
  border-radius: var(--radius-lg);
  width: 560px;
  max-height: 80vh;
  display: flex;
  flex-direction: column;
  box-shadow: var(--shadow-lg);
  animation: panel-in 0.2s cubic-bezier(0.16, 1, 0.3, 1);
}

@keyframes panel-in {
  from { opacity: 0; transform: scale(0.97); }
  to { opacity: 1; transform: scale(1); }
}

.settings-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 20px;
  border-bottom: 1px solid var(--border);
}

.settings-header h2 {
  font-size: var(--type-title);
  font-weight: 600;
  line-height: var(--leading-tight);
  color: var(--text-secondary);
  letter-spacing: var(--tracking-label);
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
  gap: 0;
  padding: 0 20px;
  border-bottom: 1px solid var(--border);
}

.settings-nav button {
  padding: 8px 12px;
  border-radius: 0;
  font-size: var(--type-label);
  font-weight: 500;
  line-height: var(--leading-tight);
  letter-spacing: var(--tracking-label);
  color: var(--text-muted);
  transition: all var(--transition-fast);
  border-bottom: 2px solid transparent;
}

.settings-nav button:hover {
  color: var(--text-secondary);
}

.settings-nav button.active {
  color: var(--accent-light);
  border-bottom-color: var(--accent);
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
  font-size: var(--type-label);
  font-weight: 600;
  line-height: var(--leading-tight);
  letter-spacing: var(--tracking-label);
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
  font-size: var(--type-caption);
  line-height: var(--leading-body);
  color: var(--text-muted);
}

.settings-footer {
  padding: 12px 20px;
  border-top: 1px solid var(--border);
  display: flex;
  justify-content: flex-end;
}

.settings-toast {
  padding: 8px 20px;
  font-size: var(--type-label);
  line-height: var(--leading-body);
  text-align: center;
  animation: fadeIn 0.2s ease-out;
}

.settings-toast.success {
  color: var(--success);
  background: var(--success-subtle);
}

.settings-toast.error {
  color: var(--error);
  background: var(--error-subtle);
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(-4px); }
  to { opacity: 1; transform: translateY(0); }
}

.btn-save {
  padding: 7px 18px;
  background: var(--accent);
  color: var(--text-on-accent);
  border-radius: var(--radius-sm);
  font-size: var(--type-label);
  font-weight: 600;
  line-height: var(--leading-tight);
  letter-spacing: var(--tracking-label);
  transition: all var(--transition-fast);
}

.btn-save:hover {
  background: var(--accent-light);
}

.btn-save:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-save:active:not(:disabled),
.btn-close:active,
.settings-nav button:active {
  transform: translateY(1px);
}

.rules-textarea {
  font-family: var(--font-main);
  font-size: var(--type-body);
  line-height: var(--leading-chat);
  min-height: 300px;
  resize: vertical;
}
</style>
