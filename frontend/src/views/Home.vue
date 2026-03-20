<script setup lang="ts">
import { ref, onMounted, computed, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { apiFetch } from '../api'
import AuthModal from '../components/AuthModal.vue'

const router = useRouter()

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
    // 使用静态 demo 音频
    demoAudio.value = new Audio('/demo/chapter_01.mp3')
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
    
    // 模拟上传进度提示
    const progressTimer = setInterval(() => {
      if (uploadProgress.value === '上传中...') {
        uploadProgress.value = '上传中...'
      }
    }, 500)
    
    const res = await apiFetch('/api/books', {
      method: 'POST',
      body: form,
      headers: token ? { 'Authorization': `Bearer ${token}` } : {}
    })
    
    clearInterval(progressTimer)
    
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
    
    // 显示OCR识别提示
    uploadProgress.value = 'OCR识别中...'
    
    uploadedBookTitle.value = data.title || file.value?.name || '书籍'
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
    
    uploadProgress.value = ''
    
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

// 查看 OCR 解析结果
const viewOcrResult = (bookId: string) => {
  router.push(`/book/${bookId}/chapters`)
}

// 跳转到书籍详情页
const goToBookDetail = (bookId: string) => {
  router.push(`/book/${bookId}`)
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
      // 立即更新书籍状态为生成中
      if (selectedBook.value) {
        selectedBook.value.status = 'generating_script'
      }
      // 立即刷新队列显示
      await fetchQueue()
      // 开始轮询进度
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
      pendingChapterNum.value = null
      // 立即更新书籍状态为生成中
      if (selectedBook.value) {
        selectedBook.value.status = 'generating_audio'
      }
      // 立即刷新队列显示
      await fetchQueue()
      // 开始轮询进度
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
const playerScriptWithTime = ref<any[]>([]) // 带时间戳的字幕
const playerCurrentLine = ref(0)

// 计算带时间戳的字幕
const calculateScriptTimestamps = (dialogues: any[], totalDuration: number) => {
  if (!dialogues.length) return []
  
  // 计算总字符数
  const totalChars = dialogues.reduce((sum, d) => sum + (d.content?.length || 0), 0)
  if (totalChars === 0) return dialogues.map((d, i) => ({ ...d, start: 0, end: totalDuration }))
  
  // 根据字符数分配时间
  let currentTime = 0
  return dialogues.map(d => {
    const charRatio = (d.content?.length || 0) / totalChars
    const duration = charRatio * totalDuration
    const result = {
      ...d,
      start: currentTime,
      end: currentTime + duration
    }
    currentTime += duration
    return result
  })
}

// 根据时间查找当前字幕行
const findCurrentLine = (time: number) => {
  if (!playerScriptWithTime.value.length) return -1
  for (let i = 0; i < playerScriptWithTime.value.length; i++) {
    const line = playerScriptWithTime.value[i]
    if (time >= line.start && time < line.end) {
      return i
    }
  }
  return playerScriptWithTime.value.length - 1
}

// 根据字幕行获取开始时间
const getTimeForPlayerLine = (lineIndex: number) => {
  if (lineIndex >= 0 && lineIndex < playerScriptWithTime.value.length) {
    return playerScriptWithTime.value[lineIndex].start
  }
  return 0
}

const playChapterAudio = async (bookId: string, chapter: any) => {
  playingChapter.value = chapter
  showAudioPlayer.value = true
  
  // 获取文稿
  try {
    const res = await apiFetch(`/api/books/${bookId}/chapters/${chapter.number}/script`)
    if (res.ok) {
      const data = await res.json()
      playerScript.value = data.dialogues || []
      // 先用预估时长初始化，音频加载后会更新
      playerScriptWithTime.value = calculateScriptTimestamps(playerScript.value, chapter.duration || 180)
    }
  } catch (e) {
    playerScript.value = []
    playerScriptWithTime.value = []
  }
}

const closeAudioPlayer = () => {
  if (audioPlayerRef.value) {
    audioPlayerRef.value.pause()
  }
  showAudioPlayer.value = false
  playingChapter.value = null
  playerScript.value = []
  playerScriptWithTime.value = []
  playerCurrentLine.value = 0
}

const onPlayerTimeUpdate = () => {
  if (!audioPlayerRef.value || !playerScriptWithTime.value.length) return
  playerCurrentTime.value = audioPlayerRef.value.currentTime
  
  // 使用精确时间匹配
  const newLine = findCurrentLine(audioPlayerRef.value.currentTime)
  if (newLine !== playerCurrentLine.value) {
    playerCurrentLine.value = newLine
    scrollToPlayerLine(newLine)
  }
}

// 滚动到当前字幕
const playerScriptContainer = ref<HTMLElement | null>(null)
const scrollToPlayerLine = (lineIndex: number) => {
  if (!playerScriptContainer.value) return
  const items = playerScriptContainer.value.querySelectorAll('.script-line')
  if (items[lineIndex]) {
    items[lineIndex].scrollIntoView({ behavior: 'smooth', block: 'center' })
  }
}

// 点击字幕跳转
const jumpToPlayerLine = (lineIndex: number) => {
  if (!audioPlayerRef.value) return
  const time = getTimeForPlayerLine(lineIndex)
  audioPlayerRef.value.currentTime = time
  playerCurrentLine.value = lineIndex
}

const seekPlayer = (e: MouseEvent) => {
  if (!audioPlayerRef.value) return
  const target = e.currentTarget as HTMLElement
  const rect = target.getBoundingClientRect()
  const percent = (e.clientX - rect.left) / rect.width
  audioPlayerRef.value.currentTime = percent * playerDuration.value
}

// 音频加载完成时更新时间戳
const onAudioLoaded = () => {
  if (audioPlayerRef.value) {
    playerDuration.value = audioPlayerRef.value.duration
    // 根据实际音频时长重新计算时间戳
    playerScriptWithTime.value = calculateScriptTimestamps(playerScript.value, playerDuration.value)
  }
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

// 本地时区时间格式化
const formatLocalTime = (dateStr: string) => {
  if (!dateStr) return ''
  
  // 处理后端返回的时间字符串
  // 如果是 UTC 时间格式但没有 Z 后缀，添加 Z 表示 UTC
  let normalizedDateStr = dateStr
  if (dateStr && !dateStr.endsWith('Z') && dateStr.includes('T')) {
    normalizedDateStr = dateStr + 'Z'
  }
  
  const d = new Date(normalizedDateStr)
  const now = new Date()
  
  // 计算时间差（毫秒）
  const diffMs = now.getTime() - d.getTime()
  
  // 如果计算出负数，可能是时间字符串已经是本地时间，尝试不添加Z
  let actualDiffMs = diffMs
  if (diffMs < 0) {
    const dLocal = new Date(dateStr)
    actualDiffMs = now.getTime() - dLocal.getTime()
  }
  
  const diffMins = Math.floor(actualDiffMs / 60000)
  const diffHours = Math.floor(actualDiffMs / 3600000)
  const diffDays = Math.floor(actualDiffMs / 86400000)
  
  // 一天内显示小时数
  if (diffMins < 1) return '刚刚'
  if (diffMins < 60) return `${diffMins}分钟前`
  if (diffHours < 24) return `${diffHours}小时前`
  
  // 超过一天按天计算
  if (diffDays < 7) return `${diffDays}天前`
  
  // 超过7天显示具体日期
  const month = d.getMonth() + 1
  const day = d.getDate()
  return `${month}月${day}日`
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
  <div class="page-container">
    <!-- Hero 区域 -->
    <div class="hero-section">
      <div class="hero-content">
        <div class="hero-icon animate-scale-in">
          <span class="icon-circle">
            <span class="icon-book">📚</span>
          </span>
        </div>
        <h1 class="hero-title animate-fade-up">枕边书</h1>
        <p class="hero-subtitle animate-fade-up animate-delay-1">AI 图书转播客 · 一键生成</p>
      </div>
      
      <!-- 右上角：服务状态 + 用户信息 -->
      <div class="top-right-section animate-fade-up animate-delay-2">
        <!-- 在线状态 -->
        <div class="status-indicator" 
          :class="backendOnline ? 'online' : 'offline'"
        >
          <span class="status-dot"></span>
          <span>{{ backendOnline ? '服务正常' : '服务离线' }}</span>
        </div>
        
        <!-- 用户信息 -->
        <div class="user-section">
          <div v-if="user" class="user-card">
            <div class="user-avatar">{{ (user.nickname || user.email || 'U')[0].toUpperCase() }}</div>
            <div class="user-details">
              <span class="user-name">{{ user.nickname || user.email }}</span>
              <span class="user-balance">
                <span class="balance-num">{{ user.balance + user.free_quota }}</span>
                <span class="balance-unit">次额度</span>
              </span>
            </div>
            <button class="btn-logout" @click="logout">退出</button>
          </div>
          <div v-else class="auth-section">
            <button class="btn btn-outline" @click="showLogin">登录</button>
            <button class="btn btn-primary btn-glow" @click="showRegister">免费注册</button>
          </div>
        </div>
      </div>
    </div>

    <!-- 上传区域 -->
    <div class="upload-section animate-fade-up animate-delay-3">
      <div class="section-header">
        <h2>📤 上传文件</h2>
        <p>支持 PDF、TXT、MD 格式</p>
      </div>
      
      <div 
        class="upload-zone"
        :class="{ 'has-file': file, 'dragging': false }"
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
        
        <div class="upload-content">
          <div class="upload-icon-wrapper">
            <div class="upload-icon-bg"></div>
            <span class="upload-icon">{{ file ? '✅' : '📄' }}</span>
          </div>
          <div class="upload-text">
            <p class="upload-main-text">{{ file ? file.name : '拖拽文件到这里或点击选择' }}</p>
            <p class="upload-sub-text" v-if="file">点击重新选择</p>
          </div>
        </div>
      </div>
      
      <div class="upload-actions">
        <button 
          class="btn btn-primary btn-lg"
          :class="{ 'btn-pulse': file && !uploading }"
          @click="upload" 
          :disabled="!file || uploading"
        >
          <span v-if="uploading" class="upload-progress-content">
            <span class="progress-dots">
              <span></span><span></span><span></span>
            </span>
            <span>{{ uploadProgress }}</span>
          </span>
          <span v-else>开始生成播客</span>
        </button>
        
        <p class="upload-tip" v-if="!user">
          💡 新用户注册即送 <strong>3次</strong> 免费体验
        </p>
        <p class="upload-tip" v-else>
          📁 任务将保留 <strong>7天</strong>，之后自动清理
        </p>
      </div>
    </div>

    <!-- 生成队列 -->
    <div class="queue-section animate-fade-up animate-delay-4" v-if="user">
      <div class="section-header">
        <h2>📋 生成队列</h2>
        <span class="queue-badge" v-if="queueBooks.length > 0">{{ queueBooks.length }}</span>
      </div>
      
      <!-- 上传成功提示 -->
      <div v-if="showUploadSuccess" class="success-toast animate-scale-in">
        <span class="toast-icon">✅</span>
        <span>《{{ uploadedBookTitle }}》已加入队列</span>
      </div>
      
      <!-- 加载中 -->
      <div v-if="loadingQueue" class="loading-state">
        <div class="loading-spinner"></div>
        <p>加载中...</p>
      </div>
      
      <!-- 空队列 -->
      <div v-else-if="queueBooks.length === 0" class="empty-state">
        <div class="empty-icon">📭</div>
        <p>暂无生成任务</p>
        <p class="empty-hint">上传文件后，任务将在这里显示</p>
      </div>
      
      <!-- 队列列表 -->
      <div v-else class="queue-list">
        <div 
          v-for="(book, index) in paginatedBooks" 
          :key="book.id" 
          class="book-card"
          :style="{ animationDelay: index * 0.1 + 's' }"
          @click="goToBookDetail(book.id)"
        >
          <!-- 状态指示条 -->
          <div class="card-status-bar" :class="book.status"></div>
          
          <!-- 删除按钮 - 右上角 -->
          <button class="btn-delete" @click.stop="deleteBook(book.id)" title="删除">
            🗑️
          </button>
          
          <!-- 左侧：状态图标 -->
          <div class="book-icon" :class="book.status">
            <span v-if="book.status === 'ready'">📄</span>
            <span v-else-if="book.status === 'script_ready'">📝</span>
            <span v-else-if="book.status === 'completed'">🎧</span>
            <span v-else-if="book.status === 'generating_script'">
              <span class="icon-spinner"></span>
            </span>
            <span v-else-if="book.status === 'generating_audio'">
              <span class="icon-wave"></span>
            </span>
            <span v-else-if="book.status === 'processing' || book.status === 'ocr' || book.status === 'pending'">
              <span class="icon-spinner"></span>
            </span>
            <span v-else>📄</span>
          </div>
          
          <!-- 中间：书籍信息 -->
          <div class="book-info">
            <h3 class="book-title">{{ book.title }}</h3>
            <div class="book-meta">
              <span class="meta-item">{{ book.total_chapters }} 章</span>
              <span class="meta-divider">·</span>
              <span class="meta-item">{{ formatLocalTime(book.created_at) }}</span>
            </div>
            <!-- 处理中的提示 -->
            <div class="book-progress-hint" v-if="book.status === 'processing' || book.status === 'ocr' || book.status === 'pending'">
              <div class="progress-dots">
                <span></span><span></span><span></span>
              </div>
              <span>正在识别文档内容...</span>
            </div>
            <div class="book-progress-hint" v-else-if="book.status === 'generating_script'">
              <div class="progress-dots">
                <span></span><span></span><span></span>
              </div>
              <span>AI正在创作播客文稿...</span>
            </div>
            <div class="book-progress-hint" v-else-if="book.status === 'generating_audio'">
              <div class="progress-dots">
                <span></span><span></span><span></span>
              </div>
              <span>正在合成语音音频...</span>
            </div>
          </div>
          
          <!-- 右侧：状态标签 -->
          <div class="book-status">
            <span v-if="book.status === 'ready'" class="badge badge-success">OCR完成</span>
            <span v-else-if="book.status === 'script_ready'" class="badge badge-info">文稿就绪</span>
            <span v-else-if="book.status === 'completed'" class="badge badge-success">已完成</span>
            <span v-else-if="book.status === 'generating_script'" class="badge badge-processing">
              生成文稿中
            </span>
            <span v-else-if="book.status === 'generating_audio'" class="badge badge-processing">
              合成音频中
            </span>
            <span v-else-if="book.status === 'processing' || book.status === 'ocr' || book.status === 'pending'" class="badge badge-processing">
              OCR识别中
            </span>
            <span v-else class="badge">{{ book.status }}</span>
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
    <div class="demo-section animate-fade-up animate-delay-5">
      <div class="section-header">
        <h2>🎧 听听效果</h2>
        <p>AI 生成的播客示例</p>
      </div>
      
      <div class="demo-player">
        <div class="demo-info">
          <span class="demo-book">📖 试听文件</span>
          <span class="demo-duration">7分06秒</span>
        </div>
        
        <!-- 音频控制 -->
        <div class="demo-controls">
          <button class="demo-play-btn" @click="toggleDemoAudio">
            <svg v-if="demoPlaying" viewBox="0 0 24 24" width="24" height="24">
              <rect x="6" y="4" width="4" height="16" rx="1" fill="currentColor"/>
              <rect x="14" y="4" width="4" height="16" rx="1" fill="currentColor"/>
            </svg>
            <svg v-else viewBox="0 0 24 24" width="24" height="24">
              <path d="M8 5v14l11-7z" fill="currentColor"/>
            </svg>
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
          <div class="player-script" v-if="playerScriptWithTime.length > 0" ref="playerScriptContainer">
            <div 
              v-for="(line, idx) in playerScriptWithTime" 
              :key="idx"
              :class="['script-line', { active: idx === playerCurrentLine }]"
              @click="jumpToPlayerLine(idx)"
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
              @loadedmetadata="onAudioLoaded"
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
/* ========== 页面容器 ========== */
.page-container {
  max-width: 900px;
  margin: 0 auto;
  padding: 20px;
  min-height: 100vh;
}

/* ========== Hero 区域 ========== */
.hero-section {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 32px;
  background: linear-gradient(135deg, rgba(0, 40, 25, 0.8), rgba(15, 36, 25, 0.6));
  border: 1px solid rgba(76, 175, 80, 0.2);
  border-radius: 20px;
  margin-bottom: 24px;
  position: relative;
  overflow: hidden;
}

.hero-section::before {
  content: '';
  position: absolute;
  top: -50%;
  right: -20%;
  width: 300px;
  height: 300px;
  background: radial-gradient(circle, rgba(76, 175, 80, 0.1) 0%, transparent 70%);
  pointer-events: none;
}

.hero-content {
  flex: 1;
}

.hero-icon {
  margin-bottom: 16px;
}

.icon-circle {
  display: inline-flex;
  width: 64px;
  height: 64px;
  background: linear-gradient(135deg, rgba(76, 175, 80, 0.25), rgba(46, 125, 50, 0.15));
  border-radius: 50%;
  align-items: center;
  justify-content: center;
  animation: ring 2s ease-in-out infinite;
}

@keyframes ring {
  0%, 100% { box-shadow: 0 0 0 0 rgba(76, 175, 80, 0.4); }
  50% { box-shadow: 0 0 0 12px rgba(76, 175, 80, 0); }
}

.icon-book {
  font-size: 32px;
}

.hero-title {
  font-size: 32px;
  color: #e8f5e9;
  margin: 0 0 8px 0;
  font-weight: 700;
}

.hero-subtitle {
  font-size: 16px;
  color: #81c784;
  margin: 0 0 16px 0;
}

.status-row {
  display: flex;
  align-items: center;
}

.status-indicator {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background: rgba(0, 30, 20, 0.6);
  border-radius: 20px;
  font-size: 13px;
}

.status-indicator.online {
  color: #81c784;
}

.status-indicator.offline {
  color: #ef5350;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: currentColor;
  animation: pulse 2s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

/* ========== 用户区域 ========== */
/* ========== 右上角区域 ========== */
.top-right-section {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 12px;
  margin-left: auto;
}

.user-section {
  margin-left: 0;
}

.user-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: rgba(0, 30, 20, 0.6);
  border-radius: 12px;
}

.user-avatar {
  width: 40px;
  height: 40px;
  background: linear-gradient(135deg, #4caf50, #2e7d32);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-weight: 700;
  font-size: 18px;
}

.user-details {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.user-name {
  color: #e8f5e9;
  font-size: 14px;
  font-weight: 500;
}

.user-balance {
  display: flex;
  align-items: baseline;
  gap: 4px;
}

.balance-num {
  color: #4caf50;
  font-weight: 700;
  font-size: 16px;
}

.balance-unit {
  color: #81c784;
  font-size: 12px;
}

.btn-logout {
  background: none;
  border: 1px solid rgba(76, 175, 80, 0.3);
  color: #81c784;
  padding: 6px 12px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 12px;
  transition: all 0.2s;
}

.btn-logout:hover {
  background: rgba(76, 175, 80, 0.1);
}

.auth-section {
  display: flex;
  gap: 12px;
  align-items: center;
}

.btn-glow {
  animation: glow 2s ease-in-out infinite;
}

@keyframes glow {
  0%, 100% { box-shadow: 0 0 5px rgba(76, 175, 80, 0.3); }
  50% { box-shadow: 0 0 20px rgba(76, 175, 80, 0.5); }
}

/* ========== Section 通用样式 ========== */
.section-header {
  margin-bottom: 20px;
}

.section-header h2 {
  color: #81c784;
  font-size: 18px;
  margin: 0 0 4px 0;
}

.section-header p {
  color: #666;
  font-size: 13px;
  margin: 0;
}

/* ========== 上传区域 ========== */
.upload-section {
  background: rgba(0, 40, 25, 0.6);
  border: 1px solid rgba(76, 175, 80, 0.2);
  border-radius: 16px;
  padding: 24px;
  margin-bottom: 24px;
}

.upload-zone {
  border: 2px dashed rgba(76, 175, 80, 0.3);
  border-radius: 16px;
  padding: 48px 32px;
  text-align: center;
  cursor: pointer;
  transition: all 0.3s ease;
  margin-bottom: 20px;
  position: relative;
  overflow: hidden;
}

.upload-zone::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(135deg, rgba(76, 175, 80, 0.05), transparent);
  opacity: 0;
  transition: opacity 0.3s;
}

.upload-zone:hover {
  border-color: #4caf50;
  transform: scale(1.01);
}

.upload-zone:hover::before {
  opacity: 1;
}

.upload-zone.has-file {
  border-style: solid;
  border-color: #4caf50;
  background: rgba(76, 175, 80, 0.05);
}

.upload-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
}

.upload-icon-wrapper {
  position: relative;
}

.upload-icon-bg {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 80px;
  height: 80px;
  background: rgba(76, 175, 80, 0.1);
  border-radius: 50%;
}

.upload-icon {
  font-size: 48px;
  position: relative;
}

.upload-main-text {
  color: #e8f5e9;
  font-size: 16px;
  margin: 0;
}

.upload-sub-text {
  color: #81c784;
  font-size: 12px;
  margin: 4px 0 0 0;
}

.upload-actions {
  text-align: center;
}

.upload-actions .btn-lg {
  min-width: 200px;
}

.loading-spinner-sm {
  display: inline-block;
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-right: 8px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* 上传进度内容 */
.upload-progress-content {
  display: flex;
  align-items: center;
  gap: 10px;
}

.upload-progress-content .progress-dots {
  display: flex;
  gap: 4px;
}

.upload-progress-content .progress-dots span {
  width: 6px;
  height: 6px;
  background: white;
  border-radius: 50%;
  animation: dotPulse 1.4s ease-in-out infinite;
}

.upload-progress-content .progress-dots span:nth-child(1) { animation-delay: 0s; }
.upload-progress-content .progress-dots span:nth-child(2) { animation-delay: 0.2s; }
.upload-progress-content .progress-dots span:nth-child(3) { animation-delay: 0.4s; }

.upload-tip {
  color: #81c784;
  font-size: 13px;
  margin: 12px 0 0 0;
}

.upload-tip strong {
  color: #4caf50;
}

/* ========== 队列区域 ========== */
.queue-section {
  background: rgba(0, 40, 25, 0.6);
  border: 1px solid rgba(76, 175, 80, 0.2);
  border-radius: 16px;
  padding: 24px;
  margin-bottom: 24px;
}

.queue-badge {
  background: linear-gradient(135deg, #4caf50, #2e7d32);
  color: white;
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 600;
}

.success-toast {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 18px;
  background: rgba(76, 175, 80, 0.15);
  border: 1px solid rgba(76, 175, 80, 0.3);
  border-radius: 10px;
  margin-bottom: 16px;
  color: #81c784;
}

.toast-icon {
  font-size: 18px;
}

.loading-state, .empty-state {
  text-align: center;
  padding: 48px 24px;
  color: #666;
}

.empty-icon {
  font-size: 48px;
  margin-bottom: 16px;
}

.empty-hint {
  font-size: 12px;
  margin-top: 8px;
}

/* ========== 书籍卡片 ========== */
.queue-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.book-card {
  position: relative;
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px;
  padding-bottom: 40px; /* 为底部状态标签留空间 */
  background: rgba(0, 30, 20, 0.5);
  border: 1px solid rgba(76, 175, 80, 0.15);
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.25s ease;
  animation: fadeInUp 0.4s ease both;
}

@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.book-card:hover {
  border-color: rgba(76, 175, 80, 0.4);
  background: rgba(0, 40, 25, 0.6);
  transform: translateX(4px);
}

.card-status-bar {
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 4px;
  border-radius: 12px 0 0 12px;
}

.card-status-bar.ready { background: #4caf50; }
.card-status-bar.script_ready { background: #2196f3; }
.card-status-bar.completed { background: #9c27b0; }
.card-status-bar.generating_script { background: #ff9800; }
.card-status-bar.generating_audio { background: #00bcd4; }
.card-status-bar.processing, .card-status-bar.ocr, .card-status-bar.pending { background: #ff9800; }

.book-icon {
  width: 48px;
  height: 48px;
  min-width: 48px;
  background: rgba(76, 175, 80, 0.15);
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
}

.book-icon.generating_script,
.book-icon.generating_audio,
.book-icon.processing,
.book-icon.ocr,
.book-icon.pending {
  background: rgba(255, 152, 0, 0.2);
}

/* 图标旋转动画 */
.icon-spinner {
  display: block;
  width: 24px;
  height: 24px;
  border: 3px solid rgba(76, 175, 80, 0.3);
  border-top-color: #4caf50;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

/* 音频波形动画 */
.icon-wave {
  display: flex;
  align-items: flex-end;
  gap: 3px;
  height: 20px;
}

.icon-wave::before,
.icon-wave::after,
.icon-wave {
  content: '';
  width: 4px;
  background: #4caf50;
  border-radius: 2px;
  animation: wave 1s ease-in-out infinite;
}

.icon-wave::before { height: 8px; animation-delay: 0s; }
.icon-wave { height: 16px; animation-delay: 0.15s; }
.icon-wave::after { height: 12px; animation-delay: 0.3s; }

@keyframes wave {
  0%, 100% { transform: scaleY(1); }
  50% { transform: scaleY(0.5); }
}

.book-info {
  flex: 1;
  min-width: 0;
}

.book-title {
  font-size: 15px;
  color: #e8f5e9;
  margin: 0 0 6px 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.book-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: #81c784;
}

.book-progress-hint {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 8px;
  font-size: 12px;
  color: #ffb74d;
}

.progress-dots {
  display: flex;
  gap: 4px;
}

.progress-dots span {
  width: 6px;
  height: 6px;
  background: #ffb74d;
  border-radius: 50%;
  animation: dotPulse 1.4s ease-in-out infinite;
}

.progress-dots span:nth-child(1) { animation-delay: 0s; }
.progress-dots span:nth-child(2) { animation-delay: 0.2s; }
.progress-dots span:nth-child(3) { animation-delay: 0.4s; }

@keyframes dotPulse {
  0%, 80%, 100% { 
    opacity: 0.3;
    transform: scale(0.8);
  }
  40% { 
    opacity: 1;
    transform: scale(1);
  }
}

.meta-divider {
  opacity: 0.5;
}

.book-status {
  position: absolute;
  right: 16px;
  bottom: 12px;
  display: flex;
  align-items: center;
}

/* 删除按钮 - 右上角 */
.btn-delete {
  position: absolute;
  top: 8px;
  right: 8px;
  width: 28px;
  height: 28px;
  background: rgba(0, 0, 0, 0.3);
  border: none;
  border-radius: 50%;
  cursor: pointer;
  opacity: 0;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  z-index: 10;
}

.book-card:hover .btn-delete {
  opacity: 1;
}

.btn-delete:hover {
  background: rgba(244, 67, 54, 0.3);
}

/* ========== 分页 ========== */
.pagination {
  display: flex;
  justify-content: center;
  gap: 8px;
  margin-top: 20px;
}

.page-btn {
  width: 36px;
  height: 36px;
  background: rgba(0, 30, 20, 0.6);
  border: 1px solid rgba(76, 175, 80, 0.2);
  border-radius: 8px;
  color: #81c784;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.2s;
}

.page-btn:hover:not(:disabled) {
  background: rgba(76, 175, 80, 0.2);
  border-color: rgba(76, 175, 80, 0.4);
}

.page-btn.active {
  background: #4caf50;
  border-color: #4caf50;
  color: white;
}

.page-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

/* ========== Demo 区域 ========== */
.demo-section {
  background: rgba(0, 40, 25, 0.6);
  border: 1px solid rgba(76, 175, 80, 0.2);
  border-radius: 16px;
  padding: 24px;
  margin-bottom: 24px;
}

.demo-player {
  background: rgba(0, 30, 20, 0.6);
  border-radius: 16px;
  overflow: hidden;
}

/* ========== 价格区域（保留原样式） ========== */
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

/* 书籍卡片 - 新设计 */
.book-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px 20px;
  background: rgba(0, 30, 20, 0.5);
  border: 1px solid rgba(76, 175, 80, 0.2);
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s;
}

.book-card:hover {
  background: rgba(0, 40, 25, 0.6);
  border-color: rgba(76, 175, 80, 0.4);
  transform: translateY(-1px);
}

.book-card-icon {
  font-size: 28px;
  line-height: 1;
}

.book-card-info {
  flex: 1;
  min-width: 0;
}

.book-card-title {
  color: #e8f5e9;
  font-size: 15px;
  font-weight: 500;
  margin-bottom: 4px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.book-card-meta {
  font-size: 12px;
  color: #81c784;
  display: flex;
  gap: 6px;
}

.book-card-status {
  flex-shrink: 0;
}

.status-badge {
  display: inline-block;
  padding: 6px 12px;
  border-radius: 16px;
  font-size: 12px;
  font-weight: 500;
}

.status-badge.ready { background: rgba(76, 175, 80, 0.2); color: #81c784; }
.status-badge.script { background: rgba(33, 150, 243, 0.2); color: #64b5f6; }
.status-badge.processing { background: rgba(255, 152, 0, 0.2); color: #ffb74d; animation: pulse 1.5s infinite; }
.status-badge.completed { background: rgba(76, 175, 80, 0.3); color: #a5d6a7; }

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.6; }
}

.book-card-arrow {
  font-size: 18px;
  color: #4caf50;
  transition: transform 0.2s;
}

.book-card:hover .book-card-arrow {
  transform: translateX(4px);
}

.delete-btn-inline {
  background: none;
  border: none;
  font-size: 16px;
  cursor: pointer;
  padding: 8px;
  opacity: 0.4;
  transition: opacity 0.2s;
  border-radius: 8px;
}

.delete-btn-inline:hover {
  opacity: 1;
  background: rgba(244, 67, 54, 0.1);
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

/* OCR 结果预览卡片 */
.ocr-result-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 16px;
  background: linear-gradient(135deg, rgba(76, 175, 80, 0.15) 0%, rgba(46, 125, 50, 0.1) 100%);
  border: 1px solid rgba(76, 175, 80, 0.3);
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s;
  margin-bottom: 12px;
}

.ocr-result-card:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(76, 175, 80, 0.2);
  border-color: #4caf50;
}

.ocr-result-icon {
  font-size: 24px;
  line-height: 1;
}

.ocr-result-content {
  flex: 1;
}

.ocr-result-content h4 {
  color: #e8f5e9;
  font-size: 14px;
  margin: 0 0 2px 0;
}

.ocr-result-content p {
  color: #81c784;
  font-size: 12px;
  margin: 0;
}

.ocr-result-arrow {
  font-size: 18px;
  color: #4caf50;
}

.divider-line {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 12px 0;
  color: #666;
  font-size: 12px;
}

.divider-line::before,
.divider-line::after {
  content: '';
  flex: 1;
  height: 1px;
  background: rgba(76, 175, 80, 0.2);
}

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
  color: white;
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
  transition: all 0.2s;
  cursor: pointer;
  border: 1px solid transparent;
}

.script-line:hover {
  background: rgba(76, 175, 80, 0.1);
}

.script-line.active {
  background: rgba(76, 175, 80, 0.25);
  border-color: rgba(76, 175, 80, 0.3);
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

/* ========== 响应式适配 ========== */
@media (max-width: 768px) {
  .page-container {
    padding: 12px;
  }
  
  /* Hero 区域 */
  .hero-section {
    flex-direction: column;
    padding: 24px 20px;
    gap: 20px;
  }
  
  .hero-content {
    text-align: center;
  }
  
  .hero-title {
    font-size: 26px;
  }
  
  .hero-subtitle {
    font-size: 14px;
  }
  
  .status-row {
    justify-content: center;
  }
  
  .user-section {
    margin-left: 0;
    width: 100%;
  }
  
  .user-card {
    justify-content: center;
    flex-wrap: wrap;
    gap: 8px;
  }
  
  .auth-section {
    width: 100%;
    justify-content: center;
  }
  
  .auth-section .btn {
    flex: 1;
    max-width: 120px;
  }
  
  /* 上传区域 */
  .upload-section {
    padding: 16px;
  }
  
  .upload-zone {
    padding: 32px 20px;
  }
  
  .upload-icon {
    font-size: 36px;
  }
  
  .upload-main-text {
    font-size: 14px;
  }
  
  .upload-actions .btn-lg {
    width: 100%;
  }
  
  /* 队列区域 */
  .queue-section {
    padding: 16px;
  }
  
  .section-header {
    text-align: center;
  }
  
  .book-card {
    padding: 14px;
    gap: 12px;
  }
  
  .card-status-bar {
    width: 3px;
  }
  
  .book-icon {
    width: 40px;
    height: 40px;
    font-size: 20px;
  }
  
  .book-title {
    font-size: 14px;
  }
  
  .book-meta {
    font-size: 11px;
  }
  
  .book-status .badge {
    font-size: 11px;
    padding: 4px 8px;
  }
  
  .btn-delete {
    display: none;
  }
  
  /* Demo 区域 */
  .demo-section {
    padding: 16px;
  }
  
  /* 播放器 */
  .player-header {
    padding: 12px;
  }
  
  .player-script {
    max-height: 200px;
  }
  
  .script-line {
    padding: 8px 10px;
    font-size: 12px;
  }
  
  /* 模态框 */
  .modal-overlay {
    padding: 12px;
  }
  
  .modal-content {
    margin: 0;
    max-height: 90vh;
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

@media (max-width: 400px) {
  .hero-title {
    font-size: 22px;
  }
  
  .icon-circle {
    width: 56px;
    height: 56px;
  }
  
  .icon-book {
    font-size: 28px;
  }
  
  .user-card {
    padding: 10px 12px;
  }
  
  .user-avatar {
    width: 36px;
    height: 36px;
    font-size: 16px;
  }
  
  .balance-num {
    font-size: 14px;
  }
  
  .book-card {
    flex-wrap: wrap;
  }
  
  .book-info {
    width: calc(100% - 60px);
  }
  
  .book-status {
    width: 100%;
    margin-top: 8px;
    justify-content: flex-start;
  }
}
</style>