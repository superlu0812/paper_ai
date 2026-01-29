<script setup>
import { ref, onMounted, computed } from 'vue'
import { RouterLink } from 'vue-router'
import { getPapers, getCategories, getDates, getDailyStats } from '../api'
import dayjs from 'dayjs'
import DatePickerWithMarkers from '../components/DatePickerWithMarkers.vue'
import SearchableSelect from '../components/SearchableSelect.vue'

// 数据状态
const papers = ref([])
const loading = ref(false)
const error = ref(null)
const total = ref(0)

// 筛选条件
const filters = ref({
  date: '',
  category: '',
  keyword: '',
  author: ''
})

// 可选项
const categories = ref([])
const dates = ref([])
const dailyStats = ref([]) // 每日统计数据，用于标记有数据的日期
const datesWithData = computed(() => {
  // 创建一个 Set，包含所有有数据的日期
  return new Set(dailyStats.value.map(stat => stat.date))
})

// 分页
const currentPage = ref(1)
const pageSize = ref(20)

// 获取所有日期和分类
onMounted(async () => {
  await loadMetadata()
  await loadPapers()
})

async function loadMetadata() {
  try {
    const [categoriesRes, datesRes, statsRes] = await Promise.all([
      getCategories(),
      getDates(),
      getDailyStats().catch(() => ({ daily_stats: [] })) // 如果失败则返回空数组
    ])
    categories.value = categoriesRes.categories || []
    dates.value = datesRes.dates || []
    dailyStats.value = statsRes.daily_stats || []

    // 默认选择最新日期
    if (dates.value.length > 0) {
      filters.value.date = dates.value[0]
    }
  } catch (err) {
    console.error('Failed to load metadata:', err)
  }
}

// 检查日期是否有数据
function hasDataForDate(date) {
  return datesWithData.value.has(date)
}

// 获取日期的最大最小值（用于日期选择器）
const minDate = computed(() => {
  if (dates.value.length === 0) return ''
  return dates.value[dates.value.length - 1] // 最早的日期
})

const maxDate = computed(() => {
  if (dates.value.length === 0) return ''
  return dates.value[0] // 最新的日期
})

async function loadPapers() {
  loading.value = true
  error.value = null

  try {
    const params = {
      date: filters.value.date || undefined,
      category: filters.value.category || undefined,
      keyword: filters.value.keyword || undefined,
      author: filters.value.author || undefined,
      limit: pageSize.value,
      offset: (currentPage.value - 1) * pageSize.value
    }

    const response = await getPapers(params)
    papers.value = response.papers || []
    total.value = response.total || 0
  } catch (err) {
    error.value = err.message || '加载论文失败'
    console.error('Failed to load papers:', err)
  } finally {
    loading.value = false
  }
}

// 处理搜索
function handleSearch() {
  currentPage.value = 1
  loadPapers()
}

// 重置筛选
function handleReset() {
  filters.value = {
    date: dates.value[0] || '',
    category: '',
    keyword: '',
    author: ''
  }
  currentPage.value = 1
  loadPapers()
}

// 生成论文ID
function getPaperId(paper) {
  const dateStr = paper.published ? paper.published.split(' ')[0] : 'unknown'
  const title = paper.title || 'untitled'
  const safeTitle = title.replace(/[^a-zA-Z0-9\s\-_]/g, '_').substring(0, 100)
  return `${dateStr}_${safeTitle}`
}

// 格式化日期
function formatDate(dateStr) {
  return dayjs(dateStr).format('YYYY-MM-DD HH:mm')
}

// 获取论文摘要：优先使用refined_summary，其次translated_summary，最后summary
function getPaperSummary(paper) {
  if (paper.refined_summary && paper.refined_summary.trim()) {
    return paper.refined_summary
  }
  if (paper.translated_summary && paper.translated_summary.trim()) {
    return paper.translated_summary
  }
  if (paper.summary && paper.summary.trim()) {
    return paper.summary
  }
  return null
}

// 分页处理
const totalPages = computed(() => Math.ceil(total.value / pageSize.value))

function goToPage(page) {
  if (page < 1 || page > totalPages.value) return
  currentPage.value = page
  loadPapers()
}
</script>

