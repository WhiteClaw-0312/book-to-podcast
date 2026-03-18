<script setup lang="ts">
import { ref, onMounted, computed, watch, nextTick } from 'vue'
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
const loadingPages = ref(false)

// 当前选中的章节
const currentChapter = ref<Chapter | null>(null)
const editingContent = ref('')
const editingTitle = ref('')

// 视图模式：chapters（章节列表）/ pages（页面列表）
const viewMode = ref<'chapters' | 'pages'>('chapters')
const currentViewPage = ref(1)

// 编辑模式
const isEditing = ref(false)
const editMode = ref<'edit' | 'split'>('edit')

// 拆分设置
const splitPosition = ref(0.5)
const splitFirstTitle = ref('')
const splitSecondTitle = ref('')

// 多选模式（用于合并）
const multiSelectMode = ref(false)
const selectedChapters = ref<number[]>([])

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
    
    // 默认选中第一章
    if (book.value?.chapters.length && !currentChapter.value) {
      await selectChapter(book.value.chapters[0].number)
    }
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
  loadingPages.value = true
  try {
    const res = await apiFetch(`/api/books/${route.params.id}/pages`)
    const data = await res.json()
    pages.value = data.pages || []
  } catch (e) {
    console.error('获取页面失败', e)
    pages.value = []
  } finally {
    loadingPages.value = false
  }
}

// 切换视图模式
const switchViewMode = async (mode: 'chapters' | 'pages') => {
  viewMode.value = mode
  if (mode === 'pages' && pages.value.length === 0) {
    await fetchPages()
  }
}

// 获取章节内容
const selectChapter = async (chapterNum: number) => {
  try {
    const res = await apiFetch(`/api/books/${route.params.id}/chapters/${chapterNum}/content?format=md`)
    const data = await res.json()
    
    currentChapter.value = {
      ...data,
      has_script: false,
      has_audio: false
    }
    
    editingContent.value = data.raw_content || data.content
    editingTitle.value = data.title
    
    // 更新 book 中的章节信息
    if (book.value) {
      const ch = book.value.chapters.find(c => c.number === chapterNum)
      if (ch) {
        ch.content = data.raw_content || data.content
        ch.word_count = data.word_count
      }
    }
    
    isEditing.value = false
  } catch (e) {
    console.error('获取章节内容失败', e)
  }
}

