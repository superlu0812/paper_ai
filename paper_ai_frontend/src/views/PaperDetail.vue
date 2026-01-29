<script setup>
import { ref, onMounted, computed, watch, nextTick, onUnmounted } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { getPaperDetail, API_BASE_URL } from '../api'
import dayjs from 'dayjs'
import { marked } from 'marked'
import * as pdfjsLib from 'pdfjs-dist'

// 设置PDF.js worker（使用本地文件，配合Nginx配置或改用.js扩展名）
pdfjsLib.GlobalWorkerOptions.workerSrc = `${import.meta.env.BASE_URL}workers/pdf.worker.min.js`

const route = useRoute()
const paperId = computed(() => route.params.paperId)

// 数据状态
const paper = ref(null)
const loading = ref(true)
const error = ref(null)
const activeTab = ref('summary')

// PDF预览相关
const pdfScale = ref(1.0)
const showPdf = ref(false)
let pdfDoc = null  // 使用普通变量存储PDF文档对象（PDF.js 5.x兼容）
const currentPage = ref(1)
const totalPages = ref(0)
const pdfCanvas = ref(null)
const pdfLoading = ref(false)
const pdfError = ref(null)
let currentRenderTask = null  // 当前渲染任务
const isRendering = ref(false)  // 是否正在渲染

onMounted(async () => {
  await loadPaperDetail()
})

async function loadPaperDetail() {
  loading.value = true
  error.value = null

  try {
    const data = await getPaperDetail(paperId.value)
    paper.value = data

    // 如果有markdown总结，默认显示总结
    if (data.llm_summary || data.markdown_path) {
      activeTab.value = 'summary'
    }
  } catch (err) {
    error.value = err.response?.data?.detail || '加载论文详情失败'
    console.error('Failed to load paper detail:', err)
  } finally {
    loading.value = false
  }
}

function formatAuthors(authors) {
  if (!authors || authors.length === 0) return '未知'
  if (authors.length <= 5) return authors.join(', ')
  return authors.slice(0, 5).join(', ') + ' ...等' + authors.length + '人'
}

function formatDate(dateStr) {
  return dayjs(dateStr).format('YYYY年MM月DD日 HH:mm')
}

// 解析markdown为HTML
const renderedMarkdown = computed(() => {
  if (!paper.value || !paper.value.llm_summary) {
    return '<p class="empty-hint">😕 暂无AI总结</p>'
  }

  try {
    // 使用marked将markdown转换为HTML
    return marked.parse(paper.value.llm_summary)
  } catch (error) {
    console.error('Markdown解析失败:', error)
    return '<p class="error-hint">Markdown解析失败</p>'
  }
})

function getPdfUrl() {
  if (!paper.value || !paper.value.pdf_path) return ''

  // 使用后端API获取PDF（使用API base URL）
  return `${API_BASE_URL}/api/paper/${paperId.value}/pdf`
}

function togglePdf() {
  showPdf.value = !showPdf.value
  if (showPdf.value) {
    // 等待DOM更新后加载PDF
    nextTick(() => {
      loadPdf()
    })
  }
}

// 检测canvas是否真正初始化完成
async function waitForCanvasReady(maxAttempts = 20, interval = 50) {
  for (let i = 0; i < maxAttempts; i++) {
    await nextTick()

    if (!pdfCanvas.value) {
      console.log(`等待canvas元素... (${i + 1}/${maxAttempts})`)
      await new Promise(resolve => setTimeout(resolve, interval))
      continue
    }

    const canvas = pdfCanvas.value

    // 检查canvas元素是否在DOM中
    if (canvas && canvas.nodeType === Node.ELEMENT_NODE) {
      // 检查context是否可用
      try {
        const context = canvas.getContext('2d')
        if (context) {
          console.log('Canvas初始化完成，元素已就绪')
          return true
        }
      } catch (e) {
        console.log('Canvas context不可用，重试中...', i + 1)
      }
    }

    console.log(`等待canvas初始化... (${i + 1}/${maxAttempts})`)
    await new Promise(resolve => setTimeout(resolve, interval))
  }

  throw new Error('Canvas初始化超时')
}

