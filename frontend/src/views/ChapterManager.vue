<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { apiFetch, getToken, getUser } from '../api'

const route = useRoute()
const router = useRouter()
const user = ref<any>(null)

interface Chapter {
  id: string
  number: number
  title: string
  content: string
  page_range: string
  word_count: number
  status: string
  has_script: boolean
  has_audio: boolean
}

interface Page {
  number: number
  content: string
}

interface BookData {
  id: string
  title: string
  status: string
  total_chapters: number
  chapters: Chapter[]
  pages_json?: string
}

const book = ref<BookData | null>(null)
const loading = ref(true)
const saving = ref(false)

// 页面数据
const pages = ref<Page[]>([])

// 当前选中展开的章节
const expandedChapter = ref<Chapter | null>(null)
const editingContent = ref('')
const editingTitle = ref('')
const isEditing = ref(false)

// 视图模式
const viewMode = ref<'chapters' | 'pages'>('chapters')

// 合并模式 - 双击触发
const mergeMode = ref(false)
const selectedForMerge = ref<number[]>([])

// 重新分章
const showReChapterDialog = ref(false)
const reChapterForceLLM = ref(true)
const reChaptering = ref(false)

// 获取书籍数据
const fetchBook = async () => {
  loading.value = true
  try {
    const res = await apiFetch(`/api/books/${route.params.id}`)
    book.value = await res.json()
  } catch (e) {
    console.error('获取书籍失败', e)
    alert('获取书籍失败')
    router.push('/')
  } finally {
    loading.value = false
  }
}

// 获取页面数据
const fetchPages = async () => {
  try {
    const res = await apiFetch(`/api/books/${route.params.id}/pages`)
    const data = await res.json()
    pages.value = data.pages || []
  } catch (e) {
    console.error('获取页面失败', e)
    pages.value = []
  }
}

// 切换视图
const switchViewMode = async (mode: 'chapters' | 'pages') => {
  viewMode.value = mode
  if (mode === 'pages' && pages.value.length === 0) {
    await fetchPages()
  }
}

// 点击章节卡片 - 展开详情
const selectChapter = async (chapterNum: number) => {
  // 如果在合并模式，切换选中状态
  if (mergeMode.value) {
    toggleMergeSelection(chapterNum)
    return
  }
  
  // 正常模式 - 展开章节详情
  try {
    const res = await apiFetch(`/api/books/${route.params.id}/chapters/${chapterNum}/content?format=md`)
    const data = await res.json()
    
    expandedChapter.value = {
      ...data,
      has_script: false,
      has_audio: false
    }
    
    editingContent.value = data.raw_content || data.content
    editingTitle.value = data.title
    isEditing.value = false
  } catch (e) {
    console.error('获取章节内容失败', e)
  }
}

// 关闭展开的章节
const closeExpanded = () => {
  expandedChapter.value = null
  isEditing.value = false
}

// 保存编辑
const saveEdit = async () => {
  if (!expandedChapter.value) return
  
  saving.value = true
  try {
    const res = await apiFetch(`/api/books/${route.params.id}/chapters/${expandedChapter.value.number}/content`, {
      method: 'PUT',
      body: JSON.stringify({
        content: editingContent.value,
        title: editingTitle.value
      })
    })
    
    if (res.ok) {
      // 更新本地数据
      if (expandedChapter.value) {
        expandedChapter.value.content = editingContent.value
        expandedChapter.value.title = editingTitle.value
        expandedChapter.value.word_count = editingContent.value.length
      }
      
      if (book.value) {
        const ch = book.value.chapters.find(c => c.number === expandedChapter.value!.number)
        if (ch) {
          ch.title = editingTitle.value
          ch.content = editingContent.value
        }
      }
      
      isEditing.value = false
    } else {
      const err = await res.json()
      throw new Error(err.detail || '保存失败')
    }
  } catch (e: any) {
    alert('保存失败: ' + e.message)
  } finally {
    saving.value = false
  }
}

// 长按开始 - 进入合并模式
const longPressTimer = ref<any>(null)

const startLongPress = (chapterNum: number) => {
  longPressTimer.value = setTimeout(() => {
    mergeMode.value = true
    selectedForMerge.value = [chapterNum]
    // 震动反馈（如果支持）
    if (navigator.vibrate) {
      navigator.vibrate(50)
    }
  }, 500)
}

