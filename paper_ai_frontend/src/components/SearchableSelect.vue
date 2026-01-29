<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'

const props = defineProps({
  modelValue: {
    type: String,
    default: ''
  },
  options: {
    type: Array,
    default: () => []
  },
  placeholder: {
    type: String,
    default: '请选择...'
  },
  searchPlaceholder: {
    type: String,
    default: '搜索...'
  },
  emptyText: {
    type: String,
    default: '没有找到匹配的选项'
  }
})

const emit = defineEmits(['update:modelValue', 'change'])

const showDropdown = ref(false)
const searchQuery = ref('')
const selectedOption = ref(props.modelValue)

// 监听外部值变化
watch(() => props.modelValue, (newVal) => {
  selectedOption.value = newVal
})

// 过滤选项
const filteredOptions = computed(() => {
  if (!searchQuery.value.trim()) {
    return props.options
  }
  const query = searchQuery.value.toLowerCase()
  return props.options.filter(option => {
    const optionText = typeof option === 'string' 
      ? (option === '' ? props.placeholder : option)
      : (option.label || option.value || '')
    return optionText.toLowerCase().includes(query)
  })
})

// 获取选项显示文本
function getOptionText(option) {
  if (typeof option === 'string') {
    // 空字符串显示为占位符文本
    return option === '' ? props.placeholder : option
  }
  return option.label || option.value || ''
}

// 获取选项值
function getOptionValue(option) {
  if (typeof option === 'string') return option
  return option.value || option
}

// 选择选项
function selectOption(option) {
  const value = getOptionValue(option)
  selectedOption.value = value
  emit('update:modelValue', value)
  emit('change', value)
  showDropdown.value = false
  searchQuery.value = ''
}

// 清除选择
function clearSelection() {
  selectedOption.value = ''
  emit('update:modelValue', '')
  emit('change', '')
  searchQuery.value = ''
}

// 获取当前选中项的显示文本
const displayText = computed(() => {
  if (selectedOption.value === null || selectedOption.value === undefined) {
    return ''
  }
  const option = props.options.find(opt => getOptionValue(opt) === selectedOption.value)
  if (option) {
    return getOptionText(option)
  }
  return selectedOption.value || ''
})

// 点击外部关闭下拉框
function handleClickOutside(event) {
  const select = event.target.closest('.searchable-select-container')
  if (!select && showDropdown.value) {
    showDropdown.value = false
    searchQuery.value = ''
  }
}

// 处理键盘事件
function handleKeydown(event) {
  if (!showDropdown.value) return
  
  if (event.key === 'Escape') {
    showDropdown.value = false
    searchQuery.value = ''
  }
}

onMounted(() => {
  document.addEventListener('click', handleClickOutside)
  document.addEventListener('keydown', handleKeydown)
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
  document.removeEventListener('keydown', handleKeydown)
})
</script>

<template>
  <div class="searchable-select-container">
    <div class="select-input-wrapper" @click="showDropdown = !showDropdown">
      <input
        type="text"
        :value="displayText"
        readonly
        class="select-input"
        :placeholder="placeholder"
      />
      <div class="select-actions">
        <button
          v-if="selectedOption"
          @click.stop="clearSelection()"
          class="clear-btn"
          title="清除选择"
        >
          ✕
        </button>
        <span class="dropdown-icon" :class="{ 'open': showDropdown }">▼</span>
      </div>
    </div>
    
    <!-- 下拉选项 -->
    <div v-if="showDropdown" class="dropdown-menu">
      <!-- 搜索框 -->
      <div class="search-box">
        <input
          type="text"
          v-model="searchQuery"
          :placeholder="searchPlaceholder"
          class="search-input"
          @click.stop
          @input.stop
        />
      </div>
      
      <!-- 选项列表 -->
      <div class="options-list">
        <div
          v-if="filteredOptions.length === 0"
          class="option-item empty-option"
        >
          {{ emptyText }}
        </div>
        <div
          v-for="(option, index) in filteredOptions"
          :key="index"
          class="option-item"
          :class="{ 'selected': getOptionValue(option) === selectedOption }"
          @click.stop="selectOption(option)"
        >
          {{ getOptionText(option) }}
        </div>
      </div>
      
      <!-- 统计信息 -->
      <div v-if="searchQuery && filteredOptions.length > 0" class="search-info">
        找到 {{ filteredOptions.length }} 个匹配项
      </div>
    </div>
  </div>