async function loadPdf() {
  if (!paper.value?.pdf_path) return

  pdfLoading.value = true
  pdfError.value = null

  try {
    // 使用API base URL构建PDF URL
    const pdfUrl = `${API_BASE_URL}/api/paper/${paperId.value}/pdf`

    // 加载PDF文档
    const loadingTask = pdfjsLib.getDocument(pdfUrl)
    pdfDoc = await loadingTask.promise  // 直接赋值给普通变量
    totalPages.value = pdfDoc.numPages
    currentPage.value = 1

    // 等待DOM更新（canvas现在会立即可用）
    await nextTick()

    // 等待canvas真正初始化完成（应该很快）
    try {
      await waitForCanvasReady(10, 50)  // 减少等待次数和间隔
    } catch (err) {
      console.error('Canvas初始化失败:', err)
      pdfError.value = 'Canvas初始化失败，请重试'
      return
    }

    // 渲染第一页，带有重试机制
    await renderPageWithRetry(currentPage.value)
  } catch (err) {
    console.error('PDF加载失败:', err)
    pdfError.value = 'PDF加载失败：' + (err.message || '未知错误')
  } finally {
    pdfLoading.value = false
  }
}

// 带重试机制的渲染函数
async function renderPageWithRetry(pageNum, maxRetries = 3) {
  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    try {
      console.log(`尝试渲染第 ${pageNum} 页 (第 ${attempt}/${maxRetries} 次)`)
      await renderPage(pageNum)

      // 渲染成功，检查canvas是否有内容
      const canvas = pdfCanvas.value
      if (canvas && canvas.width > 0 && canvas.height > 0) {
        console.log('渲染成功')
        return
      }

      // 如果canvas尺寸为0，继续重试
      console.log('Canvas尺寸为0，重试中...')
      if (attempt < maxRetries) {
        await new Promise(resolve => setTimeout(resolve, 100 * attempt))
      }
    } catch (err) {
      console.error(`第 ${attempt} 次渲染失败:`, err)
      if (attempt < maxRetries) {
        await new Promise(resolve => setTimeout(resolve, 100 * attempt))
      } else {
        throw err
      }
    }
  }
  throw new Error(`渲染失败，已重试 ${maxRetries} 次`)
}

async function renderPage(pageNum) {
  if (!pdfDoc || !pdfCanvas.value || isRendering.value) {
    console.log('渲染条件不满足:', {
      hasPdfDoc: !!pdfDoc,
      hasCanvas: !!pdfCanvas.value,
      isRendering: isRendering.value
    })
    return
  }

  // 如果有正在进行的渲染任务，先取消
  if (currentRenderTask) {
    try {
      currentRenderTask.cancel()
    } catch (e) {
      console.log('取消渲染任务失败:', e)
    }
    currentRenderTask = null
  }

  isRendering.value = true

  try {
    const canvas = pdfCanvas.value
    console.log('开始渲染，canvas当前尺寸:', { width: canvas.width, height: canvas.height })

    // 获取页面
    const page = await pdfDoc.getPage(pageNum)

    // 获取视口
    const viewport = page.getViewport({ scale: parseFloat(pdfScale.value) })
    console.log('Viewport尺寸:', { width: viewport.width, height: viewport.height })

    const context = canvas.getContext('2d')

    // 先设置canvas尺寸（在清空之前设置，确保canvas有正确尺寸）
    canvas.height = viewport.height
    canvas.width = viewport.width
    console.log('Canvas尺寸已设置:', { width: canvas.width, height: canvas.height })

    // 清空canvas（重要：避免之前的内容残留）
    context.clearRect(0, 0, canvas.width, canvas.height)

    // 等待一帧确保canvas尺寸生效
    await new Promise(resolve => requestAnimationFrame(resolve))

    // 渲染PDF页面
    const renderContext = {
      canvasContext: context,
      viewport: viewport
    }

    // 保存渲染任务引用
    currentRenderTask = page.render(renderContext)
    await currentRenderTask.promise

    currentRenderTask = null
    console.log('渲染完成')
  } catch (err) {
    // 如果是取消渲染的错误，不显示给用户
    if (err.message && err.message.includes('cancelled')) {
      console.log('渲染已取消')
    } else {
      console.error('页面渲染失败:', err)
      pdfError.value = '页面渲染失败：' + (err.message || '未知错误')
    }
    throw err
  } finally {
    isRendering.value = false
  }
}

