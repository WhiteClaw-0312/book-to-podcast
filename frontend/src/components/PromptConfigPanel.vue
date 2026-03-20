<script setup lang="ts">
import { ref, reactive, watch, computed, onMounted } from 'vue'
import { apiFetch } from '../api'

// Props
const props = defineProps<{
  visible: boolean
  bookId?: string
}>()

// Emits
const emit = defineEmits<{
  (e: 'apply', config: any): void
  (e: 'close'): void
}>()

// 配置数据
const config = reactive({
  style: 'casual',
  speaker_count: 2,
  speakers: [
    { name: '小北', gender: 'female' },
    { name: '阿南', gender: 'male' }
  ],
  dialogue_count: 65,
  interaction_level: 'balanced',
  content_depth: 'moderate',
  emotion_style: 'natural',
  pace: 'moderate',
  enable_intro: true,
  enable_summary: true,
  keep_quotes: false,
  highlight_quotes: false,
  enable_qa: false
})

// 选项数据（从后端加载）
const options = ref<any>({
  styles: [],
  interaction_levels: [],
  content_depths: [],
  emotion_styles: [],
  paces: [],
  lengths: [],
  default_speakers: {}
})

const showAdvanced = ref(false)
const loading = ref(false)
const saving = ref(false)

// 加载选项
const loadOptions = async () => {
  try {
    const res = await apiFetch('/api/prompt-configs/defaults')
    if (res.ok) {
      options.value = await res.json()
    }
  } catch (e) {
    console.error('加载选项失败', e)
  }
}

// 设置讲述人数量
const setSpeakerCount = (count: number) => {
  config.speaker_count = count
  
  const defaults = options.value.default_speakers || {}
  const defaultConfig = defaults[count] || []
  
  // 调整 speakers 数组
  while (config.speakers.length < count) {
    const idx = config.speakers.length
    if (defaultConfig[idx]) {
      config.speakers.push({ ...defaultConfig[idx] })
    } else {
      config.speakers.push({
        name: `讲述人${idx + 1}`,
        gender: 'neutral'
      })
    }
  }
  
  while (config.speakers.length > count) {
    config.speakers.pop()
  }
}

// 恢复默认
const resetToDefault = () => {
  config.style = 'casual'
  config.speaker_count = 2
  config.speakers = [
    { name: '小北', gender: 'female' },
    { name: '阿南', gender: 'male' }
  ]
  config.dialogue_count = 65
  config.interaction_level = 'balanced'
  config.content_depth = 'moderate'
  config.emotion_style = 'natural'
  config.pace = 'moderate'
  config.enable_intro = true
  config.enable_summary = true
  config.keep_quotes = false
  config.highlight_quotes = false
  config.enable_qa = false
  showAdvanced.value = false
}

// 应用配置
const applyConfig = () => {
  emit('apply', {
    ...config,
    speakers: config.speakers.map(s => ({ ...s }))
  })
}

// 关闭
const close = () => {
  emit('close')
}

// 获取选项标签
const getStyleLabel = (value: string) => {
  const style = options.value.styles?.find((s: any) => s.value === value)
  return style?.label || value
}

const getLengthLabel = (value: number) => {
  const length = options.value.lengths?.find((l: any) => l.value === value)
  return length?.label || `${value}句`
}

onMounted(() => {
  loadOptions()
})
</script>

