<script setup lang="ts">
import { ref, onMounted, computed, watch, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { apiFetch, getApiUrl, getToken, getUser } from '../api'

const route = useRoute()
const router = useRouter()
const user = ref<any>(null)

interface Dialogue {
  speaker: string
  content: string
  start_time?: number
  end_time?: number
}

interface Chapter {
  id: string
  number: number
  title: string
  status: string
  duration: number
  has_audio: boolean
  script?: Dialogue[]
}

interface BookData {
  id: string
  title: string
  status: string
  total_chapters: number
  completed_chapters: number
  ocr_progress: number
  script_progress: number
  audio_progress: number
  chapters: Chapter[]
}

interface Voice {
  id: string
  speaker_name: string
  voice_id: string
  voice_name: string
  gender: string
  description: string
}

const book = ref<BookData | null>(null)
const loading = ref(true)
const generating = ref(false)
const selectedChapters = ref<number[]>([])

// 音色相关
const voices = ref<Voice[]>([])
const showVoiceSelector = ref(false)
const voiceMapping = ref<Record<string, string>>({
  '小北': 'zh-CN-XiaoxiaoNeural',
  '阿南': 'zh-CN-YunxiNeural'
})

// 播放器状态
const currentChapter = ref<Chapter | null>(null)
const isPlaying = ref(false)
const currentTime = ref(0)
const duration = ref(0)
const audioElement = ref<HTMLAudioElement | null>(null)
const scriptData = ref<Dialogue[]>([])
const currentDialogueIndex = ref(-1)
const subtitleContainer = ref<HTMLElement | null>(null)

// 已选择的章节数
const selectedCount = computed(() => selectedChapters.value.length)

// 女声音色列表
const femaleVoices = computed(() => voices.value.filter(v => v.gender === 'female'))

// 男声音色列表
const maleVoices = computed(() => voices.value.filter(v => v.gender === 'male'))

// 获取音色列表
const fetchVoices = async () => {
  try {
    const res = await apiFetch('/api/voices')
    if (res.ok) {
      voices.value = await res.json()
    }
  } catch (e) {
    console.error('获取音色失败', e)
  }
}

// 获取书籍数据
const fetchBook = async () => {
  try {
    const res = await apiFetch(`/api/books/${route.params.id}`)
    book.value = await res.json()
  } catch (e) {
    alert('获取书籍失败')
    router.push('/')
  } finally {
    loading.value = false
  }
}

// 获取文稿
const fetchScript = async (chapterNum: number) => {
  try {
    const res = await apiFetch(`/api/books/${route.params.id}/chapters/${chapterNum}/script`)
    const data = await res.json()
    scriptData.value = data.dialogues || []
    
    // 根据时长分配时间
    if (scriptData.value.length > 0 && duration.value > 0) {
      const avgDuration = duration.value / scriptData.value.length
      scriptData.value.forEach((d, i) => {
        d.start_time = i * avgDuration
        d.end_time = (i + 1) * avgDuration
      })
    }
  } catch (e) {
    scriptData.value = []
  }
}

// 全选/取消
const selectAll = () => {
  if (book.value) {
    selectedChapters.value = book.value.chapters.map(c => c.number)
  }
}

const selectNone = () => {
  selectedChapters.value = []
}

// 生成播客
const generate = async () => {
  if (!selectedCount.value) return
  
  // 显示音色选择
  showVoiceSelector.value = true
}

// 确认生成
const confirmGenerate = async () => {
  if (!selectedCount.value) return
  
  showVoiceSelector.value = false
  generating.value = true
  
  try {
    const token = getToken()
    await apiFetch(`/api/books/${route.params.id}/generate`, {
      method: 'POST',
      headers: token ? { 'Authorization': `Bearer ${token}` } : {},
      body: JSON.stringify({
        chapters: selectedChapters.value,
        voice_mapping: voiceMapping.value
      })
    })
    
    // 开始轮询
    const timer = setInterval(async () => {
      await fetchBook()
      if (book.value?.status === 'completed' || book.value?.status === 'partial') {
        clearInterval(timer)
        generating.value = false
      }
    }, 3000)
    
  } catch (e: any) {
    alert('生成失败: ' + e.message)
    generating.value = false
  }
}

// 播放章节
const playChapter = async (chapter: Chapter) => {
  if (!chapter.has_audio) return
  
  // 停止当前播放
  if (audioElement.value) {
    audioElement.value.pause()
    audioElement.value = null
  }
  
  currentChapter.value = chapter
  isPlaying.value = false
  currentTime.value = 0
  
  // 加载音频
  const audio = new Audio(getApiUrl(`/api/books/${route.params.id}/chapters/${chapter.number}/audio`))
  audioElement.value = audio
  
  audio.onloadedmetadata = async () => {
    duration.value = audio.duration
    await fetchScript(chapter.number)
  }
  
  audio.ontimeupdate = () => {
    currentTime.value = audio.currentTime
    updateCurrentDialogue()
  }
  
  audio.onended = () => {
    isPlaying.value = false
    currentDialogueIndex.value = -1
  }
}

// 更新当前对话
const updateCurrentDialogue = () => {
  if (!scriptData.value.length) return
  
  const time = currentTime.value
  let found = -1
  
  for (let i = 0; i < scriptData.value.length; i++) {
    const d = scriptData.value[i]
    if (time >= (d.start_time || 0) && time < (d.end_time || Infinity)) {
      found = i
      break
    }
  }
  
  if (found !== currentDialogueIndex.value) {
    currentDialogueIndex.value = found
    scrollToDialogue(found)
  }
}

// 滚动到当前对话
const scrollToDialogue = async (index: number) => {
  await nextTick()
  if (subtitleContainer.value) {
    const items = subtitleContainer.value.querySelectorAll('.dialogue-item')
    if (items[index]) {
      items[index].scrollIntoView({ behavior: 'smooth', block: 'center' })
    }
  }
}

// 播放/暂停
const togglePlay = () => {
  if (!audioElement.value) return
  
  if (isPlaying.value) {
    audioElement.value.pause()
  } else {
    audioElement.value.play()
  }
  isPlaying.value = !isPlaying.value
}

// 跳转
const seek = (e: Event) => {
  if (!audioElement.value) return
  const target = e.target as HTMLInputElement
  const time = parseFloat(target.value)
  audioElement.value.currentTime = time
  currentTime.value = time
}

// 点击对话跳转
const jumpToDialogue = (index: number) => {
  if (!audioElement.value || !scriptData.value[index]) return
  const time = scriptData.value[index].start_time || 0
  audioElement.value.currentTime = time
  currentTime.value = time
}

// 格式化时间
const formatTime = (seconds: number) => {
  const m = Math.floor(seconds / 60)
  const s = Math.floor(seconds % 60)
  return `${m}:${String(s).padStart(2, '0')}`
}

// 进度百分比
const progressPercent = computed(() => {
  if (duration.value === 0) return 0
  return (currentTime.value / duration.value) * 100
})

// 下载音频
const downloadAudio = (chapterNum: number) => {
  const url = getApiUrl(`/api/books/${route.params.id}/chapters/${chapterNum}/audio`)
  const a = document.createElement('a')
  a.href = url
  a.download = `chapter_${chapterNum}.mp3`
  a.click()
}

// 返回列表
const backToList = () => {
  if (audioElement.value) {
    audioElement.value.pause()
    audioElement.value = null
  }
  currentChapter.value = null
  isPlaying.value = false
  scriptData.value = []
}

onMounted(() => {
  user.value = getUser()
  fetchVoices()
  fetchBook()
  setInterval(fetchBook, 5000)
})
</script>

<template>
  <div class="container">
    <!-- 播放器视图 -->
    <template v-if="currentChapter">
      <div class="player-container">
        <!-- 顶部信息 -->
        <div class="player-header">
          <button class="back-btn" @click="backToList">← 返回</button>
          <div class="chapter-info">
            <h2>第{{ currentChapter.number }}章: {{ currentChapter.title }}</h2>
            <p>{{ book?.title }}</p>
          </div>
        </div>
        
        <!-- 字幕区域 -->
        <div class="subtitle-container" ref="subtitleContainer">
          <div class="subtitle-wrapper">
            <div 
              v-for="(d, i) in scriptData" 
              :key="i"
              :class="['dialogue-item', { active: i === currentDialogueIndex }]"
              @click="jumpToDialogue(i)"
            >
              <span class="speaker" :class="d.speaker === '小北' ? 'speaker-a' : 'speaker-b'">
                {{ d.speaker }}
              </span>
              <span class="content">{{ d.content }}</span>
            </div>
            
            <div v-if="!scriptData.length" class="no-script">
              加载文稿中...
            </div>
          </div>
        </div>
        
        <!-- 播放控制 -->
        <div class="player-controls">
          <!-- 进度条 -->
          <div class="progress-container">
            <span class="time">{{ formatTime(currentTime) }}</span>
            <input 
              type="range" 
              class="progress-slider"
              :value="currentTime"
              :max="duration"
              step="0.1"
              @input="seek"
            />
            <span class="time">{{ formatTime(duration) }}</span>
          </div>
          
          <!-- 控制按钮 -->
          <div class="control-buttons">
            <button class="control-btn" @click="togglePlay">
              <span class="icon">{{ isPlaying ? '⏸' : '▶' }}</span>
            </button>
          </div>
          
          <!-- 操作按钮 -->
          <div class="action-buttons">
            <button class="action-btn" @click="downloadAudio(currentChapter.number)">
              ⬇️ 下载音频
            </button>
          </div>
        </div>
      </div>
    </template>
    
    <!-- 列表视图 -->
    <template v-else>
      <!-- Header -->
      <div class="card header-card">
        <h1 class="page-title" @click="router.push('/')">← {{ book?.title || '加载中...' }}</h1>
        <div class="page-subtitle">{{ book?.completed_chapters || 0 }} / {{ book?.total_chapters || 0 }} 章完成</div>
      </div>

      <!-- 加载中 -->
      <div class="card loading-card" v-if="loading">
        <div class="loading-icon">⏳</div>
        <p>加载中...</p>
      </div>

      <!-- 章节选择 -->
      <div class="card" v-else-if="book?.status === 'ready'">
        <h2 class="card-title">📖 选择章节 (共 {{ book.total_chapters }} 章)</h2>
        
        <div class="select-actions">
          <button class="btn btn-secondary" @click="selectAll">全选</button>
          <button class="btn btn-secondary" @click="selectNone">全不选</button>
          <div class="select-info">已选 {{ selectedCount }} 章 · 需要 {{ selectedCount }} 次</div>
        </div>
        
        <div class="chapter-grid">
          <div
            v-for="ch in book.chapters"
            :key="ch.number"
            :class="['chapter-item', { selected: selectedChapters.includes(ch.number) }]"
            @click="selectedChapters.includes(ch.number) 
              ? selectedChapters = selectedChapters.filter(n => n !== ch.number)
              : selectedChapters.push(ch.number)"
          >
            第{{ ch.number }}章
          </div>
        </div>
        
        <button 
          class="btn btn-primary generate-btn"
          @click="generate" 
          :disabled="!selectedCount || generating"
        >
          {{ generating ? '⏳ 生成中...' : `🎙️ 生成选中的 ${selectedCount} 章` }}
        </button>
      </div>

      <!-- 处理中 -->
      <div class="card" v-else-if="book?.status === 'processing'">
        <h2 class="card-title">⚙️ 生成中...</h2>
        <div class="progress-bar">
          <div class="progress-bar-fill" :style="{ width: progressPercent + '%' }"></div>
        </div>
        <p class="progress-text">{{ book.completed_chapters }} / {{ book.total_chapters }} 章完成</p>
      </div>

      <!-- 已完成 -->
      <div class="card" v-else-if="book?.status === 'completed' || book?.status === 'partial'">
        <h2 class="card-title">🎧 播客列表</h2>
        
        <div 
          v-for="ch in book.chapters" 
          :key="ch.number" 
          :class="['chapter-card', { playable: ch.has_audio }]"
          @click="ch.has_audio && playChapter(ch)"
        >
          <div class="chapter-card-content">
            <div class="chapter-main">
              <div class="chapter-number">第{{ ch.number }}章</div>
              <div class="chapter-title">{{ ch.title }}</div>
              <div class="chapter-duration">{{ formatTime(ch.duration) }}</div>
            </div>
            
            <div class="chapter-actions">
              <span v-if="ch.has_audio" class="play-indicator">▶ 点击播放</span>
              <span v-else class="no-audio">未生成</span>
            </div>
          </div>
        </div>
      </div>
    </template>

    <!-- 音色选择弹窗 -->
    <div v-if="showVoiceSelector" class="modal-overlay" @click.self="showVoiceSelector = false">
      <div class="modal-content voice-modal">
        <div class="modal-header">
          <h2>🎭 选择音色</h2>
          <button class="close-btn" @click="showVoiceSelector = false">×</button>
        </div>
        
        <div class="voice-selector-body">
          <p class="voice-hint">为播客中的角色选择合适的音色</p>
          
          <!-- 小北（女声） -->
          <div class="voice-group">
            <h3>👩 小北（女主持）</h3>
            <div class="voice-options">
              <div 
                v-for="v in femaleVoices" 
                :key="v.id"
                :class="['voice-option', { selected: voiceMapping['小北'] === v.voice_id }]"
                @click="voiceMapping['小北'] = v.voice_id"
              >
                <div class="voice-name">{{ v.speaker_name }}</div>
                <div class="voice-desc">{{ v.description }}</div>
              </div>
            </div>
          </div>
          
          <!-- 阿南（男声） -->
          <div class="voice-group">
            <h3>👨 阿南（男主持）</h3>
            <div class="voice-options">
              <div 
                v-for="v in maleVoices" 
                :key="v.id"
                :class="['voice-option', { selected: voiceMapping['阿南'] === v.voice_id }]"
                @click="voiceMapping['阿南'] = v.voice_id"
              >
                <div class="voice-name">{{ v.speaker_name }}</div>
                <div class="voice-desc">{{ v.description }}</div>
              </div>
            </div>
          </div>
          
          <div class="voice-actions">
            <button class="btn btn-secondary" @click="showVoiceSelector = false">取消</button>
            <button class="btn btn-primary" @click="confirmGenerate">
              🎙️ 开始生成 {{ selectedCount }} 章
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* 页面头部 */
.header-card {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.page-title {
  font-size: 20px;
  color: #4caf50;
  cursor: pointer;
  margin: 0;
}

.page-subtitle {
  font-size: 13px;
  color: #81c784;
}

.loading-card {
  text-align: center;
  padding: 40px;
}

.loading-icon {
  font-size: 32px;
}

/* 卡片标题 */
.card-title {
  margin-bottom: 16px;
  color: #4caf50;
}

/* 选择操作 */
.select-actions {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
  align-items: center;
}

.select-info {
  margin-left: auto;
  padding: 8px 0;
  color: #81c784;
  font-size: 13px;
}

/* 章节网格 */
.chapter-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(80px, 1fr));
  gap: 8px;
}