function changePage(delta) {
  const newPage = currentPage.value + delta
  if (newPage >= 1 && newPage <= totalPages.value) {
    currentPage.value = newPage
    renderPage(newPage)
  }
}

function zoomIn() {
  if (pdfScale.value < 2.0) {
    pdfScale.value += 0.1
    renderPage(currentPage.value)
  }
}

function zoomOut() {
  if (pdfScale.value > 0.5) {
    pdfScale.value -= 0.1
    renderPage(currentPage.value)
  }
}

function resetZoom() {
  pdfScale.value = 1.0
  renderPage(currentPage.value)
}

// 注释掉watch监听，避免重复渲染
// zoomIn/zoomOut/resetZoom函数已经会调用renderPage，不需要watch再监听
// watch(pdfScale, () => {
//   if (showPdf.value && currentPage.value) {
//     renderPage(currentPage.value)
//   }
// })

// 组件卸载时清理PDF文档和渲染任务
onUnmounted(() => {
  // 取消正在进行的渲染任务
  if (currentRenderTask) {
    try {
      currentRenderTask.cancel()
    } catch (e) {
      console.log('取消渲染任务失败:', e)
    }
    currentRenderTask = null
  }

  // 销毁PDF文档
  if (pdfDoc) {
    pdfDoc.destroy()
    pdfDoc = null
  }
})
</script>

