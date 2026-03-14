<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { apiFetch } from '../api'

const router = useRouter()
const apiKey = ref('')
const file = ref<File | null>(null)
const uploading = ref(false)
const bookId = ref('')
const status = ref('idle') // idle, uploading, ocr, ready
const progress = ref(0)

// 检查 API Key
onMounted(() => {
  const saved = localStorage.getItem('apiKey')
  if (saved) apiKey.value = saved
  else router.push('/')
})

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
  if (dropped?.name.endsWith('.pdf')) {
    file.value = dropped
  }
}

// 上传
const upload = async () => {
  if (!file.value || !apiKey.value) return
  
  uploading.value = true
  status.value = 'uploading'
  
  const form = new FormData()
  form.append('file', file.value)
  form.append('api_key', apiKey.value)
  
  try {
    const res = await apiFetch('/api/books', {
      method: 'POST',
      body: form
    })
    
    if (!res.ok) {
      const err = await res.json()
      throw new Error(err.detail || '上传失败')
    }
    
    const data = await res.json()
    bookId.value = data.id
    status.value = 'ocr'
    
    // 开始轮询状态
    pollStatus()
    
  } catch (e: any) {
    alert('上传失败: ' + e.message)
    status.value = 'idle'
    uploading.value = false
  }
}

// 轮询状态
const pollStatus = async () => {
  const timer = setInterval(async () => {
    try {
      const res = await apiFetch(`/api/books/${bookId.value}`)
      const data = await res.json()
      
      progress.value = data.ocr_progress
      
      if (data.status === 'ready') {
        clearInterval(timer)
        router.push(`/book/${bookId.value}`)
      }
      
      if (data.status === 'failed') {
        clearInterval(timer)
        alert('处理失败: ' + data.error_message)
        status.value = 'idle'
        uploading.value = false
      }
      
    } catch (e) {
      console.error(e)
    }
  }, 2000)
}
</script>

<template>
  <div class="container">
    <!-- Header -->
    <div class="card" style="display: flex; justify-content: space-between; align-items: center;">
      <h1 style="font-size: 20px; color: #4caf50; cursor: pointer;" @click="router.push('/')">
        ← 枕边书
      </h1>
      <button class="btn btn-secondary" @click="router.push('/balance')">
        查询余额
      </button>
    </div>

    <!-- 上传区域 -->
    <div class="card" v-if="status === 'idle'">
      <h2 style="margin-bottom: 20px; color: #4caf50;">📤 上传 PDF</h2>
      
      <div 
        class="upload-zone" 
        @click="($refs.fileInput as HTMLInputElement).click()"
        @dragover.prevent
        @drop="onDrop"
      >
        <input 
          type="file" 
          ref="fileInput" 
          accept=".pdf" 
          @change="onFileSelect" 
          style="display: none"
        />
        <div style="font-size: 48px; margin-bottom: 12px;">📄</div>
        <p>{{ file ? file.name : '拖拽 PDF 到这里或点击选择' }}</p>
        <p style="font-size: 12px; color: #81c784; margin-top: 8px;">
          支持扫描版 PDF，AI 自动识别文字
        </p>
      </div>
      
      <button 
        class="btn btn-primary" 
        @click="upload" 
        :disabled="!file"
        style="width: 100%; margin-top: 20px;"
      >
        {{ uploading ? '⏳ 上传中...' : '🚀 开始识别' }}
      </button>
    </div>

    <!-- 处理进度 -->
    <div class="card" v-else>
      <h2 style="margin-bottom: 20px; color: #4caf50;">⚙️ 处理进度</h2>
      
      <div style="text-align: center; padding: 40px;">
        <div style="font-size: 48px; margin-bottom: 16px;">
          {{ status === 'uploading' ? '📤' : '🔍' }}
        </div>
        <p style="margin-bottom: 20px;">
          {{ status === 'uploading' ? '上传文件中...' : 'OCR 识别中...' }}
        </p>
        
        <div class="progress-bar" style="max-width: 300px; margin: 0 auto;">
          <div class="progress-bar-fill" :style="{ width: progress + '%' }"></div>
        </div>
        <p style="font-size: 13px; color: #81c784; margin-top: 8px;">{{ progress }}%</p>
      </div>
    </div>
  </div>
</template>