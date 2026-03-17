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
const showUploadSuccess = ref(false)
const uploadedBookTitle = ref('')

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

// 示例音频播放器
const demoAudio = ref<HTMLAudioElement | null>(null)
const demoPlaying = ref(false)
const demoProgress = ref(0)
const demoCurrentTime = ref(0)
const demoDuration = ref(425.78)

// 示例字幕（带时间戳，与音频精确对应）
const demoScript = [
  { speaker: '小北', content: '欢迎收听今天的科技播客！阿南，今天我们要聊的这篇论文标题好长啊，什么对称性禁止之类的，听起来很高深呢。', start: 0, end: 10.78 },
  { speaker: '阿南', content: '没错，标题确实有点复杂。其实简单来说，这篇论文讨论的是二维范德华铁磁体中超低吉尔伯特阻尼的现象。', start: 10.78, end: 20.93 },
  { speaker: '小北', content: '哇，二维范德华铁磁体？这听起来像是那种可以像纸一样薄的磁性材料吗？真的存在这种东西？', start: 20.93, end: 29.81 },
  { speaker: '阿南', content: '是的，比如CrI3、Fe3GeTe2这些材料。它们的发现不仅拓宽了磁性材料的视野，还为低维自旋电子学器件带来了希望。', start: 29.81, end: 42.07 },
  { speaker: '小北', content: '诶~ 自旋电子学器件？这跟我们平时用的电子设备有什么关系吗？为什么要特别研究它们的磁性呢？', start: 42.07, end: 51.58 },
  { speaker: '阿南', content: '关系很大。因为二维范德华铁磁体的磁性可以通过栅极电压或应变等独特方式来控制，这比传统材料灵活多了。', start: 51.58, end: 61.94 },
  { speaker: '小北', content: '真的吗？那岂不是可以实现更小巧、更节能的设备？不过论文里提到的吉尔伯特阻尼又是什么呢？', start: 61.94, end: 71.03 },
  { speaker: '阿南', content: '可以说它是磁化动力学中的一个关键参数。它决定了电流诱导磁化翻转的临界电流密度，以及翻转的速度。', start: 71.03, end: 80.97 },
  { speaker: '小北', content: '哇，听起来像是某种阻力？那这个阻尼是越大越好，还是越小越好呢？我有点搞不清楚了。', start: 80.97, end: 89.43 },
  { speaker: '阿南', content: '对于低功耗的存储和逻辑器件来说，低吉尔伯特阻尼是至关重要的。阻尼越低，能量消耗就越少，效率越高。', start: 89.43, end: 99.58 },
  { speaker: '小北', content: '诶~ 原来是这样！那传统的铁磁材料，比如铁、钴、镍，它们的阻尼表现怎么样呢？有没有什么局限？', start: 99.58, end: 109.3 },
  { speaker: '阿南', content: '传统材料的阻尼随温度变化是非单调的。低温下像电导率，高温下像电阻率，这限制了阻尼不能低于某个下限。', start: 109.3, end: 119.66 },
  { speaker: '小北', content: '真的吗？也就是说传统材料不管怎么优化，阻尼都有一个最低限度，没法无限降低咯？', start: 119.66, end: 127.69 },
  { speaker: '阿南', content: '没错。但这篇论文研究的二维铁磁金属，比如Fe3GaTe2，却表现出了单调的温度依赖性，这是一个非常不寻常的现象。', start: 127.69, end: 139.53 },
  { speaker: '小北', content: '哇，单调依赖性？这意味着什么？是不是说随着温度变化，它的阻尼表现跟传统材料完全不一样？', start: 139.53, end: 148.62 },
  { speaker: '阿南', content: '是的。研究发现，在低温下，由于镜像对称性禁止了带内跃迁，导致阻尼变得超低，甚至理论上没有下限。', start: 148.62, end: 158.56 },
  { speaker: '小北', content: '诶~ 镜像对称性禁止带内跃迁？这听起来好抽象，对称性怎么还能禁止电子的跃迁呢？真的吗？', start: 158.56, end: 167.65 },
  { speaker: '阿南', content: '其实可以理解为一种量子力学的选择定则。在这种对称性保护下，电子在某些能带之间的跳转被规则禁止了。', start: 167.65, end: 177.8 },
  { speaker: '小北', content: '哇，就像是一条交通规则，告诉电子这条路不能走？那这样的话，能量损耗自然就变小了？', start: 177.8, end: 186.25 },
  { speaker: '阿南', content: '没错，正是这个原因。因为带内跃迁被禁止，导电类的阻尼消失了，所以阻尼可以随着电子散射率的降低而任意减小。', start: 186.25, end: 197.25 },
  { speaker: '小北', content: '真的吗？那如果我想增加阻尼怎么办？毕竟有时候可能需要不同的性能，这个能调控吗？', start: 197.25, end: 205.49 },
  { speaker: '阿南', content: '当然可以。通过磁化旋转、层堆叠或结构相变来打破镜像对称性，就能显著增加阻尼，因为这时带内跃迁被允许了。', start: 205.49, end: 216.27 },
  { speaker: '小北', content: '诶~ 这调控手段也太丰富了吧！那论文里还提到了拓扑节点线，这个又是对阻尼有什么影响呢？', start: 216.27, end: 225.37 },
  { speaker: '阿南', content: '拓扑节点线也是受镜像对称性保护的。它们主要贡献于带间跃迁介导的阻尼，这部分可以通过调节费米能级来调控。', start: 225.37, end: 236.15 },
  { speaker: '小北', content: '哇，调节费米能级就能改变阻尼？这感觉像是在调收音机一样，能找到最佳的信号点？', start: 236.15, end: 245.66 },
  { speaker: '阿南', content: '比喻很恰当。这些发现阐明了二维范德华铁磁体中吉尔伯特阻尼的独特特性，为设计高能效率器件提供了见解。', start: 245.66, end: 256.02 },
  { speaker: '小北', content: '真的吗？那这些结论是只适用于Fe3GaTe2这一种材料，还是其他类似的材料也适用呢？', start: 256.02, end: 264.9 },
  { speaker: '阿南', content: '这些独特特征通常适用于其他具有镜像对称性的二维范德华材料，比如Fe3GeTe2和2H-FeTe2，通用性很强。', start: 264.9, end: 276.53 },
  { speaker: '小北', content: '诶~ 那研究者是用什么方法得出这些结论的呢？是做了实验还是纯理论计算？', start: 276.53, end: 286.04 },
  { speaker: '阿南', content: '这篇论文主要是基于第一性原理计算。他们利用了力矩关联模型来计算二维范德华铁磁体的吉尔伯特阻尼。', start: 286.04, end: 295.98 },
  { speaker: '小北', content: '哇，第一性原理计算，听起来就是那种从量子力学基本方程出发的硬核计算吧？难度很大吗？', start: 295.98, end: 304.64 },
  { speaker: '阿南', content: '确实不小。这个模型捕捉了由于自旋轨道耦合导致的磁化动态耗散，这是内在吉尔伯特阻尼的主要贡献来源。', start: 304.64, end: 314.79 },
  { speaker: '小北', content: '真的吗？自旋轨道耦合我之前听说过，好像是电子自旋和轨道运动之间的相互作用？', start: 314.79, end: 322.61 },
  { speaker: '阿南', content: '没错。公式里包含了很多项，比如朗德因子、玻尔磁子，还有费米-狄拉克分布的能量导数。', start: 322.61, end: 334.88 },
  { speaker: '小北', content: '诶~ 虽然公式听不懂，但大概明白了，就是重点研究费米面附近的电子状态对阻尼的影响对吧？', start: 334.88, end: 343.97 },
  { speaker: '阿南', content: '可以说就是这样。矩阵元素表征了源自自旋轨道耦合的电子自旋力矩，这是计算阻尼的核心物理量。', start: 343.97, end: 353.27 },
  { speaker: '小北', content: '哇，感觉这篇论文不仅理论扎实，而且应用前景也很广阔啊。未来我们的手机会不会用上这种材料？', start: 353.27, end: 362.57 },
  { speaker: '阿南', content: '很有希望。特别是Fe3GaTe2的居里温度高于室温，是集成到磁性异质结的理想候选者。', start: 362.57, end: 375.05 },
  { speaker: '小北', content: '真的吗？高于室温太关键了！不然还要专门冷却的话，普通消费者根本没法用啊。', start: 375.05, end: 382.66 },
  { speaker: '阿南', content: '没错。所以这项研究对于设计基于二维范德华铁磁材料的高性能、低功耗自旋电子器件至关重要。', start: 382.66, end: 391.75 },
  { speaker: '小北', content: '诶~ 听你这么一总结，我感觉这篇论文的核心价值就在于发现了超低阻尼的机制和调控方法对吧？', start: 391.75, end: 401.05 },
  { speaker: '阿南', content: '总结得很到位。它揭示了低维结构导致的非典型磁化弛豫，打破了传统材料阻尼下限的限制。', start: 401.05, end: 409.72 },
  { speaker: '小北', content: '哇，今天的干货真多！虽然物理概念有点难，但感觉打开了新世界的大门，谢谢阿南的讲解！', start: 409.72, end: 418.38 },
  { speaker: '阿南', content: '不客气。希望听众朋友们能从中感受到凝聚态物理的魅力，我们下期节目再见。', start: 418.38, end: 425.78 },
]
const demoCurrentLine = ref(-1)
const subtitleContainer = ref<HTMLElement | null>(null)