// 长按结束
const endLongPress = () => {
  if (longPressTimer.value) {
    clearTimeout(longPressTimer.value)
    longPressTimer.value = null
  }
}

// 切换合并选中
const toggleMergeSelection = (num: number) => {
  if (selectedForMerge.value.includes(num)) {
    selectedForMerge.value = selectedForMerge.value.filter(n => n !== num)
    // 如果没有选中任何章节，退出合并模式
    if (selectedForMerge.value.length === 0) {
      mergeMode.value = false
    }
  } else {
    selectedForMerge.value.push(num)
  }
}

// 退出合并模式
const exitMergeMode = () => {
  mergeMode.value = false
  selectedForMerge.value = []
}

// 合并选中的章节
const mergeSelectedChapters = async () => {
  if (selectedForMerge.value.length < 2) {
    alert('请至少选择2个章节')
    return
  }
  
  saving.value = true
  try {
    const res = await apiFetch(`/api/books/${route.params.id}/chapters/merge`, {
      method: 'POST',
      body: JSON.stringify({
        chapters: [...selectedForMerge.value].sort((a, b) => a - b)
      })
    })
    
    if (res.ok) {
      const data = await res.json()
      // 使用后端返回的更新后的章节列表
      if (data.chapters && book.value) {
        book.value.chapters = data.chapters
        book.value.total_chapters = data.total_chapters
      }
      exitMergeMode()
    } else {
      const err = await res.json()
      throw new Error(err.detail || '合并失败')
    }
  } catch (e: any) {
    alert('合并失败: ' + e.message)
  } finally {
    saving.value = false
  }
}

// 重新智能分章
const reChapter = async () => {
  reChaptering.value = true
  try {
    const res = await apiFetch(`/api/books/${route.params.id}/re-chapter`, {
      method: 'POST',
      body: JSON.stringify({
        force_llm: reChapterForceLLM.value
      })
    })
    
    if (res.ok) {
      showReChapterDialog.value = false
      alert('正在重新分章，请稍后刷新页面查看结果')
      setTimeout(() => fetchBook(), 3000)
    } else {
      const err = await res.json()
      throw new Error(err.detail || '重新分章失败')
    }
  } catch (e: any) {
    alert('重新分章失败: ' + e.message)
  } finally {
    reChaptering.value = false
  }
}

// 返回书籍详情
const goBack = () => {
  router.push(`/book/${route.params.id}`)
}

// 是否选中（合并模式）
const isSelectedForMerge = (num: number) => {
  return selectedForMerge.value.includes(num)
}

// 选中的章节信息
const selectedChaptersInfo = computed(() => {
  if (!book.value) return []
  return selectedForMerge.value
    .sort((a, b) => a - b)
    .map(num => book.value!.chapters.find(c => c.number === num))
    .filter(Boolean)
})

onMounted(() => {
  user.value = getUser()
  fetchBook()
})
</script>

