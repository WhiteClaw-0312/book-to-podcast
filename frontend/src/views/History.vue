<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { apiFetch, getUser, getToken } from '../api'

const router = useRouter()
const user = ref<any>(null)
const books = ref<any[]>([])
const loading = ref(true)
const activeTab = ref<'all' | 'scripts' | 'audio'>('all')

// 筛选后的书籍
const filteredBooks = computed(() => {
  if (activeTab.value === 'scripts') {
    return books.value.filter(b => 
      b.chapters?.some((c: any) => c.has_script)
    )
  }
  if (activeTab.value === 'audio') {
    return books.value.filter(b => 
      b.chapters?.some((c: any) => c.has_audio)
    )
  }
  return books.value
})

// 统计
const stats = computed(() => {
  const totalBooks = books.value.length
  const totalScripts = books.value.reduce((sum, b) => 
    sum + (b.chapters?.filter((c: any) => c.has_script).length || 0), 0
  )
  const totalAudio = books.value.reduce((sum, b) => 
    sum + (b.chapters?.filter((c: any) => c.has_audio).length || 0), 0
  )
  const totalDuration = books.value.reduce((sum, b) => 
    sum + (b.chapters?.reduce((s: number, c: any) => s + (c.duration || 0), 0) || 0), 0
  )
  return { totalBooks, totalScripts, totalAudio, totalDuration }
})