// 根据时间计算当前字幕行（使用时间戳精确匹配）
const calculateCurrentLine = (time: number) => {
  for (let i = 0; i < demoScript.length; i++) {
    if (time >= demoScript[i].start && time < demoScript[i].end) {
      return i
    }
  }
  return -1
}

// 根据字幕行获取开始时间
const getTimeForLine = (lineIndex: number) => {
  if (lineIndex >= 0 && lineIndex < demoScript.length) {
    return demoScript[lineIndex].start
  }
  return 0
}

const toggleDemoAudio = () => {
  if (!demoAudio.value) {
    demoAudio.value = new Audio('http://139.196.211.206/audio/demo_chapter_1.mp3')
    demoAudio.value.onloadedmetadata = () => {
      demoDuration.value = demoAudio.value?.duration || 425.78
    }
    demoAudio.value.ontimeupdate = () => {
      if (demoAudio.value) {
        demoCurrentTime.value = demoAudio.value.currentTime
        demoProgress.value = (demoAudio.value.currentTime / demoDuration.value) * 100
        // 更新当前字幕行
        const newLine = calculateCurrentLine(demoAudio.value.currentTime)
        if (newLine !== demoCurrentLine.value) {
          demoCurrentLine.value = newLine
          scrollToCurrentLine(newLine)
        }
      }
    }
    demoAudio.value.onended = () => {
      demoPlaying.value = false
      demoProgress.value = 0
      demoCurrentTime.value = 0
      demoCurrentLine.value = -1
    }
  }
  
  if (demoPlaying.value) {
    demoAudio.value.pause()
    demoPlaying.value = false
  } else {
    demoAudio.value.play()
    demoPlaying.value = true
  }
}