<template>
  <div class="paper-list">
    <!-- 搜索筛选区域 -->
    <div class="filter-section">
      <div class="filter-header">
        <h2>🔍 论文搜索</h2>
        <button class="reset-btn" @click="handleReset" v-if="filters.category || filters.keyword || filters.author">
          重置筛选
        </button>
      </div>

      <div class="filter-grid">
        <!-- 日期选择 -->
        <div class="filter-item">
          <label>日期</label>
          <DatePickerWithMarkers
            v-model="filters.date"
            :min="minDate"
            :max="maxDate"
            :marked-dates="datesWithData"
            @change="handleSearch"
          />
          <div v-if="filters.date && hasDataForDate(filters.date)" class="date-hint">
            ✅ 该日期有 {{ dailyStats.find(s => s.date === filters.date)?.count || 0 }} 篇论文
          </div>
        </div>

        <!-- 分类选择 -->
        <div class="filter-item">
          <label>分类</label>
          <SearchableSelect
            v-model="filters.category"
            :options="['', ...categories]"
            placeholder="所有分类"
            search-placeholder="搜索分类..."
            empty-text="没有找到匹配的分类"
            @change="handleSearch"
          />
        </div>

        <!-- 关键词搜索 -->
        <div class="filter-item">
          <label>关键词</label>
          <input
            v-model="filters.keyword"
            type="text"
            placeholder="搜索标题或摘要..."
            @keyup.enter="handleSearch"
          />
        </div>

        <!-- 作者搜索 -->
        <div class="filter-item">
          <label>作者</label>
          <input
            v-model="filters.author"
            type="text"
            placeholder="搜索作者..."
            @keyup.enter="handleSearch"
          />
        </div>

        <!-- 搜索按钮 -->
        <div class="filter-item filter-actions">
          <button class="search-btn" @click="handleSearch">
            搜索
          </button>
        </div>
      </div>
    </div>

    <!-- 加载状态 -->
    <div v-if="loading" class="loading-state">
      <div class="spinner"></div>
      <p>加载中...</p>
    </div>

    <!-- 错误状态 -->
    <div v-else-if="error" class="error-state">
      <p>⚠️ {{ error }}</p>
    </div>

    <!-- 论文列表 -->
    <div v-else-if="papers.length > 0" class="papers-container">
      <div class="papers-header">
        <h3>共找到 {{ total }} 篇论文</h3>
        <span v-if="filters.date" class="date-badge">{{ filters.date }}</span>
      </div>

      <div class="papers-grid">
        <div
          v-for="paper in papers"
          :key="paper.title"
          class="paper-card"
        >
          <RouterLink :to="{ name: 'PaperDetail', params: { paperId: getPaperId(paper) } }" class="paper-link">
            <h3 class="paper-title">{{ paper.title }}</h3>
          </RouterLink>

          <div class="paper-meta">
            <div class="meta-item">
              <span class="meta-label">👥 作者:</span>
              <span class="meta-value">{{ paper.authors.slice(0, 3).join(', ') }}{{ paper.authors.length > 3 ? '...' : '' }}</span>
            </div>
            <div class="meta-item">
              <span class="meta-label">🏷️ 分类:</span>
              <span class="meta-value">{{ paper.categories.join(', ') }}</span>
            </div>
            <div class="meta-item">
              <span class="meta-label">📅 发布:</span>
              <span class="meta-value">{{ formatDate(paper.published) }}</span>
            </div>
          </div>

          <p class="paper-summary" v-if="getPaperSummary(paper)">
            {{ getPaperSummary(paper).substring(0, 200) }}{{ getPaperSummary(paper).length > 200 ? '...' : '' }}
          </p>

          <div class="paper-footer">
            <RouterLink :to="{ name: 'PaperDetail', params: { paperId: getPaperId(paper) } }" class="view-btn">
              查看详情 →
            </RouterLink>
            <a v-if="paper.pdf_url" :href="paper.pdf_url" target="_blank" class="pdf-btn">
              📄 PDF
            </a>
          </div>
        </div>
      </div>

      <!-- 分页 -->
      <div v-if="totalPages > 1" class="pagination">
        <button
          class="page-btn"
          :disabled="currentPage === 1"
          @click="goToPage(currentPage - 1)"
        >
          上一页
        </button>
        <span class="page-info">{{ currentPage }} / {{ totalPages }}</span>
        <button
          class="page-btn"
          :disabled="currentPage === totalPages"
          @click="goToPage(currentPage + 1)"
        >
          下一页
        </button>
      </div>
    </div>

    <!-- 空状态 -->
    <div v-else class="empty-state">
      <p>😕 没有找到符合条件的论文</p>
      <button class="reset-btn" @click="handleReset">重置筛选条件</button>
    </div>
  </div>