.chapter-item {
  padding: 12px 8px;
  background: rgba(0, 30, 20, 0.5);
  border: 1px solid rgba(76, 175, 80, 0.2);
  border-radius: 8px;
  cursor: pointer;
  text-align: center;
  font-size: 13px;
  transition: all 0.2s;
}

.chapter-item:hover {
  border-color: #4caf50;
}

.chapter-item.selected {
  border-color: #4caf50;
  background: rgba(76, 175, 80, 0.15);
}

.generate-btn {
  width: 100%;
  margin-top: 20px;
}

/* 进度条 */
.progress-text {
  text-align: center;
  margin-top: 12px;
  color: #81c784;
}

/* 章节卡片 */
.chapter-card {
  background: rgba(0, 30, 20, 0.4);
  border: 1px solid rgba(76, 175, 80, 0.2);
  border-radius: 12px;
  margin-bottom: 12px;
  transition: all 0.3s;
}

.chapter-card.playable {
  cursor: pointer;
}

.chapter-card.playable:hover {
  border-color: #4caf50;
  background: rgba(76, 175, 80, 0.1);
  transform: translateX(4px);
}

.chapter-card-content {
  padding: 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.chapter-main {
  flex: 1;
}

.chapter-number {
  font-size: 12px;
  color: #81c784;
  margin-bottom: 4px;
}

.chapter-title {
  font-weight: 600;
  color: #e8f5e9;
  margin-bottom: 4px;
}

.chapter-duration {
  font-size: 12px;
  color: #666;
}

.play-indicator {
  font-size: 13px;
  color: #4caf50;
}

.no-audio {
  font-size: 12px;
  color: #666;
}

/* ========== 播放器样式 ========== */
.player-container {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 40px);
}

