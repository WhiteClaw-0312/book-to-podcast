<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { apiFetch, getApiUrl } from '../api'

const route = useRoute()
const router = useRouter()
const apiKey = ref('')

interface Chapter {
  id: string
  number: number
  title: string
  status: string
  duration: number
  has_audio: boolean
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

const book = ref<BookData | null>(null)
const loading = ref(true)
const generating = ref(false)
const selectedChapters = ref<number[]>([])
const playingChapter = ref<number | null>(null)
const audioElement = ref<HTMLAudioElement | null>(null)

// 已选择的章节数
const selectedCount = computed(() => selectedChapters.value.length)

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

// 生成播客
const generate = async () => {
  if (!selectedCount.value || !apiKey.value) return
  
  generating.value = true
  
  try {
    await apiFetch(`/api/books/${route.params.id}/generate`, {
      method: 'POST',
      body: JSON.stringify({
        chapters: selectedChapters.value,
        api_key: apiKey.value
      })
    })
    
    alert(`开始生成 ${selectedCount.value} 章，请稍候...`)
    
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

// 播放音频
const togglePlay = (chapterNum: number) => {
  if (playingChapter.value === chapterNum) {
    audioElement.value?.pause()
    playingChapter.value = null
    return
  }
  
  audioElement.value?.pause()
  
  const audio = new Audio(getApiUrl(`/api/books/${route.params.id}/chapters/${chapterNum}/audio`))
  audio.play()
  
  audio.onended = () => {
    playingChapter.value = null
  }
  
  audioElement.value = audio
  playingChapter.value = chapterNum
}

// 格式化时间
const formatTime = (seconds: number) => {
  const m = Math.floor(seconds / 60)
  const s = Math.floor(seconds % 60)
  return `${m}:${String(s).padStart(2, '0')}`
}

// 获取音频URL
const getAudioUrl = (chapterNum: number) => {
  return getApiUrl(`/api/books/${route.params.id}/chapters/${chapterNum}/audio`)
}

// 获取文稿URL
const getScriptUrl = (chapterNum: number) => {
  return getApiUrl(`/api/books/${route.params.id}/chapters/${chapterNum}/script`)
}

onMounted(() => {
  const saved = localStorage.getItem('apiKey')
  if (saved) apiKey.value = saved
  
  fetchBook()
  setInterval(fetchBook, 5000) // 定时刷新
})
</script>

<template>
  <div class="container">
    <!-- Header -->
    <div class="card" style="display: flex; justify-content: space-between; align-items: center;">
      <h1 style="font-size: 20px; color: #4caf50; cursor: pointer;" @click="router.push('/')">
        ← {{ book?.title || '加载中...' }}
      </h1>
      <div style="font-size: 13px; color: #81c784;">
        {{ book?.completed_chapters || 0 }} / {{ book?.total_chapters || 0 }} 章完成
      </div>
    </div>

    <!-- 加载中 -->
    <div class="card" v-if="loading" style="text-align: center; padding: 40px;">
      <div style="font-size: 32px;">⏳</div>
      <p>加载中...</p>
    </div>

    <!-- 章节选择 -->
    <div class="card" v-else-if="book?.status === 'ready'">
      <h2 style="margin-bottom: 16px; color: #4caf50;">
        📖 选择章节 (共 {{ book.total_chapters }} 章)
      </h2>
      
      <div style="display: flex; gap: 12px; margin-bottom: 16px;">
        <button class="btn btn-secondary" @click="selectAll">全选</button>
        <button class="btn btn-secondary" @click="selectNone">全不选</button>
        <div style="margin-left: auto; padding: 8px 0; color: #81c784;">
          已选 {{ selectedCount }} 章 · 需要 {{ selectedCount }} 次
        </div>
      </div>
      
      <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(100px, 1fr)); gap: 8px;">
        <div
          v-for="ch in book.chapters"
          :key="ch.number"
          :class="['chapter-item', selectedChapters.includes(ch.number) ? 'selected' : '']"
          @click="selectedChapters.includes(ch.number) 
            ? selectedChapters = selectedChapters.filter(n => n !== ch.number)
            : selectedChapters.push(ch.number)"
        >
          <input 
            type="checkbox" 
            :checked="selectedChapters.includes(ch.number)"
            @click.stop
            style="display: none"
          />
          第{{ ch.number }}章
        </div>
      </div>
      
      <button 
        class="btn btn-primary" 
        @click="generate" 
        :disabled="!selectedCount || generating"
        style="width: 100%; margin-top: 20px;"
      >
        {{ generating ? '⏳ 生成中...' : `🎙️ 生成选中的 ${selectedCount} 章` }}
      </button>
    </div>

    <!-- 处理中 -->
    <div class="card" v-else-if="book?.status === 'processing'">
      <h2 style="margin-bottom: 20px; color: #4caf50;">⚙️ 生成中...</h2>
      <div class="progress-bar">
        <div 
          class="progress-bar-fill" 
          :style="{ width: ((book.script_progress + book.audio_progress) / 100 * 100) + '%' }"
        ></div>
      </div>
      <p style="text-align: center; margin-top: 12px; color: #81c784;">
        {{ book.completed_chapters }} / {{ book.total_chapters }} 章完成
      </p>
    </div>

    <!-- 已完成 -->
    <div class="card" v-else-if="book?.status === 'completed' || book?.status === 'partial'">
      <h2 style="margin-bottom: 16px; color: #4caf50;">🎧 播客列表</h2>
      
      <div v-for="ch in book.chapters" :key="ch.number" class="chapter-card">
        <div style="display: flex; justify-content: space-between; align-items: center;">
          <div>
            <div style="font-weight: 600;">第{{ ch.number }}章: {{ ch.title }}</div>
            <div style="font-size: 12px; color: #81c784; margin-top: 4px;">
              {{ formatTime(ch.duration) }}
            </div>
          </div>
          
          <button 
            v-if="ch.has_audio"
            class="play-btn"
            @click="togglePlay(ch.number)"
          >
            {{ playingChapter === ch.number ? '⏸' : '▶' }}
          </button>
          <span v-else style="font-size: 12px; color: #666;">未生成</span>
        </div>
        
        <div v-if="ch.has_audio" style="margin-top: 12px; display: flex; gap: 12px;">
          <a 
            :href="getAudioUrl(ch.number)"
            download
            class="link-btn"
          >
            ⬇️ 下载
          </a>
          <a 
            :href="getScriptUrl(ch.number)"
            target="_blank"
            class="link-btn"
          >
            📄 文稿
          </a>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.chapter-item {
  padding: 10px;
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
.chapter-card {
  background: rgba(0, 30, 20, 0.4);
  border: 1px solid rgba(76, 175, 80, 0.2);
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 12px;
}
.play-btn {
  width: 44px;
  height: 44px;
  border-radius: 50%;
  background: linear-gradient(135deg, #4caf50, #2e7d32);
  border: none;
  color: white;
  font-size: 18px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
}
.link-btn {
  padding: 6px 12px;
  background: rgba(76, 175, 80, 0.2);
  border: 1px solid rgba(76, 175, 80, 0.3);
  border-radius: 6px;
  color: #81c784;
  text-decoration: none;
  font-size: 12px;
}
</style>