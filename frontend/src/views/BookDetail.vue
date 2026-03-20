<script setup lang="ts">
import { ref, onMounted, computed, watch, nextTick, onUnmounted } from 'vue'
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

// 章节预览编辑
const showChapterModal = ref(false)
const currentChapter = ref<Chapter | null>(null)
const editChapterTitle = ref('')
const editChapterContent = ref('')
const savingChapter = ref(false)

// 音色相关
const voices = ref<Voice[]>([])
const showVoiceSelector = ref(false)
const voiceMapping = ref<Record<string, string>>({
  '小北': 'zh-CN-XiaoxiaoNeural',
  '阿南': 'zh-CN-YunxiNeural'
})

// 播放器状态
const playingChapter = ref<Chapter | null>(null)
const isPlaying = ref(false)
const currentTime = ref(0)
const playDuration = ref(0)
const audioElement = ref<HTMLAudioElement | null>(null)
const scriptData = ref<Dialogue[]>([])
const currentDialogueIndex = ref(-1)
const subtitleContainer = ref<HTMLElement | null>(null)
const userIsDragging = ref(false)

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

// 预览音色
const previewingVoice = ref<string | null>(null)
const previewAudio = ref<HTMLAudioElement | null>(null)

const previewVoice = async (voiceId: string) => {
  // 停止之前的预览
  if (previewAudio.value) {
    previewAudio.value.pause()
    previewAudio.value = null
  }
  
  previewingVoice.value = voiceId
  
  try {
    const audioUrl = getApiUrl(`/api/voices/edge-id/${voiceId}/preview`)
    const audio = new Audio(audioUrl)
    previewAudio.value = audio
    
    audio.onended = () => {
      previewingVoice.value = null
    }
    
    audio.onerror = () => {
      previewingVoice.value = null
      alert('预览失败，请稍后重试')
    }
    
    await audio.play()
  } catch (e) {
    previewingVoice.value = null
    console.error('预览失败', e)
  }
}

const stopPreview = () => {
  if (previewAudio.value) {
    previewAudio.value.pause()
    previewAudio.value = null
  }
  previewingVoice.value = null
}

// 打开章节预览
const openChapterPreview = async (chapter: Chapter) => {
  currentChapter.value = chapter
  editChapterTitle.value = chapter.title
  editChapterContent.value = chapter.content || ''
  showChapterModal.value = true
}

// 关闭章节预览
const closeChapterModal = () => {
  showChapterModal.value = false
  currentChapter.value = null
}

