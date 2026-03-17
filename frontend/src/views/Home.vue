<script setup lang="ts">
import { ref, onMounted, computed, onUnmounted } from 'vue'
import { apiFetch } from '../api'
import AuthModal from '../components/AuthModal.vue'

// 用户状态
const user = ref<any>(null)
const showAuthModal = ref(false)
const authMode = ref<'login' | 'register'>('login')

// 后端状态
const backendOnline = ref(false)
const showCertHint = ref(false)

// 文件上传
const file = ref<File | null>(null)
const uploading = ref(false)
const uploadProgress = ref('')

// 生成队列
const queueBooks = ref<any[]>([])
const loadingQueue = ref(false)

// 分页
const pageSize = 3
const currentPage = ref(1)
const totalPages = computed(() => Math.ceil(queueBooks.value.length / pageSize))
const paginatedBooks = computed(() => {
  const start = (currentPage.value - 1) * pageSize
  return queueBooks.value.slice(start, start + pageSize)
})

const goToPage = (page: number) => {
  currentPage.value = page
  // 切换页面时关闭展开的详情
  selectedBookId.value = null
  selectedBook.value = null
  stopPolling()
}

const prevPage = () => {
  if (currentPage.value > 1) {
    goToPage(currentPage.value - 1)
  }
}

const nextPage = () => {
  if (currentPage.value < totalPages.value) {
    goToPage(currentPage.value + 1)
  }
}

// 当前选中查看的书籍
const selectedBookId = ref<string | null>(null)
const selectedBook = ref<any>(null)
const queueProgress = ref<any>(null)
const tasks = ref<any[]>([])
const pollingTimer = ref<any>(null)

// 音色相关
const voices = ref<any[]>([])
const showVoiceSelector = ref(false)
const voiceMapping = ref<Record<string, string>>({
  '小北': 'zh-CN-XiaoxiaoNeural',
  '阿南': 'zh-CN-YunxiNeural'
})
const selectedChapters = ref<number[]>([])

// 检查后端状态
const checkBackend = async () => {
  try {
    const res = await apiFetch('/health')
    backendOnline.value = res.ok
    if (res.ok) {
      showCertHint.value = false
    }
  } catch {
    backendOnline.value = false
  }
}

// 切换到服务器版本
const switchToServer = () => {
  window.location.href = 'http://139.196.211.206/'
}

// 刷新状态
const refreshStatus = async () => {
  showCertHint.value = false
  backendOnline.value = false
  await checkBackend()
}

// 检测是否在 GitHub Pages 上
const isGitHubPages = window.location.hostname.includes('github.io')

// 检查用户登录状态 - 增加服务器验证
const checkUser = async () => {
  const token = localStorage.getItem('token')
  const userData = localStorage.getItem('user')
  
  if (token && userData) {
    try {
      user.value = JSON.parse(userData)
      
      // 验证 token 是否有效
      const res = await apiFetch('/api/auth/me')
      if (res.status === 401) {
        // Token 无效，清除登录状态
        localStorage.removeItem('token')
        localStorage.removeItem('user')
        user.value = null
      } else if (res.ok) {
        // Token 有效，更新用户信息
        const data = await res.json()
        user.value = data
        localStorage.setItem('user', JSON.stringify(data))
      }
    } catch {
      user.value = null
    }
  }
}

// 文件选择
const onFileSelect = (e: Event) => {
  const target = e.target as HTMLInputElement
  if (target.files?.length) {
    file.value = target.files[0]
  }
}

const onDrop = (e: DragEvent) => {
  e.preventDefault()
  const dropped = e.dataTransfer?.files[0]
  if (dropped && (dropped.name.endsWith('.pdf') || dropped.name.endsWith('.txt') || dropped.name.endsWith('.md'))) {
    file.value = dropped
  }
}

// 上传
const upload = async () => {
  if (!file.value) return
  
  // 检查是否登录
  if (!user.value) {
    authMode.value = 'login'
    showAuthModal.value = true
    return
  }
  
  uploading.value = true
  uploadProgress.value = '上传中...'
  
  const form = new FormData()
  form.append('file', file.value)
  
  try {
    const token = localStorage.getItem('token')
    const res = await apiFetch('/api/books', {
      method: 'POST',
      body: form,
      headers: token ? { 'Authorization': `Bearer ${token}` } : {}
    })
    
    if (res.status === 401) {
      // Token 失效，清除登录状态
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      user.value = null
      authMode.value = 'login'
      showAuthModal.value = true
      uploading.value = false
      uploadProgress.value = ''
      return
    }
    
    if (!res.ok) {
      const err = await res.json()
      throw new Error(err.detail || '上传失败')
    }
    
    const data = await res.json()
    uploadProgress.value = '上传成功，正在识别...'
    file.value = null
    
    // 刷新队列并跳转到第一页
    await fetchQueue()
    currentPage.value = 1
    
    // 自动选中刚上传的书籍
    selectedBookId.value = data.id
    await selectBook(data.id)
    
    // 清除文件选择
    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement
    if (fileInput) fileInput.value = ''
    
  } catch (e: any) {
    alert('上传失败: ' + e.message)
    uploadProgress.value = ''
  } finally {
    uploading.value = false
  }
}

