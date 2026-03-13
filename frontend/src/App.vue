<template>
  <div class="min-h-screen bg-gradient-to-br from-green-900 via-green-800 to-gray-900">
    <!-- Header -->
    <header class="bg-green-950/80 backdrop-blur-md border-b border-green-500/30">
      <div class="max-w-6xl mx-auto px-6 py-4">
        <div class="flex items-center justify-between">
          <div>
            <h1 class="text-2xl font-bold text-white flex items-center gap-2">
              <span class="text-green-400">📚</span> 枕边书
            </h1>
            <p class="text-green-300/70 text-sm">AI 图书转播客平台</p>
          </div>
          <div class="flex items-center gap-4">
            <span class="px-3 py-1 bg-green-500/20 text-green-300 text-xs rounded-full border border-green-500/30">
              Beta v1.0
            </span>
          </div>
        </div>
      </div>
    </header>

    <!-- Main Content -->
    <main class="max-w-6xl mx-auto px-6 py-8">
      <!-- Status Bar -->
      <div class="mb-6 bg-green-950/50 rounded-xl border border-green-500/20 p-4">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-3">
            <div :class="backendOnline ? 'bg-green-500' : 'bg-red-500'" class="w-2 h-2 rounded-full animate-pulse"></div>
            <span class="text-green-300 text-sm">
              {{ backendOnline ? '后端服务在线' : '后端服务离线' }}
            </span>
          </div>
          <button @click="checkBackend" class="text-green-400 hover:text-green-300 text-sm">
            刷新状态
          </button>
        </div>
      </div>

      <!-- API Key Section -->
      <section class="mb-8 bg-green-950/50 rounded-2xl border border-green-500/20 p-6">
        <h2 class="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <span class="text-green-400">🔑</span> API 配置
        </h2>
        <div class="grid grid-cols-1 gap-4">
          <div>
            <label class="block text-green-300 text-sm mb-2">Qwen API Key (OCR + 文稿生成)</label>
            <input 
              v-model="qwenApiKey" 
              type="password" 
              class="w-full px-4 py-3 bg-green-900/50 border border-green-500/30 rounded-xl text-white placeholder-green-600 focus:ring-2 focus:ring-green-500 focus:border-transparent outline-none transition-all"
              placeholder="sk-xxx"
            />
          </div>
        </div>
      </section>

      <!-- Upload Section -->
      <section v-if="!currentTask" class="mb-8 bg-green-950/50 rounded-2xl border border-green-500/20 p-6">
        <h2 class="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <span class="text-green-400">📤</span> 上传 PDF
        </h2>
        
        <!-- Drop Zone -->
        <div 
          class="border-2 border-dashed border-green-500/40 rounded-2xl p-12 text-center cursor-pointer hover:border-green-400 hover:bg-green-500/5 transition-all group"
          @click="triggerUpload"
          @dragover.prevent
          @drop.prevent="handleDrop"
        >
          <input 
            type="file" 
            ref="fileInput" 
            accept=".pdf" 
            class="hidden" 
            @change="handleFileSelect"
          />
          <div class="text-6xl mb-4 group-hover:scale-110 transition-transform">📄</div>
          <p class="text-green-300 text-lg mb-2">拖拽 PDF 到这里</p>
          <p class="text-green-500 text-sm">或点击选择文件</p>
          <p v-if="selectedFile" class="mt-4 text-green-400 font-medium bg-green-500/10 inline-block px-4 py-2 rounded-lg">
            {{ selectedFile.name }}
          </p>
        </div>

        <!-- Submit Button -->
        <button 
          @click="uploadPdf"
          :disabled="!canUpload || uploading"
          class="mt-6 w-full py-4 bg-gradient-to-r from-green-500 to-green-600 hover:from-green-400 hover:to-green-500 disabled:from-gray-600 disabled:to-gray-700 text-white font-semibold rounded-xl transition-all transform hover:scale-[1.02] disabled:scale-100 disabled:cursor-not-allowed"
        >
          {{ uploading ? '⏳ 上传中...' : '🚀 开始转换' }}
        </button>
      </section>

      <!-- Progress Section -->
      <section v-if="currentTask && !isCompleted" class="mb-8 bg-green-950/50 rounded-2xl border border-green-500/20 p-6">
        <h2 class="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <span class="text-green-400 animate-spin">⚙️</span> 处理中
        </h2>
        
        <div class="mb-4">
          <div class="flex items-center justify-between mb-2">
            <span class="text-green-300">{{ currentTask.book_title }}</span>
            <span class="text-green-400 font-mono">{{ progressPercent }}%</span>
          </div>
          <div class="h-3 bg-green-900 rounded-full overflow-hidden">
            <div 
              class="h-full bg-gradient-to-r from-green-400 to-green-500 rounded-full transition-all duration-500"
              :style="{ width: progressPercent + '%' }"
            ></div>
          </div>
        </div>

        <div class="bg-green-900/50 rounded-xl p-4">
          <div class="flex items-center gap-3 mb-3">
            <span :class="stepStatus.ocr" class="w-6 h-6 rounded-full flex items-center justify-center text-xs">
              {{ stepStatus.ocr === 'done' ? '✓' : stepStatus.ocr === 'active' ? '●' : '○' }}
            </span>
            <span :class="stepClass(stepStatus.ocr)">OCR 文字识别</span>
          </div>
          <div class="flex items-center gap-3 mb-3">
            <span :class="stepStatus.script" class="w-6 h-6 rounded-full flex items-center justify-center text-xs">
              {{ stepStatus.script === 'done' ? '✓' : stepStatus.script === 'active' ? '●' : '○' }}
            </span>
            <span :class="stepClass(stepStatus.script)">生成播客文稿</span>
          </div>
          <div class="flex items-center gap-3">
            <span :class="stepStatus.audio" class="w-6 h-6 rounded-full flex items-center justify-center text-xs">
              {{ stepStatus.audio === 'done' ? '✓' : stepStatus.audio === 'active' ? '●' : '○' }}
            </span>
            <span :class="stepClass(stepStatus.audio)">合成语音音频</span>
          </div>
        </div>

        <p class="mt-4 text-green-400 text-sm">
          {{ statusText }}
        </p>
      </section>

      <!-- Chapter Selection -->
      <section v-if="showChapterSelect" class="mb-8 bg-green-950/50 rounded-2xl border border-green-500/20 p-6">
        <h2 class="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <span class="text-green-400">📖</span> 选择要生成的章节
        </h2>
        
        <div class="flex gap-4 mb-4">
          <button @click="selectAll" class="px-4 py-2 bg-green-500/20 text-green-300 rounded-lg hover:bg-green-500/30 transition-colors text-sm">
            全选
          </button>
          <button @click="selectNone" class="px-4 py-2 bg-green-500/20 text-green-300 rounded-lg hover:bg-green-500/30 transition-colors text-sm">
            全不选
          </button>
        </div>

        <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
          <label 
            v-for="ch in chapters" 
            :key="ch.number"
            class="flex items-center gap-3 p-3 bg-green-900/30 rounded-xl cursor-pointer hover:bg-green-900/50 transition-colors"
            :class="{ 'ring-2 ring-green-400': ch.selected }"
          >
            <input 
              type="checkbox" 
              v-model="ch.selected"
              class="w-4 h-4 accent-green-500"
            />
            <span class="text-green-300 text-sm">第{{ ch.number }}章</span>
          </label>
        </div>

        <button 
          @click="generateSelected"
          :disabled="!hasSelectedChapters"
          class="mt-6 w-full py-4 bg-gradient-to-r from-green-500 to-green-600 hover:from-green-400 hover:to-green-500 disabled:from-gray-600 disabled:to-gray-700 text-white font-semibold rounded-xl transition-all"
        >
          🎙️ 生成选中的 {{ selectedCount }} 个章节
        </button>
      </section>

      <!-- Podcast List -->
      <section v-if="podcasts.length > 0" class="bg-green-950/50 rounded-2xl border border-green-500/20 p-6">
        <div class="flex items-center justify-between mb-6">
          <h2 class="text-lg font-semibold text-white flex items-center gap-2">
            <span class="text-green-400">🎧</span> 播客列表
          </h2>
          <span class="text-green-400 text-sm">{{ podcasts.length }} 个章节</span>
        </div>
        
        <div class="space-y-3">
          <PodcastPlayer
            v-for="podcast in podcasts"
            :key="podcast.number"
            :podcast="podcast"
            :task-id="currentTask?.id"
          />
        </div>
      </section>
    </main>

    <!-- Footer -->
    <footer class="text-center py-6 text-green-500/50 text-sm border-t border-green-500/10">
      <p>Powered by Qwen AI + edge-tts</p>
    </footer>
  </div>
