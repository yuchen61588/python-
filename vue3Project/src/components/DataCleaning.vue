<script setup>
import { ref, reactive, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useDataStore } from '../stores/index'
import { cleanData } from '../utils/api'

const props = defineProps({
  data: {
    type: Array,
    required: true
  }
})

const emit = defineEmits(['update:data', 'cleaningComplete'])

const dataStore = useDataStore()
const loading = ref(false)

const cleaningOptions = ref([
  { label: '缺失值处理', value: 'missing_values' },
  { label: '异常值检测', value: 'outliers' },
  { label: '数据标准化', value: 'standardization' }
])
const selectedOption = ref('missing_values')

const columns = computed(() => {
  if (!props.data || props.data.length === 0) return []
  return Object.keys(props.data[0]).map(key => ({
    prop: key,
    label: key
  }))
})

const selectedColumns = ref([])
const missingValueStrategy = ref('mean')
const missingValueStrategies = [
  { label: '均值填充', value: 'mean' },
  { label: '中位数填充', value: 'median' },
  { label: '众数填充', value: 'mode' },
  { label: '删除含缺失值的行', value: 'drop' }
]

const outlierStrategy = ref('zscore')
const outlierStrategies = [
  { label: 'Z-score方法', value: 'zscore' },
  { label: 'IQR四分位法', value: 'iqr' }
]

const standardizationStrategy = ref('z_score')
const standardizationStrategies = [
  { label: 'Z-score标准化', value: 'z_score' },
  { label: '最小-最大标准化', value: 'min_max' }
]

// 执行数据清洗
const runDataCleaning = async () => {
  if (selectedColumns.value.length === 0) {
    ElMessage.warning('请至少选择一列进行处理')
    return
  }
  
  loading.value = true
  
  try {
    // 构建清洗参数
    const parameters = {}
    
    switch (selectedOption.value) {
      case 'missing_values':
        parameters.strategy = missingValueStrategy.value
        parameters.columns = selectedColumns.value
        break
      case 'outliers':
        parameters.method = outlierStrategy.value
        parameters.columns = selectedColumns.value
        parameters.threshold = 3.0 // z-score阈值，可以根据需要调整
        break
      case 'standardization':
        parameters.method = standardizationStrategy.value
        parameters.columns = selectedColumns.value
        break
    }
    
    // 调用后端API处理数据
    // 注意：这里还需要从dataStore获取当前文件ID
    if (dataStore.currentFile) {
      const response = await cleanData(
        dataStore.currentFile.id,
        selectedOption.value,
        parameters
      )
      
      if (response.data) {
        // 假设后端返回清洗后的数据
        if (response.data.result) {
          updateData(response.data.result)
          ElMessage.success(`${getCleaningOptionLabel(selectedOption.value)}完成`)
        } else {
          // 本地处理方案（当后端未返回具体数据时）
          localDataProcessing()
        }
      }
    } else {
      // 本地处理方案（当没有文件ID时）
      localDataProcessing()
    }
  } catch (error) {
    console.error('数据清洗失败:', error)
    ElMessage.error('数据清洗失败: ' + (error.message || '未知错误'))
    
    // 本地处理方案（当API调用失败时）
    localDataProcessing()
  } finally {
    loading.value = false
  }
}

// 本地数据处理（后端API不可用时的备选方案）
const localDataProcessing = () => {
  switch (selectedOption.value) {
    case 'missing_values':
      handleMissingValues()
      break
    case 'outliers':
      handleOutliers()
      break
    case 'standardization':
      handleStandardization()
      break
  }
}

// 获取清洗选项的显示标签
const getCleaningOptionLabel = (value) => {
  const option = cleaningOptions.value.find(opt => opt.value === value)
  return option ? option.label : value
}

// 处理缺失值
const handleMissingValues = () => {
  const processedData = [...props.data]
  const columnsToProcess = selectedColumns.value
  
  if (missingValueStrategy.value === 'drop') {
    // 删除含有缺失值的行
    const filteredData = processedData.filter(row => {
      return columnsToProcess.every(column => {
        const value = row[column]
        return value !== null && value !== undefined && value !== ''
      })
    })
    updateData(filteredData)
    ElMessage.success(`已删除包含缺失值的行，剩余${filteredData.length}条数据`)
    return
  }
  
  // 对每一列进行处理
  columnsToProcess.forEach(column => {
    // 计算统计值
    const values = processedData.map(row => {
      const val = row[column]
      return val !== null && val !== undefined && val !== '' ? Number(val) : null
    }).filter(val => val !== null)
    
    let fillValue
    
    switch (missingValueStrategy.value) {
      case 'mean':
        // 计算均值
        fillValue = values.reduce((sum, val) => sum + val, 0) / values.length
        break
      case 'median':
        // 计算中位数
        values.sort((a, b) => a - b)
        const mid = Math.floor(values.length / 2)
        fillValue = values.length % 2 === 0 ? (values[mid - 1] + values[mid]) / 2 : values[mid]
        break
      case 'mode':
        // 计算众数
        const counts = {}
        values.forEach(val => {
          counts[val] = (counts[val] || 0) + 1
        })
        fillValue = Object.keys(counts).reduce((a, b) => counts[a] > counts[b] ? a : b)
        break
    }
    
    // 填充缺失值
    processedData.forEach(row => {
      const val = row[column]
      if (val === null || val === undefined || val === '') {
        row[column] = fillValue
      }
    })
  })
  
  updateData(processedData)
  ElMessage.success('缺失值处理完成')
}