<template>
  <Teleport to="body">
    <div v-if="visible" class="modal-overlay" @click.self="close">
      <div class="modal-content config-modal">
        <!-- 头部 -->
        <div class="modal-header">
          <h2>🎙️ 播客配置</h2>
          <button class="close-btn" @click="close">×</button>
        </div>
        
        <!-- 内容 -->
        <div class="modal-body">
          <p class="hint">配置您的播客风格，让生成的内容更符合您的需求</p>
          
          <!-- 1. 播客风格 -->
          <div class="config-section">
            <h3>🎭 播客风格</h3>
            <div class="style-grid">
              <div 
                v-for="style in options.styles" 
                :key="style.value"
                :class="['style-card', { active: config.style === style.value }]"
                @click="config.style = style.value"
              >
                <span class="style-label">{{ style.label }}</span>
                <span class="style-desc">{{ style.desc }}</span>
              </div>
            </div>
          </div>
          
          <!-- 2. 讲述人配置 -->
          <div class="config-section">
            <h3>👥 讲述人配置</h3>
            
            <div class="speaker-count-row">
              <label>讲述人数：</label>
              <div class="count-btns">
                <button 
                  v-for="n in 4" 
                  :key="n"
                  :class="['count-btn', { active: config.speaker_count === n }]"
                  @click="setSpeakerCount(n)"
                >{{ n }}人</button>
              </div>
            </div>
            
            <div class="speaker-list">
              <div 
                v-for="(speaker, index) in config.speakers" 
                :key="index" 
                class="speaker-item"
              >
                <span class="speaker-index">{{ index + 1 }}</span>
                <input 
                  type="text" 
                  v-model="speaker.name" 
                  placeholder="输入名字"
                  class="speaker-name-input"
                />
                <select v-model="speaker.gender" class="gender-select">
                  <option value="female">👩 女声</option>
                  <option value="male">👨 男声</option>
                  <option value="neutral">🧑 中性</option>
                </select>
              </div>
            </div>
          </div>
          
          <!-- 3. 文稿长度 -->
          <div class="config-section">
            <h3>⏱️ 文稿长度</h3>
            <div class="length-options">
              <div 
                v-for="length in options.lengths" 
                :key="length.value"
                :class="['length-card', { active: config.dialogue_count === length.value }]"
                @click="config.dialogue_count = length.value"
              >
                <span class="length-label">{{ length.label }}</span>
                <span class="length-desc">{{ length.desc }}</span>
              </div>
            </div>
          </div>
          
          <!-- 4. 高级选项（折叠） -->
          <div class="config-section collapsible">
            <h3 class="collapsible-header" @click="showAdvanced = !showAdvanced">
              ⚙️ 高级选项
              <span class="expand-icon">{{ showAdvanced ? '▼' : '▶' }}</span>
            </h3>
            
            <div v-if="showAdvanced" class="advanced-content">
              <!-- 互动程度 -->
              <div class="option-row">
                <label>互动程度</label>
                <div class="option-btns">
                  <button 
                    v-for="opt in options.interaction_levels" 
                    :key="opt.value"
                    :class="{ active: config.interaction_level === opt.value }"
                    @click="config.interaction_level = opt.value"
                  >{{ opt.label }}</button>
                </div>
              </div>
              
              <!-- 内容深度 -->
              <div class="option-row">
                <label>内容深度</label>
                <div class="option-btns">
                  <button 
                    v-for="opt in options.content_depths" 
                    :key="opt.value"
                    :class="{ active: config.content_depth === opt.value }"
                    @click="config.content_depth = opt.value"
                  >{{ opt.label }}</button>
                </div>
              </div>
              
              <!-- 情感表达 -->
              <div class="option-row">
                <label>情感表达</label>
                <div class="option-btns">
                  <button 
                    v-for="opt in options.emotion_styles" 
                    :key="opt.value"
                    :class="{ active: config.emotion_style === opt.value }"
                    @click="config.emotion_style = opt.value"
                  >{{ opt.label }}</button>
                </div>
              </div>
              
              <!-- 节奏控制 -->
              <div class="option-row">
                <label>节奏控制</label>
                <div class="option-btns">
                  <button 
                    v-for="opt in options.paces" 
                    :key="opt.value"
                    :class="{ active: config.pace === opt.value }"
                    @click="config.pace = opt.value"
                  >{{ opt.label }}</button>
                </div>
              </div>
              
              <!-- 特色功能 -->
              <div class="option-row features">
                <label>特色功能</label>
                <div class="feature-toggles">
                  <label class="toggle">
                    <input type="checkbox" v-model="config.enable_intro" />
                    <span class="toggle-label">开头引入</span>
                  </label>
                  <label class="toggle">
                    <input type="checkbox" v-model="config.enable_summary" />
                    <span class="toggle-label">章节总结</span>
                  </label>
                  <label class="toggle">
                    <input type="checkbox" v-model="config.keep_quotes" />
                    <span class="toggle-label">保留引用</span>
                  </label>
                  <label class="toggle">
                    <input type="checkbox" v-model="config.highlight_quotes" />
                    <span class="toggle-label">提炼金句</span>
                  </label>
                  <label class="toggle">
                    <input type="checkbox" v-model="config.enable_qa" />
                    <span class="toggle-label">Q&A环节</span>
                  </label>
                </div>
              </div>
            </div>
          </div>
        </div>
        
        <!-- 底部 -->
        <div class="modal-footer">
          <button class="btn btn-secondary" @click="resetToDefault">恢复默认</button>
          <button class="btn btn-primary" @click="applyConfig">
            ✅ 应用配置
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
/* 遮罩 */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 20px;
}

/* 弹窗 */
.config-modal {
  background: linear-gradient(135deg, #1a3a2a 0%, #0f2419 100%);
  border: 1px solid rgba(76, 175, 80, 0.3);
  border-radius: 20px;
  width: 100%;
  max-width: 640px;
  max-height: 90vh;
  overflow-y: auto;
}

/* 头部 */
.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px;
  border-bottom: 1px solid rgba(76, 175, 80, 0.2);
}

.modal-header h2 {
  color: #4caf50;
  margin: 0;
  font-size: 20px;
}

.close-btn {
  background: none;
  border: none;
  color: #81c784;
  font-size: 28px;
  cursor: pointer;
  line-height: 1;
}

.close-btn:hover {
  color: #4caf50;
}

/* 内容 */
.modal-body {
  padding: 20px 24px;
}

.hint {
  color: #81c784;
  font-size: 13px;
  margin: 0 0 20px 0;
}

/* 配置区块 */
.config-section {
  margin-bottom: 24px;
}

.config-section h3 {
  color: #e8f5e9;
  font-size: 15px;
  margin: 0 0 12px 0;
  font-weight: 600;
}

/* 风格网格 */
.style-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
}