// 获取历史记录
const fetchHistory = async () => {
  try {
    const token = getToken()
    const res = await apiFetch('/api/books/my-books', {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    if (res.ok) {
      books.value = await res.json()
    }
  } catch (e) {
    console.error(e)
  }
  loading.value = false
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

// 查看书籍
const viewBook = (bookId: string) => {
  router.push(`/book/${bookId}`)
}

// 编辑文稿
const editScript = (bookId: string, chapterNum: number) => {
  router.push(`/book/${bookId}/script?chapter=${chapterNum}`)
}

// 播放音频
const playAudio = (bookId: string) => {
  router.push(`/book/${bookId}`)
}

// 删除书籍
const deleteBook = async (bookId: string) => {
  if (!confirm('确定删除此书籍？文稿和音频将一并删除。')) return
  
  try {
    const token = getToken()
    const res = await apiFetch(`/api/books/${bookId}`, {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${token}` }
    })
    if (res.ok) {
      books.value = books.value.filter(b => b.id !== bookId)
    }
  } catch (e) {
    console.error(e)
  }
}

onMounted(() => {
  user.value = getUser()
  if (!user.value) {
    router.push('/')
    return
  }
  fetchHistory()
})
</script>

<template>
  <div class="container">
    <!-- Header -->
    <div class="card header-card">
      <h1 style="color: #4caf50; font-size: 22px; margin: 0;">📜 我的历史</h1>
      <div class="header-actions">
        <button class="btn btn-secondary" @click="router.push('/')">← 返回首页</button>
      </div>
    </div>

    <!-- 统计卡片 -->
    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-icon">📚</div>
        <div class="stat-value">{{ stats.totalBooks }}</div>
        <div class="stat-label">书籍</div>
      </div>
      <div class="stat-card">
        <div class="stat-icon">📝</div>
        <div class="stat-value">{{ stats.totalScripts }}</div>
        <div class="stat-label">文稿</div>
      </div>
      <div class="stat-card">
        <div class="stat-icon">🎧</div>
        <div class="stat-value">{{ stats.totalAudio }}</div>
        <div class="stat-label">音频</div>
      </div>
      <div class="stat-card">
        <div class="stat-icon">⏱️</div>
        <div class="stat-value">{{ Math.floor(stats.totalDuration / 60) }}</div>
        <div class="stat-label">分钟</div>
      </div>
    </div>

    <!-- 筛选标签 -->
    <div class="card filter-card">
      <div class="filter-tabs">
        <button 
          :class="['filter-tab', { active: activeTab === 'all' }]"
          @click="activeTab = 'all'"
        >全部</button>
        <button 
          :class="['filter-tab', { active: activeTab === 'scripts' }]"
          @click="activeTab = 'scripts'"
        >📝 有文稿</button>
        <button 
          :class="['filter-tab', { active: activeTab === 'audio' }]"
          @click="activeTab = 'audio'"
        >🎧 有音频</button>
      </div>
    </div>

    <!-- 加载中 -->
    <div v-if="loading" class="card loading-card">
      <div class="loading">加载中...</div>
    </div>

    <!-- 空状态 -->
    <div v-else-if="filteredBooks.length === 0" class="card empty-card">
      <div class="empty-icon">📭</div>
      <p class="empty-text">暂无历史记录</p>
      <button class="btn btn-primary" @click="router.push('/')">开始创建播客</button>
    </div>

    <!-- 书籍列表 -->
    <div v-else class="books-list">
      <div v-for="book in filteredBooks" :key="book.id" class="card book-card">
        <div class="book-header">
          <div class="book-info">
            <h2 class="book-title">{{ book.title }}</h2>
            <div class="book-meta">
              <span>{{ book.total_chapters }} 章</span>
              <span>·</span>
              <span>{{ formatDate(book.created_at) }}</span>
              <span v-if="book.expires_at" class="expires">
                · 保留至 {{ new Date(book.expires_at).toLocaleDateString() }}
              </span>
            </div>
          </div>
          <div class="book-actions">
            <button class="btn btn-secondary btn-sm" @click="viewBook(book.id)">查看</button>
            <button class="btn btn-danger btn-sm" @click="deleteBook(book.id)">删除</button>
          </div>
        </div>

        <!-- 状态标签 -->
        <div class="book-status">
          <span v-if="book.status === 'ready'" class="status-badge ready">✅ OCR 完成</span>
          <span v-else-if="book.status === 'script_ready'" class="status-badge script">📝 文稿就绪</span>
          <span v-else-if="book.status === 'generating_script'" class="status-badge processing">⏳ 生成文稿中</span>
          <span v-else-if="book.status === 'generating_audio'" class="status-badge processing">⏳ 生成音频中</span>
          <span v-else-if="book.status === 'completed'" class="status-badge completed">🎉 已完成</span>
          <span v-else-if="book.status === 'partial'" class="status-badge partial">📊 部分完成</span>
          <span v-else class="status-badge">{{ book.status }}</span>
        </div>

        <!-- 章节列表 -->
        <div class="chapters-list">
          <div 
            v-for="chapter in book.chapters" 
            :key="chapter.id" 
            class="chapter-row"
          >
            <div class="chapter-info">
              <span class="chapter-num">第{{ chapter.number }}章</span>
              <span class="chapter-title">{{ chapter.title }}</span>
            </div>
            
            <div class="chapter-actions">
              <!-- 文稿状态 -->
              <button 
                v-if="chapter.has_script" 
                class="action-btn script"
                @click="editScript(book.id, chapter.number)"
                title="编辑文稿"
              >
                📝 编辑文稿
              </button>
              <span v-else class="action-btn disabled">无文稿</span>
              
              <!-- 音频状态 -->
              <button 
                v-if="chapter.has_audio" 
                class="action-btn audio"
                @click="playAudio(book.id)"
                title="播放音频"
              >
                🎧 {{ formatTime(chapter.duration) }}
              </button>
              <span v-else class="action-btn disabled">无音频</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.header-card {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-actions {
  display: flex;
  gap: 10px;
}

/* 统计卡片 */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 20px;
}

.stat-card {
  background: linear-gradient(135deg, rgba(76, 175, 80, 0.2), rgba(46, 125, 50, 0.1));
  border: 1px solid rgba(76, 175, 80, 0.3);
  border-radius: 12px;
  padding: 20px;
  text-align: center;
}

.stat-icon {
  font-size: 24px;
  margin-bottom: 8px;
}

.stat-value {
  font-size: 28px;
  font-weight: 600;
  color: #4caf50;
}

.stat-label {
  font-size: 12px;
  color: #81c784;
  margin-top: 4px;
}

/* 筛选 */
.filter-card {
  padding: 12px 20px;
  margin-bottom: 20px;
}

.filter-tabs {
  display: flex;
  gap: 8px;
}

.filter-tab {
  background: none;
  border: 1px solid rgba(76, 175, 80, 0.3);
  color: #81c784;
  padding: 8px 16px;
  border-radius: 20px;
  cursor: pointer;
  font-size: 13px;
  transition: all 0.3s;
}

.filter-tab.active {
  background: #4caf50;
  border-color: #4caf50;
  color: white;
}

/* 加载和空状态 */
.loading-card, .empty-card {
  text-align: center;
  padding: 60px 20px;
}

.loading {
  color: #81c784;
}

.empty-icon {
  font-size: 48px;
  margin-bottom: 16px;
}

.empty-text {
  color: #81c784;
  margin-bottom: 20px;
}

/* 书籍列表 */
.books-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.book-card {
  padding: 20px;
}

.book-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 12px;
}

.book-title {
  color: #e8f5e9;
  font-size: 18px;
  margin: 0 0 8px 0;
}

.book-meta {
  color: #81c784;
  font-size: 12px;
}

.book-meta .expires {
  color: #666;
}

.book-actions {
  display: flex;
  gap: 8px;
}

.btn-sm {
  padding: 6px 12px;
  font-size: 12px;
}

.btn-danger {
  background: rgba(244, 67, 54, 0.2);
  border: 1px solid rgba(244, 67, 54, 0.3);
  color: #ef5350;
}

/* 状态标签 */
.book-status {
  margin-bottom: 16px;
}

.status-badge {
  display: inline-block;
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 12px;
}

.status-badge.ready {
  background: rgba(76, 175, 80, 0.2);
  color: #81c784;
}

.status-badge.script {
  background: rgba(33, 150, 243, 0.2);
  color: #64b5f6;
}

.status-badge.processing {
  background: rgba(255, 152, 0, 0.2);
  color: #ffb74d;
}

.status-badge.completed {
  background: rgba(76, 175, 80, 0.3);
  color: #a5d6a7;
}

.status-badge.partial {
  background: rgba(156, 39, 176, 0.2);
  color: #ce93d8;
}

/* 章节列表 */
.chapters-list {
  border-top: 1px solid rgba(76, 175, 80, 0.2);
  padding-top: 12px;
}

.chapter-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 0;
  border-bottom: 1px solid rgba(76, 175, 80, 0.1);
}

.chapter-row:last-child {
  border-bottom: none;
}

.chapter-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.chapter-num {
  color: #4caf50;
  font-size: 13px;
  font-weight: 600;
  min-width: 50px;
}

.chapter-title {
  color: #e8f5e9;
  font-size: 14px;
}

.chapter-actions {
  display: flex;
  gap: 8px;
}

.action-btn {
  padding: 6px 12px;
  border-radius: 6px;
  font-size: 12px;
  cursor: pointer;
  border: none;
  transition: all 0.3s;
}

.action-btn.script {
  background: rgba(33, 150, 243, 0.2);
  color: #64b5f6;
}

.action-btn.script:hover {
  background: rgba(33, 150, 243, 0.3);
}

.action-btn.audio {
  background: rgba(76, 175, 80, 0.2);
  color: #81c784;
}

.action-btn.audio:hover {
  background: rgba(76, 175, 80, 0.3);
}

.action-btn.disabled {
  background: rgba(100, 100, 100, 0.2);
  color: #666;
  cursor: not-allowed;
}

@media (max-width: 600px) {
  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }
  
  .book-header {
    flex-direction: column;
    gap: 12px;
  }
  
  .chapter-row {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }
  
  .chapter-actions {
    width: 100%;
    justify-content: flex-end;
  }
}
</style>