// 处理异常值
const handleOutliers = () => {
  const processedData = [...props.data]
  const columnsToProcess = selectedColumns.value
  
  // 对每一列进行处理
  columnsToProcess.forEach(column => {
    // 提取数值
    const values = processedData.map(row => Number(row[column]))
      .filter(val => !isNaN(val))
    
    let lowerBound, upperBound
    
    if (outlierStrategy.value === 'zscore') {
      // Z-score方法检测异常值
      const mean = values.reduce((sum, val) => sum + val, 0) / values.length
      const stdDev = Math.sqrt(values.reduce((sum, val) => sum + Math.pow(val - mean, 2), 0) / values.length)
      
      lowerBound = mean - 3 * stdDev
      upperBound = mean + 3 * stdDev
    } else {
      // 四分位法(IQR)检测异常值
      values.sort((a, b) => a - b)
      const q1Index = Math.floor(values.length * 0.25)
      const q3Index = Math.floor(values.length * 0.75)
      const q1 = values[q1Index]
      const q3 = values[q3Index]
      const iqr = q3 - q1
      
      lowerBound = q1 - 1.5 * iqr
      upperBound = q3 + 1.5 * iqr
    }
    
    // 处理异常值（设为边界值）
    processedData.forEach(row => {
      const val = Number(row[column])
      if (!isNaN(val)) {
        if (val < lowerBound) {
          row[column] = lowerBound
        } else if (val > upperBound) {
          row[column] = upperBound
        }
      }
    })
  })
  
  updateData(processedData)
  ElMessage.success('异常值处理完成')
}

// 数据标准化
const handleStandardization = () => {
  const processedData = [...props.data]
  const columnsToProcess = selectedColumns.value
  
  // 对每一列进行处理
  columnsToProcess.forEach(column => {
    // 提取数值
    const values = processedData.map(row => Number(row[column]))
      .filter(val => !isNaN(val))
    
    if (standardizationStrategy.value === 'z_score') {
      // Z-score标准化
      const mean = values.reduce((sum, val) => sum + val, 0) / values.length
      const stdDev = Math.sqrt(values.reduce((sum, val) => sum + Math.pow(val - mean, 2), 0) / values.length)
      
      processedData.forEach(row => {
        const val = Number(row[column])
        if (!isNaN(val)) {
          row[column] = (val - mean) / stdDev
        }
      })
    } else {
      // 最小-最大标准化
      const min = Math.min(...values)
      const max = Math.max(...values)
      const range = max - min
      
      processedData.forEach(row => {
        const val = Number(row[column])
        if (!isNaN(val)) {
          row[column] = (val - min) / range
        }
      })
    }
  })
  
  updateData(processedData)
  ElMessage.success('数据标准化完成')
}

// 更新数据
const updateData = (newData) => {
  emit('update:data', newData)
  dataStore.setCurrentData(newData)
}

// 完成清洗
const finishCleaning = () => {
  ElMessageBox.confirm('确认完成数据清洗？', '提示', {
    confirmButtonText: '确认',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(() => {
    ElMessage.success('数据清洗完成')
    emit('cleaningComplete', props.data)
  }).catch(() => {})
}
</script>

<template>
  <div class="data-cleaning">
    <el-card v-loading="loading">
      <template #header>
        <div class="card-header">
          <h2>数据清洗</h2>
          <el-button type="primary" @click="finishCleaning">完成清洗</el-button>
        </div>
      </template>
      
      <el-form label-width="120px">
        <el-form-item label="清洗方法">
          <el-select v-model="selectedOption" style="width: 100%">
            <el-option
              v-for="item in cleaningOptions"
              :key="item.value"
              :label="item.label"
              :value="item.value"
            />
          </el-select>
        </el-form-item>
        
        <el-form-item label="选择列">
          <el-select v-model="selectedColumns" multiple style="width: 100%" placeholder="请选择要处理的列">
            <el-option
              v-for="column in columns"
              :key="column.prop"
              :label="column.label"
              :value="column.prop"
            />
          </el-select>
        </el-form-item>
        
        <!-- 缺失值处理参数 -->
        <el-form-item v-if="selectedOption === 'missing_values'" label="处理策略">
          <el-select v-model="missingValueStrategy" style="width: 100%">
            <el-option
              v-for="item in missingValueStrategies"
              :key="item.value"
              :label="item.label"
              :value="item.value"
            />
          </el-select>
        </el-form-item>
        
        <!-- 异常值处理参数 -->
        <el-form-item v-if="selectedOption === 'outliers'" label="检测方法">
          <el-select v-model="outlierStrategy" style="width: 100%">
            <el-option
              v-for="item in outlierStrategies"
              :key="item.value"
              :label="item.label"
              :value="item.value"
            />
          </el-select>
        </el-form-item>
        
        <!-- 标准化参数 -->
        <el-form-item v-if="selectedOption === 'standardization'" label="标准化方法">
          <el-select v-model="standardizationStrategy" style="width: 100%">
            <el-option
              v-for="item in standardizationStrategies"
              :key="item.value"
              :label="item.label"
              :value="item.value"
            />
          </el-select>
        </el-form-item>
        
        <el-form-item>
          <el-button type="primary" @click="runDataCleaning">执行清洗</el-button>
        </el-form-item>
      </el-form>
      
      <div class="data-preview">
        <h3>数据预览</h3>
        <el-table :data="props.data.slice(0, 10)" border style="width: 100%" max-height="400">
          <el-table-column
            v-for="column in columns"
            :key="column.prop"
            :prop="column.prop"
            :label="column.label"
          />
        </el-table>
        <div class="data-summary">
          <p>总记录数: {{ props.data.length }}</p>
        </div>
      </div>
    </el-card>
  </div>
</template>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.data-preview {
  margin-top: 20px;
}

.data-summary {
  margin-top: 10px;
  font-size: 14px;
  color: #606266;
}
</style> 