// 保存章节内容
const saveChapterContent = async () => {
  if (!currentChapter.value) return
  
  savingChapter.value = true
  try {
    const res = await apiFetch(`/api/books/${route.params.id}/chapters/${currentChapter.value.number}/content`, {
      method: 'PUT',
      body: JSON.stringify({
        title: editChapterTitle.value,
        content: editChapterContent.value
      })
    })
    
    if (res.ok) {
      // 更新本地数据
      if (book.value) {
        const ch = book.value.chapters.find(c => c.number === currentChapter.value!.number)
        if (ch) {
          ch.title = editChapterTitle.value
          ch.content = editChapterContent.value
        }
      }
      showChapterModal.value = false
      alert('保存成功')
    } else {
      const err = await res.json()
      throw new Error(err.detail || '保存失败')
    }
  } catch (e: any) {
    alert('保存失败: ' + e.message)
  } finally {
    savingChapter.value = false
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

// 全选/取消
const selectAll = () => {
  if (book.value) {
    selectedChapters.value = book.value.chapters.map(c => c.number)
  }
}

const selectNone = () => {
  selectedChapters.value = []
}

// 切换章节选中状态
const toggleChapterSelection = (num: number) => {
  if (selectedChapters.value.includes(num)) {
    selectedChapters.value = selectedChapters.value.filter(n => n !== num)
  } else {
    selectedChapters.value.push(num)
  }
}

// 队列进度
const queueProgress = ref<any>(null)
const tasks = ref<any[]>([])
const pollingTimer = ref<any>(null)

// 获取进度
const fetchProgress = async () => {
  try {
    const res = await apiFetch(`/api/books/${route.params.id}/progress`)
    const data = await res.json()
    queueProgress.value = data.queue
    tasks.value = data.tasks || []
    
    // 更新书籍状态
    await fetchBook()
    
    // 如果完成，停止轮询
    if (data.queue?.status === 'completed' || data.book_status === 'script_ready' || data.book_status === 'completed') {
      if (pollingTimer.value) {
        clearInterval(pollingTimer.value)
        pollingTimer.value = null
      }
      generating.value = false
    }
  } catch (e) {
    console.error('获取进度失败', e)
  }
}

// 开始轮询进度
const startPolling = () => {
  if (pollingTimer.value) {
    clearInterval(pollingTimer.value)
  }
  pollingTimer.value = setInterval(fetchProgress, 2000)
}

// 生成文稿（第一步）
const generateScripts = async () => {
  if (!selectedCount.value) return
  
  generating.value = true
  
  try {
    const token = getToken()
    const res = await apiFetch(`/api/books/${route.params.id}/generate-script`, {
      method: 'POST',
      headers: token ? { 'Authorization': `Bearer ${token}` } : {},
      body: JSON.stringify({
        chapters: selectedChapters.value
      })
    })
    
    if (res.ok) {
      selectedChapters.value = []
      startPolling()
    } else {
      const err = await res.json()
      throw new Error(err.detail || '生成失败')
    }
    
  } catch (e: any) {
    alert('生成文稿失败: ' + e.message)
    generating.value = false
  }
}

// 编辑文稿
const editScript = (chapterNum: number) => {
  router.push(`/book/${route.params.id}/script?chapter=${chapterNum}`)
}

// 生成音频（第二步，需要扣费）
const generate = async () => {
  if (!selectedCount.value) return
  
  // 显示音色选择
  showVoiceSelector.value = true
}

// 生成单章音频
const generateSingleAudio = async (chapterNum: number) => {
  // 设置选中章节
  selectedChapters.value = [chapterNum]
  // 显示音色选择
  showVoiceSelector.value = true
}

// 确认生成音频
const confirmGenerate = async () => {
  if (!selectedCount.value) return
  
  showVoiceSelector.value = false
  generating.value = true
  
  try {
    const token = getToken()
    const res = await apiFetch(`/api/books/${route.params.id}/generate-audio`, {
      method: 'POST',
      headers: token ? { 'Authorization': `Bearer ${token}` } : {},
      body: JSON.stringify({
        chapters: selectedChapters.value,
        voice_mapping: voiceMapping.value
      })
    })
    
    if (res.ok) {
      selectedChapters.value = []
      startPolling()
    } else {
      const err = await res.json()
      throw new Error(err.detail || '生成失败')
    }
    
  } catch (e: any) {
    alert('生成音频失败: ' + e.message)
    generating.value = false
  }
}

// ========== 播放章节 ==========
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
  currentDialogueIndex.value = -1
  userIsDragging.value = false
  
  // 创建音频
  const audio = new Audio(getApiUrl(`/api/books/${route.params.id}/chapters/${chapter.number}/audio`))
  audioElement.value = audio
  
  // 音频加载完成
  audio.addEventListener('loadedmetadata', async () => {
    playDuration.value = audio.duration
    
    // 获取文稿
    await fetchScript(chapter.number)
    
    // 分配时间给每个对话
    if (scriptData.value.length > 0 && playDuration.value > 0) {
      const avgDuration = playDuration.value / scriptData.value.length
      scriptData.value.forEach((d, i) => {
        d.start_time = i * avgDuration
        d.end_time = (i + 1) * avgDuration
      })
    }
  })
  
  // 时间更新 - 使用 requestAnimationFrame 更流畅
  let lastTime = 0
  const updateTime = () => {
    if (!audioElement.value) return
    
    // 只有时间真正变化时才更新
    if (Math.abs(audio.currentTime - lastTime) > 0.1) {
      lastTime = audio.currentTime
      currentTime.value = audio.currentTime
      updateCurrentDialogue()
    }
    
    if (isPlaying.value) {
      requestAnimationFrame(updateTime)
    }
  }
  
  // 播放时开始更新
  audio.addEventListener('play', () => {
    requestAnimationFrame(updateTime)
  })
  
  // 暂停时停止更新
  audio.addEventListener('pause', () => {
    currentTime.value = audio.currentTime
  })
  
  // 跳转完成事件 - 确保时间更新
  audio.addEventListener('seeked', () => {
    currentTime.value = audio.currentTime
    updateCurrentDialogue()
    userIsDragging.value = false
  })
  
  // 播放结束
  audio.addEventListener('ended', () => {
    isPlaying.value = false
    currentDialogueIndex.value = -1
  })
}

// ========== 获取文稿 ==========
const fetchScript = async (chapterNum: number) => {
  try {
    const res = await apiFetch(`/api/books/${route.params.id}/chapters/${chapterNum}/script`)
    const data = await res.json()
    scriptData.value = data.dialogues || []
  } catch (e) {
    scriptData.value = []
  }
}

// ========== 更新当前对话高亮 ==========
const updateCurrentDialogue = () => {
  if (!scriptData.value.length) return
  
  const time = currentTime.value
  for (let i = 0; i < scriptData.value.length; i++) {
    const d = scriptData.value[i]
    if (time >= (d.start_time || 0) && time < (d.end_time || Infinity)) {
      if (currentDialogueIndex.value !== i) {
        currentDialogueIndex.value = i
        scrollToDialogue(i)
      }
      break
    }
  }
}

// ========== 滚动到当前对话 ==========
const scrollToDialogue = (index: number) => {
  nextTick(() => {
    if (subtitleContainer.value) {
      const items = subtitleContainer.value.querySelectorAll('.dialogue-item')
      if (items[index]) {
        items[index].scrollIntoView({ behavior: 'smooth', block: 'center' })
      }
    }
  })
}

// ========== 播放/暂停 ==========
const togglePlay = () => {
  if (!audioElement.value) return
  
  if (isPlaying.value) {
    audioElement.value.pause()
    isPlaying.value = false
  } else {
    audioElement.value.play()
    isPlaying.value = true
  }
}

// ========== 进度条交互 ==========
// 用户开始拖拽
const onSliderDown = () => {
  userIsDragging.value = true
}

// 用户拖拽中 - 只更新 UI
const onSliderInput = (e: Event) => {
  const slider = e.target as HTMLInputElement
  currentTime.value = parseFloat(slider.value)
}

// 用户结束拖拽 - 执行跳转
const onSliderChange = (e: Event) => {
  const slider = e.target as HTMLInputElement
  const targetTime = parseFloat(slider.value)
  
  if (audioElement.value) {
    // 设置标志防止重复更新
    userIsDragging.value = true
    // 设置音频时间
    audioElement.value.currentTime = targetTime
    currentTime.value = targetTime
    // seeked 事件会重置 userIsDragging
  }
}

// ========== 点击字幕跳转 ==========
const jumpToDialogue = (index: number) => {
  if (!audioElement.value || !scriptData.value[index]) return
  
  const targetTime = scriptData.value[index].start_time || 0
  
  // 防止重复更新
  userIsDragging.value = true
  
  // 设置音频时间
  audioElement.value.currentTime = targetTime
  currentTime.value = targetTime
  currentDialogueIndex.value = index
  
  // 如果未播放，开始播放
  if (!isPlaying.value) {
    audioElement.value.play()
    isPlaying.value = true
  }
  
  // seeked 事件会重置 userIsDragging
}

// ========== 点击进度条跳转 ==========
const onProgressClick = (e: MouseEvent) => {
  if (!audioElement.value || !playDuration.value) return
  
  const target = e.currentTarget as HTMLElement
  const rect = target.getBoundingClientRect()
  const clickX = e.clientX - rect.left
  const percent = Math.max(0, Math.min(1, clickX / rect.width))
  const targetTime = percent * playDuration.value
  
  // 防止重复更新
  userIsDragging.value = true
  
  // 设置音频时间
  audioElement.value.currentTime = targetTime
  currentTime.value = targetTime
  updateCurrentDialogue()
  
  // seeked 事件会重置 userIsDragging
}

// 格式化时间
const formatTime = (seconds: number) => {
  if (isNaN(seconds) || seconds < 0) return '0:00'
  const m = Math.floor(seconds / 60)
  const s = Math.floor(seconds % 60)
  return `${m}:${String(s).padStart(2, '0')}`
}

// 进度百分比
const progressPercent = computed(() => {
  if (playDuration.value === 0) return 0
  return (currentTime.value / playDuration.value) * 100
})

// 下载音频
const downloadAudio = (chapterNum: number) => {
  const url = getApiUrl(`/api/books/${route.params.id}/chapters/${chapterNum}/audio`)
  const a = document.createElement('a')
  a.href = url
  a.download = `chapter_${chapterNum}.mp3`
  a.click()
}

// 下载文稿
const downloadScript = () => {
  if (!currentChapter.value || !scriptData.value.length) return
  
  // 生成文稿文本
  let text = `第${currentChapter.value.number}章：${currentChapter.value.title}\n\n`
  text += `《${book.value?.title || '未知书籍'}》\n\n`
  text += `${'='.repeat(40)}\n\n`
  
  scriptData.value.forEach(d => {
    text += `【${d.speaker}】\n${d.content}\n\n`
  })
  
  // 创建下载
  const blob = new Blob([text], { type: 'text/plain;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `chapter_${currentChapter.value.number}_文稿.txt`
  a.click()
  URL.revokeObjectURL(url)
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
  fetchBook().then(() => {
    // 如果正在处理，开始轮询
    if (book.value?.status === 'generating_script' || book.value?.status === 'generating_audio') {
      generating.value = true
      startPolling()
    }
  })
})

// 组件卸载时清理
import { onUnmounted } from 'vue'
onUnmounted(() => {
  if (pollingTimer.value) {
    clearInterval(pollingTimer.value)
  }
  // 停止预览音频
  if (previewAudio.value) {
    previewAudio.value.pause()
    previewAudio.value = null
  }
})
</script>

<template>
  <div class="container">
    <!-- 播放器视图 -->
    <template v-if="currentChapter">
      <div class="player-container animate-fade-up">
        <!-- 顶部信息 -->
        <div class="player-header">
          <button class="back-btn" @click="backToList">
            <span class="back-icon">←</span>
            <span>返回</span>
          </button>
          <div class="chapter-info">
            <div class="chapter-badge">第{{ currentChapter.number }}章</div>
            <h2 class="chapter-title-text">{{ currentChapter.title }}</h2>
            <p class="book-title-text">{{ book?.title }}</p>
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
              <div class="loading-spinner"></div>
              <span>加载文稿中...</span>
            </div>
          </div>
        </div>
        
        <!-- 播放控制 -->
        <div class="player-controls">
          <!-- 进度条 -->
          <div class="progress-section">
            <div class="progress-bar-visual" @click="onProgressClick">
              <div class="progress-fill-visual" :style="{ width: progressPercent + '%' }"></div>
              <div class="progress-thumb" :style="{ left: progressPercent + '%' }"></div>
            </div>
            <div class="progress-times">
              <span class="time">{{ formatTime(currentTime) }}</span>
              <span class="time">{{ formatTime(playDuration) }}</span>
            </div>
          </div>
          
          <!-- 控制按钮 -->
          <div class="control-buttons">
            <button class="control-btn" @click="togglePlay">
              <span class="icon">{{ isPlaying ? '⏸' : '▶' }}</span>
            </button>
          </div>
          
          <!-- 操作按钮 -->
          <div class="action-buttons">
            <button class="action-btn" @click="downloadScript">
              📝 下载文稿
            </button>
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

      <!-- 章节选择（OCR完成，尚未生成文稿） -->
      <div class="card ocr-complete-card" v-else-if="book?.status === 'ready'">
        <!-- 成功动画区域 -->
        <div class="success-animation">
          <div class="success-icon">
            <svg viewBox="0 0 24 24" class="checkmark">
              <path class="checkmark-path" fill="none" stroke="currentColor" stroke-width="2" d="M5 13l4 4L19 7"/>
            </svg>
          </div>
          <h2 class="success-title">OCR 解析完成</h2>
          <p class="success-subtitle">已识别 <span class="highlight">{{ book.total_chapters }}</span> 个章节</p>
        </div>
        
        <!-- 章节快速预览 -->
        <div class="chapters-preview">
          <div class="preview-header">
            <h3>📚 章节列表</h3>
            <span class="chapter-count">{{ book.total_chapters }} 章</span>
          </div>
          
          <p class="chapter-hint">💡 点击选择需要生成文稿的章节，选择完成后点击下方「生成文稿」按钮</p>
          
          <div class="chapter-chips">
            <div 
              v-for="ch in book.chapters.slice(0, 8)" 
              :key="ch.number"
              :class="['chapter-chip', { selected: selectedChapters.includes(ch.number) }]"
              @click="toggleChapterSelection(ch.number)"
            >
              <span class="chip-num">{{ ch.number }}</span>
              <span class="chip-title">{{ ch.title }}</span>
            </div>
            <div v-if="book.chapters.length > 8" class="chapter-chip more-chips">
              +{{ book.chapters.length - 8 }} 章
            </div>
          </div>
        </div>
        
        <!-- 操作区域 -->
        <div class="action-area">
          <!-- 已选择提示 -->
          <div class="selection-info" v-if="selectedCount > 0">
            <span class="selection-badge">已选 {{ selectedCount }} 章</span>
            <button class="btn btn-text-sm" @click="selectNone">清除选择</button>
          </div>
          
          <!-- 快速操作按钮 -->
          <div class="quick-actions">
            <button 
              class="btn btn-primary btn-lg pulse-btn"
              @click="generateScripts"
              :disabled="generating"
            >
              <span class="btn-icon">✨</span>
              <span class="btn-text">{{ generating ? '生成中...' : '生成文稿' }}</span>
            </button>
            
            <button 
              class="btn btn-secondary btn-lg"
              @click="router.push(`/book/${route.params.id}/chapters`)"
            >
              <span class="btn-icon">📝</span>
              <span class="btn-text">编辑章节</span>
            </button>
          </div>
          
          <!-- 进度显示 -->
          <div class="generating-progress" v-if="generating">
            <div class="progress-bar">
              <div class="progress-fill" :style="{ width: (queueProgress?.progress || 0) + '%' }"></div>
            </div>
            <p class="progress-text">正在生成文稿，请稍候...</p>
          </div>
        </div>
        
        <!-- 底部提示 -->
        <p class="tip-text">
          💡 生成文稿后，可以编辑文稿内容并生成播客音频
        </p>
      </div>

      <!-- 章节预览对话框 -->
      <div v-if="showChapterModal" class="modal-overlay" @click.self="closeChapterModal">
        <div class="modal-content chapter-modal">
          <div class="modal-header">
            <h2>第{{ currentChapter?.number }}章 · {{ currentChapter?.title }}</h2>
            <button class="close-btn" @click="closeChapterModal">×</button>
          </div>
          <div class="modal-body">
            <div class="form-group">
              <label>章节标题</label>
              <input type="text" class="input" v-model="editChapterTitle" placeholder="输入章节标题" />
            </div>
            <div class="form-group">
              <label>章节内容</label>
              <textarea 
                class="textarea chapter-textarea" 
                v-model="editChapterContent" 
                placeholder="章节内容"
              ></textarea>
            </div>
            <div class="chapter-meta-info">
              <span>{{ editChapterContent.length }} 字</span>
              <span v-if="currentChapter?.page_range">· {{ currentChapter.page_range }} 页</span>
            </div>
          </div>
          <div class="modal-footer">
            <button class="btn btn-secondary" @click="closeChapterModal">取消</button>
            <button class="btn btn-primary" @click="saveChapterContent" :disabled="savingChapter">
              {{ savingChapter ? '保存中...' : '💾 保存' }}
            </button>
          </div>
        </div>
      </div>

      <!-- 文稿就绪，等待编辑/生成音频 -->
      <div class="card status-card script-ready-card" v-else-if="book?.status === 'script_ready' || book?.status === 'partial'">
        <!-- 状态头部 -->
        <div class="status-header">
          <div class="status-icon animate-scale-in">
            <svg viewBox="0 0 24 24" class="checkmark">
              <path class="checkmark-path" fill="none" stroke="currentColor" stroke-width="2" d="M5 13l4 4L19 7"/>
            </svg>
          </div>
          <div class="status-info">
            <h2 class="status-title animate-fade-up">文稿已就绪</h2>
            <p class="status-subtitle animate-fade-up animate-delay-1">编辑文稿或生成音频</p>
          </div>
        </div>
        
        <!-- 章节列表 -->
        <div class="chapters-list animate-fade-up animate-delay-2">
          <div class="list-header">
            <h3>📚 章节文稿</h3>
            <span class="badge badge-success">{{ book.chapters.filter(c => c.has_script).length }} 章已生成</span>
          </div>
          
          <div class="chapter-items">
            <div 
              v-for="ch in book.chapters" 
              :key="ch.number" 
              :class="['chapter-item-row', { 'has-audio': ch.has_audio }]"
            >
              <div class="chapter-item-left">
                <div class="chapter-item-num">{{ ch.number }}</div>
                <div class="chapter-item-info">
                  <span class="chapter-item-title">{{ ch.title }}</span>
                  <span class="chapter-item-status" v-if="ch.has_audio">✅ 已生成音频</span>
                </div>
              </div>
              
              <div class="chapter-item-actions">
                <button 
                  v-if="ch.has_script"
                  class="btn btn-secondary btn-sm"
                  @click.stop="editScript(ch.number)"
                >✏️ 编辑</button>
                
                <button 
                  v-if="ch.has_audio"
                  class="btn btn-primary btn-sm"
                  @click.stop="playChapter(ch)"
                >🎧 播放</button>
                
                <button 
                  v-if="!ch.has_audio && ch.has_script"
                  class="btn btn-primary btn-sm"
                  @click.stop="generateSingleAudio(ch.number)"
                >🎙️ 生成音频</button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 正在生成文稿 -->
      <div class="card status-card generating-card" v-else-if="book?.status === 'generating_script'">
        <!-- 动画头部 -->
        <div class="generating-header">
          <div class="generating-icon">
            <div class="spinner"></div>
          </div>
          <div class="generating-info">
            <h2 class="status-title">正在生成文稿</h2>
            <p class="status-subtitle">AI 正在创作播客文稿...</p>
          </div>
        </div>
        
        <!-- 进度区域 -->
        <div class="progress-area">
          <div class="progress-header">
            <span class="progress-label">整体进度</span>
            <span class="progress-value">{{ queueProgress?.progress || 0 }}%</span>
          </div>
          <div class="progress-bar progress-bar-animated">
            <div class="progress-bar-fill" :style="{ width: (queueProgress?.progress || 0) + '%' }"></div>
          </div>
          <div class="progress-stats">
            <span>{{ queueProgress?.completed || 0 }} / {{ queueProgress?.total || 0 }} 章</span>
            <span v-if="queueProgress?.processing > 0" class="badge badge-warning">处理中 {{ queueProgress.processing }} 章</span>
          </div>
        </div>
        
        <!-- 任务列表 -->
        <div class="tasks-area" v-if="tasks.length > 0">
          <div v-for="task in tasks" :key="task.id" :class="['task-row', task.status]">
            <div class="task-info">
              <span class="task-chapter">第{{ task.chapter_number }}章</span>
              <span class="task-status-text">
                {{ task.status === 'pending' ? '等待中' : task.status === 'processing' ? '处理中' : task.status === 'completed' ? '完成' : '失败' }}
              </span>
            </div>
            <div v-if="task.status === 'processing'" class="task-progress-bar">
              <div class="task-progress-fill" :style="{ width: task.progress + '%' }"></div>
            </div>
          </div>
        </div>
        
        <div class="hint-box">
          💡 您可以切换到其他页面，稍后回来查看进度
        </div>
      </div>

      <!-- 正在生成音频 -->
      <div class="card status-card generating-card" v-else-if="book?.status === 'generating_audio'">
        <!-- 动画头部 -->
        <div class="generating-header">
          <div class="generating-icon audio-icon">
            <div class="audio-waves">
              <span></span><span></span><span></span><span></span>
            </div>
          </div>
          <div class="generating-info">
            <h2 class="status-title">正在生成音频</h2>
            <p class="status-subtitle">合成播客语音...</p>
          </div>
        </div>
        
        <!-- 进度区域 -->
        <div class="progress-area">
          <div class="progress-header">
            <span class="progress-label">整体进度</span>
            <span class="progress-value">{{ queueProgress?.progress || 0 }}%</span>
          </div>
          <div class="progress-bar progress-bar-animated">
            <div class="progress-bar-fill audio" :style="{ width: (queueProgress?.progress || 0) + '%' }"></div>
          </div>
          <div class="progress-stats">
            <span>{{ queueProgress?.completed || 0 }} / {{ queueProgress?.total || 0 }} 章</span>
            <span v-if="queueProgress?.processing > 0" class="badge badge-info">合成中 {{ queueProgress.processing }} 章</span>
          </div>
        </div>
        
        <!-- 任务列表 -->
        <div class="tasks-area" v-if="tasks.length > 0">
          <div v-for="task in tasks" :key="task.id" :class="['task-row', task.status]">
            <div class="task-info">
              <span class="task-chapter">第{{ task.chapter_number }}章</span>
              <span class="task-status-text">
                {{ task.status === 'pending' ? '等待中' : task.status === 'processing' ? '合成中' : task.status === 'completed' ? '完成' : '失败' }}
              </span>
            </div>
            <div v-if="task.status === 'processing'" class="task-progress-bar">
              <div class="task-progress-fill audio" :style="{ width: task.progress + '%' }"></div>
            </div>
          </div>
        </div>
        
        <div class="hint-box">
          💡 音频合成需要较长时间，您可以稍后回来查看
        </div>
      </div>

      <!-- 处理中（旧流程兼容） -->
      <div class="card status-card" v-else-if="book?.status === 'processing'">
        <div class="generating-header">
          <div class="generating-icon">
            <div class="spinner"></div>
          </div>
          <div class="generating-info">
            <h2 class="status-title">生成中</h2>
            <p class="status-subtitle">{{ book.completed_chapters }} / {{ book.total_chapters }} 章完成</p>
          </div>
        </div>
        <div class="progress-bar progress-bar-animated">
          <div class="progress-bar-fill" :style="{ width: progressPercent + '%' }"></div>
        </div>
      </div>

      <!-- 已完成 -->
      <div class="card" v-else-if="book?.status === 'completed'">
        <h2 class="card-title">🎧 播客已就绪</h2>
        <p class="card-hint">您可以查看文稿、编辑内容或播放音频</p>
        
        <div 
          v-for="ch in book.chapters" 
          :key="ch.number" 
          :class="['chapter-card', { playable: ch.has_audio }]"
        >
          <div class="chapter-card-content">
            <div class="chapter-main">
              <div class="chapter-number">第{{ ch.number }}章</div>
              <div class="chapter-title">{{ ch.title }}</div>
              <div class="chapter-duration" v-if="ch.has_audio">{{ formatTime(ch.duration) }}</div>
            </div>
            
            <div class="chapter-btns">
              <button 
                v-if="ch.has_script"
                class="btn btn-secondary btn-sm"
                @click="editScript(ch.number)"
              >📝 查看文稿</button>
              <button 
                v-if="ch.has_audio"
                class="btn btn-primary btn-sm"
                @click="playChapter(ch)"
              >🎧 播放音频</button>
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
                :class="['voice-option', { selected: voiceMapping['小北'] === v.voice_id, previewing: previewingVoice === v.voice_id }]"
                @click="voiceMapping['小北'] = v.voice_id"
              >
                <div class="voice-header">
                  <div class="voice-name">{{ v.speaker_name }}</div>
                  <button 
                    class="preview-btn"
                    @click.stop="previewingVoice === v.voice_id ? stopPreview() : previewVoice(v.voice_id)"
                    :title="previewingVoice === v.voice_id ? '停止预览' : '试听'"
                  >
                    {{ previewingVoice === v.voice_id ? '⏹️' : '▶️' }}
                  </button>
                </div>
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
                :class="['voice-option', { selected: voiceMapping['阿南'] === v.voice_id, previewing: previewingVoice === v.voice_id }]"
                @click="voiceMapping['阿南'] = v.voice_id"
              >
                <div class="voice-header">
                  <div class="voice-name">{{ v.speaker_name }}</div>
                  <button 
                    class="preview-btn"
                    @click.stop="previewingVoice === v.voice_id ? stopPreview() : previewVoice(v.voice_id)"
                    :title="previewingVoice === v.voice_id ? '停止预览' : '试听'"
                  >
                    {{ previewingVoice === v.voice_id ? '⏹️' : '▶️' }}
                  </button>
                </div>
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
  animation: fadeInUp 0.4s ease;
}

@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.player-header {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px;
  background: linear-gradient(135deg, rgba(0, 40, 25, 0.9), rgba(15, 36, 25, 0.8));
  border: 1px solid rgba(76, 175, 80, 0.2);
  border-radius: 16px;
  margin-bottom: 16px;
}

.back-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  background: rgba(76, 175, 80, 0.15);
  border: 1px solid rgba(76, 175, 80, 0.3);
  color: #81c784;
  padding: 10px 18px;
  border-radius: 10px;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.2s;
}

