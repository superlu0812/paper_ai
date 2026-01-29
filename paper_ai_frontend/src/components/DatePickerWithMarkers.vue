<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import dayjs from 'dayjs'

const props = defineProps({
  modelValue: {
    type: String,
    default: ''
  },
  min: {
    type: String,
    default: ''
  },
  max: {
    type: String,
    default: ''
  },
  markedDates: {
    type: Set,
    default: () => new Set()
  }
})

const emit = defineEmits(['update:modelValue', 'change'])

const showCalendar = ref(false)
const currentMonth = ref(dayjs())
const selectedDate = ref(props.modelValue ? dayjs(props.modelValue) : null)

// 监听外部值变化
watch(() => props.modelValue, (newVal) => {
  if (newVal) {
    selectedDate.value = dayjs(newVal)
    currentMonth.value = dayjs(newVal)
  } else {
    selectedDate.value = null
  }
})

// 生成日历网格
const calendarDays = computed(() => {
  const startOfMonth = currentMonth.value.startOf('month')
  const endOfMonth = currentMonth.value.endOf('month')
  const startDay = startOfMonth.day() // 0 = 周日, 6 = 周六
  const daysInMonth = endOfMonth.date()
  
  const days = []
  
  // 上个月的日期（填充第一周）
  for (let i = startDay - 1; i >= 0; i--) {
    const date = startOfMonth.subtract(i + 1, 'day')
    days.push({
      date,
      isCurrentMonth: false,
      isToday: date.isSame(dayjs(), 'day'),
      isSelected: selectedDate.value && date.isSame(selectedDate.value, 'day'),
      hasData: props.markedDates.has(date.format('YYYY-MM-DD'))
    })
  }
  
  // 当前月的日期
  for (let i = 1; i <= daysInMonth; i++) {
    const date = startOfMonth.date(i)
    days.push({
      date,
      isCurrentMonth: true,
      isToday: date.isSame(dayjs(), 'day'),
      isSelected: selectedDate.value && date.isSame(selectedDate.value, 'day'),
      hasData: props.markedDates.has(date.format('YYYY-MM-DD'))
    })
  }
  
  // 下个月的日期（填充最后一周）
  const remainingDays = 42 - days.length // 6行 x 7列 = 42
  for (let i = 1; i <= remainingDays; i++) {
    const date = endOfMonth.add(i, 'day')
    days.push({
      date,
      isCurrentMonth: false,
      isToday: date.isSame(dayjs(), 'day'),
      isSelected: selectedDate.value && date.isSame(selectedDate.value, 'day'),
      hasData: props.markedDates.has(date.format('YYYY-MM-DD'))
    })
  }
  
  return days
})

// 检查日期是否在范围内
function isDateInRange(date) {
  if (props.min && date.isBefore(dayjs(props.min), 'day')) return false
  if (props.max && date.isAfter(dayjs(props.max), 'day')) return false
  return true
}

// 选择日期
function selectDate(day) {
  if (!day.isCurrentMonth || !isDateInRange(day.date)) return
  
  selectedDate.value = day.date
  const dateStr = day.date.format('YYYY-MM-DD')
  emit('update:modelValue', dateStr)
  emit('change', dateStr)
  showCalendar.value = false
}

// 清除选择
function clearDate() {
  selectedDate.value = null
  emit('update:modelValue', '')
  emit('change', '')
}

// 切换月份
function changeMonth(delta) {
  currentMonth.value = currentMonth.value.add(delta, 'month')
}

// 格式化显示日期
const displayDate = computed(() => {
  if (!selectedDate.value) return ''
  return selectedDate.value.format('YYYY-MM-DD')
})

// 点击外部关闭日历
function handleClickOutside(event) {
  const calendar = event.target.closest('.date-picker-container')
  if (!calendar && showCalendar.value) {
    showCalendar.value = false
  }
}

onMounted(() => {
  document.addEventListener('click', handleClickOutside)
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
})
</script>

