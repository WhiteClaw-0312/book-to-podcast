<template>
  <div class="min-h-screen bg-gradient-to-br from-indigo-50 to-purple-50">
    <!-- Header -->
    <header class="bg-white shadow-sm">
      <div class="max-w-4xl mx-auto px-4 py-4">
        <h1 class="text-2xl font-bold text-indigo-600">📚 枕边书</h1>
        <p class="text-gray-500 text-sm">图书转播客 - 让书本开口说话</p>
      </div>
    </header>

    <!-- Main Content -->
    <main class="max-w-4xl mx-auto px-4 py-8">
      <!-- Upload Section -->
      <section v-if="!currentTask" class="card mb-8">
        <h2 class="text-xl font-semibold mb-4">上传 PDF</h2>
        
        <!-- Drop Zone -->
        <div 
          class="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center cursor-pointer hover:border-indigo-400 transition-colors"
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
          <div class="text-4xl mb-2">📄</div>
          <p class="text-gray-600">拖拽 PDF 到这里，或点击选择文件</p>
          <p v-if="selectedFile" class="mt-2 text-indigo-600 font-medium">
            已选择: {{ selectedFile.name }}
          </p>
        </div>

        <!-- API Keys -->
        <div class="mt-4 grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">
              Qwen API Key
            </label>
            <input 
              v-model="qwenApiKey" 
              type="password" 
              class="input-field"
              placeholder="sk-xxx"
            />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">
              Qwen TTS API Key
            </label>
            <input 
              v-model="qwenTtsKey" 
              type="password" 
              class="input-field"
              placeholder="sk-xxx"
            />
          </div>
        </div>

        <!-- Submit Button -->
        <button 
          @click="uploadPdf"
          :disabled="!canUpload || uploading"
          class="btn-primary mt-4 w-full"
        >
          {{ uploading ? '上传中...' : '开始转换' }}
        </button>
      </section>

      <!-- Progress Section -->
      <section v-if="currentTask && !isCompleted" class="card mb-8">
        <h2 class="text-xl font-semibold mb-4">处理中...</h2>
        
        <div class="mb-4">
          <p class="text-gray-700 font-medium">{{ currentTask.book_title }}</p>
          <p class="text-sm text-gray-500">{{ statusText }}</p>
        </div>

        <div class="progress-bar">
          <div class="progress-bar-fill" :style="{ width: progressPercent + '%' }"></div>
        </div>
        
        <p class="mt-2 text-sm text-gray-500 text-right">
          {{ progressPercent }}%
        </p>
      </section>

      <!-- Podcast List -->
      <section v-if="isCompleted || podcasts.length > 0" class="card">
        <h2 class="text-xl font-semibold mb-4">🎧 播客列表</h2>
        
        <div v-if="podcasts.length === 0" class="text-center text-gray-500 py-8">
          暂无播客
        </div>
        
        <div v-else class="space-y-4">
          <PodcastPlayer
            v-for="podcast in podcasts"
            :key="podcast.number"
            :podcast="podcast"
            :task-id="currentTask?.id"
            @play="handlePlay"
          />
        </div>
      </section>
    </main>

    <!-- Footer -->
    <footer class="text-center py-4 text-gray-500 text-sm">
      <p>Powered by Qwen AI</p>
    </footer>
  </div>
</template>

<script>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import axios from 'axios'
import PodcastPlayer from './components/PodcastPlayer.vue'

export default {
  name: 'App',
  components: { PodcastPlayer },
  setup() {
    const fileInput = ref(null)
    const selectedFile = ref(null)
    const qwenApiKey = ref('')
    const qwenTtsKey = ref('')
    const uploading = ref(false)
    const currentTask = ref(null)
    const podcasts = ref([])
    let pollInterval = null

    const canUpload = computed(() => {
      return selectedFile.value && qwenApiKey.value && qwenTtsKey.value
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

    // API 基础地址
const API_BASE = 'http://139.196.211.206:8000'

const uploadPdf = async () => {
      if (!canUpload.value) return

      uploading.value = true
      
      try {
        const formData = new FormData()
        formData.append('file', selectedFile.value)
        formData.append('qwen_api_key', qwenApiKey.value)
        formData.append('qwen_tts_key', qwenTtsKey.value)

        const response = await axios.post(`${API_BASE}/api/upload`, formData, {
          headers: { 'Content-Type': 'multipart/form-data' }
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

    const handlePlay = (chapterNum) => {
      console.log('Playing chapter:', chapterNum)
    }

    onMounted(async () => {
      // 加载最近的任务
      try {
        const response = await axios.get(`${API_BASE}/api/tasks?limit=5`)
        // 可以显示历史任务
      } catch (error) {
        console.log('No existing tasks')
      }
    })

    onUnmounted(() => {
      stopPolling()
    })

    return {
      fileInput,
      selectedFile,
      qwenApiKey,
      qwenTtsKey,
      uploading,
      currentTask,
      podcasts,
      canUpload,
      statusText,
      progressPercent,
      isCompleted,
      triggerUpload,
      handleFileSelect,
      handleDrop,
      uploadPdf,
      handlePlay
    }
  }
}
</script>