</template>

<style scoped>
.searchable-select-container {
  position: relative;
  width: 100%;
}

.select-input-wrapper {
  position: relative;
  display: flex;
  align-items: center;
  cursor: pointer;
}

.select-input {
  flex: 1;
  padding: 0.6rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 0.95rem;
  cursor: pointer;
  transition: border-color 0.2s;
  background-color: white;
}

.select-input:hover {
  border-color: #667eea;
}

.select-input:focus {
  outline: none;
  border-color: #667eea;
}

.select-actions {
  position: absolute;
  right: 0.5rem;
  display: flex;
  align-items: center;
  gap: 0.3rem;
  pointer-events: none;
}

.clear-btn {
  background: #e74c3c;
  color: white;
  border: none;
  border-radius: 50%;
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  font-size: 0.7rem;
  line-height: 1;
  transition: background-color 0.2s;
  pointer-events: all;
  flex-shrink: 0;
}

.clear-btn:hover {
  background: #c0392b;
}

.dropdown-icon {
  font-size: 0.7rem;
  color: #7f8c8d;
  transition: transform 0.2s;
  pointer-events: none;
  flex-shrink: 0;
}

.dropdown-icon.open {
  transform: rotate(180deg);
}

/* 下拉菜单 */
.dropdown-menu {
  position: absolute;
  top: calc(100% + 0.25rem);
  left: 0;
  right: 0;
  z-index: 1000;
  background: white;
  border-radius: 8px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
  overflow: hidden;
  animation: slideDown 0.2s ease;
  max-height: 300px;
  display: flex;
  flex-direction: column;
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

/* 搜索框 */
.search-box {
  padding: 0.75rem;
  border-bottom: 1px solid #e9ecef;
  background-color: #f8f9fa;
}

.search-input {
  width: 100%;
  padding: 0.5rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 0.9rem;
  transition: border-color 0.2s;
}

.search-input:focus {
  outline: none;
  border-color: #667eea;
}

/* 选项列表 */
.options-list {
  max-height: 200px;
  overflow-y: auto;
  padding: 0.25rem 0;
}

.option-item {
  padding: 0.75rem 1rem;
  cursor: pointer;
  transition: background-color 0.2s;
  font-size: 0.95rem;
  color: #2c3e50;
}

.option-item:hover {
  background-color: #f0f4ff;
}

.option-item.selected {
  background-color: #667eea;
  color: white;
  font-weight: 500;
}

.option-item.empty-option {
  color: #7f8c8d;
  cursor: default;
  text-align: center;
  font-style: italic;
}

.option-item.empty-option:hover {
  background-color: transparent;
}

/* 搜索信息 */
.search-info {
  padding: 0.5rem 1rem;
  font-size: 0.85rem;
  color: #7f8c8d;
  background-color: #f8f9fa;
  border-top: 1px solid #e9ecef;
  text-align: center;
}

/* 滚动条样式 */
.options-list::-webkit-scrollbar {
  width: 6px;
}

.options-list::-webkit-scrollbar-track {
  background: #f1f1f1;
}

.options-list::-webkit-scrollbar-thumb {
  background: #bdc3c7;
  border-radius: 3px;
}

.options-list::-webkit-scrollbar-thumb:hover {
  background: #95a5a6;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .dropdown-menu {
    max-height: 250px;
  }
  
  .options-list {
    max-height: 150px;
  }
  
  .option-item {
    padding: 0.6rem 0.8rem;
    font-size: 0.9rem;
  }
}
</style>