.style-card {
  background: rgba(0, 30, 20, 0.6);
  border: 1px solid rgba(76, 175, 80, 0.2);
  border-radius: 10px;
  padding: 12px;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.style-card:hover {
  border-color: rgba(76, 175, 80, 0.5);
}

.style-card.active {
  border-color: #4caf50;
  background: rgba(76, 175, 80, 0.15);
}

.style-label {
  color: #e8f5e9;
  font-size: 14px;
  font-weight: 500;
}

.style-desc {
  color: #81c784;
  font-size: 11px;
}

/* 讲述人配置 */
.speaker-count-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.speaker-count-row label {
  color: #a5d6a7;
  font-size: 13px;
}

.count-btns {
  display: flex;
  gap: 8px;
}

.count-btn {
  width: 44px;
  height: 36px;
  background: rgba(0, 30, 20, 0.6);
  border: 1px solid rgba(76, 175, 80, 0.3);
  border-radius: 8px;
  color: #81c784;
  cursor: pointer;
  font-size: 13px;
  transition: all 0.2s;
}

.count-btn:hover {
  border-color: #4caf50;
}

.count-btn.active {
  background: rgba(76, 175, 80, 0.3);
  border-color: #4caf50;
  color: #e8f5e9;
}

.speaker-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.speaker-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 14px;
  background: rgba(0, 30, 20, 0.4);
  border-radius: 10px;
}

.speaker-index {
  width: 24px;
  height: 24px;
  background: rgba(76, 175, 80, 0.3);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #81c784;
  font-size: 12px;
  font-weight: 600;
}

.speaker-name-input {
  flex: 1;
  background: rgba(0, 30, 20, 0.6);
  border: 1px solid rgba(76, 175, 80, 0.3);
  border-radius: 8px;
  padding: 8px 12px;
  color: #e8f5e9;
  font-size: 14px;
}

.speaker-name-input:focus {
  outline: none;
  border-color: #4caf50;
}

.gender-select {
  background: rgba(0, 30, 20, 0.6);
  border: 1px solid rgba(76, 175, 80, 0.3);
  border-radius: 8px;
  padding: 8px 12px;
  color: #e8f5e9;
  font-size: 13px;
  cursor: pointer;
}

/* 长度选项 */
.length-options {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
}

.length-card {
  background: rgba(0, 30, 20, 0.6);
  border: 1px solid rgba(76, 175, 80, 0.2);
  border-radius: 10px;
  padding: 12px;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  flex-direction: column;
  gap: 4px;
  text-align: center;
}

.length-card:hover {
  border-color: rgba(76, 175, 80, 0.5);
}

.length-card.active {
  border-color: #4caf50;
  background: rgba(76, 175, 80, 0.15);
}

.length-label {
  color: #e8f5e9;
  font-size: 14px;
  font-weight: 500;
}

.length-desc {
  color: #81c784;
  font-size: 11px;
}

/* 高级选项 */
.collapsible-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  cursor: pointer;
  padding: 12px 16px;
  background: rgba(0, 30, 20, 0.4);
  border-radius: 10px;
  margin-bottom: 12px;
}

.expand-icon {
  color: #81c784;
  font-size: 12px;
}

.advanced-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.option-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.option-row label {
  color: #a5d6a7;
  font-size: 13px;
  min-width: 80px;
}

.option-btns {
  display: flex;
  gap: 8px;
  flex: 1;
}

.option-btns button {
  flex: 1;
  padding: 8px 12px;
  background: rgba(0, 30, 20, 0.6);
  border: 1px solid rgba(76, 175, 80, 0.3);
  border-radius: 8px;
  color: #81c784;
  cursor: pointer;
  font-size: 12px;
  transition: all 0.2s;
}

.option-btns button:hover {
  border-color: #4caf50;
}

.option-btns button.active {
  background: rgba(76, 175, 80, 0.3);
  border-color: #4caf50;
  color: #e8f5e9;
}

/* 特色功能 */
.feature-toggles {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  flex: 1;
}

.toggle {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
}

.toggle input {
  width: 16px;
  height: 16px;
  cursor: pointer;
}

.toggle-label {
  color: #e8f5e9;
  font-size: 13px;
}

/* 底部 */
.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 16px 24px;
  border-top: 1px solid rgba(76, 175, 80, 0.2);
}

/* 按钮 */
.btn {
  padding: 10px 20px;
  border-radius: 10px;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
  border: none;
}

.btn-primary {
  background: linear-gradient(135deg, #4caf50, #2e7d32);
  color: white;
}

.btn-primary:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(76, 175, 80, 0.3);
}

.btn-secondary {
  background: rgba(76, 175, 80, 0.15);
  border: 1px solid rgba(76, 175, 80, 0.3);
  color: #81c784;
}

.btn-secondary:hover {
  background: rgba(76, 175, 80, 0.25);
}

/* 响应式 */
@media (max-width: 600px) {
  .style-grid,
  .length-options {
    grid-template-columns: repeat(2, 1fr);
  }
  
  .option-row {
    flex-direction: column;
    align-items: flex-start;
  }
  
  .option-btns {
    width: 100%;
  }
  
  .feature-toggles {
    flex-direction: column;
  }
}
</style>