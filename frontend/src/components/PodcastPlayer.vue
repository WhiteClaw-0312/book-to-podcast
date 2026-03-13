<template>
  <div class="border border-green-500/30 rounded-xl p-4 bg-green-900/30">
    <!-- Header -->
    <div class="flex items-center justify-between mb-3">
      <div>
        <h3 class="font-medium text-green-100">
          第 {{ podcast.number }} 章: {{ podcast.title }}
        </h3>
        <p class="text-sm text-green-400">
          {{ formatDuration(podcast.duration) }}
        </p>
      </div>
      
      <div class="flex gap-2">
        <a 
          v-if="taskId"
          :href="`${API_BASE}/api/audio/${taskId}/${String(podcast.number).padStart(2, '0')}`"
          download
          class="text-green-400 hover:text-green-300"
          title="下载音频"
        >
          ⬇️
        </a>
      </div>
    </div>

    <!-- Player -->
    <div class="flex items-center gap-3">
      <!-- Play Button -->
      <button 
        @click="togglePlay"
        class="w-12 h-12 flex items-center justify-center rounded-full bg-gradient-to-br from-green-400 to-green-600 text-white hover:from-green-300 hover:to-green-500 transition-all shadow-lg shadow-green-500/20"
      >
        {{ isPlaying ? '⏸' : '▶️' }}
      </button>

      <!-- Progress -->
      <div class="flex-1">
        <div 
          class="h-2 bg-green-800 rounded-full cursor-pointer overflow-hidden"
          @click="seek"
          ref="progressBar"
        >
          <div 
            class="h-full bg-gradient-to-r from-green-400 to-green-500 rounded-full transition-all"
            :style="{ width: progressPercent + '%' }"
          ></div>
        </div>
        
        <div class="flex justify-between text-xs text-green-400 mt-1">
          <span>{{ formatTime(currentTime) }}</span>
          <span>{{ formatTime(duration) }}</span>
        </div>
      </div>
    </div>

    <!-- Script Toggle -->
    <button 
      @click="showScript = !showScript"
      class="mt-3 text-sm text-green-400 hover:text-green-300"
    >
      {{ showScript ? '▲ 隐藏文稿' : '▼ 显示文稿' }}
    </button>

    <!-- Script Content -->
    <div v-if="showScript && script" class="mt-3 p-3 bg-green-950/50 rounded-lg max-h-64 overflow-y-auto text-sm">
      <div 
        v-for="(line, i) in script.dialogues" 
        :key="i"
        class="mb-2"
      >
        <span class="font-medium text-green-300">[{{ line.speaker }}]:</span>
        <span class="text-green-100">{{ line.content }}</span>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted, onUnmounted } from 'vue'
import axios from 'axios'

const API_BASE = 'http://139.196.211.206:8000'

export default {
  name: 'PodcastPlayer',
  props: {
    podcast: Object,
    taskId: String
  },
  setup(props) {
    const isPlaying = ref(false)
    const currentTime = ref(0)
    const duration = ref(0)
    const progressPercent = ref(0)
    const showScript = ref(false)
    const script = ref(null)
    const progressBar = ref(null)
    let audio = null

    const formatDuration = (seconds) => {
      if (!seconds) return '0:00'
      const m = Math.floor(seconds / 60)
      const s = Math.floor(seconds % 60)
      return `${m}:${s.toString().padStart(2, '0')}`
    }

    const formatTime = (seconds) => {
      const m = Math.floor(seconds / 60)
      const s = Math.floor(seconds % 60)
      return `${m}:${s.toString().padStart(2, '0')}`
    }

    const initAudio = () => {
      if (!props.taskId || !props.podcast.number) return
      
      const chapterNum = String(props.podcast.number).padStart(2, '0')
      const audioUrl = `${API_BASE}/api/audio/${props.taskId}/${chapterNum}`
      
      audio = new Audio(audioUrl)
      
      audio.addEventListener('loadedmetadata', () => {
        duration.value = audio.duration
      })
      
      audio.addEventListener('timeupdate', () => {
        currentTime.value = audio.currentTime
        progressPercent.value = (audio.currentTime / audio.duration) * 100
      })
      
      audio.addEventListener('ended', () => {
        isPlaying.value = false
      })
    }

    const togglePlay = () => {
      if (!audio) {
        initAudio()
      }
      
      if (isPlaying.value) {
        audio.pause()
      } else {
        audio.play()
      }
      
      isPlaying.value = !isPlaying.value
    }

    const seek = (e) => {
      if (!audio || !progressBar.value) return
      
      const rect = progressBar.value.getBoundingClientRect()
      const percent = (e.clientX - rect.left) / rect.width
      audio.currentTime = percent * audio.duration
    }

    onMounted(() => {
      initAudio()
    })

    onUnmounted(() => {
      if (audio) {
        audio.pause()
        audio = null
      }
    })

    return {
      isPlaying,
      currentTime,
      duration,
      progressPercent,
      showScript,
      script,
      progressBar,
      formatDuration,
      formatTime,
      togglePlay,
      seek
    }
  }
}
</script>