// 保存编辑
const saveEdit = async () => {
  if (!currentChapter.value) return
  
  saving.value = true
  try {
    const res = await apiFetch(`/api/books/${route.params.id}/chapters/${currentChapter.value.number}/content`, {
      method: 'PUT',
      body: JSON.stringify({
        content: editingContent.value,
        title: editingTitle.value
      })
    })
    
    if (res.ok) {
      if (currentChapter.value) {
        currentChapter.value.content = editingContent.value
        currentChapter.value.title = editingTitle.value
        currentChapter.value.word_count = editingContent.value.length
      }
      
      if (book.value) {
        const ch = book.value.chapters.find(c => c.number === currentChapter.value!.number)
        if (ch) {
          ch.title = editingTitle.value
          ch.content = editingContent.value
        }
      }
      
      isEditing.value = false
      alert('保存成功')
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

// 取消编辑
const cancelEdit = () => {
  editingContent.value = currentChapter.value?.content || ''
  editingTitle.value = currentChapter.value?.title || ''
  isEditing.value = false
}

// 拆分章节
const splitChapter = async () => {
  if (!currentChapter.value) return
  
  saving.value = true
  try {
    const res = await apiFetch(`/api/books/${route.params.id}/chapters/${currentChapter.value.number}/split`, {
      method: 'POST',
      body: JSON.stringify({
        position: splitPosition.value,
        first_title: splitFirstTitle.value || `第${currentChapter.value.number}章（上）`,
        second_title: splitSecondTitle.value || `第${currentChapter.value.number}章（下）`
      })
    })
    
    if (res.ok) {
      alert('章节已拆分')
      await fetchBook()
      editMode.value = 'edit'
      splitFirstTitle.value = ''
      splitSecondTitle.value = ''
    } else {
      const err = await res.json()
      throw new Error(err.detail || '拆分失败')
    }
  } catch (e: any) {
    alert('拆分失败: ' + e.message)
  } finally {
    saving.value = false
  }
}

// 多选相关
const toggleChapterSelection = (num: number) => {
  if (selectedChapters.value.includes(num)) {
    selectedChapters.value = selectedChapters.value.filter(n => n !== num)
  } else {
    selectedChapters.value.push(num)
  }
}

const exitMultiSelect = () => {
  multiSelectMode.value = false
  selectedChapters.value = []
}

// 合并章节
const mergeChapters = async () => {
  if (selectedChapters.value.length < 2) {
    alert('请至少选择2个章节')
    return
  }
  
  saving.value = true
  try {
    const res = await apiFetch(`/api/books/${route.params.id}/chapters/merge`, {
      method: 'POST',
      body: JSON.stringify({
        chapters: selectedChapters.value.sort((a, b) => a - b)
      })
    })
    
    if (res.ok) {
      alert('章节已合并')
      exitMultiSelect()
      await fetchBook()
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

// 生成文稿
const goToGenerate = () => {
  router.push(`/book/${route.params.id}`)
}

onMounted(() => {
  user.value = getUser()
  fetchBook()
})

// Markdown 渲染
const renderMarkdown = (text: string): string => {
  if (!text) return ''
  let html = text
  html = html.replace(/^### (.+)$/gm, '<h3>$1</h3>')
  html = html.replace(/^## (.+)$/gm, '<h2>$1</h2>')
  html = html.replace(/^# (.+)$/gm, '<h1>$1</h1>')
  html = html.replace(/^> (.+)$/gm, '<blockquote>$1</blockquote>')
  html = html.replace(/^---$/gm, '<hr>')
  html = html.split('\n\n').map(para => {
    para = para.trim()
    if (!para) return ''
    if (para.startsWith('<h') || para.startsWith('<blockquote') || para.startsWith('<hr')) return para
    return `<p>${para.replace(/\n/g, '<br>')}</p>`
  }).join('\n')
  return html
}
</script>

<template>
  <div class="container">
    <!-- 顶部导航 -->
    <div class="header">
      <div class="header-left">
        <button class="back-btn" @click="goBack">← 返回</button>
        <div class="title-section">
          <h1 class="title">{{ book?.title || '加载中...' }}</h1>
          <p class="subtitle">📄 OCR 解析结果 · {{ book?.total_chapters || 0 }} 个章节 · {{ pages.length || 0 }} 页</p>
        </div>
      </div>
      <div class="header-right">
        <template v-if="!multiSelectMode">
          <!-- 视图切换 -->
          <div class="view-toggle">
            <button 
              :class="['toggle-btn', { active: viewMode === 'chapters' }]"
              @click="switchViewMode('chapters')"
            >📑 章节视图</button>
            <button 
              :class="['toggle-btn', { active: viewMode === 'pages' }]"
              @click="switchViewMode('pages')"
            >📄 页面视图</button>
          </div>
          <button v-if="viewMode === 'chapters'" class="btn btn-secondary" @click="multiSelectMode = true">
            📑 多选合并
          </button>
        </template>
        <template v-else>
          <button class="btn btn-secondary" @click="exitMultiSelect">取消</button>
          <button 
            class="btn btn-primary" 
            @click="mergeChapters"
            :disabled="selectedChapters.length < 2 || saving"
          >
            合并 {{ selectedChapters.length }} 章
          </button>
        </template>
      </div>
    </div>

    <!-- 加载中 -->
    <div class="loading-container" v-if="loading">
      <div class="loading-icon">⏳</div>
      <p>加载中...</p>
    </div>

    <!-- 主内容区 -->
    <div class="main-content" v-else-if="book">
      <!-- ========== 章节视图 ========== -->
      <template v-if="viewMode === 'chapters'">
        <!-- 左侧章节列表 -->
        <div class="chapter-list-panel">
          <div class="panel-header">
            <h2>📚 章节列表 ({{ book.total_chapters }} 章)</h2>
            <button class="btn btn-sm btn-outline" @click="showReChapterDialog = true">
              🔄 重新分章
            </button>
          </div>
          
          <div class="chapter-list">
            <div
              v-for="ch in book.chapters"
              :key="ch.number"
              :class="[
                'chapter-item',
                { active: currentChapter?.number === ch.number },
                { selected: selectedChapters.includes(ch.number) }
              ]"
              @click="multiSelectMode ? toggleChapterSelection(ch.number) : selectChapter(ch.number)"
            >
              <div class="chapter-num">
                <input
                  v-if="multiSelectMode"
                  type="checkbox"
                  :checked="selectedChapters.includes(ch.number)"
                  @click.stop
                  @change="toggleChapterSelection(ch.number)"
                />
                <span>第{{ ch.number }}章</span>
                <span v-if="ch.page_range" class="page-range">📄 {{ ch.page_range }}</span>
              </div>
              <div class="chapter-title">{{ ch.title }}</div>
              <div class="chapter-preview">{{ (ch.content || '').substring(0, 80) }}...</div>
              <div class="chapter-meta">
                <span>{{ (ch.content || '').length }} 字</span>
              </div>
            </div>
          </div>
          
          <div class="panel-footer">
            <button class="btn btn-primary btn-block" @click="goToGenerate">
              ✅ 完成编辑，生成文稿
            </button>
          </div>
        </div>

        <!-- 右侧内容区 -->
        <div class="content-panel" v-if="currentChapter">
          <div class="content-header">
            <div class="chapter-info">
              <h2>{{ currentChapter.title }}</h2>
              <div class="meta">
                <span v-if="currentChapter.page_range">📄 {{ currentChapter.page_range }} 页</span>
                <span>{{ currentChapter.word_count }} 字</span>
              </div>
            </div>
            
            <div class="content-actions">
              <button 
                v-if="!isEditing"
                class="btn btn-primary"
                @click="isEditing = true"
              >✏️ 编辑</button>
              <template v-else>
                <button class="btn btn-secondary" @click="cancelEdit" :disabled="saving">取消</button>
                <button class="btn btn-primary" @click="saveEdit" :disabled="saving">
                  {{ saving ? '保存中...' : '💾 保存' }}
                </button>
              </template>
            </div>
          </div>

          <div class="edit-mode-tabs" v-if="isEditing">
            <button 
              :class="['tab-btn', { active: editMode === 'edit' }]"
              @click="editMode = 'edit'"
            >📝 编辑内容</button>
            <button 
              :class="['tab-btn', { active: editMode === 'split' }]"
              @click="editMode = 'split'"
            >✂️ 拆分章节</button>
          </div>

          <div class="content-body">
            <template v-if="isEditing && editMode === 'edit'">
              <div class="edit-form">
                <div class="form-group">
                  <label>章节标题</label>
                  <input type="text" class="input" v-model="editingTitle" placeholder="输入章节标题" />
                </div>
                <div class="form-group">
                  <label>章节内容</label>
                  <textarea class="textarea content-editor" v-model="editingContent" placeholder="输入章节内容"></textarea>
                </div>
              </div>
            </template>

            <template v-else-if="isEditing && editMode === 'split'">
              <div class="split-form">
                <p class="hint">将当前章节拆分为两个章节</p>
                <div class="form-group">
                  <label>拆分位置</label>
                  <input type="range" min="0.1" max="0.9" step="0.1" v-model="splitPosition" class="range-slider" />
                  <div class="range-labels">
                    <span>开头</span>
                    <span>{{ Math.round(splitPosition * 100) }}%</span>
                    <span>结尾</span>
                  </div>
                </div>
                <div class="form-row">
                  <div class="form-group">
                    <label>上半部分标题</label>
                    <input type="text" class="input" v-model="splitFirstTitle" :placeholder="`第${currentChapter.number}章（上）`" />
                  </div>
                  <div class="form-group">
                    <label>下半部分标题</label>
                    <input type="text" class="input" v-model="splitSecondTitle" :placeholder="`第${currentChapter.number}章（下）`" />
                  </div>
                </div>
                <button class="btn btn-primary" @click="splitChapter" :disabled="saving">
                  {{ saving ? '拆分中...' : '✂️ 确认拆分' }}
                </button>
              </div>
            </template>

            <template v-else>
              <div class="markdown-preview" v-html="renderMarkdown(currentChapter.content)"></div>
            </template>
          </div>
        </div>

        <div class="content-panel empty" v-else>
          <div class="empty-state">
            <div class="empty-icon">📖</div>
            <p>请从左侧选择一个章节查看内容</p>
          </div>
        </div>
      </template>

      <!-- ========== 页面视图 ========== -->
      <template v-else-if="viewMode === 'pages'">
        <div class="pages-view">
          <div class="pages-header">
            <h2>📄 页面列表 ({{ pages.length }} 页)</h2>
            <p class="hint">查看每页解析出的原始内容</p>
          </div>
          
          <div class="pages-loading" v-if="loadingPages">
            <div class="loading-icon">⏳</div>
            <p>加载页面数据...</p>
          </div>
          
          <div class="pages-grid" v-else>
            <div 
              v-for="page in pages" 
              :key="page.number"
              class="page-card"
              @click="currentViewPage = page.number"
            >
              <div class="page-header">
                <span class="page-number">第 {{ page.number }} 页</span>
              </div>
              <div class="page-preview">{{ page.content }}</div>
              <div class="page-footer">{{ page.content.length }} 字</div>
            </div>
          </div>
        </div>
      </template>
    </div>
  </div>

  <!-- 重新分章对话框 -->
  <div v-if="showReChapterDialog" class="modal-overlay" @click.self="showReChapterDialog = false">
    <div class="modal-content">
      <div class="modal-header">
        <h2>🔄 重新智能分章</h2>
        <button class="close-btn" @click="showReChapterDialog = false">×</button>
      </div>
      
      <div class="modal-body">
        <p class="hint">使用 AI 智能分析书籍内容，重新划分章节结构。</p>
        
        <div class="form-group">
          <label class="checkbox-label">
            <input type="checkbox" v-model="reChapterForceLLM" />
            强制使用 LLM 智能分析
          </label>
        </div>
        
        <div class="warning-box">
          ⚠️ 重新分章会删除当前的章节划分，已生成的文稿和音频也会丢失。
        </div>
      </div>
      
      <div class="modal-footer">
        <button class="btn btn-secondary" @click="showReChapterDialog = false">取消</button>
        <button class="btn btn-primary" @click="reChapter" :disabled="reChaptering">
          {{ reChaptering ? '处理中...' : '开始重新分章' }}
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.container { max-width: 1400px; margin: 0 auto; padding: 20px; }

/* 头部 */
.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding: 16px 20px;
  background: rgba(0, 40, 25, 0.6);
  border-radius: 12px;
}
.header-left { display: flex; align-items: center; gap: 16px; }
.back-btn {
  background: rgba(76, 175, 80, 0.2);
  border: 1px solid rgba(76, 175, 80, 0.3);
  color: #81c784;
  padding: 8px 16px;
  border-radius: 8px;
  cursor: pointer;
}
.back-btn:hover { background: rgba(76, 175, 80, 0.3); }
.title-section { display: flex; flex-direction: column; }
.title { font-size: 20px; color: #e8f5e9; margin: 0; }
.subtitle { font-size: 13px; color: #81c784; margin: 4px 0 0 0; }
.header-right { display: flex; gap: 12px; align-items: center; }

/* 视图切换 */
.view-toggle {
  display: flex;
  background: rgba(0, 30, 20, 0.6);
  border-radius: 8px;
  overflow: hidden;
}
.toggle-btn {
  padding: 8px 16px;
  background: transparent;
  border: none;
  color: #81c784;
  cursor: pointer;
  font-size: 13px;
  transition: all 0.2s;
}
.toggle-btn:hover { background: rgba(76, 175, 80, 0.1); }
.toggle-btn.active {
  background: rgba(76, 175, 80, 0.3);
  color: #e8f5e9;
}

/* 主内容区 */
.main-content { min-height: calc(100vh - 140px); }

/* 章节视图布局 */
.main-content:has(.chapter-list-panel) {
  display: grid;
  grid-template-columns: 300px 1fr;
  gap: 20px;
}

/* 左侧章节列表 */
.chapter-list-panel {
  background: rgba(0, 40, 25, 0.6);
  border-radius: 12px;
  display: flex;
  flex-direction: column;
}
.panel-header {
  padding: 16px;
  border-bottom: 1px solid rgba(76, 175, 80, 0.2);
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.panel-header h2 { font-size: 16px; color: #81c784; margin: 0; }
.chapter-list { flex: 1; overflow-y: auto; padding: 8px; max-height: calc(100vh - 280px); }
.chapter-item {
  padding: 12px 16px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  margin-bottom: 4px;
}
.chapter-item:hover { background: rgba(76, 175, 80, 0.1); }
.chapter-item.active { background: rgba(76, 175, 80, 0.2); border-left: 3px solid #4caf50; }
.chapter-item.selected { background: rgba(33, 150, 243, 0.15); border-left: 3px solid #2196f3; }
.chapter-num { display: flex; align-items: center; gap: 8px; font-size: 12px; color: #81c784; margin-bottom: 4px; }
.chapter-num input { width: 16px; height: 16px; }
.page-range { color: #666; font-size: 11px; }
.chapter-title { font-size: 14px; color: #e8f5e9; margin-bottom: 4px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.chapter-preview { font-size: 12px; color: #666; margin-bottom: 4px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.chapter-meta { font-size: 11px; color: #555; }
.panel-footer { padding: 16px; border-top: 1px solid rgba(76, 175, 80, 0.2); }

/* 右侧内容区 */
.content-panel {
  background: rgba(0, 40, 25, 0.6);
  border-radius: 12px;
  display: flex;
  flex-direction: column;
}
.content-panel.empty { display: flex; align-items: center; justify-content: center; }
.empty-state { text-align: center; color: #666; }
.empty-icon { font-size: 48px; margin-bottom: 16px; }
.content-header {
  padding: 16px 20px;
  border-bottom: 1px solid rgba(76, 175, 80, 0.2);
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.chapter-info h2 { font-size: 18px; color: #e8f5e9; margin: 0 0 8px 0; }
.meta { font-size: 12px; color: #81c784; display: flex; gap: 16px; }
.content-actions { display: flex; gap: 8px; }

/* 编辑模式标签 */
.edit-mode-tabs { display: flex; padding: 0 20px; border-bottom: 1px solid rgba(76, 175, 80, 0.2); }
.tab-btn {
  flex: 1;
  padding: 12px;
  background: none;
  border: none;
  color: #81c784;
  font-size: 14px;
  cursor: pointer;
  border-bottom: 2px solid transparent;
}
.tab-btn:hover { background: rgba(76, 175, 80, 0.1); }
.tab-btn.active { border-bottom-color: #4caf50; color: #e8f5e9; }

/* 内容体 */
.content-body { flex: 1; overflow-y: auto; padding: 20px; }

/* Markdown 预览 */
.markdown-preview { color: #e8f5e9; line-height: 1.8; font-size: 15px; }
.markdown-preview :deep(h1) { font-size: 24px; color: #4caf50; margin: 24px 0 16px 0; padding-bottom: 8px; border-bottom: 1px solid rgba(76, 175, 80, 0.3); }
.markdown-preview :deep(h2) { font-size: 20px; color: #81c784; margin: 20px 0 12px 0; }
.markdown-preview :deep(h3) { font-size: 18px; color: #a5d6a7; margin: 16px 0 8px 0; }
.markdown-preview :deep(p) { margin: 0 0 16px 0; text-align: justify; }
.markdown-preview :deep(blockquote) { margin: 16px 0; padding: 12px 16px; background: rgba(76, 175, 80, 0.1); border-left: 3px solid #4caf50; border-radius: 0 8px 8px 0; color: #a5d6a7; }
.markdown-preview :deep(hr) { border: none; height: 1px; background: rgba(76, 175, 80, 0.2); margin: 24px 0; }

/* 表单样式 */
.edit-form, .split-form { max-width: 800px; }
.form-group { margin-bottom: 20px; }
.form-group label { display: block; font-size: 13px; color: #81c784; margin-bottom: 8px; }
.input { width: 100%; padding: 12px 16px; background: rgba(0, 30, 20, 0.6); border: 1px solid rgba(76, 175, 80, 0.3); border-radius: 8px; color: #e8f5e9; font-size: 14px; }
.input:focus { outline: none; border-color: #4caf50; }
.textarea { width: 100%; min-height: 400px; padding: 16px; background: rgba(0, 30, 20, 0.6); border: 1px solid rgba(76, 175, 80, 0.3); border-radius: 8px; color: #e8f5e9; font-size: 14px; font-family: inherit; line-height: 1.6; resize: vertical; }
.textarea:focus { outline: none; border-color: #4caf50; }
.form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.form-hint { font-size: 12px; color: #666; margin-top: 4px; }
.hint { font-size: 13px; color: #81c784; margin-bottom: 16px; }
.range-slider { width: 100%; margin: 8px 0; }
.range-labels { display: flex; justify-content: space-between; font-size: 12px; color: #666; }

/* 按钮 */
.btn { padding: 10px 20px; border-radius: 8px; font-size: 14px; cursor: pointer; transition: all 0.2s; border: none; }
.btn-primary { background: linear-gradient(135deg, #4caf50, #2e7d32); color: white; }
.btn-primary:hover { transform: translateY(-1px); box-shadow: 0 4px 12px rgba(76, 175, 80, 0.3); }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; transform: none; }
.btn-secondary { background: rgba(76, 175, 80, 0.2); border: 1px solid rgba(76, 175, 80, 0.3); color: #81c784; }
.btn-secondary:hover { background: rgba(76, 175, 80, 0.3); }
.btn-outline { background: transparent; border: 1px solid rgba(76, 175, 80, 0.3); color: #81c784; }
.btn-outline:hover { background: rgba(76, 175, 80, 0.1); }
.btn-sm { padding: 6px 12px; font-size: 12px; }
.btn-block { width: 100%; }

/* 页面视图 */
.pages-view { background: rgba(0, 40, 25, 0.6); border-radius: 12px; padding: 20px; }
.pages-header { margin-bottom: 20px; }
.pages-header h2 { color: #81c784; margin: 0 0 8px 0; }
.pages-loading { text-align: center; padding: 60px; color: #666; }
.pages-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 16px; }
.page-card {
  background: rgba(0, 30, 20, 0.6);
  border: 1px solid rgba(76, 175, 80, 0.2);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}
.page-card:hover { border-color: #4caf50; transform: translateY(-2px); }
.page-header { padding: 12px 16px; border-bottom: 1px solid rgba(76, 175, 80, 0.2); }
.page-number { font-size: 14px; font-weight: 600; color: #81c784; }
.page-preview {
  padding: 12px 16px;
  font-size: 13px;
  color: #a5d6a7;
  line-height: 1.6;
  max-height: 150px;
  overflow: hidden;
  white-space: pre-wrap;
}
.page-footer { padding: 8px 16px; font-size: 11px; color: #666; border-top: 1px solid rgba(76, 175, 80, 0.2); }

/* 模态框 */
.modal-overlay { position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0, 0, 0, 0.7); display: flex; align-items: center; justify-content: center; z-index: 1000; }
.modal-content { background: linear-gradient(135deg, #1a3a2a 0%, #0f2419 100%); border: 1px solid rgba(76, 175, 80, 0.3); border-radius: 16px; width: 100%; max-width: 480px; margin: 20px; }
.modal-header { display: flex; justify-content: space-between; align-items: center; padding: 20px; border-bottom: 1px solid rgba(76, 175, 80, 0.2); }
.modal-header h2 { color: #4caf50; margin: 0; font-size: 18px; }
.close-btn { background: none; border: none; color: #81c784; font-size: 28px; cursor: pointer; }
.modal-body { padding: 20px; }
.modal-footer { display: flex; justify-content: flex-end; gap: 12px; padding: 16px 20px; border-top: 1px solid rgba(76, 175, 80, 0.2); }
.warning-box { background: rgba(255, 152, 0, 0.15); border: 1px solid rgba(255, 152, 0, 0.3); border-radius: 8px; padding: 12px; color: #ffb74d; font-size: 13px; margin-top: 16px; }
.checkbox-label { display: flex; align-items: center; gap: 8px; color: #e8f5e9; cursor: pointer; }
.checkbox-label input { width: 18px; height: 18px; }

/* 加载状态 */
.loading-container { display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 400px; color: #666; }
.loading-icon { font-size: 48px; margin-bottom: 16px; }

/* 响应式 */
@media (max-width: 768px) {
  .main-content { display: block !important; }
  .chapter-list-panel { max-height: 300px; margin-bottom: 20px; }
  .form-row { grid-template-columns: 1fr; }
  .header { flex-direction: column; gap: 12px; }
  .header-right { width: 100%; justify-content: space-between; }
}
</style>