// 点击字幕跳转
const jumpToLine = (lineIndex: number) => {
  if (!demoAudio.value) return
  const time = getTimeForLine(lineIndex)
  demoAudio.value.currentTime = time
  demoCurrentLine.value = lineIndex
  if (!demoPlaying.value) {
    demoAudio.value.play()
    demoPlaying.value = true
  }
}

// 滚动到当前字幕
const scrollToCurrentLine = (lineIndex: number) => {
  if (!subtitleContainer.value) return
  const items = subtitleContainer.value.querySelectorAll('.demo-line')
  if (items[lineIndex]) {
    items[lineIndex].scrollIntoView({ behavior: 'smooth', block: 'center' })
  }
}

const seekDemoAudio = (e: MouseEvent) => {
  if (!demoAudio.value) return
  const target = e.currentTarget as HTMLElement
  const rect = target.getBoundingClientRect()
  const percent = (e.clientX - rect.left) / rect.width
  const time = percent * demoDuration.value
  demoAudio.value.currentTime = time
  demoCurrentLine.value = calculateCurrentLine(time)
}

// 新手引导
const showGuide = ref(false)
const guideStep = ref(0)
const guideDismissed = ref(false)

const checkFirstVisit = () => {
  const visited = localStorage.getItem('zhenbianshu_visited')
  if (!visited && !user.value) {
    showGuide.value = true
    localStorage.setItem('zhenbianshu_visited', 'true')
  }
}