.back-btn:hover {
  background: rgba(76, 175, 80, 0.25);
  transform: translateX(-2px);
}

.back-icon {
  font-size: 16px;
}

.chapter-info {
  flex: 1;
}

.chapter-badge {
  display: inline-block;
  background: linear-gradient(135deg, rgba(76, 175, 80, 0.3), rgba(46, 125, 50, 0.2));
  color: #81c784;
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 600;
  margin-bottom: 8px;
}

.chapter-title-text {
  font-size: 20px;
  color: #e8f5e9;
  margin: 0 0 4px 0;
  font-weight: 600;
}

.book-title-text {
  font-size: 13px;
  color: #81c784;
  margin: 0;
}

/* 字幕区域 */
.subtitle-container {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  background: rgba(0, 30, 20, 0.5);
  border: 1px solid rgba(76, 175, 80, 0.15);
  border-radius: 16px;
  margin-bottom: 16px;
  scroll-behavior: smooth;
}

.subtitle-wrapper {
  max-width: 600px;
  margin: 0 auto;
  padding: 20px 0;
}

.dialogue-item {
  padding: 16px 20px;
  margin-bottom: 12px;
  border-radius: 14px;
  background: rgba(0, 40, 25, 0.4);
  border: 1px solid rgba(76, 175, 80, 0.1);
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.dialogue-item:hover {
  background: rgba(76, 175, 80, 0.12);
  border-color: rgba(76, 175, 80, 0.3);
  transform: translateX(4px);
}

.dialogue-item.active {
  background: linear-gradient(135deg, rgba(76, 175, 80, 0.2), rgba(46, 125, 50, 0.15));
  border-color: #4caf50;
  transform: scale(1.02);
  box-shadow: 0 4px 20px rgba(76, 175, 80, 0.15);
}

.speaker {
  display: inline-block;
  padding: 4px 14px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 600;
  margin-bottom: 10px;
}

.speaker-a {
  background: linear-gradient(135deg, rgba(76, 175, 80, 0.4), rgba(46, 125, 50, 0.3));
  color: #a5d6a7;
}

.speaker-b {
  background: linear-gradient(135deg, rgba(33, 150, 243, 0.4), rgba(25, 118, 210, 0.3));
  color: #90caf9;
}

.content {
  display: block;
  font-size: 15px;
  line-height: 1.7;
  color: #e8f5e9;
}

.no-script {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  text-align: center;
  color: #666;
  padding: 60px 20px;
}

/* 播放控制 */
.player-controls {
  background: linear-gradient(135deg, rgba(0, 40, 25, 0.9), rgba(15, 36, 25, 0.8));
  border: 1px solid rgba(76, 175, 80, 0.2);
  border-radius: 16px;
  padding: 24px;
}

/* 进度条 */
.progress-section {
  margin-bottom: 24px;
}

.progress-bar-visual {
  position: relative;
  height: 8px;
  background: rgba(76, 175, 80, 0.15);
  border-radius: 4px;
  cursor: pointer;
  overflow: visible;
  transition: height 0.2s;
}

.progress-bar-visual:hover {
  height: 12px;
}

.progress-fill-visual {
  position: absolute;
  top: 0;
  left: 0;
  height: 100%;
  background: linear-gradient(90deg, #4caf50, #81c784);
  border-radius: 4px;
  transition: width 0.1s;
}

.progress-thumb {
  position: absolute;
  top: 50%;
  width: 18px;
  height: 18px;
  background: #4caf50;
  border-radius: 50%;
  transform: translate(-50%, -50%);
  box-shadow: 0 2px 8px rgba(76, 175, 80, 0.4);
  transition: transform 0.2s;
}

.progress-bar-visual:hover .progress-thumb {
  transform: translate(-50%, -50%) scale(1.2);
}

.progress-times {
  display: flex;
  justify-content: space-between;
  margin-top: 10px;
}

.time {
  font-size: 13px;
  color: #81c784;
  font-weight: 500;
}

/* 控制按钮 */
.control-buttons {
  display: flex;
  justify-content: center;
  margin-bottom: 20px;
}

.control-btn {
  width: 72px;
  height: 72px;
  border-radius: 50%;
  background: linear-gradient(135deg, #4caf50, #2e7d32);
  border: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 4px 20px rgba(76, 175, 80, 0.3);
}

.control-btn:hover {
  transform: scale(1.1);
  box-shadow: 0 6px 30px rgba(76, 175, 80, 0.4);
}

.control-btn:active {
  transform: scale(0.95);
}

.control-btn .icon {
  font-size: 28px;
  color: white;
}

/* 操作按钮 */
.action-buttons {
  display: flex;
  justify-content: center;
  gap: 16px;
}

.action-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 20px;
  background: rgba(76, 175, 80, 0.15);
  border: 1px solid rgba(76, 175, 80, 0.3);
  border-radius: 10px;
  color: #81c784;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
}

.action-btn:hover {
  background: rgba(76, 175, 80, 0.25);
  border-color: rgba(76, 175, 80, 0.5);
  transform: translateY(-2px);
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

.voice-option.previewing {
  border-color: #2196f3;
  animation: pulse 1s infinite;
}

@keyframes pulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(33, 150, 243, 0.4); }
  50% { box-shadow: 0 0 0 8px rgba(33, 150, 243, 0); }
}

.voice-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}