.player-header {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px 20px;
  background: rgba(0, 40, 25, 0.8);
  border-radius: 12px;
  margin-bottom: 12px;
}

.back-btn {
  background: rgba(76, 175, 80, 0.2);
  border: 1px solid rgba(76, 175, 80, 0.3);
  color: #81c784;
  padding: 8px 16px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
}

.back-btn:hover {
  background: rgba(76, 175, 80, 0.3);
}

.chapter-info h2 {
  font-size: 18px;
  color: #e8f5e9;
  margin: 0;
}

.chapter-info p {
  font-size: 13px;
  color: #81c784;
  margin: 4px 0 0 0;
}

/* 字幕区域 */
.subtitle-container {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  background: rgba(0, 30, 20, 0.6);
  border-radius: 12px;
  margin-bottom: 12px;
  scroll-behavior: smooth;
}

.subtitle-wrapper {
  max-width: 600px;
  margin: 0 auto;
  padding: 40px 0;
}

.dialogue-item {
  padding: 16px;
  margin-bottom: 12px;
  border-radius: 12px;
  background: rgba(0, 40, 25, 0.4);
  border: 1px solid transparent;
  cursor: pointer;
  transition: all 0.3s;
}

.dialogue-item:hover {
  background: rgba(76, 175, 80, 0.1);
}