<template>
  <div v-if="loading" class="loading-state">
    <div class="spinner"></div>
    <p>加载中...</p>
  </div>

  <div v-else-if="error" class="error-state">
    <p>⚠️ {{ error }}</p>
    <RouterLink :to="{ name: 'Home' }" class="back-link">← 返回论文列表</RouterLink>
  </div>

  <div v-else-if="paper" class="paper-detail">
    <!-- 返回链接 -->
    <div class="back-nav">
      <RouterLink :to="{ name: 'Home' }" class="back-link">← 返回论文列表</RouterLink>
    </div>

    <!-- 论文标题和基本信息 -->
    <div class="paper-header">
      <h1 class="detail-title">{{ paper.title }}</h1>

      <div class="paper-info">
        <div class="info-item">
          <span class="info-label">👥 作者:</span>
          <span class="info-value">{{ formatAuthors(paper.authors) }}</span>
        </div>
        <div class="info-item">
          <span class="info-label">🏷️ 分类:</span>
          <span class="info-value">{{ paper.categories.join(', ') }}</span>
        </div>
        <div class="info-item">
          <span class="info-label">📅 发布时间:</span>
          <span class="info-value">{{ formatDate(paper.published) }}</span>
        </div>
        <div class="info-item" v-if="paper.doi">
          <span class="info-label">🔗 DOI:</span>
          <span class="info-value">{{ paper.doi }}</span>
        </div>
      </div>

      <div class="paper-actions">
        <a :href="paper.pdf_url" target="_blank" class="action-btn primary">
          📄 下载PDF
        </a>
        <a :href="paper.entry_id" target="_blank" class="action-btn secondary">
          🔗 Arxiv链接
        </a>
        <button
          v-if="paper.pdf_path"
          @click="togglePdf"
          class="action-btn"
          :class="showPdf ? 'warning' : 'success'"
        >
          {{ showPdf ? '📖 隐藏PDF' : '📖 预览PDF' }}
        </button>
      </div>
    </div>

    <!-- PDF预览 -->
    <div v-if="showPdf && paper.pdf_path" class="pdf-preview">
      <div class="pdf-controls-top">
        <div class="page-controls">
          <button @click="changePage(-1)" class="control-btn" :disabled="currentPage <= 1">
            ⬅️ 上一页
          </button>
          <span class="page-info">
            第 {{ currentPage }} / {{ totalPages }} 页
          </span>
          <button @click="changePage(1)" class="control-btn" :disabled="currentPage >= totalPages">
            下一页 ➡️
          </button>
        </div>
        <div class="zoom-controls">
          <button @click="zoomOut" class="control-btn" :disabled="pdfScale <= 0.5">
            ➖ 缩小
          </button>
          <span class="zoom-level">{{ Math.round(pdfScale * 100) }}%</span>
          <button @click="zoomIn" class="control-btn" :disabled="pdfScale >= 2.0">
            ➕ 放大
          </button>
          <button @click="resetZoom" class="control-btn">
            🔄 重置
          </button>
        </div>
      </div>

      <div class="pdf-container">
        <!-- 加载状态 -->
        <div v-show="pdfLoading" class="pdf-loading">
          <div class="spinner"></div>
          <p>加载PDF中...</p>
        </div>

        <!-- 错误状态 -->
        <div v-show="pdfError" class="pdf-error">
          <p>⚠️ {{ pdfError }}</p>
        </div>

        <!-- Canvas始终存在，用样式控制显示/隐藏 -->
        <div v-show="!pdfLoading && !pdfError" class="pdf-canvas-wrapper">
          <canvas ref="pdfCanvas" class="pdf-canvas"></canvas>
        </div>
      </div>
    </div>

    <!-- 内容标签页 -->
    <div class="content-tabs">
      <button
        :class="['tab-btn', { active: activeTab === 'summary' }]"
        @click="activeTab = 'summary'"
        :disabled="!paper.llm_summary"
      >
        📝 AI总结
      </button>
      <button
        :class="['tab-btn', { active: activeTab === 'abstract' }]"
        @click="activeTab = 'abstract'"
      >
        📄 摘要
      </button>
      <button
        :class="['tab-btn', { active: activeTab === 'content' }]"
        @click="activeTab = 'content'"
        :disabled="!paper.content"
      >
        📃 全文内容
      </button>
    </div>

    <!-- 内容区域 -->
    <div class="content-area">
      <!-- AI总结 -->
      <div v-if="activeTab === 'summary'" class="tab-content">
        <div v-if="paper" class="markdown-content" v-html="renderedMarkdown"></div>
      </div>

      <!-- 摘要 -->
      <div v-if="activeTab === 'abstract'" class="tab-content">
        <div class="abstract-content">
          <h3>摘要</h3>
          
          <!-- 译文（translated_summary） -->
          <div v-if="paper.translated_summary && paper.translated_summary.trim()" class="summary-section">
            <div class="summary-label">译文</div>
            <p class="summary-text">{{ paper.translated_summary }}</p>
          </div>
          
          <!-- 原文（summary） -->
          <div v-if="paper.summary && paper.summary.trim()" class="summary-section">
            <div class="summary-label">原文</div>
            <p class="summary-text">{{ paper.summary }}</p>
          </div>
          
          <!-- 如果都没有，显示提示 -->
          <div v-if="(!paper.translated_summary || !paper.translated_summary.trim()) && (!paper.summary || !paper.summary.trim())" class="empty-hint">
            <p>😕 暂无摘要信息</p>
          </div>
        </div>
      </div>

      <!-- 全文内容 -->
      <div v-if="activeTab === 'content'" class="tab-content">
        <div v-if="paper.content" class="content-text">
          <pre>{{ paper.content }}</pre>
        </div>
        <div v-else class="empty-content">
          <p>😕 暂无全文内容</p>
          <p class="hint">提示：需要下载PDF并提取文字内容</p>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.loading-state,