.voice-name {
  color: #e8f5e9;
  font-size: 14px;
  font-weight: 600;
}

.preview-btn {
  background: rgba(33, 150, 243, 0.2);
  border: none;
  border-radius: 50%;
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  font-size: 12px;
  transition: all 0.3s;
}

.preview-btn:hover {
  background: rgba(33, 150, 243, 0.3);
  transform: scale(1.1);
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

/* 新增样式 */
.card-hint {
  color: #81c784;
  font-size: 13px;
  margin-bottom: 20px;
}

.chapter-list {
  margin-bottom: 20px;
}

.chapter-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  background: rgba(0, 30, 20, 0.4);
  border-radius: 8px;
  margin-bottom: 8px;
}

.chapter-btns {
  display: flex;
  gap: 8px;
  align-items: center;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #81c784;
  font-size: 13px;
  cursor: pointer;
}

.checkbox-label input {
  width: 16px;
  height: 16px;
  cursor: pointer;
}

.generate-audio-section {
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid rgba(76, 175, 80, 0.2);
  text-align: center;
}

.cost-info {
  color: #81c784;
  font-size: 13px;
  margin-bottom: 12px;
}

.chapter-card-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

/* 进度显示样式 */
.progress-section {
  margin: 24px 0;
}

.progress-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.progress-label {
  color: #a5d6a7;
  font-size: 14px;
}