.dialogue-item.active {
  background: rgba(76, 175, 80, 0.2);
  border-color: #4caf50;
  transform: scale(1.02);
}

.speaker {
  display: inline-block;
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 600;
  margin-bottom: 8px;
}

.speaker-a {
  background: rgba(76, 175, 80, 0.3);
  color: #a5d6a7;
}

.speaker-b {
  background: rgba(33, 150, 243, 0.3);
  color: #90caf9;
}

.content {
  display: block;
  font-size: 15px;
  line-height: 1.6;
  color: #e8f5e9;
}

.no-script {
  text-align: center;
  color: #666;
  padding: 40px;
}

/* 播放控制 */
.player-controls {
  background: rgba(0, 40, 25, 0.8);
  border-radius: 12px;
  padding: 20px;
}

.progress-container {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.time {
  font-size: 13px;
  color: #81c784;
  min-width: 40px;
}

.progress-slider {
  flex: 1;
  height: 4px;
  -webkit-appearance: none;
  background: rgba(76, 175, 80, 0.2);
  border-radius: 2px;
  cursor: pointer;
}

.progress-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 16px;
  height: 16px;
  background: #4caf50;
  border-radius: 50%;
  cursor: pointer;
}

.control-buttons {
  display: flex;
  justify-content: center;
  margin-bottom: 16px;
}