.error-state {
  text-align: center;
  padding: 3rem;
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.spinner {
  border: 3px solid #f3f3f3;
  border-top: 3px solid #667eea;
  border-radius: 50%;
  width: 40px;
  height: 40px;
  animation: spin 1s linear infinite;
  margin: 0 auto 1rem;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.back-link {
  display: inline-block;
  color: #667eea;
  text-decoration: none;
  font-weight: 500;
  margin-bottom: 1rem;
  transition: opacity 0.2s;
}

.back-link:hover {
  opacity: 0.8;
}

/* 论文详情 */
.paper-detail {
  width: 100%;
}

.back-nav {
  margin-bottom: 1rem;
}

.paper-header {
  background: white;
  border-radius: 8px;
  padding: 2rem;
  margin-bottom: 2rem;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.detail-title {
  margin: 0 0 1.5rem 0;
  font-size: 1.8rem;
  color: #2c3e50;
  line-height: 1.4;
}

.paper-info {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.info-item {
  display: flex;
  gap: 0.5rem;
  align-items: flex-start;
}

.info-label {
  color: #7f8c8d;
  font-weight: 500;
  flex-shrink: 0;
}

.info-value {
  color: #34495e;
  word-break: break-word;
}

.paper-actions {
  display: flex;
  gap: 1rem;
  flex-wrap: wrap;
}

.action-btn {
  padding: 0.7rem 1.5rem;
  border: none;
  border-radius: 6px;
  font-size: 1rem;
  font-weight: 500;
  cursor: pointer;
  text-decoration: none;
  transition: opacity 0.2s, transform 0.1s;
}

.action-btn:hover {
  opacity: 0.9;
  transform: translateY(-1px);
}

.action-btn.primary {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.action-btn.secondary {
  background-color: #3498db;
  color: white;
}

.action-btn.success {
  background-color: #27ae60;
  color: white;
}

.action-btn.warning {
  background-color: #e67e22;
  color: white;
}

/* PDF预览 */
.pdf-preview {
  background: white;
  border-radius: 8px;
  padding: 1.5rem;
  margin-bottom: 2rem;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.pdf-controls-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
  margin-bottom: 1rem;
  flex-wrap: wrap;
}

.page-controls,
.zoom-controls {
  display: flex;
  align-items: center;
  gap: 0.8rem;
}

.page-info {
  font-weight: 600;
  color: #2c3e50;
  min-width: 120px;
  text-align: center;
}

.control-btn {
  padding: 0.5rem 1rem;
  background-color: #ecf0f1;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.9rem;
  transition: background-color 0.2s;
}

.control-btn:hover:not(:disabled) {
  background-color: #bdc3c7;
}

.control-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.zoom-level {
  font-weight: 600;
  color: #2c3e50;
  min-width: 60px;
  text-align: center;
}

.pdf-container {
  width: 100%;
  min-height: 600px;
  border: 1px solid #ddd;
  border-radius: 4px;
  overflow: auto;
  background-color: #f8f9fa;
  display: flex;
  justify-content: center;
  align-items: flex-start;
  padding: 1rem;
}

.pdf-loading,
.pdf-error {
  text-align: center;
  padding: 3rem;
  color: #7f8c8d;
}

.pdf-error {
  color: #e74c3c;
}

.pdf-canvas-wrapper {
  display: flex;
  justify-content: center;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.pdf-canvas {
  max-width: 100%;
  height: auto;
  display: block;
  min-height: 400px; /* 确保canvas有一个最小高度 */
}

/* 标签页 */
.content-tabs {
  background: white;
  border-radius: 8px;
  padding: 0;
  margin-bottom: 0;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  display: flex;
  overflow: hidden;
}

.tab-btn {
  flex: 1;
  padding: 1rem 1.5rem;
  background-color: white;
  border: none;
  border-bottom: 3px solid transparent;
  cursor: pointer;
  font-size: 1rem;
  font-weight: 500;
  color: #7f8c8d;
  transition: all 0.2s;
}

.tab-btn:hover:not(:disabled) {
  background-color: #f8f9fa;
  color: #2c3e50;
}

.tab-btn.active {
  color: #667eea;
  border-bottom-color: #667eea;
  background-color: #f8f9fa;
}

.tab-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* 内容区域 */
.content-area {
  background: white;
  border-radius: 8px;
  padding: 2rem;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  min-height: 400px;
}

.tab-content {
  animation: fadeIn 0.3s ease;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.markdown-content {
  line-height: 1.8;
  color: #2c3e50;
}

.markdown-content :deep(h1),
.markdown-content :deep(h2),
.markdown-content :deep(h3) {
  margin-top: 1.5rem;
  margin-bottom: 1rem;
  color: #2c3e50;
}

.markdown-content :deep(h1) {
  font-size: 1.8rem;
  border-bottom: 2px solid #ecf0f1;
  padding-bottom: 0.5rem;
}

.markdown-content :deep(h2) {
  font-size: 1.5rem;
}

.markdown-content :deep(h3) {
  font-size: 1.3rem;
}

.markdown-content :deep(p) {
  margin-bottom: 1rem;
}

.markdown-content :deep(ul),
.markdown-content :deep(ol) {
  margin-bottom: 1rem;
  padding-left: 2rem;
}

.markdown-content :deep(li) {
  margin-bottom: 0.5rem;
}

.markdown-content :deep(code) {
  background-color: #f8f9fa;
  padding: 0.2rem 0.4rem;
  border-radius: 3px;
  font-family: 'Courier New', monospace;
}

.markdown-content :deep(pre) {
  background-color: #2c3e50;
  color: #ecf0f1;
  padding: 1rem;
  border-radius: 4px;
  overflow-x: auto;
  margin-bottom: 1rem;
}

.markdown-content :deep(pre code) {
  background-color: transparent;
  padding: 0;
}

.markdown-content :deep(.empty-hint),
.markdown-content :deep(.error-hint) {
  text-align: center;
  padding: 3rem;
  color: #7f8c8d;
  font-size: 1.1rem;
}

.markdown-content :deep(.error-hint) {
  color: #e74c3c;
}

.abstract-content h3 {
  margin-top: 0;
  color: #2c3e50;
  font-size: 1.5rem;
  margin-bottom: 1rem;
}

.abstract-content p {
  font-size: 1.05rem;
  line-height: 1.8;
  color: #34495e;
}

.summary-section {
  margin-bottom: 2rem;
}

.summary-section:last-child {
  margin-bottom: 0;
}

.summary-label {
  font-size: 0.9rem;
  font-weight: 600;
  color: #667eea;
  margin-bottom: 0.8rem;
  padding-bottom: 0.5rem;
  border-bottom: 2px solid #ecf0f1;
}

.summary-text {
  font-size: 1.05rem;
  line-height: 1.8;
  color: #34495e;
  margin: 0;
}

.content-text pre {
  white-space: pre-wrap;
  word-wrap: break-word;
  font-family: 'Courier New', monospace;
  font-size: 0.9rem;
  line-height: 1.6;
  color: #2c3e50;
  background-color: #f8f9fa;
  padding: 1.5rem;
  border-radius: 4px;
  overflow-x: auto;
}

.empty-content {
  text-align: center;
  padding: 3rem;
  color: #7f8c8d;
}

.empty-content p {
  margin: 0.5rem 0;
  font-size: 1.1rem;
}

.empty-content .hint {
  font-size: 0.9rem;
  color: #95a5a6;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .paper-header {
    padding: 1.5rem;
  }

  .detail-title {
    font-size: 1.4rem;
  }

  .paper-info {
    grid-template-columns: 1fr;
  }

  .paper-actions {
    flex-direction: column;
  }

  .action-btn {
    width: 100%;
    text-align: center;
  }

  .content-tabs {
    flex-direction: column;
  }

  .tab-btn {
    border-bottom: 1px solid #ecf0f1;
    border-left: 3px solid transparent;
  }

  .tab-btn.active {
    border-bottom-color: #ecf0f1;
    border-left-color: #667eea;
  }

  .content-area {
    padding: 1.5rem;
  }

  .pdf-controls-top {
    flex-direction: column;
    gap: 0.8rem;
  }

  .page-controls,
  .zoom-controls {
    width: 100%;
    justify-content: space-between;
    flex-wrap: wrap;
  }

  .pdf-container {
    min-height: 400px;
    padding: 0.5rem;
  }
}
</style>