.progress-percent {
  color: #4caf50;
  font-size: 20px;
  font-weight: 600;
}

.progress-bar-container {
  height: 12px;
  background: rgba(76, 175, 80, 0.1);
  border-radius: 6px;
  overflow: hidden;
}

.progress-bar-fill {
  height: 100%;
  background: linear-gradient(90deg, #4caf50, #81c784);
  border-radius: 6px;
  transition: width 0.5s ease;
}

.progress-bar-fill.audio {
  background: linear-gradient(90deg, #2196f3, #64b5f6);
}

.progress-stats {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 8px;
  color: #81c784;
  font-size: 12px;
}

.processing-badge {
  background: rgba(255, 152, 0, 0.2);
  color: #ffb74d;
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 11px;
}

.tasks-list {
  margin-top: 20px;
  max-height: 300px;
  overflow-y: auto;
}

.task-item {
  background: rgba(0, 30, 20, 0.4);
  border-radius: 8px;
  padding: 12px;
  margin-bottom: 8px;
}

.task-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.task-chapter {
  color: #e8f5e9;
  font-size: 13px;
  font-weight: 500;
}

.task-status {
  font-size: 12px;
}

.task-status.pending { color: #ffb74d; }
.task-status.processing { color: #64b5f6; }
.task-status.completed { color: #81c784; }
.task-status.failed { color: #ef5350; }

.task-progress {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 8px;
}

.mini-progress-bar {
  flex: 1;
  height: 4px;
  background: rgba(76, 175, 80, 0.2);
  border-radius: 2px;
  overflow: hidden;
}

.mini-progress-fill {
  height: 100%;
  background: #4caf50;
  transition: width 0.3s;
}

.mini-progress-fill.audio {
  background: #2196f3;
}

.mini-progress-text {
  color: #81c784;
  font-size: 11px;
  min-width: 30px;
}

.task-message {
  color: #a5d6a7;
  font-size: 11px;
  margin-top: 4px;
}

.progress-hint {
  text-align: center;
  color: #666;
  font-size: 12px;
  margin-top: 16px;
}

.card-header-row {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 16px;
}

.card-header-row .card-title {
  margin-bottom: 4px;
}

.card-header-row .card-hint {
  margin-bottom: 0;
}

/* 章节预览列表 */
.chapter-preview-list {
  margin-bottom: 20px;
}

.chapter-preview-item {
  padding: 16px;
  background: rgba(0, 30, 20, 0.4);
  border: 1px solid rgba(76, 175, 80, 0.2);
  border-radius: 10px;
  margin-bottom: 12px;
  cursor: pointer;
  transition: all 0.2s;
  max-height: 200px;
  overflow-y: auto;
}

.chapter-preview-item:hover {
  border-color: rgba(76, 175, 80, 0.5);
  background: rgba(0, 40, 25, 0.5);
}

.chapter-preview-item::-webkit-scrollbar {
  width: 6px;
}

.chapter-preview-item::-webkit-scrollbar-track {
  background: rgba(0, 0, 0, 0.2);
  border-radius: 3px;
}

.chapter-preview-item::-webkit-scrollbar-thumb {
  background: rgba(76, 175, 80, 0.4);
  border-radius: 3px;
}

.chapter-preview-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 10px;
  position: sticky;
  top: 0;
  background: rgba(0, 30, 20, 0.9);
  padding: 4px 0;
  margin: -16px -16px 10px -16px;
  padding: 12px 16px;
}

.chapter-preview-num {
  background: rgba(76, 175, 80, 0.2);
  color: #81c784;
  padding: 2px 10px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
}

.chapter-preview-title {
  color: #e8f5e9;
  font-size: 15px;
  font-weight: 500;
  flex: 1;
}

.chapter-preview-expand {
  font-size: 12px;
  color: #4caf50;
  opacity: 0;
  transition: opacity 0.2s;
}

.chapter-preview-item:hover .chapter-preview-expand {
  opacity: 1;
}

.chapter-preview-content {
  color: #a5d6a7;
  font-size: 13px;
  line-height: 1.7;
  margin-bottom: 10px;
  white-space: pre-wrap;
  word-break: break-word;
}

.chapter-preview-meta {
  font-size: 11px;
  color: #666;
  border-top: 1px solid rgba(76, 175, 80, 0.1);
  padding-top: 10px;
}

/* 操作区域 */
.action-area {
  padding-top: 16px;
  border-top: 1px solid rgba(76, 175, 80, 0.2);
}

/* 章节编辑对话框 */
.chapter-modal {
  max-width: 700px;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
}

.chapter-modal .modal-body {
  overflow-y: auto;
  flex: 1;
}

.chapter-textarea {
  min-height: 350px;
  max-height: 50vh;
  resize: vertical;
}

.chapter-meta-info {
  font-size: 12px;
  color: #666;
  margin-top: 8px;
}

.divider::before,
.divider::after {
  content: '';
  flex: 1;
  height: 1px;
  background: rgba(76, 175, 80, 0.2);
}

/* 章节网格优化 */
.chapter-item {
  display: flex;
  flex-direction: column;
  padding: 12px;
  background: rgba(0, 30, 20, 0.5);
  border: 1px solid rgba(76, 175, 80, 0.2);
  border-radius: 8px;
  cursor: pointer;
  text-align: center;
  transition: all 0.2s;
}

.chapter-item:hover {
  border-color: #4caf50;
}

.chapter-item.selected {
  border-color: #4caf50;
  background: rgba(76, 175, 80, 0.15);
}

.chapter-item-num {
  font-size: 12px;
  color: #81c784;
  margin-bottom: 4px;
}

.chapter-item-title {
  font-size: 13px;
  color: #e8f5e9;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* OCR 完成页面样式 */
.ocr-complete-card {
  padding: 40px;
  text-align: center;
}

.success-animation {
  margin-bottom: 40px;
}

.success-icon {
  width: 80px;
  height: 80px;
  margin: 0 auto 20px;
  background: linear-gradient(135deg, rgba(76, 175, 80, 0.2), rgba(46, 125, 50, 0.1));
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  animation: scaleIn 0.5s ease, pulse 2s ease-in-out infinite;
}

@keyframes scaleIn {
  0% { transform: scale(0); opacity: 0; }
  100% { transform: scale(1); opacity: 1; }
}

@keyframes pulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(76, 175, 80, 0.4); }
  50% { box-shadow: 0 0 0 15px rgba(76, 175, 80, 0); }
}

.checkmark {
  width: 40px;
  height: 40px;
  color: #4caf50;
}

.checkmark-path {
  stroke-dasharray: 30;
  stroke-dashoffset: 30;
  animation: draw 0.6s ease forwards 0.3s;
}

@keyframes draw {
  to { stroke-dashoffset: 0; }
}

.success-title {
  font-size: 28px;
  color: #e8f5e9;
  margin: 0 0 8px 0;
  animation: fadeInUp 0.5s ease 0.2s both;
}

.success-subtitle {
  font-size: 16px;
  color: #81c784;
  margin: 0;
  animation: fadeInUp 0.5s ease 0.3s both;
}

.success-subtitle .highlight {
  color: #4caf50;
  font-weight: 700;
  font-size: 20px;
}

@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* 章节预览 */
.chapters-preview {
  background: rgba(0, 30, 20, 0.4);
  border-radius: 16px;
  padding: 20px;
  margin-bottom: 30px;
  text-align: left;
  animation: fadeInUp 0.5s ease 0.4s both;
}

.preview-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.preview-header h3 {
  color: #81c784;
  font-size: 14px;
  margin: 0;
}

.chapter-count {
  background: rgba(76, 175, 80, 0.2);
  color: #81c784;
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 12px;
}

.chapter-hint {
  color: #a5d6a7;
  font-size: 13px;
  margin: 0 0 16px 0;
  padding: 10px 14px;
  background: rgba(76, 175, 80, 0.1);
  border-radius: 8px;
  border-left: 3px solid #4caf50;
}

.chapter-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.chapter-chip {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  background: rgba(0, 40, 25, 0.6);
  border: 1px solid rgba(76, 175, 80, 0.2);
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s;
}

.chapter-chip:hover {
  border-color: rgba(76, 175, 80, 0.5);
  transform: translateY(-2px);
}

.chapter-chip.selected {
  border-color: #4caf50;
  background: rgba(76, 175, 80, 0.2);
}

.chip-num {
  background: rgba(76, 175, 80, 0.3);
  color: #81c784;
  width: 24px;
  height: 24px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 600;
}

.chip-title {
  color: #e8f5e9;
  font-size: 13px;
  max-width: 150px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.more-chips {
  color: #81c784;
  font-size: 13px;
  cursor: default;
}

.more-chips:hover {
  transform: none;
}

/* 操作区域 */
.action-area {
  animation: fadeInUp 0.5s ease 0.5s both;
}

.selection-info {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
}

.selection-badge {
  background: linear-gradient(135deg, #4caf50, #2e7d32);
  color: white;
  padding: 6px 16px;
  border-radius: 20px;
  font-size: 14px;
  font-weight: 600;
}

.btn-text-sm {
  background: none;
  border: none;
  color: #81c784;
  font-size: 12px;
  cursor: pointer;
  padding: 4px 8px;
}

.btn-text-sm:hover {
  color: #4caf50;
}

.quick-actions {
  display: flex;
  gap: 16px;
  justify-content: center;
  margin-bottom: 20px;
}

.btn-lg {
  padding: 16px 32px;
  font-size: 16px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  gap: 10px;
}

.btn-icon {
  font-size: 20px;
}

.pulse-btn {
  position: relative;
  overflow: hidden;
}

.pulse-btn::after {
  content: '';
  position: absolute;
  top: 50%;
  left: 50%;
  width: 0;
  height: 0;
  background: rgba(255, 255, 255, 0.2);
  border-radius: 50%;
  transform: translate(-50%, -50%);
  animation: ripple 2s ease-out infinite;
}

@keyframes ripple {
  0% { width: 0; height: 0; opacity: 1; }
  100% { width: 200px; height: 200px; opacity: 0; }
}

/* 进度显示 */
.generating-progress {
  margin-top: 20px;
}

.progress-bar {
  height: 8px;
  background: rgba(76, 175, 80, 0.2);
  border-radius: 4px;
  overflow: hidden;
  margin-bottom: 12px;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #4caf50, #81c784);
  border-radius: 4px;
  transition: width 0.5s ease;
  animation: shimmer 2s linear infinite;
  background-size: 200% 100%;
}

@keyframes shimmer {
  0% { background-position: -200% 0; }
  100% { background-position: 200% 0; }
}

.progress-text {
  color: #81c784;
  font-size: 13px;
  margin: 0;
}

.tip-text {
  color: #666;
  font-size: 13px;
  margin: 20px 0 0 0;
  animation: fadeInUp 0.5s ease 0.6s both;
}

/* ========== 状态卡片通用样式 ========== */
.status-card {
  padding: 32px;
}

.status-header {
  display: flex;
  align-items: center;
  gap: 20px;
  margin-bottom: 28px;
}

.status-icon {
  width: 60px;
  height: 60px;
  background: linear-gradient(135deg, rgba(76, 175, 80, 0.25), rgba(46, 125, 50, 0.15));
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.status-icon svg {
  width: 32px;
  height: 32px;
  color: #4caf50;
}

.status-info {
  flex: 1;
}

.status-title {
  font-size: 22px;
  color: #e8f5e9;
  margin: 0 0 6px 0;
}

.status-subtitle {
  font-size: 14px;
  color: #81c784;
  margin: 0;
}

/* ========== 文稿就绪页面 ========== */
.chapters-list {
  margin-bottom: 24px;
}

.list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.list-header h3 {
  color: #81c784;
  font-size: 14px;
  margin: 0;
}

.chapter-items {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.chapter-item-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 16px;
  background: rgba(0, 30, 20, 0.5);
  border: 1px solid rgba(76, 175, 80, 0.15);
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.chapter-item-row:hover {
  border-color: rgba(76, 175, 80, 0.35);
  background: rgba(0, 40, 25, 0.6);
}

.chapter-item-row.selected {
  border-color: #4caf50;
  background: rgba(76, 175, 80, 0.12);
}

.chapter-item-row.has-audio {
  cursor: default;
}

.chapter-item-left {
  display: flex;
  align-items: center;
  gap: 14px;
}

.chapter-item-num {
  width: 32px;
  height: 32px;
  background: rgba(76, 175, 80, 0.2);
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 600;
  color: #81c784;
}

.chapter-item-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.chapter-item-title {
  font-size: 14px;
  color: #e8f5e9;
}

.chapter-item-status {
  font-size: 12px;
  color: #4caf50;
}

.chapter-item-actions {
  display: flex;
  gap: 10px;
  align-items: center;
}

/* ========== 生成中页面 ========== */
.generating-header {
  display: flex;
  align-items: center;
  gap: 20px;
  margin-bottom: 28px;
}

.generating-icon {
  width: 56px;
  height: 56px;
  background: linear-gradient(135deg, rgba(76, 175, 80, 0.2), rgba(46, 125, 50, 0.1));
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  animation: pulse 2s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.08); }
}

.spinner {
  width: 28px;
  height: 28px;
  border: 3px solid rgba(76, 175, 80, 0.2);
  border-top-color: #4caf50;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.audio-icon {
  background: linear-gradient(135deg, rgba(33, 150, 243, 0.2), rgba(25, 118, 210, 0.1));
}

.audio-waves {
  display: flex;
  align-items: flex-end;
  gap: 3px;
  height: 20px;
}

.audio-waves span {
  width: 4px;
  background: #2196f3;
  border-radius: 2px;
  animation: wave 1s ease-in-out infinite;
}

.audio-waves span:nth-child(1) { animation-delay: 0s; height: 8px; }
.audio-waves span:nth-child(2) { animation-delay: 0.15s; height: 16px; }
.audio-waves span:nth-child(3) { animation-delay: 0.3s; height: 12px; }
.audio-waves span:nth-child(4) { animation-delay: 0.45s; height: 18px; }

@keyframes wave {
  0%, 100% { transform: scaleY(1); }
  50% { transform: scaleY(0.5); }
}

.generating-info {
  flex: 1;
}

.progress-area {
  margin-bottom: 20px;
}

.progress-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.progress-label {
  color: #a5d6a7;
  font-size: 13px;
}

.progress-value {
  color: #4caf50;
  font-size: 18px;
  font-weight: 700;
}

.progress-stats {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 10px;
  font-size: 12px;
  color: #81c784;
}

.tasks-area {
  max-height: 200px;
  overflow-y: auto;
  margin-bottom: 16px;
}

.task-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  background: rgba(0, 30, 20, 0.4);
  border-radius: 8px;
  margin-bottom: 6px;
}

.task-row.processing {
  background: rgba(76, 175, 80, 0.1);
}

.task-row.completed {
  opacity: 0.7;
}

.task-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.task-chapter {
  font-size: 13px;
  color: #e8f5e9;
}

.task-status-text {
  font-size: 12px;
  color: #81c784;
}

.task-row.pending .task-status-text { color: #ffb74d; }
.task-row.processing .task-status-text { color: #64b5f6; }
.task-row.completed .task-status-text { color: #81c784; }
.task-row.failed .task-status-text { color: #ef5350; }

.task-progress-bar {
  width: 80px;
  height: 4px;
  background: rgba(76, 175, 80, 0.2);
  border-radius: 2px;
  overflow: hidden;
}

.task-progress-fill {
  height: 100%;
  background: #4caf50;
  border-radius: 2px;
  transition: width 0.3s;
}

.task-progress-fill.audio {
  background: #2196f3;
}

@media (max-width: 600px) {
  .ocr-complete-card {
    padding: 24px;
  }
  
  .quick-actions {
    flex-direction: column;
  }
  
  .btn-lg {
    width: 100%;
    justify-content: center;
  }
  
  .status-card {
    padding: 20px;
  }
  
  .status-header {
    flex-direction: column;
    text-align: center;
  }
}
</style>