.control-btn {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  background: linear-gradient(135deg, #4caf50, #2e7d32);
  border: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: transform 0.2s;
}

.control-btn:hover {
  transform: scale(1.1);
}

.control-btn .icon {
  font-size: 24px;
  color: white;
}

.action-buttons {
  display: flex;
  justify-content: center;
}

.action-btn {
  background: rgba(76, 175, 80, 0.2);
  border: 1px solid rgba(76, 175, 80, 0.3);
  color: #81c784;
  padding: 10px 20px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
}

.action-btn:hover {
  background: rgba(76, 175, 80, 0.3);
}

/* 音色选择弹窗 */
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
}

.modal-content {
  background: linear-gradient(135deg, #1a3a2a 0%, #0f2419 100%);
  border: 1px solid rgba(76, 175, 80, 0.3);
  border-radius: 16px;
  width: 100%;
  max-width: 600px;
  max-height: 80vh;
  overflow-y: auto;
  margin: 20px;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px;
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

.voice-selector-body {
  padding: 20px;
}

.voice-hint {
  color: #81c784;
  font-size: 14px;
  margin-bottom: 24px;
}

.voice-group {
  margin-bottom: 24px;
}

.voice-group h3 {
  color: #e8f5e9;
  font-size: 16px;
  margin: 0 0 12px 0;
}

.voice-options {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px;
}

.voice-option {
  background: rgba(0, 30, 20, 0.6);
  border: 1px solid rgba(76, 175, 80, 0.2);
  border-radius: 8px;
  padding: 12px;
  cursor: pointer;
  transition: all 0.3s;
}

.voice-option:hover {
  border-color: rgba(76, 175, 80, 0.5);
  background: rgba(0, 40, 25, 0.6);
}

.voice-option.selected {
  border-color: #4caf50;
  background: rgba(76, 175, 80, 0.15);
}

.voice-name {
  color: #e8f5e9;
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 4px;
}

.voice-desc {
  color: #81c784;
  font-size: 12px;
}

.voice-actions {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
  margin-top: 24px;
  padding-top: 20px;
  border-top: 1px solid rgba(76, 175, 80, 0.2);
}

@media (max-width: 500px) {
  .voice-options {
    grid-template-columns: 1fr;
  }
}
</style>