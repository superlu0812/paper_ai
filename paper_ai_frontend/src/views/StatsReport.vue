<script setup>
import { ref, onMounted, computed } from 'vue'
import { getDailyStats } from '../api'
import dayjs from 'dayjs'

// 数据状态
const loading = ref(false)
const error = ref(null)
const dailyStats = ref([])
const totalDates = ref(0)
const totalPapers = ref(0)

// 加载统计数据
async function loadStats() {
  loading.value = true
  error.value = null

  try {
    const response = await getDailyStats()
    dailyStats.value = response.daily_stats || []
    totalDates.value = response.total_dates || 0
    totalPapers.value = response.total_papers || 0
    
    // 按日期倒序排列（最新的在前）
    dailyStats.value.sort((a, b) => {
      return dayjs(b.date).valueOf() - dayjs(a.date).valueOf()
    })
  } catch (err) {
    error.value = err.message || '加载统计数据失败'
    console.error('Failed to load stats:', err)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadStats()
})

// 格式化日期
function formatDate(dateStr) {
  return dayjs(dateStr).format('YYYY年MM月DD日')
}

// 计算最大数量（用于图表比例）
const maxCount = computed(() => {
  if (dailyStats.value.length === 0) return 1
  return Math.max(...dailyStats.value.map(stat => stat.count))
})

// 计算百分比（用于图表显示）
function getPercentage(count) {
  if (maxCount.value === 0) return 0
  return (count / maxCount.value) * 100
}

// 获取颜色（根据数量）
function getBarColor(count) {
  const percentage = getPercentage(count)
  if (percentage >= 80) return '#667eea'
  if (percentage >= 50) return '#764ba2'
  if (percentage >= 30) return '#f093fb'
  return '#4facfe'
}
</script>

<template>
  <div class="stats-report">
    <div class="stats-header">
      <h2>📊 论文统计报表</h2>
      <button class="refresh-btn" @click="loadStats" :disabled="loading">
        {{ loading ? '加载中...' : '🔄 刷新' }}
      </button>
    </div>

    <!-- 加载状态 -->
    <div v-if="loading" class="loading-state">
      <div class="spinner"></div>
      <p>加载中...</p>
    </div>

    <!-- 错误状态 -->
    <div v-else-if="error" class="error-state">
      <p>⚠️ {{ error }}</p>
      <button class="retry-btn" @click="loadStats">重试</button>
    </div>

    <!-- 统计内容 -->
    <div v-else class="stats-content">
      <!-- 总体统计 -->
      <div class="summary-cards">
        <div class="summary-card">
          <div class="card-icon">📅</div>
          <div class="card-content">
            <div class="card-label">总日期数</div>
            <div class="card-value">{{ totalDates }}</div>
          </div>
        </div>
        <div class="summary-card">
          <div class="card-icon">📄</div>
          <div class="card-content">
            <div class="card-label">总论文数</div>
            <div class="card-value">{{ totalPapers }}</div>
          </div>
        </div>
        <div class="summary-card">
          <div class="card-icon">📈</div>
          <div class="card-content">
            <div class="card-label">平均每日</div>
            <div class="card-value">
              {{ totalDates > 0 ? Math.round(totalPapers / totalDates) : 0 }}
            </div>
          </div>
        </div>
      </div>

      <!-- 每日统计列表 -->
      <div class="daily-stats-section">
        <h3>每日论文数量统计</h3>
        <div v-if="dailyStats.length === 0" class="empty-state">
          <p>😕 暂无统计数据</p>
        </div>
        <div v-else class="stats-list">
          <div
            v-for="stat in dailyStats"
            :key="stat.date"
            class="stat-item"
          >
            <div class="stat-date">
              <span class="date-text">{{ formatDate(stat.date) }}</span>
              <span class="date-original">({{ stat.date }})</span>
            </div>
            <div class="stat-bar-container">
              <div
                class="stat-bar"
                :style="{
                  width: `${getPercentage(stat.count)}%`,
                  backgroundColor: getBarColor(stat.count)
                }"
              >
                <span class="stat-count">{{ stat.count }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 图表视图（可选） -->
      <div class="chart-section">
        <h3>趋势图表</h3>
        <div class="chart-container">
          <div
            v-for="stat in dailyStats"
            :key="stat.date"
            class="chart-bar"
            :style="{
              height: `${getPercentage(stat.count)}%`,
              backgroundColor: getBarColor(stat.count)
            }"
            :title="`${formatDate(stat.date)}: ${stat.count} 篇`"
          >
            <span class="chart-label">{{ stat.count }}</span>
          </div>
        </div>
        <div class="chart-footer">
          <div
            v-for="stat in dailyStats.slice(0, 10)"
            :key="stat.date"
            class="chart-date-label"
          >
            {{ dayjs(stat.date).format('MM/DD') }}
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.stats-report {
  width: 100%;
}