<template>
  <div class="date-picker-container">
    <div class="date-input-wrapper">
      <input
        type="text"
        :value="displayDate"
        readonly
        @click="showCalendar = !showCalendar"
        class="date-input"
        :class="{ 'has-data': displayDate && markedDates.has(displayDate) }"
        placeholder="选择日期"
      />
      <button
        v-if="displayDate"
        @click.stop="clearDate()"
        class="clear-btn"
        title="清除日期"
      >
        ✕
      </button>
      <button
        @click.stop="showCalendar = !showCalendar"
        class="calendar-btn"
        title="打开日历"
      >
        📅
      </button>
    </div>
    
    <!-- 日历弹窗 -->
    <div v-if="showCalendar" class="calendar-popup">
      <div class="calendar-header">
        <button @click="changeMonth(-1)" class="nav-btn">‹</button>
        <span class="month-year">{{ currentMonth.format('YYYY年MM月') }}</span>
        <button @click="changeMonth(1)" class="nav-btn">›</button>
      </div>
      
      <div class="calendar-weekdays">
        <div class="weekday" v-for="day in ['日', '一', '二', '三', '四', '五', '六']" :key="day">
          {{ day }}
        </div>
      </div>
      
      <div class="calendar-days">
        <div
          v-for="(day, index) in calendarDays"
          :key="index"
          class="calendar-day"
          :class="{
            'other-month': !day.isCurrentMonth,
            'today': day.isToday,
            'selected': day.isSelected,
            'has-data': day.hasData,
            'disabled': !isDateInRange(day.date)
          }"
          @click="selectDate(day)"
        >
          <span class="day-number">{{ day.date.date() }}</span>
          <span v-if="day.hasData" class="data-dot"></span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.date-picker-container {
  position: relative;
  width: 100%;
}

.date-input-wrapper {
  position: relative;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.date-input {
  flex: 1;
  padding: 0.6rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 0.95rem;
  cursor: pointer;
  transition: border-color 0.2s, background-color 0.2s;
}

.date-input:hover {
  border-color: #667eea;
}

.date-input.has-data {
  border-color: #667eea;
  background-color: #f0f4ff;
}

.date-input:focus {
  outline: none;
  border-color: #667eea;
}

.clear-btn,
.calendar-btn {
  background: transparent;
  border: none;
  cursor: pointer;
  font-size: 1rem;
  padding: 0.3rem;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: opacity 0.2s;
  flex-shrink: 0;
}

.clear-btn {
  color: #e74c3c;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background-color: #fee;
}

.clear-btn:hover {
  background-color: #fcc;
}

.calendar-btn {
  color: #667eea;
}

.calendar-btn:hover {
  opacity: 0.7;
}

/* 日历弹窗 */
.calendar-popup {
  position: absolute;
  top: calc(100% + 0.5rem);
  left: 0;
  z-index: 1000;
  background: white;
  border-radius: 8px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
  padding: 1rem;
  min-width: 280px;
  animation: slideDown 0.2s ease;
}

@keyframes slideDown {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.calendar-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
  padding-bottom: 0.5rem;
  border-bottom: 1px solid #e9ecef;
}

.nav-btn {
  background: #f8f9fa;
  border: none;
  border-radius: 4px;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  font-size: 1.2rem;
  color: #2c3e50;
  transition: background-color 0.2s;
}

.nav-btn:hover {
  background: #e9ecef;
}

.month-year {
  font-weight: 600;
  color: #2c3e50;
  font-size: 1rem;
}

.calendar-weekdays {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 0.25rem;
  margin-bottom: 0.5rem;
}

.weekday {
  text-align: center;
  font-weight: 600;
  color: #7f8c8d;
  font-size: 0.85rem;
  padding: 0.5rem 0;
}

.calendar-days {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 0.25rem;
}

.calendar-day {
  position: relative;
  aspect-ratio: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  border-radius: 4px;
  transition: all 0.2s;
  font-size: 0.9rem;
}

.calendar-day:hover:not(.disabled) {
  background-color: #f0f4ff;
}

.calendar-day.other-month {
  color: #bdc3c7;
}

.calendar-day.today {
  font-weight: 600;
  color: #667eea;
}

.calendar-day.today:not(.selected) {
  border: 2px solid #667eea;
}

.calendar-day.selected {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  font-weight: 600;
}

.calendar-day.has-data:not(.selected) {
  position: relative;
}

.calendar-day.disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.day-number {
  position: relative;
  z-index: 1;
}

.data-dot {
  position: absolute;
  bottom: 4px;
  right: 4px;
  width: 6px;
  height: 6px;
  background-color: #27ae60;
  border-radius: 50%;
  z-index: 2;
}

.calendar-day.selected .data-dot {
  background-color: white;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .calendar-popup {
    min-width: 260px;
    padding: 0.8rem;
  }
  
  .calendar-day {
    font-size: 0.85rem;
  }
  
  .data-dot {
    width: 5px;
    height: 5px;
    bottom: 3px;
    right: 3px;
  }
}
</style>