<template>
  <div class="page-container">
    <!-- 顶部导航 -->
    <header class="header">
      <button class="back-btn" @click="goBack">← 返回</button>
      <div class="header-info">
        <h1>{{ book?.title || '加载中...' }}</h1>
        <p>📄 OCR 解析结果 · {{ book?.total_chapters || 0 }} 章节</p>
      </div>
      <div class="header-actions">
        <div class="view-toggle">
          <button 
            :class="['toggle-btn', { active: viewMode === 'chapters' }]"
            @click="switchViewMode('chapters')"
          >📑 章节</button>
          <button 
            :class="['toggle-btn', { active: viewMode === 'pages' }]"
            @click="switchViewMode('pages')"
          >📄 页面</button>
        </div>
        <button class="btn btn-secondary" @click="showReChapterDialog = true">
          🔄 重新分章
        </button>
        <button class="btn btn-primary" @click="goBack">
          ✅ 完成
        </button>
      </div>
    </header>

    <!-- 加载中 -->
    <div class="loading-state" v-if="loading">
      <div class="loading-spinner"></div>
      <p>加载中...</p>
    </div>

    <!-- ========== 章节视图 ========== -->
    <main class="main-content" v-else-if="viewMode === 'chapters' && book">
      <!-- 合并模式提示条 -->
      <div class="merge-hint-bar" v-if="mergeMode">
        <span>已选择 {{ selectedForMerge.length }} 个章节</span>
        <span class="merge-hint-text">点击章节卡片选择/取消</span>
        <button class="btn btn-sm btn-primary" @click="mergeSelectedChapters" :disabled="selectedForMerge.length < 2 || saving">
          {{ saving ? '合并中...' : `合并 ${selectedForMerge.length} 章` }}
        </button>
        <button class="btn btn-sm btn-secondary" @click="exitMergeMode">取消</button>
      </div>

      <!-- 章节网格 -->
      <div class="chapters-grid">
        <div 
          v-for="ch in book.chapters"
          :key="ch.number"
          :class="[
            'chapter-card',
            { 
              'selected-merge': mergeMode && isSelectedForMerge(ch.number),
              'expanded': expandedChapter?.number === ch.number 
            }
          ]"
          @click="selectChapter(ch.number)"
          @mousedown="startLongPress(ch.number)"
          @mouseup="endLongPress"
          @mouseleave="endLongPress"
          @touchstart.prevent="startLongPress(ch.number)"
          @touchend="endLongPress"
        >
          <!-- 合并模式选中标记 -->
          <div class="merge-check" v-if="mergeMode">
            <span v-if="isSelectedForMerge(ch.number)">✓</span>
            <span v-else class="merge-check-empty"></span>
          </div>

          <!-- 章节号 -->
          <div class="chapter-num">第 {{ ch.number }} 章</div>
          
          <!-- 章节标题 -->
          <div class="chapter-title">{{ ch.title }}</div>
          
          <!-- 章节预览 -->
          <div class="chapter-preview">
            {{ ch.content || '' }}
          </div>
          
          <!-- 底部信息 -->
          <div class="chapter-footer">
            <span class="word-count">{{ ch.word_count || 0 }} 字</span>
            <span class="hint-text" v-if="!mergeMode">点击查看 · 长按合并</span>
          </div>
        </div>
      </div>

      <!-- 合并模式底部工具栏 -->
      <div class="merge-toolbar" v-if="mergeMode && selectedForMerge.length >= 2">
        <div class="merge-preview">
          <span class="merge-label">将合并：</span>
          <span class="merge-chapters">
            第 {{ [...selectedForMerge].sort((a,b) => a-b).join('、') }} 章
          </span>
        </div>
        <button class="btn btn-primary btn-lg" @click="mergeSelectedChapters" :disabled="saving">
          {{ saving ? '合并中...' : `🔗 合并 ${selectedForMerge.length} 章` }}
        </button>
      </div>
    </main>

    <!-- ========== 页面视图 ========== -->
    <main class="main-content pages-view" v-else-if="viewMode === 'pages'">
      <div class="pages-grid">
        <div v-for="page in pages" :key="page.number" class="page-card">
          <div class="page-header">第 {{ page.number }} 页</div>
          <div class="page-content">{{ page.content }}</div>
          <div class="page-footer">{{ page.content.length }} 字</div>
        </div>
      </div>
    </main>

    <!-- ========== 章节详情弹窗 ========== -->
    <Teleport to="body">
      <div class="chapter-modal-overlay" v-if="expandedChapter" @click.self="closeExpanded">
        <div class="chapter-modal">
          <!-- 弹窗头部 -->
          <div class="modal-header">
            <div class="modal-title">
              <span class="modal-chapter-num">第 {{ expandedChapter.number }} 章</span>
              <input 
                v-if="isEditing"
                type="text" 
                class="title-input" 
                v-model="editingTitle" 
                placeholder="输入章节标题"
              />
              <h2 v-else>{{ expandedChapter.title }}</h2>
            </div>
            <div class="modal-actions">
              <template v-if="!isEditing">
                <button class="btn btn-secondary btn-sm" @click="isEditing = true">✏️ 编辑</button>
                <button class="btn btn-secondary btn-sm" @click="closeExpanded">✕ 关闭</button>
              </template>
              <template v-else>
                <button class="btn btn-primary btn-sm" @click="saveEdit" :disabled="saving">
                  {{ saving ? '保存中...' : '💾 保存' }}
                </button>
                <button class="btn btn-secondary btn-sm" @click="isEditing = false; editingTitle = expandedChapter.title; editingContent = expandedChapter.content">取消</button>
              </template>
            </div>
          </div>

          <!-- 弹窗内容 -->
          <div class="modal-body">
            <div v-if="isEditing" class="edit-area">
              <textarea 
                class="content-textarea" 
                v-model="editingContent" 
                placeholder="输入章节内容"
              ></textarea>
            </div>
            <div v-else class="content-preview">
              {{ expandedChapter.content }}
            </div>
          </div>

          <!-- 弹窗底部 -->
          <div class="modal-footer">
            <span class="word-count">{{ expandedChapter.word_count || (expandedChapter.content || '').length }} 字</span>
            <span class="hint" v-if="expandedChapter.page_range">· 页码 {{ expandedChapter.page_range }}</span>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- ========== 重新分章对话框 ========== -->
    <div class="dialog-overlay" v-if="showReChapterDialog" @click.self="showReChapterDialog = false">
      <div class="dialog">
        <div class="dialog-header">
          <h3>🔄 重新智能分章</h3>
          <button class="close-btn" @click="showReChapterDialog = false">×</button>
        </div>
        <div class="dialog-body">
          <p class="dialog-hint">使用 AI 重新分析书籍内容，自动划分章节结构。</p>
          <label class="checkbox-item">
            <input type="checkbox" v-model="reChapterForceLLM" />
            <span>使用 LLM 智能分析（推荐）</span>
          </label>
          <div class="warning-box">
            ⚠️ 重新分章会覆盖当前章节结构，已生成的文稿和音频将丢失。
          </div>
        </div>
        <div class="dialog-footer">
          <button class="btn btn-secondary" @click="showReChapterDialog = false">取消</button>
          <button class="btn btn-primary" @click="reChapter" :disabled="reChaptering">
            {{ reChaptering ? '处理中...' : '开始重新分章' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* 基础容器 */
.page-container {
  min-height: 100vh;
  background: linear-gradient(180deg, #0a1f15 0%, #061510 100%);
  padding: 20px;
}

/* 头部导航 */
.header {
  display: flex;
  align-items: center;
  gap: 20px;
  padding: 16px 24px;
  background: rgba(0, 40, 25, 0.6);
  border-radius: 16px;
  margin-bottom: 24px;
  backdrop-filter: blur(10px);
}

.back-btn {
  background: rgba(76, 175, 80, 0.15);
  border: 1px solid rgba(76, 175, 80, 0.3);
  color: #81c784;
  padding: 10px 20px;
  border-radius: 10px;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.2s;
}

.back-btn:hover {
  background: rgba(76, 175, 80, 0.25);
  transform: translateX(-2px);
}

.header-info {
  flex: 1;
}

.header-info h1 {
  font-size: 18px;
  color: #e8f5e9;
  margin: 0 0 4px 0;
}

.header-info p {
  font-size: 13px;
  color: #81c784;
  margin: 0;
}

.header-actions {
  display: flex;
  gap: 12px;
  align-items: center;
}

/* 视图切换 */
.view-toggle {
  display: flex;
  background: rgba(0, 30, 20, 0.8);
  border-radius: 10px;
  padding: 4px;
}

.toggle-btn {
  padding: 8px 16px;
  background: transparent;
  border: none;
  color: #81c784;
  cursor: pointer;
  font-size: 13px;
  border-radius: 8px;
  transition: all 0.2s;
}

.toggle-btn:hover {
  background: rgba(76, 175, 80, 0.1);
}

.toggle-btn.active {
  background: rgba(76, 175, 80, 0.3);
  color: #e8f5e9;
}

/* 按钮 */
.btn {
  padding: 10px 20px;
  border-radius: 10px;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
  border: none;
  font-weight: 500;
}

.btn-primary {
  background: linear-gradient(135deg, #4caf50, #2e7d32);
  color: white;
}

.btn-primary:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(76, 175, 80, 0.3);
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  transform: none;
}

.btn-secondary {
  background: rgba(76, 175, 80, 0.15);
  border: 1px solid rgba(76, 175, 80, 0.3);
  color: #81c784;
}

.btn-secondary:hover {
  background: rgba(76, 175, 80, 0.25);
}

.btn-sm {
  padding: 6px 14px;
  font-size: 13px;
}

.btn-lg {
  padding: 14px 28px;
  font-size: 16px;
}

/* 加载状态 */
.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 400px;
  color: #666;
}

.loading-spinner {
  width: 48px;
  height: 48px;
  border: 3px solid rgba(76, 175, 80, 0.2);
  border-top-color: #4caf50;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 16px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* 合并模式提示条 */
.merge-hint-bar {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 12px 20px;
  background: rgba(33, 150, 243, 0.15);
  border: 1px solid rgba(33, 150, 243, 0.3);
  border-radius: 12px;
  margin-bottom: 20px;
  color: #64b5f6;
  font-size: 14px;
}

.merge-hint-text {
  flex: 1;
  font-size: 12px;
  color: #90caf9;
}

/* 章节网格 */
.chapters-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 20px;
}

/* 章节卡片 */
.chapter-card {
  position: relative;
  background: rgba(0, 30, 20, 0.6);
  border: 1px solid rgba(76, 175, 80, 0.2);
  border-radius: 16px;
  padding: 20px;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  overflow: hidden;
}

.chapter-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: linear-gradient(90deg, #4caf50, #81c784);
  opacity: 0;
  transition: opacity 0.3s;
}

.chapter-card:hover {
  transform: translateY(-4px) scale(1.02);
  border-color: rgba(76, 175, 80, 0.5);
  box-shadow: 0 12px 40px rgba(76, 175, 80, 0.15);
}

.chapter-card:hover::before {
  opacity: 1;
}

.chapter-card.expanded {
  border-color: #4caf50;
  box-shadow: 0 8px 32px rgba(76, 175, 80, 0.2);
}

/* 合并模式选中状态 */
.chapter-card.selected-merge {
  border-color: #2196f3;
  background: rgba(33, 150, 243, 0.1);
}

.chapter-card.selected-merge::before {
  background: linear-gradient(90deg, #2196f3, #64b5f6);
  opacity: 1;
}

.merge-check {
  position: absolute;
  top: 16px;
  right: 16px;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: rgba(33, 150, 243, 0.3);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #64b5f6;
  font-size: 14px;
  font-weight: bold;
}

.merge-check-empty {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  border: 2px solid rgba(76, 175, 80, 0.4);
}

.chapter-card.selected-merge .merge-check {
  background: #2196f3;
  color: white;
}

/* 章节卡片内容 */
.chapter-num {
  display: inline-block;
  background: rgba(76, 175, 80, 0.2);
  color: #81c784;
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 600;
  margin-bottom: 12px;
}

.chapter-title {
  font-size: 16px;
  color: #e8f5e9;
  font-weight: 600;
  margin-bottom: 12px;
  line-height: 1.4;
}

.chapter-preview {
  font-size: 13px;
  color: #a5d6a7;
  line-height: 1.7;
  margin-bottom: 16px;
  max-height: 100px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: pre-wrap;
}

.chapter-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 12px;
  border-top: 1px solid rgba(76, 175, 80, 0.15);
}

.word-count {
  font-size: 12px;
  color: #81c784;
  background: rgba(76, 175, 80, 0.1);
  padding: 4px 10px;
  border-radius: 12px;
}

.hint-text {
  font-size: 11px;
  color: #666;
}

/* 合并工具栏 */
.merge-toolbar {
  position: fixed;
  bottom: 24px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  align-items: center;
  gap: 20px;
  padding: 16px 24px;
  background: linear-gradient(135deg, #1a3a2a 0%, #0f2419 100%);
  border: 1px solid rgba(76, 175, 80, 0.3);
  border-radius: 16px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
  z-index: 100;
}

.merge-preview {
  display: flex;
  flex-direction: column;
}

.merge-label {
  font-size: 12px;
  color: #81c784;
}

.merge-chapters {
  font-size: 14px;
  color: #e8f5e9;
  font-weight: 600;
}

/* 页面视图 */
.pages-view {
  background: rgba(0, 40, 25, 0.4);
  border-radius: 16px;
  padding: 24px;
}

.pages-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}

.page-card {
  background: rgba(0, 30, 20, 0.6);
  border: 1px solid rgba(76, 175, 80, 0.2);
  border-radius: 12px;
  overflow: hidden;
  transition: all 0.2s;
}

.page-card:hover {
  border-color: rgba(76, 175, 80, 0.4);
  transform: translateY(-2px);
}

.page-header {
  padding: 12px 16px;
  background: rgba(76, 175, 80, 0.1);
  color: #81c784;
  font-weight: 600;
  font-size: 13px;
}

.page-content {
  padding: 12px 16px;
  font-size: 13px;
  color: #a5d6a7;
  line-height: 1.6;
  max-height: 150px;
  overflow: hidden;
  white-space: pre-wrap;
}

.page-footer {
  padding: 8px 16px;
  font-size: 11px;
  color: #666;
  border-top: 1px solid rgba(76, 175, 80, 0.15);
}

/* 章节详情弹窗 */
.chapter-modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.8);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  animation: fadeIn 0.2s ease;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.chapter-modal {
  width: 90%;
  max-width: 800px;
  max-height: 85vh;
  background: linear-gradient(135deg, #1a3a2a 0%, #0f2419 100%);
  border: 1px solid rgba(76, 175, 80, 0.3);
  border-radius: 20px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  animation: slideUp 0.3s ease;
}

@keyframes slideUp {
  from { 
    opacity: 0;
    transform: translateY(20px);
  }
  to { 
    opacity: 1;
    transform: translateY(0);
  }
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px;
  border-bottom: 1px solid rgba(76, 175, 80, 0.2);
  background: rgba(0, 40, 25, 0.6);
}

.modal-title {
  display: flex;
  align-items: center;
  gap: 12px;
}

.modal-chapter-num {
  background: rgba(76, 175, 80, 0.2);
  color: #81c784;
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 600;
}

.modal-title h2 {
  font-size: 18px;
  color: #e8f5e9;
  margin: 0;
}

.title-input {
  background: rgba(0, 30, 20, 0.6);
  border: 1px solid rgba(76, 175, 80, 0.3);
  border-radius: 8px;
  padding: 8px 16px;
  color: #e8f5e9;
  font-size: 16px;
  width: 400px;
}

.title-input:focus {
  outline: none;
  border-color: #4caf50;
}

.modal-actions {
  display: flex;
  gap: 8px;
}

.modal-body {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
}

.edit-area {
  height: 100%;
}

.content-textarea {
  width: 100%;
  min-height: 400px;
  background: rgba(0, 30, 20, 0.6);
  border: 1px solid rgba(76, 175, 80, 0.3);
  border-radius: 12px;
  padding: 16px;
  color: #e8f5e9;
  font-size: 14px;
  line-height: 1.8;
  resize: none;
}

.content-textarea:focus {
  outline: none;
  border-color: #4caf50;
}

.content-preview {
  font-size: 15px;
  color: #e8f5e9;
  line-height: 1.8;
  white-space: pre-wrap;
}

.modal-footer {
  padding: 12px 24px;
  border-top: 1px solid rgba(76, 175, 80, 0.2);
  font-size: 12px;
  color: #81c784;
}

/* 对话框 */
.dialog-overlay {
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

.dialog {
  width: 90%;
  max-width: 440px;
  background: linear-gradient(135deg, #1a3a2a 0%, #0f2419 100%);
  border: 1px solid rgba(76, 175, 80, 0.3);
  border-radius: 16px;
}

.dialog-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px;
  border-bottom: 1px solid rgba(76, 175, 80, 0.2);
}

.dialog-header h3 {
  color: #81c784;
  margin: 0;
  font-size: 18px;
}

.close-btn {
  background: none;
  border: none;
  color: #81c784;
  font-size: 24px;
  cursor: pointer;
  padding: 0;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
}

.close-btn:hover {
  background: rgba(76, 175, 80, 0.1);
}

.dialog-body {
  padding: 20px;
}

.dialog-hint {
  color: #a5d6a7;
  font-size: 14px;
  margin-bottom: 16px;
}

.checkbox-item {
  display: flex;
  align-items: center;
  gap: 10px;
  color: #e8f5e9;
  cursor: pointer;
  font-size: 14px;
}

.checkbox-item input {
  width: 18px;
  height: 18px;
}

.warning-box {
  background: rgba(255, 152, 0, 0.15);
  border: 1px solid rgba(255, 152, 0, 0.3);
  border-radius: 10px;
  padding: 12px 16px;
  color: #ffb74d;
  font-size: 13px;
  margin-top: 16px;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 16px 20px;
  border-top: 1px solid rgba(76, 175, 80, 0.2);
}

/* 响应式 */
@media (max-width: 768px) {
  .header {
    flex-direction: column;
    gap: 12px;
  }
  
  .header-actions {
    width: 100%;
    flex-wrap: wrap;
    justify-content: center;
  }
  
  .chapters-grid {
    grid-template-columns: 1fr;
  }
  
  .chapter-modal {
    width: 95%;
    max-height: 90vh;
  }
  
  .title-input {
    width: 100%;
  }
  
  .merge-toolbar {
    flex-direction: column;
    width: 90%;
    text-align: center;
  }
}
</style>