.stats-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2rem;
  background: white;
  padding: 1.5rem;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.stats-header h2 {
  margin: 0;
  color: #2c3e50;
  font-size: 1.5rem;
}

.refresh-btn {
  padding: 0.6rem 1.2rem;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.95rem;
  font-weight: 500;
  transition: opacity 0.2s;
}

.refresh-btn:hover:not(:disabled) {
  opacity: 0.9;
}

.refresh-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* 加载和错误状态 */
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

.retry-btn {
  margin-top: 1rem;
  padding: 0.6rem 1.2rem;
  background-color: #667eea;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.95rem;
}

.retry-btn:hover {
  background-color: #5568d3;
}

/* 统计内容 */
.stats-content {
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

/* 总体统计卡片 */
.summary-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1.5rem;
}

.summary-card {
  background: white;
  border-radius: 8px;
  padding: 1.5rem;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  display: flex;
  align-items: center;
  gap: 1rem;
  transition: transform 0.2s, box-shadow 0.2s;
}

.summary-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
}

.card-icon {
  font-size: 2.5rem;
  line-height: 1;
}

.card-content {
  flex: 1;
}

.card-label {
  font-size: 0.9rem;
  color: #7f8c8d;
  margin-bottom: 0.5rem;
}

.card-value {
  font-size: 2rem;
  font-weight: 600;
  color: #2c3e50;
}

/* 每日统计列表 */
.daily-stats-section {
  background: white;
  border-radius: 8px;
  padding: 1.5rem;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.daily-stats-section h3 {
  margin: 0 0 1.5rem 0;
  color: #2c3e50;
  font-size: 1.2rem;
}

.empty-state {
  text-align: center;
  padding: 3rem;
  color: #7f8c8d;
}

.stats-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 0.8rem;
  border-radius: 4px;
  background-color: #f8f9fa;
  transition: background-color 0.2s;
}

.stat-item:hover {
  background-color: #e9ecef;
}

.stat-date {
  min-width: 180px;
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
}

.date-text {
  font-weight: 500;
  color: #2c3e50;
  font-size: 0.95rem;
}

.date-original {
  font-size: 0.8rem;
  color: #7f8c8d;
}

.stat-bar-container {
  flex: 1;
  position: relative;
  height: 32px;
  background-color: #e9ecef;
  border-radius: 4px;
  overflow: hidden;
}

.stat-bar {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  padding-right: 0.8rem;
  transition: width 0.3s ease;
  border-radius: 4px;
}

.stat-count {
  color: white;
  font-weight: 600;
  font-size: 0.9rem;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.2);
}

/* 图表视图 */
.chart-section {
  background: white;
  border-radius: 8px;
  padding: 1.5rem;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.chart-section h3 {
  margin: 0 0 1.5rem 0;
  color: #2c3e50;
  font-size: 1.2rem;
}

.chart-container {
  display: flex;
  align-items: flex-end;
  justify-content: space-around;
  gap: 0.5rem;
  height: 300px;
  padding: 1rem 0;
  border-bottom: 2px solid #e9ecef;
}

.chart-bar {
  flex: 1;
  min-width: 40px;
  position: relative;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  border-radius: 4px 4px 0 0;
  transition: all 0.3s ease;
  cursor: pointer;
}

.chart-bar:hover {
  opacity: 0.8;
  transform: scaleY(1.05);
}

.chart-label {
  position: absolute;
  top: -20px;
  color: #2c3e50;
  font-size: 0.8rem;
  font-weight: 600;
  white-space: nowrap;
}

.chart-footer {
  display: flex;
  justify-content: space-around;
  gap: 0.5rem;
  margin-top: 0.5rem;
  padding-top: 0.5rem;
}

.chart-date-label {
  flex: 1;
  text-align: center;
  font-size: 0.75rem;
  color: #7f8c8d;
  min-width: 40px;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .stats-header {
    flex-direction: column;
    gap: 1rem;
    align-items: flex-start;
  }

  .summary-cards {
    grid-template-columns: 1fr;
  }

  .stat-item {
    flex-direction: column;
    align-items: flex-start;
  }

  .stat-date {
    min-width: auto;
    width: 100%;
  }

  .stat-bar-container {
    width: 100%;
  }

  .chart-container {
    height: 200px;
    gap: 0.3rem;
  }

  .chart-bar {
    min-width: 30px;
  }

  .chart-label {
    font-size: 0.7rem;
    top: -18px;
  }

  .chart-date-label {
    font-size: 0.7rem;
  }
}
</style>