</template>

<script>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import axios from 'axios'
import PodcastPlayer from './components/PodcastPlayer.vue'

const API_BASE = 'http://139.196.211.206:8000'

export default {
  name: 'App',
  components: { PodcastPlayer },
  setup() {
    const fileInput = ref(null)
    const selectedFile = ref(null)
    const qwenApiKey = ref('')
    const uploading = ref(false)
    const currentTask = ref(null)
    const podcasts = ref([])
    const chapters = ref([])
    const backendOnline = ref(false)
    let pollInterval = null

    const canUpload = computed(() => {
      return selectedFile.value && qwenApiKey.value && backendOnline.value
    })

    const statusText = computed(() => {
      if (!currentTask.value) return ''
      const p = currentTask.value.progress
      return p.message || '处理中...'
    })

    const progressPercent = computed(() => {
      if (!currentTask.value) return 0
      return currentTask.value.progress.progress
    })

    const isCompleted = computed(() => {
      return currentTask.value?.status === 'completed'
    })

    const showChapterSelect = computed(() => {
      return currentTask.value?.status === 'chapters_ready'
    })

    const selectedCount = computed(() => {
      return chapters.value.filter(c => c.selected).length
    })

    const hasSelectedChapters = computed(() => {
      return selectedCount.value > 0
    })

    const stepStatus = computed(() => {
      if (!currentTask.value) return { ocr: 'pending', script: 'pending', audio: 'pending' }
      const progress = currentTask.value.progress.progress
      return {
        ocr: progress < 40 ? (progress > 0 ? 'active' : 'pending') : 'done',
        script: progress >= 40 && progress < 90 ? 'active' : (progress >= 90 ? 'done' : 'pending'),
        audio: progress >= 90 ? 'active' : 'pending'
      }
    })

    const stepClass = (status) => {
      return {
        'text-green-400': status === 'done',
        'text-green-300 animate-pulse': status === 'active',
        'text-green-600': status === 'pending'
      }
    }

    const checkBackend = async () => {
      try {
        const response = await axios.get(`${API_BASE}/`, { timeout: 5000 })
        backendOnline.value = response.status === 200
      } catch {
        backendOnline.value = false
      }
    }

    const triggerUpload = () => {
      fileInput.value?.click()
    }

    const handleFileSelect = (e) => {
      const file = e.target.files[0]
      if (file && file.name.endsWith('.pdf')) {
        selectedFile.value = file
      }
    }

    const handleDrop = (e) => {
      const file = e.dataTransfer.files[0]
      if (file && file.name.endsWith('.pdf')) {
        selectedFile.value = file
      }
    }

    const uploadPdf = async () => {
      if (!canUpload.value) return

      uploading.value = true
      
      try {
        const formData = new FormData()
        formData.append('file', selectedFile.value)
        formData.append('qwen_api_key', qwenApiKey.value)

        const response = await axios.post(`${API_BASE}/api/upload`, formData, {
          headers: { 'Content-Type': 'multipart/form-data' },
          timeout: 30000
        })

        currentTask.value = { id: response.data.task_id }
        startPolling()
        
      } catch (error) {
        alert('上传失败: ' + (error.response?.data?.detail || error.message))
      } finally {
        uploading.value = false
      }
    }

    const startPolling = () => {
      pollInterval = setInterval(async () => {
        if (!currentTask.value?.id) return
        
        try {
          const response = await axios.get(`${API_BASE}/api/status/${currentTask.value.id}`)
          currentTask.value = response.data
          
          if (response.data.status === 'completed') {
            podcasts.value = response.data.chapters
            stopPolling()
          } else if (response.data.status === 'chapters_ready') {
            // OCR 完成，显示章节选择
            chapters.value = response.data.chapters.map(ch => ({
              ...ch,
              selected: true
            }))
            stopPolling()
          } else if (response.data.status === 'failed') {
            alert('处理失败: ' + response.data.progress.message)
            stopPolling()
          }
        } catch (error) {
          console.error('Polling error:', error)
        }
      }, 2000)
    }

    const stopPolling = () => {
      if (pollInterval) {
        clearInterval(pollInterval)
        pollInterval = null
      }
    }

    const selectAll = () => {
      chapters.value.forEach(ch => ch.selected = true)
    }

    const selectNone = () => {
      chapters.value.forEach(ch => ch.selected = false)
    }

    const generateSelected = async () => {
      const selected = chapters.value.filter(c => c.selected).map(c => c.number)
      
      try {
        await axios.post(`${API_BASE}/api/generate/${currentTask.value.id}`, {
          chapters: selected
        })
        
        currentTask.value.status = 'processing'
        startPolling()
        
      } catch (error) {
        alert('生成失败: ' + (error.response?.data?.detail || error.message))
      }
    }

    onMounted(async () => {
      await checkBackend()
    })

    onUnmounted(() => {
      stopPolling()
    })

    return {
      fileInput,
      selectedFile,
      qwenApiKey,
      uploading,
      currentTask,
      podcasts,
      chapters,
      backendOnline,
      canUpload,
      statusText,
      progressPercent,
      isCompleted,
      showChapterSelect,
      selectedCount,
      hasSelectedChapters,
      stepStatus,
      stepClass,
      checkBackend,
      triggerUpload,
      handleFileSelect,
      handleDrop,
      uploadPdf,
      selectAll,
      selectNone,
      generateSelected
    }
  }
}
</script>