</template>

<style scoped>
.paper-list {
  width: 100%;
}

/* 筛选区域 */
.filter-section {
  background: white;
  border-radius: 8px;
  padding: 1.5rem;
  margin-bottom: 2rem;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.filter-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.filter-header h2 {
  margin: 0;
  font-size: 1.3rem;
  color: #2c3e50;
}

.reset-btn {
  padding: 0.5rem 1rem;
  background-color: #e74c3c;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.9rem;
  transition: background-color 0.2s;
}

.reset-btn:hover {
  background-color: #c0392b;
}

.filter-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
}

.filter-item {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.filter-item label {
  font-size: 0.9rem;
  font-weight: 500;
  color: #34495e;
}

.filter-item select,
.filter-item input {
  padding: 0.6rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 0.95rem;
  transition: border-color 0.2s;
}

.date-hint {
  margin-top: 0.3rem;
  font-size: 0.85rem;
  color: #27ae60;
  font-weight: 500;
}

.filter-item select:focus,
.filter-item input:focus {
  outline: none;
  border-color: #667eea;
}

.filter-actions {
  justify-content: flex-end;
}

.search-btn {
  padding: 0.6rem 1.5rem;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 1rem;
  font-weight: 500;
  transition: opacity 0.2s;
}

.search-btn:hover {
  opacity: 0.9;
}

/* 加载和错误状态 */
.loading-state,
.error-state,
.empty-state {
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

/* 论文列表 */
.papers-container {
  margin-top: 2rem;
}

.papers-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
}

.papers-header h3 {
  margin: 0;
  color: #2c3e50;
  font-size: 1.2rem;
}

.date-badge {
  background-color: #667eea;
  color: white;
  padding: 0.4rem 0.8rem;
  border-radius: 20px;
  font-size: 0.9rem;
  font-weight: 500;
}

.papers-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
  gap: 1.5rem;
}

.paper-card {
  background: white;
  border-radius: 8px;
  padding: 1.5rem;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  transition: transform 0.2s, box-shadow 0.2s;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.paper-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
}

.paper-link {
  text-decoration: none;
  color: inherit;
}

.paper-title {
  margin: 0;
  font-size: 1.1rem;
  color: #2c3e50;
  line-height: 1.4;
  font-weight: 600;
}

.paper-title:hover {
  color: #667eea;
}

.paper-meta {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  font-size: 0.85rem;
}

.meta-item {
  display: flex;
  gap: 0.5rem;
}

.meta-label {
  color: #7f8c8d;
  font-weight: 500;
  flex-shrink: 0;
}

.meta-value {
  color: #34495e;
  flex: 1;
}

.paper-summary {
  margin: 0;
  font-size: 0.9rem;
  color: #555;
  line-height: 1.6;
  flex: 1;
}

.paper-footer {
  display: flex;
  gap: 1rem;
  margin-top: auto;
}

.view-btn,
.pdf-btn {
  padding: 0.5rem 1rem;
  border-radius: 4px;
  text-decoration: none;
  font-size: 0.9rem;
  font-weight: 500;
  transition: opacity 0.2s;
}

.view-btn {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.view-btn:hover {
  opacity: 0.9;
}

.pdf-btn {
  background-color: #ecf0f1;
  color: #2c3e50;
}

.pdf-btn:hover {
  background-color: #bdc3c7;
}

/* 分页 */
.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 1rem;
  margin-top: 2rem;
}

.page-btn {
  padding: 0.5rem 1.5rem;
  background-color: #667eea;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.95rem;
  transition: opacity 0.2s;
}

.page-btn:hover:not(:disabled) {
  opacity: 0.9;
}

.page-btn:disabled {
  background-color: #bdc3c7;
  cursor: not-allowed;
}

.page-info {
  font-weight: 500;
  color: #2c3e50;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .filter-grid {
    grid-template-columns: 1fr;
  }

  .papers-grid {
    grid-template-columns: 1fr;
  }

  .paper-card {
    padding: 1rem;
  }
}
</style>