// 登录成功
const onAuthSuccess = async (userData: any) => {
  user.value = userData
  // 刷新队列
  await fetchQueue()
  // 自动继续上传
  if (file.value) {
    upload()
  }
}

// 登出
const logout = () => {
  localStorage.removeItem('token')
  localStorage.removeItem('user')
  user.value = null
  queueBooks.value = []
  selectedBook.value = null
  selectedBookId.value = null
}

// 显示登录/注册
const showLogin = () => {
  authMode.value = 'login'
  showAuthModal.value = true
}

const showRegister = () => {
  authMode.value = 'register'
  showAuthModal.value = true
}

// 获取生成队列
const fetchQueue = async () => {
  if (!user.value) return
  
  loadingQueue.value = true
  try {
    const token = localStorage.getItem('token')
    const res = await apiFetch('/api/books/my-books', {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    if (res.ok) {
      queueBooks.value = await res.json()
    } else if (res.status === 401) {
      // Token 失效
      logout()
    }
  } catch (e) {
    console.error('获取队列失败', e)
  }
  loadingQueue.value = false
}

// 选中书籍查看详情
const selectBook = async (bookId: string) => {
  if (selectedBookId.value === bookId) {
    // 取消选中
    selectedBookId.value = null
    selectedBook.value = null
    stopPolling()
    return
  }
  
  selectedBookId.value = bookId
  await fetchBookDetail()
  
  // 如果正在处理，开始轮询
  if (selectedBook.value?.status === 'generating_script' || selectedBook.value?.status === 'generating_audio') {
    startPolling()
  }
}

// 获取书籍详情
const fetchBookDetail = async () => {
  if (!selectedBookId.value) return
  
  try {
    const res = await apiFetch(`/api/books/${selectedBookId.value}`)
    if (res.ok) {
      selectedBook.value = await res.json()
    }
  } catch (e) {
    console.error('获取书籍详情失败', e)
  }
}

// 获取进度
const fetchProgress = async () => {
  if (!selectedBookId.value) return
  
  try {
    const res = await apiFetch(`/api/books/${selectedBookId.value}/progress`)
    const data = await res.json()
    queueProgress.value = data.queue
    tasks.value = data.tasks || []
    
    // 更新书籍状态
    await fetchBookDetail()
    await fetchQueue()
    
    // 如果完成，停止轮询
    if (data.queue?.status === 'completed' || data.book_status === 'script_ready' || data.book_status === 'completed') {
      stopPolling()
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

// 停止轮询
const stopPolling = () => {
  if (pollingTimer.value) {
    clearInterval(pollingTimer.value)
    pollingTimer.value = null
  }
}

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

// 女声音色列表
const femaleVoices = computed(() => voices.value.filter(v => v.gender === 'female'))
const maleVoices = computed(() => voices.value.filter(v => v.gender === 'male'))

// 预览音色
const previewingVoice = ref<string | null>(null)
const previewAudio = ref<HTMLAudioElement | null>(null)

const previewVoice = async (voiceId: string) => {
  if (previewAudio.value) {
    previewAudio.value.pause()
    previewAudio.value = null
  }
  
  previewingVoice.value = voiceId
  
  try {
    const audioUrl = `http://139.196.211.206/api/voices/edge-id/${voiceId}/preview`
    const audio = new Audio(audioUrl)
    previewAudio.value = audio
    
    audio.onended = () => {
      previewingVoice.value = null
    }
    
    audio.onerror = () => {
      previewingVoice.value = null
    }
    
    await audio.play()
  } catch (e) {
    previewingVoice.value = null
  }
}

const stopPreview = () => {
  if (previewAudio.value) {
    previewAudio.value.pause()
    previewAudio.value = null
  }
  previewingVoice.value = null
}

// 选择章节
const toggleChapter = (num: number) => {
  if (selectedChapters.value.includes(num)) {
    selectedChapters.value = selectedChapters.value.filter(n => n !== num)
  } else {
    selectedChapters.value.push(num)
  }
}

const selectAllChapters = () => {
  if (selectedBook.value) {
    selectedChapters.value = selectedBook.value.chapters.map((c: any) => c.number)
  }
}

const deselectAllChapters = () => {
  selectedChapters.value = []
}

// 生成文稿
const generateScripts = async () => {
  if (!selectedChapters.value.length || !selectedBookId.value) return
  
  try {
    const token = localStorage.getItem('token')
    const res = await apiFetch(`/api/books/${selectedBookId.value}/generate-script`, {
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
  }
}

// 显示音色选择器
const openVoiceSelector = () => {
  showVoiceSelector.value = true
}

// 确认生成音频
const confirmGenerateAudio = async () => {
  if (!selectedChapters.value.length || !selectedBookId.value) return
  
  showVoiceSelector.value = false
  
  try {
    const token = localStorage.getItem('token')
    const res = await apiFetch(`/api/books/${selectedBookId.value}/generate-audio`, {
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
  }
}

// 删除书籍
const deleteBook = async (bookId: string) => {
  if (!confirm('确定删除此书籍？文稿和音频将一并删除。')) return
  
  try {
    const token = localStorage.getItem('token')
    const res = await apiFetch(`/api/books/${bookId}`, {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${token}` }
    })
    
    if (res.ok) {
      // 从列表中移除
      queueBooks.value = queueBooks.value.filter(b => b.id !== bookId)
      
      // 关闭展开的详情
      if (selectedBookId.value === bookId) {
        selectedBookId.value = null
        selectedBook.value = null
        stopPolling()
      }
      
      // 调整页码
      const newTotalPages = Math.ceil(queueBooks.value.length / pageSize)
      if (currentPage.value > newTotalPages && newTotalPages > 0) {
        currentPage.value = newTotalPages
      }
    } else {
      const err = await res.json()
      alert('删除失败: ' + (err.detail || '未知错误'))
    }
  } catch (e: any) {
    alert('删除失败: ' + e.message)
  }
}

// 格式化时间
const formatTime = (seconds: number) => {
  const m = Math.floor(seconds / 60)
  const s = Math.floor(seconds % 60)
  return `${m}:${String(s).padStart(2, '0')}`
}

const formatDate = (dateStr: string) => {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  return `${d.getMonth() + 1}/${d.getDate()} ${d.getHours()}:${String(d.getMinutes()).padStart(2, '0')}`
}

// 统计
const stats = computed(() => {
  const totalBooks = queueBooks.value.length
  const totalScripts = queueBooks.value.reduce((sum, b) => 
    sum + (b.chapters?.filter((c: any) => c.has_script).length || 0), 0
  )
  const totalAudio = queueBooks.value.reduce((sum, b) => 
    sum + (b.chapters?.filter((c: any) => c.has_audio).length || 0), 0
  )
  return { totalBooks, totalScripts, totalAudio }
})

// 选中的章节数
const selectedCount = computed(() => selectedChapters.value.length)

onMounted(async () => {
  await checkBackend()
  await checkUser()
  await fetchVoices()
  if (user.value) {
    await fetchQueue()
  }
  setInterval(checkBackend, 30000)
})

onUnmounted(() => {
  stopPolling()
  if (previewAudio.value) {
    previewAudio.value.pause()
  }
})
</script>

<template>
  <div class="container">
    <!-- Header -->
    <div class="card header-card">
      <div class="header-left">
        <h1 class="site-title">📚 枕边书</h1>
        <p class="site-subtitle">AI 图书转播客 · 一键生成</p>
      </div>
      <div class="header-right">
        <div 
          class="status-badge" 
          :class="backendOnline ? 'online' : 'offline'"
          @click="backendOnline ? null : (showCertHint = true)"
          :title="backendOnline ? '后端服务正常运行' : '点击查看解决方案'"
        >
          {{ backendOnline ? '● 在线' : '○ 离线' }}
        </div>
        <div v-if="user" class="user-info">
          <span class="user-name">{{ user.nickname || user.email }}</span>
          <span class="user-balance">{{ user.balance + user.free_quota }}次</span>
          <button class="logout-btn" @click="logout">退出</button>
        </div>
        <div v-else class="auth-buttons">
          <button class="btn-text" @click="showLogin">登录</button>
          <button class="btn-secondary" @click="showRegister">注册</button>
        </div>
      </div>
    </div>

    <!-- 上传区域 -->
    <div class="card upload-card">
      <h2 class="card-title">📤 上传文件</h2>
      
      <div 
        class="upload-zone" 
        @click="($refs.fileInput as HTMLInputElement).click()"
        @dragover.prevent
        @drop="onDrop"
      >
        <input 
          type="file" 
          ref="fileInput" 
          accept=".pdf,.txt,.md" 
          @change="onFileSelect" 
          style="display: none"
        />
        <div class="upload-icon">📄</div>
        <p class="upload-text">{{ file ? file.name : '拖拽文件到这里或点击选择' }}</p>
        <p class="upload-hint">支持 PDF、TXT、MD 格式</p>
      </div>
      
      <button 
        class="btn btn-primary upload-btn"
        @click="upload" 
        :disabled="!file || uploading"
      >
        {{ uploading ? '⏳ ' + uploadProgress : '🚀 开始生成播客' }}
      </button>
      
      <p class="upload-tip" v-if="!user">
        💡 新用户注册即送 <strong>3次</strong> 免费体验
      </p>
    </div>

    <!-- 功能介绍 -->
    <div class="card features-card">
      <h2 class="card-title">✨ 功能特点</h2>
      <div class="features-grid">
        <div class="feature-item">
          <div class="feature-icon">📄</div>
          <h3>智能解析</h3>
          <p>PDF/文本自动识别，提取章节</p>
        </div>
        <div class="feature-item">
          <div class="feature-icon">🎙️</div>
          <h3>AI播客</h3>
          <p>双人对话，像听节目一样听书</p>
        </div>
        <div class="feature-item">
          <div class="feature-icon">🎭</div>
          <h3>多音色</h3>
          <p>多种音色可选，角色自由搭配</p>
        </div>
        <div class="feature-item">
          <div class="feature-icon">✏️</div>
          <h3>可编辑</h3>
          <p>文稿可编辑，Prompt可自定义</p>
        </div>
      </div>
    </div>

    <!-- 价格 -->
    <div class="card pricing-card">
      <h2 class="card-title">💎 价格方案</h2>
      <div class="pricing-grid">
        <div class="price-item">
          <div class="price-amount">¥10</div>
          <div class="price-count">100次</div>
          <div class="price-unit">¥0.10/次</div>
        </div>
        <div class="price-item featured">
          <div class="price-badge">推荐</div>
          <div class="price-amount">¥45</div>
          <div class="price-count">500次</div>
          <div class="price-unit">¥0.09/次</div>
        </div>
        <div class="price-item">
          <div class="price-amount">¥80</div>
          <div class="price-count">1000次</div>
          <div class="price-unit">¥0.08/次</div>
        </div>
      </div>
    </div>

    <!-- 生成队列 -->
    <div class="card queue-card" v-if="user">
      <h2 class="card-title">📋 生成队列</h2>
      
      <!-- 未登录提示 -->
      <div v-if="!user" class="queue-empty">
        <p>请先登录查看生成队列</p>
      </div>
      
      <!-- 加载中 -->
      <div v-else-if="loadingQueue" class="queue-loading">
        <span>加载中...</span>
      </div>
      
      <!-- 空队列 -->
      <div v-else-if="queueBooks.length === 0" class="queue-empty">
        <p>暂无生成任务</p>
        <p class="queue-hint">上传文件后，任务将在这里显示</p>
      </div>
      
      <!-- 队列列表 -->
      <div v-else class="queue-list">
        <!-- 书籍列表 -->
        <div 
          v-for="book in paginatedBooks" 
          :key="book.id" 
          :class="['queue-item', { expanded: selectedBookId === book.id }]"
        >
          <!-- 书籍标题行 -->
          <div class="queue-item-header" @click="selectBook(book.id)">
            <div class="queue-item-info">
              <span class="queue-item-title">{{ book.title }}</span>
              <span class="queue-item-meta">
                {{ book.total_chapters }}章 · {{ formatDate(book.created_at) }}
              </span>
            </div>
            <div class="queue-item-status">
              <span v-if="book.status === 'ready'" class="status-tag ready">📄 OCR完成</span>
              <span v-else-if="book.status === 'script_ready'" class="status-tag script">📝 文稿就绪</span>
              <span v-else-if="book.status === 'generating_script'" class="status-tag processing">⏳ 生成文稿中</span>
              <span v-else-if="book.status === 'generating_audio'" class="status-tag processing">⏳ 生成音频中</span>
              <span v-else-if="book.status === 'completed'" class="status-tag completed">✅ 已完成</span>
              <span v-else-if="book.status === 'partial'" class="status-tag partial">📊 部分完成</span>
              <span v-else class="status-tag">{{ book.status }}</span>
            </div>
            <button class="delete-btn" @click.stop="deleteBook(book.id)" title="删除">🗑️</button>
          </div>
          
          <!-- 展开的详情 -->
          <div v-if="selectedBookId === book.id" class="queue-item-detail">
            <!-- 正在生成文稿 -->
            <div v-if="book.status === 'generating_script'" class="progress-section">
              <div class="progress-header">
                <span class="progress-label">文稿生成进度</span>
                <span class="progress-percent">{{ queueProgress?.progress || 0 }}%</span>
              </div>
              <div class="progress-bar-container">
                <div class="progress-bar-fill" :style="{ width: (queueProgress?.progress || 0) + '%' }"></div>
              </div>
              <div class="progress-stats">
                <span>{{ queueProgress?.completed || 0 }} / {{ queueProgress?.total || 0 }} 章</span>
              </div>
              
              <!-- 任务列表 -->
              <div class="tasks-list" v-if="tasks.length > 0">
                <div v-for="task in tasks" :key="task.id" class="task-item">
                  <span class="task-chapter">第{{ task.chapter_number }}章</span>
                  <span :class="['task-status', task.status]">
                    {{ task.status === 'pending' ? '⏳' : task.status === 'processing' ? '🔄' : task.status === 'completed' ? '✅' : '❌' }}
                  </span>
                </div>
              </div>
            </div>
            
            <!-- 正在生成音频 -->
            <div v-else-if="book.status === 'generating_audio'" class="progress-section">
              <div class="progress-header">
                <span class="progress-label">音频生成进度</span>
                <span class="progress-percent">{{ queueProgress?.progress || 0 }}%</span>
              </div>
              <div class="progress-bar-container">
                <div class="progress-bar-fill audio" :style="{ width: (queueProgress?.progress || 0) + '%' }"></div>
              </div>
              <div class="progress-stats">
                <span>{{ queueProgress?.completed || 0 }} / {{ queueProgress?.total || 0 }} 章</span>
              </div>
              
              <!-- 任务列表 -->
              <div class="tasks-list" v-if="tasks.length > 0">
                <div v-for="task in tasks" :key="task.id" class="task-item">
                  <span class="task-chapter">第{{ task.chapter_number }}章</span>
                  <span :class="['task-status', task.status]">
                    {{ task.status === 'pending' ? '⏳' : task.status === 'processing' ? '🔄' : task.status === 'completed' ? '✅' : '❌' }}
                  </span>
                </div>
              </div>
            </div>
            
            <!-- OCR完成，可以选择生成文稿 -->
            <div v-else-if="book.status === 'ready'" class="action-section">
              <p class="action-hint">选择章节生成文稿（免费）</p>
              <div class="chapter-select">
                <button class="btn-small" @click="selectAllChapters">全选</button>
                <button class="btn-small" @click="deselectAllChapters">全不选</button>
              </div>
              <div class="chapter-grid">
                <div
                  v-for="ch in selectedBook?.chapters || []"
                  :key="ch.number"
                  :class="['chapter-chip', { selected: selectedChapters.includes(ch.number) }]"
                  @click="toggleChapter(ch.number)"
                >
                  {{ ch.number }}
                </div>
              </div>
              <button 
                class="btn btn-primary action-btn"
                @click="generateScripts"
                :disabled="!selectedCount"
              >
                📝 生成文稿（已选 {{ selectedCount }} 章）
              </button>
            </div>
            
            <!-- 文稿就绪，可以生成音频 -->
            <div v-else-if="book.status === 'script_ready' || book.status === 'partial'" class="action-section">
              <p class="action-hint">选择章节生成音频（需要扣费）</p>
              <div class="chapter-list-detail">
                <div v-for="ch in selectedBook?.chapters || []" :key="ch.number" class="chapter-row">
                  <div class="chapter-info">
                    <span class="chapter-num">第{{ ch.number }}章</span>
                    <span class="chapter-title">{{ ch.title }}</span>
                  </div>
                  <div class="chapter-status">
                    <span v-if="ch.has_audio" class="has-audio">✅ 音频 {{ formatTime(ch.duration) }}</span>
                    <label v-else class="checkbox-label" @click.stop>
                      <input 
                        type="checkbox" 
                        :checked="selectedChapters.includes(ch.number)"
                        @change="toggleChapter(ch.number)"
                      />
                      生成音频
                    </label>
                  </div>
                </div>
              </div>
              <div v-if="selectedCount > 0" class="generate-action">
                <span class="cost-hint">需要 {{ selectedCount }} 次额度</span>
                <button class="btn btn-primary" @click="openVoiceSelector">🎙️ 生成音频</button>
              </div>
            </div>
            
            <!-- 已完成 -->
            <div v-else-if="book.status === 'completed'" class="completed-section">
              <p class="completed-hint">🎉 所有章节已完成，点击章节播放音频</p>
              <div class="chapter-list-detail">
                <div v-for="ch in selectedBook?.chapters || []" :key="ch.number" class="chapter-row clickable">
                  <div class="chapter-info">
                    <span class="chapter-num">第{{ ch.number }}章</span>
                    <span class="chapter-title">{{ ch.title }}</span>
                  </div>
                  <div class="chapter-status">
                    <span class="has-audio">🎧 {{ formatTime(ch.duration) }}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
        
        <!-- 分页 -->
        <div v-if="totalPages > 1" class="pagination">
          <button class="page-btn" @click="prevPage" :disabled="currentPage === 1">‹</button>
          <button 
            v-for="p in totalPages" 
            :key="p" 
            :class="['page-btn', { active: p === currentPage }]"
            @click="goToPage(p)"
          >
            {{ p }}
          </button>
          <button class="page-btn" @click="nextPage" :disabled="currentPage === totalPages">›</button>
        </div>
      </div>
    </div>

    <!-- 登录/注册对话框 -->
    <AuthModal 
      v-if="showAuthModal"
      :mode="authMode"
      @close="showAuthModal = false"
      @success="onAuthSuccess"
    />
    
    <!-- 离线提示对话框 -->
    <div v-if="showCertHint" class="modal-overlay" @click.self="showCertHint = false">
      <div class="modal-content cert-hint-modal">
        <div class="modal-header">
          <h2>🔒 无法连接服务器</h2>
          <button class="close-btn" @click="showCertHint = false">×</button>
        </div>
        <div class="cert-hint-body">
          <p class="hint-title">后端服务暂时无法访问</p>
          <p class="hint-desc" v-if="isGitHubPages">
            GitHub Pages 使用 HTTPS，无法直接访问 HTTP 接口。<br>
            请点击下方按钮切换到服务器版本：
          </p>
          <p class="hint-desc" v-else>
            服务器可能暂时离线，请稍后重试。
          </p>
          
          <div class="hint-actions">
            <button class="btn-primary big-btn" @click="switchToServer" v-if="isGitHubPages">
              🚀 切换到服务器版本
            </button>
            <button class="btn-secondary big-btn" @click="refreshStatus" v-else>
              🔄 刷新状态
            </button>
          </div>
        </div>
      </div>
    </div>
    
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
                <div class="voice-header">
                  <div class="voice-name">{{ v.speaker_name }}</div>
                  <button 
                    class="preview-btn"
                    @click.stop="previewingVoice === v.voice_id ? stopPreview() : previewVoice(v.voice_id)"
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
                :class="['voice-option', { selected: voiceMapping['阿南'] === v.voice_id }]"
                @click="voiceMapping['阿南'] = v.voice_id"
              >
                <div class="voice-header">
                  <div class="voice-name">{{ v.speaker_name }}</div>
                  <button 
                    class="preview-btn"
                    @click.stop="previewingVoice === v.voice_id ? stopPreview() : previewVoice(v.voice_id)"
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
            <button class="btn btn-primary" @click="confirmGenerateAudio">
              🎙️ 开始生成 {{ selectedCount }} 章
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* Header */
.header-card {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 16px;
}

.header-left {
  flex: 1;
}

.site-title {
  font-size: 28px;
  color: #4caf50;
  margin: 0;
}

.site-subtitle {
  font-size: 13px;
  color: #81c784;
  margin: 4px 0 0 0;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.status-badge {
  padding: 6px 12px;
  border-radius: 20px;
  font-size: 12px;
  border: 1px solid;
}

.status-badge.online {
  background: rgba(76, 175, 80, 0.2);
  border-color: #4caf50;
  color: #81c784;
}

.status-badge.offline {
  background: rgba(244, 67, 54, 0.2);
  border-color: #f44336;
  color: #ef5350;
  cursor: pointer;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.user-name {
  color: #e8f5e9;
  font-size: 14px;
}

.user-balance {
  background: rgba(76, 175, 80, 0.2);
  padding: 4px 10px;
  border-radius: 12px;
  color: #4caf50;
  font-size: 12px;
}

.logout-btn {
  background: none;
  border: 1px solid rgba(76, 175, 80, 0.3);
  color: #81c784;
  padding: 6px 12px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
}

.auth-buttons {
  display: flex;
  gap: 8px;
}

.btn-text {
  background: none;
  border: none;
  color: #81c784;
  padding: 8px 16px;
  cursor: pointer;
  font-size: 14px;
}

.btn-secondary {
  background: rgba(76, 175, 80, 0.2);
  border: 1px solid rgba(76, 175, 80, 0.3);
  color: #81c784;
  padding: 8px 16px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
}

/* Card */
.card-title {
  margin-bottom: 20px;
  color: #4caf50;
  font-size: 18px;
}

/* Upload */
.upload-card {
  margin-bottom: 20px;
}

.upload-zone {
  border: 2px dashed rgba(76, 175, 80, 0.4);
  border-radius: 16px;
  padding: 40px;
  text-align: center;
  cursor: pointer;
  transition: all 0.3s;
  margin-bottom: 20px;
}

.upload-zone:hover {
  border-color: #4caf50;
  background: rgba(76, 175, 80, 0.05);
}

.upload-icon {
  font-size: 48px;
  margin-bottom: 12px;
}

.upload-text {
  color: #e8f5e9;
  margin: 0 0 8px 0;
}

.upload-hint {
  font-size: 12px;
  color: #81c784;
  margin: 0;
}

.upload-btn {
  width: 100%;
}

.upload-tip {
  text-align: center;
  color: #81c784;
  font-size: 13px;
  margin: 12px 0 0 0;
}

.upload-tip strong {
  color: #4caf50;
}

/* Features */
.features-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 16px;
}

.feature-item {
  text-align: center;
  padding: 20px;
  background: rgba(0, 30, 20, 0.4);
  border-radius: 12px;
}

.feature-icon {
  font-size: 32px;
  margin-bottom: 8px;
}

.feature-item h3 {
  font-size: 14px;
  color: #e8f5e9;
  margin: 0 0 6px 0;
}

.feature-item p {
  font-size: 12px;
  color: #81c784;
  margin: 0;
}

/* Pricing */
.pricing-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}

.price-item {
  text-align: center;
  padding: 20px;
  background: rgba(0, 30, 20, 0.4);
  border: 1px solid rgba(76, 175, 80, 0.2);
  border-radius: 12px;
  position: relative;
}

.price-item.featured {
  border-color: #4caf50;
  background: rgba(76, 175, 80, 0.1);
}

.price-badge {
  position: absolute;
  top: -10px;
  left: 50%;
  transform: translateX(-50%);
  background: #4caf50;
  color: white;
  padding: 4px 12px;
  border-radius: 10px;
  font-size: 11px;
}

.price-amount {
  font-size: 24px;
  color: #4caf50;
  font-weight: 600;
}

.price-count {
  font-size: 13px;
  color: #a5d6a7;
  margin: 4px 0;
}

.price-unit {
  font-size: 11px;
  color: #666;
}

/* Queue */
.queue-card {
  margin-top: 20px;
}

.queue-loading, .queue-empty {
  text-align: center;
  padding: 40px;
  color: #81c784;
}

.queue-hint {
  font-size: 12px;
  color: #666;
  margin-top: 8px;
}

.queue-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.queue-item {
  background: rgba(0, 30, 20, 0.4);
  border: 1px solid rgba(76, 175, 80, 0.2);
  border-radius: 12px;
  overflow: hidden;
}

.queue-item.expanded {
  border-color: #4caf50;
}

.queue-item-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px;
  cursor: pointer;
  transition: background 0.2s;
}

.queue-item-header:hover {
  background: rgba(76, 175, 80, 0.1);
}

.queue-item-info {
  flex: 1;
  min-width: 0;
}

.queue-item-title {
  display: block;
  color: #e8f5e9;
  font-size: 15px;
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.queue-item-meta {
  font-size: 12px;
  color: #81c784;
}

.queue-item-status {
  flex-shrink: 0;
}

.status-tag {
  display: inline-block;
  padding: 4px 10px;
  border-radius: 12px;
  font-size: 11px;
}

.status-tag.ready { background: rgba(76, 175, 80, 0.2); color: #81c784; }
.status-tag.script { background: rgba(33, 150, 243, 0.2); color: #64b5f6; }
.status-tag.processing { background: rgba(255, 152, 0, 0.2); color: #ffb74d; }
.status-tag.completed { background: rgba(76, 175, 80, 0.3); color: #a5d6a7; }
.status-tag.partial { background: rgba(156, 39, 176, 0.2); color: #ce93d8; }

.delete-btn {
  background: none;
  border: none;
  font-size: 16px;
  cursor: pointer;
  padding: 4px;
  opacity: 0.5;
  transition: opacity 0.2s;
}

.delete-btn:hover {
  opacity: 1;
}

/* Queue item detail */
.queue-item-detail {
  border-top: 1px solid rgba(76, 175, 80, 0.2);
  padding: 16px;
}

.progress-section {
  margin-bottom: 16px;
}

.progress-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
}

.progress-label {
  color: #a5d6a7;
  font-size: 13px;
}

.progress-percent {
  color: #4caf50;
  font-size: 18px;
  font-weight: 600;
}

.progress-bar-container {
  height: 8px;
  background: rgba(76, 175, 80, 0.1);
  border-radius: 4px;
  overflow: hidden;
}

.progress-bar-fill {
  height: 100%;
  background: linear-gradient(90deg, #4caf50, #81c784);
  border-radius: 4px;
  transition: width 0.5s ease;
}

.progress-bar-fill.audio {
  background: linear-gradient(90deg, #2196f3, #64b5f6);
}

.progress-stats {
  margin-top: 8px;
  font-size: 12px;
  color: #81c784;
}

.tasks-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
}

.task-item {
  display: flex;
  align-items: center;
  gap: 6px;
  background: rgba(0, 30, 20, 0.6);
  padding: 6px 10px;
  border-radius: 6px;
  font-size: 11px;
}

.task-chapter {
  color: #e8f5e9;
}

.task-status.pending { color: #ffb74d; }
.task-status.processing { color: #64b5f6; }
.task-status.completed { color: #81c784; }
.task-status.failed { color: #ef5350; }

/* Action section */
.action-section {
  padding: 8px 0;
}

.action-hint {
  color: #81c784;
  font-size: 13px;
  margin-bottom: 12px;
}

.chapter-select {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}

.btn-small {
  background: rgba(76, 175, 80, 0.2);
  border: 1px solid rgba(76, 175, 80, 0.3);
  color: #81c784;
  padding: 4px 10px;
  border-radius: 4px;
  font-size: 11px;
  cursor: pointer;
}

.chapter-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(40px, 1fr));
  gap: 6px;
  margin-bottom: 16px;
}

.chapter-chip {
  text-align: center;
  padding: 8px 4px;
  background: rgba(0, 30, 20, 0.6);
  border: 1px solid rgba(76, 175, 80, 0.2);
  border-radius: 6px;
  color: #81c784;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
}

.chapter-chip:hover {
  border-color: #4caf50;
}

.chapter-chip.selected {
  border-color: #4caf50;
  background: rgba(76, 175, 80, 0.2);
  color: #a5d6a7;
}

.action-btn {
  width: 100%;
}

/* Chapter list detail */
.chapter-list-detail {
  margin-bottom: 16px;
}

.chapter-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 0;
  border-bottom: 1px solid rgba(76, 175, 80, 0.1);
}

.chapter-row.clickable {
  cursor: pointer;
}

.chapter-row.clickable:hover {
  background: rgba(76, 175, 80, 0.1);
}

.chapter-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.chapter-num {
  color: #4caf50;
  font-size: 12px;
  font-weight: 600;
}

.chapter-title {
  color: #e8f5e9;
  font-size: 13px;
}

.chapter-status {
  display: flex;
  align-items: center;
  gap: 8px;
}

.has-audio {
  color: #81c784;
  font-size: 12px;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #81c784;
  font-size: 12px;
  cursor: pointer;
}

.checkbox-label input {
  width: 14px;
  height: 14px;
}

.generate-action {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-top: 12px;
  border-top: 1px solid rgba(76, 175, 80, 0.2);
}

.cost-hint {
  color: #81c784;
  font-size: 12px;
}

/* Completed section */
.completed-section {
  padding: 8px 0;
}

.completed-hint {
  color: #a5d6a7;
  font-size: 12px;
  margin-bottom: 12px;
}

/* Modal */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.8);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: linear-gradient(135deg, #1a3a2a 0%, #0f2419 100%);
  border: 1px solid rgba(76, 175, 80, 0.3);
  border-radius: 16px;
  padding: 24px;
  width: 100%;
  max-width: 400px;
  margin: 20px;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
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
  padding: 0;
  line-height: 1;
}

.cert-hint-modal {
  max-width: 420px;
}

.cert-hint-body {
  padding: 10px 0;
}

.hint-title {
  color: #ef5350;
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 16px;
}

.hint-desc {
  color: #a5d6a7;
  font-size: 14px;
  margin-bottom: 20px;
  line-height: 1.6;
}

.hint-actions {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.hint-actions .big-btn {
  width: 100%;
  padding: 16px;
  border-radius: 10px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
}

.hint-actions .btn-primary {
  background: linear-gradient(135deg, #4caf50, #2e7d32);
  border: none;
  color: white;
}

.hint-actions .btn-secondary {
  background: rgba(76, 175, 80, 0.2);
  border: 1px solid rgba(76, 175, 80, 0.3);
  color: #81c784;
}

/* Voice selector */
.voice-modal {
  max-width: 600px;
  max-height: 80vh;
  overflow-y: auto;
}

.voice-selector-body {
  padding: 10px 0;
}

.voice-hint {
  color: #81c784;
  font-size: 14px;
  margin-bottom: 20px;
}

.voice-group {
  margin-bottom: 20px;
}

.voice-group h3 {
  color: #e8f5e9;
  font-size: 14px;
  margin: 0 0 10px 0;
}

.voice-options {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px;
}

.voice-option {
  background: rgba(0, 30, 20, 0.6);
  border: 1px solid rgba(76, 175, 80, 0.2);
  border-radius: 8px;
  padding: 10px;
  cursor: pointer;
  transition: all 0.2s;
}

.voice-option:hover {
  border-color: rgba(76, 175, 80, 0.5);
}

.voice-option.selected {
  border-color: #4caf50;
  background: rgba(76, 175, 80, 0.15);
}

.voice-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}

.voice-name {
  color: #e8f5e9;
  font-size: 13px;
  font-weight: 500;
}

.preview-btn {
  background: rgba(33, 150, 243, 0.2);
  border: none;
  border-radius: 50%;
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  font-size: 10px;
}

.voice-desc {
  color: #81c784;
  font-size: 11px;
}

.voice-actions {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px solid rgba(76, 175, 80, 0.2);
}

/* 分页 */
.pagination {
  display: flex;
  justify-content: center;
  gap: 8px;
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid rgba(76, 175, 80, 0.2);
}

.page-btn {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 30, 20, 0.6);
  border: 1px solid rgba(76, 175, 80, 0.3);
  border-radius: 6px;
  color: #81c784;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
}

.page-btn:hover:not(:disabled) {
  border-color: #4caf50;
  background: rgba(76, 175, 80, 0.2);
}

.page-btn.active {
  border-color: #4caf50;
  background: rgba(76, 175, 80, 0.3);
  color: #a5d6a7;
}

.page-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

@media (max-width: 600px) {
  .pricing-grid {
    grid-template-columns: 1fr;
  }
  
  .header-card {
    flex-direction: column;
    align-items: flex-start;
  }
  
  .header-right {
    width: 100%;
    justify-content: space-between;
  }
  
  .voice-options {
    grid-template-columns: 1fr;
  }
}
</style>