const nextGuideStep = () => {
  if (guideStep.value < 2) {
    guideStep.value++
  } else {
    dismissGuide()
  }
}

const dismissGuide = () => {
  showGuide.value = false
  guideDismissed.value = true
}
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
    uploadedBookTitle.value = data.title || file.value?.name || '书籍'
    uploadProgress.value = ''
    file.value = null
    
    // 刷新队列并跳转到第一页
    await fetchQueue()
    currentPage.value = 1
    
    // 显示成功提示
    showUploadSuccess.value = true
    setTimeout(() => {
      showUploadSuccess.value = false
    }, 3000)
    
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
    
    // 只在任务完成时更新书籍详情和队列
    if (data.queue?.status === 'completed' || data.book_status === 'script_ready' || data.book_status === 'completed') {
      stopPolling()
      // 延迟刷新，让用户看到完成状态
      setTimeout(async () => {
        await fetchBookDetail()
        await fetchQueue()
      }, 500)
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
  pollingTimer.value = setInterval(fetchProgress, 3000) // 改为3秒
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

// 生成单个章节音频
const pendingChapterNum = ref<number | null>(null)

const generateSingleChapterAudio = (bookId: string, chapterNum: number) => {
  selectedChapters.value = [chapterNum]
  pendingChapterNum.value = chapterNum
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

// 查看文稿
const viewScript = (bookId: string, chapterNum: number) => {
  // 跳转到文稿编辑页面
  window.location.href = `/book/${bookId}/script?chapter=${chapterNum}`
}

// 播放章节音频
const playingChapter = ref<any>(null)
const showAudioPlayer = ref(false)
const audioPlayerRef = ref<HTMLAudioElement | null>(null)
const playerCurrentTime = ref(0)
const playerDuration = ref(0)
const playerScript = ref<any[]>([])
const playerCurrentLine = ref(0)

const playChapterAudio = async (bookId: string, chapter: any) => {
  playingChapter.value = chapter
  showAudioPlayer.value = true
  
  // 获取文稿
  try {
    const res = await apiFetch(`/api/books/${bookId}/chapters/${chapter.number}/script`)
    if (res.ok) {
      const data = await res.json()
      playerScript.value = data.dialogues || []
    }
  } catch (e) {
    playerScript.value = []
  }
}

const closeAudioPlayer = () => {
  if (audioPlayerRef.value) {
    audioPlayerRef.value.pause()
  }
  showAudioPlayer.value = false
  playingChapter.value = null
  playerScript.value = []
  playerCurrentLine.value = 0
}

const onPlayerTimeUpdate = () => {
  if (!audioPlayerRef.value || !playerScript.value.length) return
  playerCurrentTime.value = audioPlayerRef.value.currentTime
  const lineDuration = playerDuration.value / playerScript.value.length
  playerCurrentLine.value = Math.min(
    Math.floor(audioPlayerRef.value.currentTime / lineDuration),
    playerScript.value.length - 1
  )
}

const seekPlayer = (e: MouseEvent) => {
  if (!audioPlayerRef.value) return
  const target = e.currentTarget as HTMLElement
  const rect = target.getBoundingClientRect()
  const percent = (e.clientX - rect.left) / rect.width
  audioPlayerRef.value.currentTime = percent * playerDuration.value
}

// 刷新书籍状态
const refreshBookStatus = async (bookId: string) => {
  await fetchBookDetail()
  await fetchQueue()
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
  checkFirstVisit()
  setInterval(checkBackend, 30000)
})

onUnmounted(() => {
  stopPolling()
  if (previewAudio.value) {
    previewAudio.value.pause()
  }
  if (demoAudio.value) {
    demoAudio.value.pause()
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

    <!-- 生成队列 -->
    <div class="card queue-card" v-if="user">
      <div class="queue-header">
        <h2 class="card-title">📋 生成队列</h2>
        <span class="queue-count" v-if="queueBooks.length > 0">共 {{ queueBooks.length }} 个任务</span>
      </div>
      
      <!-- 上传成功提示 -->
      <div v-if="showUploadSuccess" class="upload-success-toast">
        <span class="toast-icon">✅</span>
        <span class="toast-text">《{{ uploadedBookTitle }}》已加入生成队列</span>
      </div>
      
      <!-- 加载中 -->
      <div v-if="loadingQueue" class="queue-loading">
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
            
            <!-- 文稿就绪，可以查看文稿或生成音频 -->
            <div v-else-if="book.status === 'script_ready' || book.status === 'partial'" class="action-section">
              <p class="action-hint">文稿已就绪，查看或生成音频</p>
              <div class="chapter-list-detail">
                <div v-for="ch in selectedBook?.chapters || []" :key="ch.number" class="chapter-row">
                  <div class="chapter-info">
                    <span class="chapter-num">第{{ ch.number }}章</span>
                    <span class="chapter-title">{{ ch.title }}</span>
                  </div>
                  <div class="chapter-actions-row">
                    <button class="btn-small" @click="viewScript(book.id, ch.number)">📝 查看</button>
                    <template v-if="ch.has_audio">
                      <span class="has-audio">✅ {{ formatTime(ch.duration) }}</span>
                    </template>
                    <template v-else>
                      <button class="btn-small primary" @click="generateSingleChapterAudio(book.id, ch.number)">🎙️ 生成</button>
                    </template>
                  </div>
                </div>
              </div>
            </div>
            
            <!-- 已完成 -->
            <div v-else-if="book.status === 'completed'" class="completed-section">
              <p class="completed-hint">🎉 所有章节已完成</p>
              <div class="chapter-list-detail">
                <div v-for="ch in selectedBook?.chapters || []" :key="ch.number" class="chapter-row">
                  <div class="chapter-info">
                    <span class="chapter-num">第{{ ch.number }}章</span>
                    <span class="chapter-title">{{ ch.title }}</span>
                  </div>
                  <div class="chapter-actions-row">
                    <button class="btn-small" @click="viewScript(book.id, ch.number)">📝 文稿</button>
                    <button class="btn-small primary" @click="playChapterAudio(book.id, ch)">🎧 播放</button>
                  </div>
                </div>
              </div>
            </div>
            
            <!-- 其他状态（pending等） -->
            <div v-else class="other-status-section">
              <p class="status-hint">
                <template v-if="book.status === 'pending'">⏳ 正在识别文档...</template>
                <template v-else-if="book.status === 'processing'">⏳ 处理中...</template>
                <template v-else>状态: {{ book.status }}</template>
              </p>
              <button class="btn btn-secondary" @click="refreshBookStatus(book.id)">刷新状态</button>
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

    <!-- 示例作品 -->
    <div class="card demo-card">
      <h2 class="card-title">🎧 听听效果</h2>
      <p class="demo-subtitle">这是 AI 生成的播客示例，感受一下效果</p>
      <div class="demo-player">
        <div class="demo-info">
          <span class="demo-book">📖 试听文件</span>
          <span class="demo-duration">7分06秒</span>
        </div>
        
        <!-- 音频控制 -->
        <div class="demo-controls">
          <button class="demo-play-btn" @click="toggleDemoAudio">
            {{ demoPlaying ? '⏸️' : '▶️' }}
          </button>
          <div class="demo-progress" @click="seekDemoAudio">
            <div class="demo-progress-fill" :style="{ width: demoProgress + '%' }"></div>
          </div>
          <span class="demo-time">{{ formatTime(demoCurrentTime) }} / {{ formatTime(demoDuration) }}</span>
        </div>
        
        <!-- 字幕显示（在音频下方） -->
        <div class="demo-subtitle-box" ref="subtitleContainer">
          <div 
            v-for="(line, idx) in demoScript" 
            :key="idx"
            :class="['demo-line', { active: idx === demoCurrentLine }]"
            @click="jumpToLine(idx)"
          >
            <span :class="['speaker-tag', line.speaker === '小北' ? 'female' : 'male']">{{ line.speaker }}</span>
            <span class="line-content">{{ line.content }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 功能介绍 -->
    <div class="card features-card">
      <h2 class="card-title">✨ 为什么选择我们</h2>
      <div class="features-simple">
        <div class="feature-simple-item">
          <span class="feature-simple-icon">🎙️</span>
          <div class="feature-simple-content">
            <h3>AI 双人播客</h3>
            <p>自动生成主持人对话，像听节目一样听书</p>
          </div>
        </div>
        <div class="feature-simple-item">
          <span class="feature-simple-icon">⚡</span>
          <div class="feature-simple-content">
            <h3>一键生成</h3>
            <p>上传 PDF/文本，自动识别章节并转换</p>
          </div>
        </div>
        <div class="feature-simple-item">
          <span class="feature-simple-icon">🎭</span>
          <div class="feature-simple-content">
            <h3>多音色可选</h3>
            <p>男女主持人多种音色，自由搭配</p>
          </div>
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
    
    <!-- 新手引导 -->
    <div v-if="showGuide && !guideDismissed" class="guide-overlay" @click.self="dismissGuide">
      <div class="guide-content" :class="'guide-step-' + guideStep">
        <div class="guide-arrow" v-if="guideStep === 0">👆</div>
        <div class="guide-text">
          <template v-if="guideStep === 0">
            <h3>👋 欢迎来到枕边书</h3>
            <p>上传一本 PDF 或文本文件，AI 将自动转换成播客</p>
          </template>
          <template v-else-if="guideStep === 1">
            <h3>🎧 先听听效果</h3>
            <p>下方有示例播客，点击播放感受一下</p>
          </template>
          <template v-else>
            <h3>🎁 新用户福利</h3>
            <p>注册即送 <strong>3次</strong> 免费体验额度</p>
          </template>
        </div>
        <div class="guide-actions">
          <button class="guide-skip" @click="dismissGuide">跳过</button>
          <button class="guide-next" @click="nextGuideStep">
            {{ guideStep < 2 ? '下一步' : '开始使用' }}
          </button>
        </div>
      </div>
    </div>
    
    <!-- 音频播放器弹窗 -->
    <div v-if="showAudioPlayer" class="modal-overlay" @click.self="closeAudioPlayer">
      <div class="modal-content audio-player-modal">
        <div class="modal-header">
          <h2>🎧 {{ playingChapter?.title || '播放音频' }}</h2>
          <button class="close-btn" @click="closeAudioPlayer">×</button>
        </div>
        
        <div class="player-body">
          <!-- 字幕区域 -->
          <div class="player-script" v-if="playerScript.length > 0">
            <div 
              v-for="(line, idx) in playerScript" 
              :key="idx"
              :class="['script-line', { active: idx === playerCurrentLine }]"
            >
              <span :class="['speaker-tag', line.speaker === '小北' ? 'female' : 'male']">{{ line.speaker }}</span>
              <span class="script-content">{{ line.content }}</span>
            </div>
          </div>
          
          <!-- 控制区域 -->
          <div class="player-controls-bottom">
            <audio 
              ref="audioPlayerRef"
              :src="`/api/books/${selectedBookId}/chapters/${playingChapter?.number}/audio`"
              @loadedmetadata="playerDuration = audioPlayerRef?.duration || 0"
              @timeupdate="onPlayerTimeUpdate"
              @ended="closeAudioPlayer"
              autoplay
            />
            <div class="player-progress" @click="seekPlayer">
              <div class="player-progress-fill" :style="{ width: (playerCurrentTime / playerDuration * 100) + '%' }"></div>
            </div>
            <div class="player-time-row">
              <span>{{ formatTime(playerCurrentTime) }}</span>
              <span>{{ formatTime(playerDuration) }}</span>
            </div>
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

.queue-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.queue-header .card-title {
  margin-bottom: 0;
}

.queue-count {
  font-size: 12px;
  color: #81c784;
  background: rgba(76, 175, 80, 0.1);
  padding: 4px 10px;
  border-radius: 12px;
}

.upload-success-toast {
  display: flex;
  align-items: center;
  gap: 10px;
  background: linear-gradient(135deg, rgba(76, 175, 80, 0.2), rgba(46, 125, 50, 0.1));
  border: 1px solid rgba(76, 175, 80, 0.4);
  border-radius: 10px;
  padding: 12px 16px;
  margin-bottom: 16px;
  animation: slideIn 0.3s ease;
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.toast-icon {
  font-size: 18px;
}

.toast-text {
  color: #a5d6a7;
  font-size: 14px;
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

/* Demo player */
.demo-card {
  margin-top: 20px;
}

.demo-subtitle {
  color: #81c784;
  font-size: 13px;
  margin-bottom: 16px;
}

.demo-player {
  background: rgba(0, 30, 20, 0.4);
  border-radius: 12px;
  padding: 16px;
}

.demo-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.demo-book {
  color: #e8f5e9;
  font-size: 14px;
  font-weight: 500;
}

.demo-duration {
  color: #81c784;
  font-size: 12px;
}

.demo-controls {
  display: flex;
  align-items: center;
  gap: 12px;
}

.demo-play-btn {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: linear-gradient(135deg, #4caf50, #2e7d32);
  border: none;
  font-size: 16px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: transform 0.2s;
}

.demo-play-btn:hover {
  transform: scale(1.1);
}

.demo-progress {
  flex: 1;
  height: 6px;
  background: rgba(76, 175, 80, 0.2);
  border-radius: 3px;
  cursor: pointer;
  overflow: hidden;
}

.demo-progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #4caf50, #81c784);
  border-radius: 3px;
  transition: width 0.1s;
}

.demo-time {
  color: #81c784;
  font-size: 12px;
  min-width: 80px;
}

.demo-desc {
  color: #666;
  font-size: 12px;
  margin: 12px 0 0 0;
}

/* Simplified features */
.features-simple {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.feature-simple-item {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  padding: 16px;
  background: rgba(0, 30, 20, 0.4);
  border-radius: 12px;
  transition: all 0.3s;
}

.feature-simple-item:hover {
  background: rgba(76, 175, 80, 0.1);
}

.feature-simple-icon {
  font-size: 28px;
  flex-shrink: 0;
}

.feature-simple-content h3 {
  color: #e8f5e9;
  font-size: 15px;
  margin: 0 0 4px 0;
}

.feature-simple-content p {
  color: #81c784;
  font-size: 13px;
  margin: 0;
}

/* Guide overlay */
.guide-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.85);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
}

.guide-content {
  background: linear-gradient(135deg, #1a3a2a 0%, #0f2419 100%);
  border: 1px solid rgba(76, 175, 80, 0.4);
  border-radius: 16px;
  padding: 32px;
  max-width: 400px;
  text-align: center;
  animation: guideIn 0.3s ease;
}

@keyframes guideIn {
  from {
    opacity: 0;
    transform: scale(0.9);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}

.guide-arrow {
  font-size: 40px;
  margin-bottom: 16px;
  animation: bounce 1s infinite;
}

@keyframes bounce {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-10px); }
}

.guide-text h3 {
  color: #4caf50;
  font-size: 22px;
  margin: 0 0 12px 0;
}

.guide-text p {
  color: #a5d6a7;
  font-size: 15px;
  margin: 0;
  line-height: 1.6;
}

.guide-text strong {
  color: #4caf50;
}

.guide-actions {
  display: flex;
  justify-content: center;
  gap: 16px;
  margin-top: 24px;
}

.guide-skip {
  background: none;
  border: 1px solid rgba(76, 175, 80, 0.3);
  color: #81c784;
  padding: 10px 24px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
}

.guide-next {
  background: linear-gradient(135deg, #4caf50, #2e7d32);
  border: none;
  color: white;
  padding: 10px 24px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 600;
}

/* Demo subtitle box */
.demo-subtitle-box {
  max-height: 150px;
  overflow-y: auto;
  margin-top: 12px;
  padding: 8px;
  background: rgba(0, 20, 15, 0.6);
  border-radius: 8px;
}

.demo-line {
  padding: 6px 10px;
  margin-bottom: 2px;
  border-radius: 6px;
  font-size: 12px;
  line-height: 1.4;
  cursor: pointer;
  transition: all 0.2s;
  border: 1px solid transparent;
}

.demo-line:hover {
  background: rgba(76, 175, 80, 0.1);
}

.demo-line.active {
  background: rgba(76, 175, 80, 0.25);
  border-color: rgba(76, 175, 80, 0.4);
}

.demo-loading {
  text-align: center;
  color: #81c784;
  padding: 20px;
  font-size: 13px;
}

.speaker-tag {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 11px;
  font-weight: 600;
  margin-right: 8px;
}

.speaker-tag.female {
  background: rgba(233, 30, 99, 0.3);
  color: #f48fb1;
}

.speaker-tag.male {
  background: rgba(33, 150, 243, 0.3);
  color: #81d4fa;
}

.line-content {
  color: #e8f5e9;
}

/* Chapter actions row */
.chapter-actions-row {
  display: flex;
  gap: 8px;
  align-items: center;
}

.check-text {
  font-size: 12px;
  color: #81c784;
  margin-left: 4px;
}

.btn-small.primary {
  background: rgba(76, 175, 80, 0.3);
  border-color: #4caf50;
  color: #a5d6a7;
}

/* Audio player modal */
.audio-player-modal {
  max-width: 500px;
  max-height: 80vh;
}

.player-body {
  padding: 0;
}

.player-script {
  max-height: 300px;
  overflow-y: auto;
  padding: 16px;
  background: rgba(0, 20, 15, 0.4);
}

.script-line {
  padding: 10px 12px;
  margin-bottom: 6px;
  border-radius: 8px;
  font-size: 13px;
  line-height: 1.5;
  transition: all 0.3s;
}

.script-line.active {
  background: rgba(76, 175, 80, 0.2);
  transform: translateX(4px);
}

.script-content {
  color: #e8f5e9;
}

.player-controls-bottom {
  padding: 16px;
  border-top: 1px solid rgba(76, 175, 80, 0.2);
}

.player-progress {
  height: 6px;
  background: rgba(76, 175, 80, 0.2);
  border-radius: 3px;
  cursor: pointer;
  margin-bottom: 8px;
}

.player-progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #4caf50, #81c784);
  border-radius: 3px;
}

.player-time-row {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: #81c784;
}

/* Other status section */
.other-status-section {
  padding: 20px;
  text-align: center;
}

.status-hint {
  color: #ffb74d;
  font-size: 14px;
  margin-bottom: 12px;
}

@media (max-width: 600px) {
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
  
  .demo-controls {
    flex-wrap: wrap;
  }
  
  .demo-time {
    order: 3;
    width: 100%;
    text-align: center;
    margin-top: 8px;
  }
}
</style>