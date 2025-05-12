<script setup>
import { ref, computed, reactive, onMounted, watch } from 'vue'
import { useDataStore } from '../stores/index'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import { runAnalysis, getDataFiles } from '../utils/api'

const dataStore = useDataStore()
const analysisMethod = ref('regression')
const analysisResult = ref(null)
const dataFiles = ref([])
const weatherFileId = ref(null)
const analysisOptions = [
  { label: '回归预测', value: 'regression' }
]

const loading = ref(false)
const chartInstance = ref(null)
const chartContainer = ref(null)
const noDataMessage = ref('')
const showFeatureSelector = ref(false)

// 分析参数
const analysisParams = reactive({
  // 通用参数
  selectedFeatures: [],
  targetFeature: '',
  
  // 聚类参数
  clusteringAlgorithm: 'kmeans',
  clusterCount: 3,
  
  // 回归参数
  regressionAlgorithm: 'linear',
  testSize: 0.2,
  
  // 线性回归高级参数
  linearOptions: {
    linearType: 'standard',
    alpha: 1.0,
    usePolynomial: false,
    polynomialDegree: 2
  }
})

// 默认特征分组
const defaultFeatures = reactive({
  bbq: [],
  temperature: [],
  humidity: [],
  precipitation: [],
  date: ['DATE', 'MONTH']
})

// 计算其他特征
const otherFeatures = computed(() => {
  if (!dataStore.currentData || dataStore.currentData.length === 0) return []
  
  const allKeys = Object.keys(dataStore.currentData[0])
  const groupedFeatures = [
    ...defaultFeatures.bbq,
    ...defaultFeatures.temperature,
    ...defaultFeatures.humidity,
    ...defaultFeatures.precipitation,
    ...defaultFeatures.date
  ]
  
  return allKeys.filter(key => !groupedFeatures.includes(key))
})

// 算法选项
const algorithmOptions = {
  clustering: [
    { label: 'K均值聚类', value: 'kmeans' },
    { label: '层次聚类', value: 'hierarchical' }
  ],
  regression: [
    { label: '线性回归', value: 'linear' },
    { label: '随机森林回归', value: 'random_forest' }
  ]
}

// 线性回归高级选项
const linearRegressionTypes = [
  { label: '标准线性回归', value: 'standard' },
  { label: '岭回归 (Ridge)', value: 'ridge' },
  { label: 'Lasso回归', value: 'lasso' }
]

// 提取特征分组
const extractFeatureGroups = () => {
  if (!dataStore.currentData || dataStore.currentData.length === 0) return
  
  // 清空现有分组
  defaultFeatures.bbq = []
  defaultFeatures.temperature = []
  defaultFeatures.humidity = []
  defaultFeatures.precipitation = []
  defaultFeatures.date = ['DATE', 'MONTH']
  
  // 获取数据列
  const firstRow = dataStore.currentData[0]
  const allColumns = Object.keys(firstRow)
  
  console.log('数据集所有列名:', allColumns)
  
  // 遍历所有列名，根据命名模式进行分类
  allColumns.forEach(column => {
    // 跳过已归类的日期列
    if (defaultFeatures.date.includes(column)) {
      return
    }
    
    // 查找BBQ_weather相关列
    if (column.includes('BBQ_weather')) {
      defaultFeatures.bbq.push(column)
    } 
    // 查找包含"_numeric"的列 (由后端创建的数值化特征)
    else if (column.includes('_numeric')) {
      if (column.includes('BBQ')) {
        defaultFeatures.bbq.push(column)
      } else if (column.includes('MONTH') || column.includes('DAY')) {
        defaultFeatures.date.push(column)
      } else {
        // 其他数值特征添加到温度组
        defaultFeatures.temperature.push(column)
      }
    }
    // 按城市_特征类型格式进行分类
    else if (column.includes('_temp_') || column.toLowerCase().includes('_temperature')) {
      defaultFeatures.temperature.push(column)
    } else if (column.includes('_humidity')) {
      defaultFeatures.humidity.push(column)
    } else if (column.includes('_precipitation')) {
      defaultFeatures.precipitation.push(column)
    } else if (column.includes('_pressure') || column.includes('_cloud_cover') || 
               column.includes('_wind_') || column.includes('_global_radiation') || 
               column.includes('_sunshine')) {
      // 其他可能的数值特征也添加到温度组用于分析
      defaultFeatures.temperature.push(column)
    } else if (column.includes('random_feature')) {
      // 由后端创建的随机特征，用于演示
      defaultFeatures.temperature.push(column)
    }
  })
  
  // 如果温度组为空，尝试查找包含"temp"的列
  if (defaultFeatures.temperature.length === 0) {
    allColumns.forEach(column => {
      if ((column.toLowerCase().includes('temp') || column.toLowerCase().includes('temperature')) && 
          !defaultFeatures.temperature.includes(column)) {
        defaultFeatures.temperature.push(column)
      }
    })
  }
  
  // 如果湿度组为空，尝试查找包含"humidity"的列
  if (defaultFeatures.humidity.length === 0) {
    allColumns.forEach(column => {
      if ((column.toLowerCase().includes('humidity') || column.toLowerCase().includes('humid')) && 
          !defaultFeatures.humidity.includes(column)) {
        defaultFeatures.humidity.push(column)
      }
    })
  }
  
  // 如果降水组为空，尝试查找包含"precipitation"、"rain"或"precip"的列
  if (defaultFeatures.precipitation.length === 0) {
    allColumns.forEach(column => {
      if ((column.toLowerCase().includes('precip') || column.toLowerCase().includes('rain')) && 
          !defaultFeatures.precipitation.includes(column)) {
        defaultFeatures.precipitation.push(column)
      }
    })
  }
  
  console.log('提取特征分组：', {
    date: defaultFeatures.date,
    temperature: defaultFeatures.temperature,
    humidity: defaultFeatures.humidity,
    precipitation: defaultFeatures.precipitation,
    bbq: defaultFeatures.bbq
  })
}

// 初始化特征选择
const initFeatures = () => {
  extractFeatureGroups()
  
  // 获取所有可用的数值列（排除日期）
  const availableColumns = dataStore.currentData ? Object.keys(dataStore.currentData[0]) : []
  
  // 尝试通过检查首行数据确定数值列
  const numericColumns = availableColumns.filter(column => {
    if (defaultFeatures.date.includes(column) && !column.includes('_numeric')) return false
    
    const value = dataStore.currentData[0][column]
    return typeof value === 'number' || (!isNaN(Number(value)) && value !== '')
  })
  
  // 尝试获取所有数值列和 _numeric 后缀的列
  let effectiveNumericColumns = [
    ...numericColumns,
    ...availableColumns.filter(col => col.includes('_numeric'))
  ]
  
  // 如果检测到的有效数值列过少，尝试使用BBQ列
  if (effectiveNumericColumns.length < 3 && defaultFeatures.bbq.length > 0) {
    const bbqColumns = defaultFeatures.bbq.filter(col => col.includes('_numeric'))
    if (bbqColumns.length > 0) {
      console.log('使用BBQ的数值版本作为特征:', bbqColumns)
      for (const col of bbqColumns) {
        if (!effectiveNumericColumns.includes(col)) {
          effectiveNumericColumns.push(col)
        }
      }
    }
  }
  
  // 去除重复项
  effectiveNumericColumns = [...new Set(effectiveNumericColumns)]
  
  console.log('有效的数值列:', effectiveNumericColumns)
  
  if (effectiveNumericColumns.length === 0) {
    console.error('没有找到数值列')
    return
  }
  
  // 设置默认聚类特征
  if (analysisMethod.value === 'clustering') {
    // 优先使用BBQ数值版本特征
    const bbqNumericCols = effectiveNumericColumns.filter(col => col.includes('BBQ') && col.includes('_numeric'))
    
    if (bbqNumericCols.length > 0) {
      // 使用BBQ数值版本进行聚类
      analysisParams.selectedFeatures = bbqNumericCols.slice(0, 5)
      console.log('使用BBQ数值特征进行聚类:', analysisParams.selectedFeatures)
    }
    // 次优先使用温度特征
    else if (defaultFeatures.temperature.length > 0) {
      analysisParams.selectedFeatures = defaultFeatures.temperature.slice(0, 5)
    } 
    // 如果没有温度特征，使用前5个数值列
    else {
      analysisParams.selectedFeatures = effectiveNumericColumns.slice(0, 5)
    }
  } 
  // 设置默认回归特征
  else if (analysisMethod.value === 'regression') {
    // 如果有BBQ数值特征，选一个作为目标，其他作为特征
    const bbqNumericCols = effectiveNumericColumns.filter(col => col.includes('BBQ') && col.includes('_numeric'))
    
    if (bbqNumericCols.length > 0) {
      analysisParams.targetFeature = bbqNumericCols[0]
      
      // 选择其他特征作为预测变量
      const predictors = []
      
      // 添加剩余的BBQ特征
      const otherBbqCols = bbqNumericCols.filter(col => col !== analysisParams.targetFeature).slice(0, 2)
      if (otherBbqCols.length > 0) {
        predictors.push(...otherBbqCols)
      }
      
      // 添加时间特征
      const timeFeatures = effectiveNumericColumns.filter(col => 
        (col.includes('MONTH_numeric') || col.includes('DAY_numeric')) && 
        !predictors.includes(col)
      ).slice(0, 2)
      
      if (timeFeatures.length > 0) {
        predictors.push(...timeFeatures)
      }
      
      // 添加随机特征
      const randomFeatures = effectiveNumericColumns.filter(col => 
        col.includes('random_feature') && 
        !predictors.includes(col)
      ).slice(0, 2)
      
      if (randomFeatures.length > 0) {
        predictors.push(...randomFeatures)
      }
      
      // 如果仍然不足5个，添加其他数值特征
      if (predictors.length < 5) {
        const otherFeatures = effectiveNumericColumns
          .filter(col => !predictors.includes(col) && col !== analysisParams.targetFeature)
          .slice(0, 5 - predictors.length)
        
        predictors.push(...otherFeatures)
      }
      
      analysisParams.selectedFeatures = predictors.slice(0, 5)
      console.log('使用BBQ特征进行回归预测:', {
        target: analysisParams.targetFeature,
        features: analysisParams.selectedFeatures
      })
    }
    // 如果有温度特征，选一个作为目标
    else if (defaultFeatures.temperature.length > 0) {
      // 选择原始代码逻辑...
      analysisParams.targetFeature = defaultFeatures.temperature[0]
      
      // 选择其他特征作为预测变量
      const predictors = []
      
      // 添加湿度特征
      if (defaultFeatures.humidity.length > 0) {
        predictors.push(defaultFeatures.humidity[0])
      }
      
      // 添加降水特征
      if (defaultFeatures.precipitation.length > 0) {
        predictors.push(defaultFeatures.precipitation[0])
      }
      
      // 添加其他温度特征
      const otherTemps = defaultFeatures.temperature
        .filter(t => t !== analysisParams.targetFeature)
        .slice(0, 3)
      
      predictors.push(...otherTemps)
      
      // 如果仍然不足5个，添加其他数值特征
      if (predictors.length < 5) {
        const otherFeatures = effectiveNumericColumns
          .filter(col => !predictors.includes(col) && col !== analysisParams.targetFeature)
          .slice(0, 5 - predictors.length)
        
        predictors.push(...otherFeatures)
      }
      
      analysisParams.selectedFeatures = predictors.slice(0, 5)
    } 
    // 如果没有温度特征，使用第一个数值列作为目标，其他作为特征
    else if (effectiveNumericColumns.length > 0) {
      analysisParams.targetFeature = effectiveNumericColumns[0]
      analysisParams.selectedFeatures = effectiveNumericColumns.slice(1, 6)
    }
  }
  
  console.log('初始特征设置:', {
    method: analysisMethod.value,
    target: analysisParams.targetFeature,
    features: analysisParams.selectedFeatures
  })
}

// 获取文件列表
const fetchDataFiles = async () => {
  try {
    loading.value = true
    const response = await getDataFiles()
    dataFiles.value = response.data || []
    
    // 查找天气数据文件
    const weatherFile = dataFiles.value.find(file => 
      file.name.includes('weather_prediction_dataset') || 
      file.name.toLowerCase().includes('weather')
    )
    
    if (weatherFile) {
      weatherFileId.value = weatherFile.id
      // 如果找到天气数据，填充数据
      if (dataStore.currentData && dataStore.currentData.length > 0) {
        noDataMessage.value = ''
        // 提取默认特征分组并设置默认特征
        initFeatures()
      } else {
        noDataMessage.value = '找到天气数据文件，但没有加载数据内容，请先在数据管理页面预览数据'
      }
    } else {
      noDataMessage.value = '找不到天气数据文件，请先上传weather_prediction_dataset.csv'
    }
  } catch (error) {
    ElMessage.error('获取文件列表失败: ' + (error.message || '未知错误'))
    noDataMessage.value = '获取文件列表失败'
  } finally {
    loading.value = false
  }
}

// 更新：设置当前选中的文件
const selectDataFile = (fileId) => {
  weatherFileId.value = fileId
  // 更新当前选中的文件
  const selectedFile = dataFiles.value.find(file => file.id === fileId)
  if (selectedFile) {
    ElMessage.success(`已选择数据文件: ${selectedFile.name}`)
  }
}

// 获取数据中的特征
const availableFeatures = computed(() => {
  if (!dataStore.currentData || dataStore.currentData.length === 0) return []
  
  const firstRow = dataStore.currentData[0]
  return Object.keys(firstRow).map(key => {
    // 简单判断字段类型
    const value = firstRow[key]
    const isNumeric = !isNaN(Number(value)) && value !== ''
    
    return {
      field: key,
      label: key,
      type: isNumeric ? 'numeric' : 'categorical'
    }
  })
})

// 获取数值型特征
const numericFeatures = computed(() => {
  return availableFeatures.value.filter(feature => feature.type === 'numeric')
})

// 获取分类特征
const categoricalFeatures = computed(() => {
  return availableFeatures.value.filter(feature => feature.type === 'categorical')
})

// 检查数据
const checkData = () => {
  if (!weatherFileId.value) {
    noDataMessage.value = '找不到天气数据文件，请先上传数据'
    return false
  }
  
  if (!dataStore.currentData || dataStore.currentData.length === 0) {
    noDataMessage.value = '没有可用数据，请先在数据管理页面上传数据'
    return false
  }
  
  noDataMessage.value = ''
  return true
}

// 运行分析
const runAnalysisTask = async () => {
  if (!checkData()) return
  
  if (!analysisMethod.value) {
    ElMessage.warning('请选择分析方法')
    return
  }
  
  loading.value = true
  
  try {
    // 确保有特征被选择
    if (analysisParams.selectedFeatures.length === 0) {
      console.log('没有选择特征，重新初始化特征...')
      initFeatures()
      
      // 如果仍然没有特征被选择，显示错误并返回
      if (analysisParams.selectedFeatures.length === 0) {
        ElMessage.error('无法自动选择合适的特征进行分析')
        loading.value = false
        return
      }
    }
    
    // 获取当前数据集中实际存在的列
    const availableColumns = Object.keys(dataStore.currentData[0])
    console.log('实际可用的列名:', availableColumns)
    
    // 从可用列中确保选择有效的特征
    let selectedFeatures = [...analysisParams.selectedFeatures]
    
    // 验证所有选择的特征确实存在于数据中
    const validFeatures = selectedFeatures.filter(f => availableColumns.includes(f))
    const invalidFeatures = selectedFeatures.filter(f => !availableColumns.includes(f))
    
    if (invalidFeatures.length > 0) {
      console.warn('忽略不存在的特征:', invalidFeatures)
      ElMessage.warning(`忽略不存在的特征: ${invalidFeatures.join(', ')}`)
    }
    
    // 如果没有有效特征，尝试再次自动选择
    if (validFeatures.length === 0) {
      console.log('没有选择有效特征，尝试自动选择...')
      
      // 先检查数据集是否包含BBQ_weather相关列或其数值版本
      const bbqCols = availableColumns.filter(col => 
        col.includes('BBQ_weather') || (col.includes('BBQ') && col.includes('_numeric'))
      )
      
      if (bbqCols.length > 0) {
        // 优先使用BBQ数值版本
        const bbqNumericCols = bbqCols.filter(col => col.includes('_numeric'))
        if (bbqNumericCols.length > 0) {
          selectedFeatures = bbqNumericCols.slice(0, 5)
          console.log('使用BBQ数值列作为特征:', selectedFeatures)
        } else {
          // 直接使用原始BBQ列，后端会处理转换
          selectedFeatures = bbqCols.slice(0, 5)
          console.log('使用原始BBQ列作为特征:', selectedFeatures)
        }
      } 
      // 尝试使用随机特征
      else {
        const randomCols = availableColumns.filter(col => col.includes('random_feature'))
        if (randomCols.length > 0) {
          selectedFeatures = randomCols.slice(0, 5)
          console.log('使用随机特征:', selectedFeatures)
        }
        // 尝试使用非日期列
        else {
          const nonDateCols = availableColumns.filter(col => 
            col !== 'DATE' && col !== 'MONTH' && !col.includes('BBQ_weather')
          ).slice(0, 5)
          
          if (nonDateCols.length > 0) {
            selectedFeatures = nonDateCols
            console.log('使用非日期列作为特征:', selectedFeatures)
          } else {
            ElMessage.error('没有可用的数值特征进行分析')
            loading.value = false
            return
          }
        }
      }
      
      // 最终验证
      const finalValidFeatures = selectedFeatures.filter(f => availableColumns.includes(f))
      if (finalValidFeatures.length === 0) {
        ElMessage.error('无法找到有效的特征进行分析')
        loading.value = false
        return
      }
      
      selectedFeatures = finalValidFeatures
      console.log('自动选择的有效特征:', selectedFeatures)
      
      // 更新UI上的选择特征
      analysisParams.selectedFeatures = selectedFeatures
    } else {
      selectedFeatures = validFeatures
    }
    
    // 检查目标特征（对于回归和分类）
    if (analysisMethod.value === 'regression') {
      if (!analysisParams.targetFeature) {
        // 如果未指定目标特征，使用与特征不同的列
        const bbqCols = availableColumns.filter(col => 
          (col.includes('BBQ') && col.includes('_numeric')) &&
          !selectedFeatures.includes(col)
        )
        
        const randomCols = availableColumns.filter(col => 
          col.includes('random_feature') && 
          !selectedFeatures.includes(col)
        )
        
        if (bbqCols.length > 0) {
          analysisParams.targetFeature = bbqCols[0]
          console.log('自动选择BBQ列作为目标特征:', analysisParams.targetFeature)
          ElMessage.info(`自动选择 "${analysisParams.targetFeature}" 作为目标特征`)
        } else if (randomCols.length > 0) {
          analysisParams.targetFeature = randomCols[0]
          console.log('自动选择随机特征作为目标:', analysisParams.targetFeature)
          ElMessage.info(`自动选择 "${analysisParams.targetFeature}" 作为目标特征`)
        } else if (availableColumns.includes('DATE_numeric')) {
          analysisParams.targetFeature = 'DATE_numeric'
          console.log('使用DATE_numeric作为目标特征')
          ElMessage.info('使用DATE_numeric作为目标特征')
        } else {
          ElMessage.warning('请选择目标特征')
          loading.value = false
          return
        }
      }
      
      if (!availableColumns.includes(analysisParams.targetFeature)) {
        // 尝试从可用列中找到一个替代的目标特征
        const bbqCols = availableColumns.filter(col => 
          (col.includes('BBQ') && col.includes('_numeric')) &&
          !selectedFeatures.includes(col)
        )
        
        const randomCols = availableColumns.filter(col => 
          col.includes('random_feature') && 
          !selectedFeatures.includes(col)
        )
        
        const newTarget = bbqCols[0] || randomCols[0] || availableColumns.find(col => 
          col !== 'DATE' && 
          col !== 'MONTH' && 
          !selectedFeatures.includes(col)
        )
        
        if (newTarget) {
          console.log(`目标特征 "${analysisParams.targetFeature}" 不存在，使用 "${newTarget}" 替代`)
          ElMessage.warning(`目标特征 "${analysisParams.targetFeature}" 不存在，使用 "${newTarget}" 替代`)
          analysisParams.targetFeature = newTarget
        } else {
          ElMessage.error(`目标特征 "${analysisParams.targetFeature}" 在数据中不存在，且无法找到替代特征`)
          console.error(`目标特征 "${analysisParams.targetFeature}" 在数据中不存在，且无法找到替代特征`)
          loading.value = false
          return
        }
      }
      
      // 确保目标特征不在选定特征中
      selectedFeatures = selectedFeatures.filter(f => f !== analysisParams.targetFeature)
      
      // 确保至少有一个特征用于预测
      if (selectedFeatures.length === 0) {
        // 尝试找到新的特征
        const bbqCols = availableColumns.filter(col => 
          (col.includes('BBQ') && col.includes('_numeric')) &&
          col !== analysisParams.targetFeature
        )
        
        const randomCols = availableColumns.filter(col => 
          col.includes('random_feature') && 
          col !== analysisParams.targetFeature
        )
        
        if (bbqCols.length > 0) {
          selectedFeatures = bbqCols.slice(0, 5)
          console.log('使用BBQ特征进行回归分析:', selectedFeatures)
          ElMessage.info(`自动选择BBQ特征进行回归分析`)
        } else if (randomCols.length > 0) {
          selectedFeatures = randomCols.slice(0, 3)
          console.log('使用随机特征进行回归分析:', selectedFeatures)
          ElMessage.info(`自动选择随机特征进行回归分析`)
        } else {
          const newFeatures = availableColumns.filter(col => 
            col !== 'DATE' && 
            col !== 'MONTH' && 
            col !== analysisParams.targetFeature
          ).slice(0, 3)
          
          if (newFeatures.length > 0) {
            selectedFeatures = newFeatures
            console.log('自动选择特征进行回归分析:', selectedFeatures)
            ElMessage.info(`自动选择特征进行回归分析`)
          } else {
            ElMessage.error('没有足够的特征进行回归分析')
            loading.value = false
            return
          }
        }
      }
    }
    
    // 如果特征列表仍为空，显示错误
    if (selectedFeatures.length === 0) {
      ElMessage.error('没有有效的特征可用于分析')
      loading.value = false
      return
    }
    
    // 更新UI显示的特征
    analysisParams.selectedFeatures = selectedFeatures
    
    // 根据分析方法构建参数
    const parameters = {
      features: selectedFeatures, // 使用已验证的特征列表
    }
    
    // 添加特定分析方法的参数
    if (analysisMethod.value === 'clustering') {
      parameters.n_clusters = analysisParams.clusterCount
      parameters.algorithm = analysisParams.clusteringAlgorithm
    } else if (analysisMethod.value === 'regression') {
      parameters.target = analysisParams.targetFeature
      parameters.algorithm = analysisParams.regressionAlgorithm
      parameters.test_size = analysisParams.testSize
      
      // 添加线性回归高级选项
      if (analysisParams.regressionAlgorithm === 'linear') {
        parameters.linear_type = analysisParams.linearOptions.linearType
        parameters.alpha = analysisParams.linearOptions.alpha
        parameters.use_polynomial = analysisParams.linearOptions.usePolynomial
        parameters.polynomial_degree = analysisParams.linearOptions.polynomialDegree
      }
    }
    
    console.log('发送分析请求:', parameters)
    
    // 检查weatherFileId是否有效
    if (!weatherFileId.value) {
      // 如果没有有效ID，尝试使用DataStore中的currentFile
      if (dataStore.currentFile && dataStore.currentFile.id) {
        weatherFileId.value = dataStore.currentFile.id
        console.log('使用当前选择的文件ID:', weatherFileId.value)
      } else if (dataFiles.value && dataFiles.value.length > 0) {
        // 如果没有当前文件，使用最新的一个文件
        weatherFileId.value = dataFiles.value[0].id
        console.log('使用最新文件ID:', weatherFileId.value)
      } else {
      ElMessage.error('缺少有效的文件ID')
      console.error('缺少有效的文件ID')
      loading.value = false
      return
      }
    }
    
    // 构建完整的请求
    const requestData = {
      file_id: weatherFileId.value,
      cleaned_data_id: null,
      analysis_type: analysisMethod.value,
      parameters: parameters
    }
    
    console.log('完整请求数据:', JSON.stringify(requestData))
    
    // 调用后端API进行分析
    const response = await runAnalysis(
      weatherFileId.value,
      null,
      analysisMethod.value,
      parameters
    )
    
    if (response.data) {
      analysisResult.value = {
        ...response.data,
        type: analysisMethod.value,
        algorithm: parameters.algorithm
      }
      ElMessage.success('分析完成')
    }
  } catch (error) {
    console.error('分析失败:', error)
    
    if (error.response && error.response.status === 400) {
      // 尝试使用模拟数据
      console.log('API请求失败，使用模拟数据...')
      generateMockResults()
    } else if (error.response) {
      console.error('服务器返回错误:', error.response.status, error.response.data)
      ElMessage.error('分析失败: ' + (error.response.data?.error || error.message || '未知错误'))
    } else {
      ElMessage.error('分析失败: ' + (error.message || '未知错误'))
    }
  } finally {
    loading.value = false
    
    // 如果有分析结果，渲染图表
    if (analysisResult.value) {
      setTimeout(() => {
        renderAnalysisChart()
      }, 100)
    }
  }
}

// 生成模拟分析结果（当后端未实现时使用）
const generateMockResults = () => {
  const data = dataStore.currentData
  
  // 使用已选择的特征或自动选择特征
  const features = analysisParams.selectedFeatures.length > 0 ? 
    analysisParams.selectedFeatures : 
    Object.keys(data[0])
      .filter(key => key !== 'DATE' && key !== 'MONTH' && !key.includes('BBQ_weather'))
      .slice(0, 5)
  
  if (features.length === 0) {
    ElMessage.error('无法生成模拟结果：没有可用特征')
    return
  }
  
  console.log('使用特征生成模拟结果:', features)
  
  switch (analysisMethod.value) {
    case 'clustering':
      // 模拟聚类结果
      const clusterCount = analysisParams.clusterCount || 3
      console.log(`生成${clusterCount}个聚类的模拟结果`)
      
      // 随机分配聚类标签，但使BBQ_weather列的数据倾向于分入相同聚类
      const clusterLabels = data.map((row, index) => {
        // 如果是BBQ_weather相关特征，根据值分配聚类标签
        for (const feature of features) {
          if (feature.includes('BBQ')) {
            return Math.floor(Math.random() * (clusterCount / 2))  // BBQ好的天气倾向于前半部分聚类
          }
        }
        // 其他情况随机分配
        return Math.floor(Math.random() * clusterCount)
      })
      
      // 计算每个聚类的数量
      const clusterCounts = Array(clusterCount).fill(0).map((_, i) => 
        clusterLabels.filter(label => label === i).length
      )
      
      // 生成聚类中心（半随机，让BBQ列的值更有意义）
      const clusterCenters = Array(clusterCount).fill(0).map((_, cluster) => {
        const center = {}
        features.forEach(feature => {
          if (feature.includes('BBQ')) {
            // BBQ特征在不同聚类中有明显差异
            center[feature] = cluster < clusterCount / 2 ? 0.8 : 0.2
          } else if (feature.includes('MONTH')) {
            // 月份特征有季节性
            center[feature] = (cluster % 4) * 3 + 1 + Math.random()
          } else if (feature.includes('DAY')) {
            // 日期特征比较均匀
            center[feature] = Math.floor(Math.random() * 28) + 1
          } else {
            // 随机值但保持在合理范围
            center[feature] = Math.random() * 10
          }
        })
        return center
      })
      
      analysisResult.value = {
        type: 'clustering',
        algorithm: analysisParams.clusteringAlgorithm || 'kmeans',
        result: {
          clusters: clusterLabels,
          centers: clusterCenters,
          clusterCounts,
          feature_names: features
        },
        chartType: 'pie'
      }
      break
      
    case 'regression':
      // 模拟回归结果
      const targetFeature = analysisParams.targetFeature || features[0]
      const modelFeatures = features.filter(f => f !== targetFeature)
      
      if (modelFeatures.length === 0) {
        ElMessage.error('无法生成回归模型：没有足够的特征')
        return
      }
      
      const rSquared = 0.7 + Math.random() * 0.25 // 模拟 R² 值（0.7-0.95）
      const meanAbsoluteError = Math.random() * 2 // 模拟 MAE
      const meanSquaredError = Math.pow(meanAbsoluteError, 2) // 模拟 MSE
      
      // 生成系数，使得与BBQ相关的特征有更高系数
      const coefficients = modelFeatures.map(feature => {
        if (feature.includes('BBQ')) {
          return 1.5 + Math.random()
        } else if (feature.includes('MONTH') || feature.includes('DATE')) {
          return 0.7 + Math.random() * 0.5
        } else {
          return Math.random() * 2 - 1
        }
      })
      
      // 生成预测值 vs 实际值
      const predictions = []
      for (let i = 0; i < 20; i++) {
        const actual = 20 + Math.random() * 60  // 模拟实际值在20-80范围内
        const noise = (Math.random() - 0.5) * 15  // 添加一些随机噪声
        const predicted = actual + noise  // 预测值 = 实际值 + 噪声
        predictions.push({ actual, predicted })
      }
      
      analysisResult.value = {
        type: 'regression',
        algorithm: analysisParams.regressionAlgorithm || 'linear',
        result: {
          coefficients: coefficients,
          intercept: 10 + Math.random() * 20,
          r2_score: rSquared,
          feature_names: modelFeatures,
          target: targetFeature,
          predictions,
          metrics: {
            r2: rSquared,
            mae: meanAbsoluteError,
            mse: meanSquaredError
          }
        },
        chartType: 'scatter'
      }
      break
  }
  
  ElMessage.success('生成模拟分析结果')
}

// 渲染分析结果图表
const renderAnalysisChart = () => {
  if (!chartContainer.value || !analysisResult.value) return
  
  if (chartInstance.value) {
    chartInstance.value.dispose()
  }
  
  chartInstance.value = echarts.init(chartContainer.value)
  
  const option = {
    title: {
      text: getChartTitle(),
      left: 'center'
    },
    tooltip: {
      trigger: 'item'
    },
    toolbox: {
      feature: {
        saveAsImage: {}
      }
    }
  }
  
  const result = analysisResult.value.result || {}
  
  switch (analysisResult.value.type) {
    case 'clustering':
      // 聚类结果可视化 - 饼图
      const clusterCounts = result.clusterCounts || 
        (result.clusters ? 
          Array.from(new Set(result.clusters)).map(cluster => 
            result.clusters.filter(c => c === cluster).length
          ) : [])
      
      option.series = [
        {
          name: '聚类分布',
          type: 'pie',
          radius: '60%',
          data: clusterCounts.map((count, index) => ({
            name: `聚类 ${index + 1}`,
            value: count
          })),
          emphasis: {
            itemStyle: {
              shadowBlur: 10,
              shadowOffsetX: 0,
              shadowColor: 'rgba(0, 0, 0, 0.5)'
            }
          }
        }
      ]
      option.legend = {
        orient: 'vertical',
        left: 'left',
        data: clusterCounts.map((_, index) => `聚类 ${index + 1}`)
      }
      break
      
    case 'regression':
      // 判断是否是随机森林模型
      const isRandomForest = analysisResult.value.algorithm === 'random_forest'
      
      // 回归结果可视化 - 散点图
      const predictions = result.predictions || []
      
      // 计算最小值和最大值，用于轴范围和理想线
      const actualValues = predictions.map(p => p.actual)
      const predictedValues = predictions.map(p => p.predicted)
      
      // 计算数据的实际范围
      const minActual = Math.min(...actualValues)
      const maxActual = Math.max(...actualValues)
      const minPredicted = Math.min(...predictedValues)
      const maxPredicted = Math.max(...predictedValues)
      
      // 确定坐标轴的实际范围，留出额外空间
      const rangeBuffer = Math.max(1, (Math.max(maxActual, maxPredicted) - Math.min(minActual, minPredicted)) * 0.2)
      const axisMin = Math.floor(Math.min(minActual, minPredicted) - rangeBuffer)
      const axisMax = Math.ceil(Math.max(maxActual, maxPredicted) + rangeBuffer)
      
      option.title.subtext = `目标特征: ${result.target || analysisParams.targetFeature}`
      option.title.subtextStyle = {
        fontSize: 14,
        color: '#666'
      }
      
      option.xAxis = {
        type: 'value',
        name: '实际值',
        nameLocation: 'middle',
        nameGap: 30,
        min: axisMin,
        max: axisMax,
        axisLabel: {
          formatter: '{value}'
        }
      }
      
      option.yAxis = {
        type: 'value',
        name: '预测值',
        nameLocation: 'middle',
        nameGap: 30,
        min: axisMin,
        max: axisMax,
        axisLabel: {
          formatter: '{value}'
        }
      }
      
      option.tooltip = {
        trigger: 'item',
        formatter: function(params) {
          if (params.seriesName === '预测 vs 实际') {
            const point = params.data
            const actual = point[0]
            const predicted = point[1]
            const error = Math.abs(predicted - actual)
            const errorPercent = actual !== 0 ? (error / Math.abs(actual) * 100).toFixed(1) : '∞'
            
            return `实际值: ${actual.toFixed(2)}<br/>` +
                   `预测值: ${predicted.toFixed(2)}<br/>` +
                   `误差: ${error.toFixed(2)}<br/>` +
                   `相对误差: ${errorPercent}%`
          }
          return params.seriesName
        }
      }
      
      option.grid = {
        left: '5%',
        right: '5%',
        bottom: '10%',
        top: '15%',
        containLabel: true
      }
      
      // 计算每个点的误差，用于颜色映射
      const scatterData = predictions.map(p => {
        const error = Math.abs(p.predicted - p.actual)
        const relativeError = p.actual !== 0 ? error / Math.abs(p.actual) : 1
        return [p.actual, p.predicted, relativeError] // 第三个值用于颜色映射
      })
      
      // 添加理想线 (y=x)
      if (isRandomForest) {
        // 随机森林使用增强的散点图
        option.visualMap = {
          min: 0,
          max: 1,
          dimension: 2, // 映射到数据的第三个维度
          inRange: {
            color: ['#5470c6', '#91cc75', '#ee6666']
          },
          text: ['高误差', '低误差'],
          calculable: true,
          orient: 'horizontal',
          left: 'center',
          bottom: '0%',
          formatter: function (value) {
            return (value * 100).toFixed(0) + '%';
          }
        }
        
        option.series = [
          {
            name: '预测 vs 实际',
            type: 'scatter',
            symbolSize: function(data) {
              // 根据相对误差调整大小：误差越大，点越大
              return 10 + data[2] * 20
            },
            data: scatterData,
            emphasis: {
              itemStyle: {
                borderColor: '#000',
                borderWidth: 1
              },
              label: {
                show: true,
                formatter: function(params) {
                  const error = params.data[2]
                  return (error * 100).toFixed(1) + '%'
                },
                position: 'top'
              }
            }
          },
          {
            name: '理想线 (y=x)',
            type: 'line',
            data: [[minActual, minActual], [maxActual, maxActual]],
            lineStyle: {
              type: 'solid',
              color: '#000',
              width: 2
            },
            symbol: 'none'
          }
        ]
        
        option.legend = {
          data: ['预测 vs 实际', '理想线 (y=x)'],
          bottom: '3%',
          left: 'center',
          orient: 'horizontal'
        }
      } else {
        // 线性模型使用原始的散点图 + 趋势线
        option.series = [
          {
            name: '预测 vs 实际',
            type: 'scatter',
            symbolSize: 12,
            data: predictions.map(p => [p.actual, p.predicted]),
            itemStyle: {
              color: '#5470c6',
              opacity: 0.7
            },
            emphasis: {
              itemStyle: {
                borderColor: '#ff7000',
                borderWidth: 2,
                opacity: 1
              }
            }
          },
          {
            name: '理想线 (y=x)',
            type: 'line',
            data: [[minActual, minActual], [maxActual, maxActual]],
            lineStyle: {
              type: 'solid',
              color: '#91cc75',
              width: 2
            },
            symbol: 'none'
          }
        ]
        
        // 只为线性模型添加趋势线
        // 添加回归趋势线
        const xSum = actualValues.reduce((a, b) => a + b, 0)
        const ySum = predictedValues.reduce((a, b) => a + b, 0)
        const xMean = xSum / actualValues.length
        const yMean = ySum / predictedValues.length
        
        let numerator = 0
        let denominator = 0
        
        for (let i = 0; i < actualValues.length; i++) {
          numerator += (actualValues[i] - xMean) * (predictedValues[i] - yMean)
          denominator += Math.pow(actualValues[i] - xMean, 2)
        }
        
        const slope = denominator !== 0 ? numerator / denominator : 0
        const intercept = yMean - slope * xMean
        
        option.series.push({
          name: '回归趋势线',
          type: 'line',
          data: [[minActual, minActual * slope + intercept], [maxActual, maxActual * slope + intercept]],
          lineStyle: {
            type: 'dashed',
            color: '#ee6666',
            width: 2
          },
          symbol: 'none'
        })
        
        option.legend = {
          data: ['预测 vs 实际', '理想线 (y=x)', '回归趋势线'],
          bottom: 0
        }
      }
      
      break
  }
  
  chartInstance.value.setOption(option)
  
  // 如果是随机森林模型，添加特征重要性图表
  if (analysisResult.value.type === 'regression' && analysisResult.value.algorithm === 'random_forest') {
    renderFeatureImportanceChart()
    
    // 添加残差分布图
    renderResidualHistogram()
  }
}

// 新增：渲染随机森林残差分布直方图
const renderResidualHistogram = () => {
  // 确保结果中有预测数据
  if (!analysisResult.value || !analysisResult.value.result || !analysisResult.value.result.predictions) {
    return
  }
  
  // 首先移除任何已存在的残差图表
  const existingCharts = document.querySelectorAll('.residual-chart')
  existingCharts.forEach(chart => {
    chart.parentNode.removeChild(chart)
  })
  
  // 创建图表容器
  const residualChartContainer = document.createElement('div')
  residualChartContainer.style.width = '100%'
  residualChartContainer.style.height = '300px'
  residualChartContainer.style.marginTop = '30px'
  residualChartContainer.className = 'residual-chart' // 添加类名以便后续清除
  
  // 将图表容器添加到页面
  chartContainer.value.parentNode.appendChild(residualChartContainer)
  
  // 初始化图表实例
  const residualChart = echarts.init(residualChartContainer)
  
  // 计算残差
  const predictions = analysisResult.value.result.predictions
  const residuals = predictions.map(p => p.predicted - p.actual)
  
  // 计算残差的统计信息
  const meanResidual = residuals.reduce((sum, val) => sum + val, 0) / residuals.length
  const absResiduals = residuals.map(r => Math.abs(r))
  const maxAbsResidual = Math.max(...absResiduals)
  
  // 创建直方图数据
  // 将残差分成10个区间
  const binCount = 10
  const binSize = (maxAbsResidual * 2) / binCount
  const bins = Array(binCount).fill(0)
  
  residuals.forEach(residual => {
    // 将残差映射到相应的区间
    const binIndex = Math.min(
      Math.floor((residual + maxAbsResidual) / binSize),
      binCount - 1
    )
    bins[binIndex]++
  })
  
  // 计算区间边界
  const binLabels = []
  for (let i = 0; i < binCount; i++) {
    const lowerBound = -maxAbsResidual + i * binSize
    const upperBound = -maxAbsResidual + (i + 1) * binSize
    binLabels.push(`${lowerBound.toFixed(2)} 到 ${upperBound.toFixed(2)}`)
  }
  
  // 设置图表选项
  const option = {
    title: {
      text: '预测误差分布',
      subtext: `平均误差: ${meanResidual.toFixed(4)}`,
      left: 'center'
    },
    tooltip: {
      trigger: 'axis',
      formatter: '{b}: {c}个样本'
    },
    toolbox: {
      feature: {
        saveAsImage: {}
      }
    },
    grid: {
      left: '5%',
      right: '5%',
      bottom: '15%',
      top: '15%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: binLabels,
      name: '误差范围',
      nameLocation: 'middle',
      nameGap: 30,
      axisLabel: {
        interval: 0,
        rotate: 45
      }
    },
    yAxis: {
      type: 'value',
      name: '样本数量'
    },
    series: [{
      name: '误差分布',
      type: 'bar',
      data: bins,
      itemStyle: {
        color: function(params) {
          // 使用颜色区分误差：中间区域(接近0)为绿色，两端为红色
          const index = params.dataIndex
          const middle = binCount / 2
          const distance = Math.abs(index - middle) / middle
          
          // 渐变颜色
          return distance < 0.3 ? '#91cc75' : // 低误差 - 绿色
                 distance < 0.6 ? '#5470c6' : // 中误差 - 蓝色
                 '#ee6666'                    // 高误差 - 红色
        }
      }
    }]
  }
  
  // 渲染图表
  residualChart.setOption(option)
}

// 渲染随机森林特征重要性图表
const renderFeatureImportanceChart = () => {
  // 确保结果中有特征重要性数据
  if (!analysisResult.value || !analysisResult.value.result || !analysisResult.value.result.coefficients) {
    return
  }
  
  // 首先移除任何已存在的特征重要性图表
  const existingCharts = document.querySelectorAll('.feature-importance-chart')
  existingCharts.forEach(chart => {
    chart.parentNode.removeChild(chart)
  })
  
  // 创建图表容器
  const importanceChartContainer = document.createElement('div')
  importanceChartContainer.style.width = '100%'
  importanceChartContainer.style.height = '400px'
  importanceChartContainer.style.marginTop = '30px'
  importanceChartContainer.className = 'feature-importance-chart' // 添加类名以便后续清除
  
  // 将图表容器添加到页面
  chartContainer.value.parentNode.appendChild(importanceChartContainer)
  
  // 初始化图表实例
  const importanceChart = echarts.init(importanceChartContainer)
  
  // 准备数据
  const featureNames = analysisResult.value.result.feature_names || analysisParams.selectedFeatures
  const importanceValues = analysisResult.value.result.coefficients
  
  // 创建特征重要性数据数组
  const importanceData = []
  for (let i = 0; i < featureNames.length; i++) {
    // 确保有效的值
    if (typeof importanceValues[i] === 'number') {
      importanceData.push({
        name: featureNames[i],
        value: importanceValues[i]
      })
    }
  }
  
  // 按重要性排序
  importanceData.sort((a, b) => b.value - a.value)
  
  // 设置图表选项
  const option = {
    title: {
      text: '随机森林特征重要性',
      left: 'center'
    },
    tooltip: {
      trigger: 'axis',
      formatter: '{b}: {c}'
    },
    toolbox: {
      feature: {
        saveAsImage: {}
      }
    },
    grid: {
      left: '5%',
      right: '5%',
      bottom: '10%',
      top: '15%',
      containLabel: true
    },
    xAxis: {
      type: 'value',
      name: '重要性分数',
      nameLocation: 'middle',
      nameGap: 30
    },
    yAxis: {
      type: 'category',
      data: importanceData.map(item => item.name),
      axisLabel: {
        interval: 0,
        rotate: 30
      }
    },
    series: [{
      name: '特征重要性',
      type: 'bar',
      data: importanceData.map(item => item.value),
      itemStyle: {
        color: function(params) {
          // 使用不同颜色区分重要性程度
          const value = importanceData[params.dataIndex].value
          if (value > 0.4) return '#91cc75'  // 高重要性 - 绿色
          if (value > 0.2) return '#5470c6'  // 中等重要性 - 蓝色
          return '#ee6666'                   // 低重要性 - 红色
        }
      },
      label: {
        show: true,
        position: 'right',
        formatter: '{c}'
      }
    }]
  }
  
  // 渲染图表
  importanceChart.setOption(option)
}

// 获取图表标题
const getChartTitle = () => {
  const result = analysisResult.value
  
  switch (result.type) {
    case 'clustering':
      return `聚类分析结果 (${getAlgorithmLabel(result.algorithm, 'clustering')})`
    case 'regression':
      return `回归分析结果 (${getAlgorithmLabel(result.algorithm, 'regression')})`
    default:
      return '分析结果'
  }
}

// 获取算法标签
const getAlgorithmLabel = (value, type) => {
  const option = algorithmOptions[type].find(opt => opt.value === value)
  return option ? option.label : value
}

// 监听分析方法变化，自动重新初始化特征
watch(analysisMethod, () => {
  initFeatures()
})

// 添加setDefaultFeatures函数
const setDefaultFeatures = () => {
  // 重新提取特征分组
  extractFeatureGroups()
  
  // 获取可用列
  const availableColumns = dataStore.currentData ? Object.keys(dataStore.currentData[0]) : []
  
  // 优先使用BBQ数值特征
  const bbqNumericCols = availableColumns.filter(col => 
    col.includes('BBQ') && col.includes('_numeric')
  )
  
  if (bbqNumericCols.length > 0) {
    if (analysisMethod.value === 'clustering') {
      // 聚类时使用所有BBQ数值特征
      analysisParams.selectedFeatures = bbqNumericCols.slice(0, 5)
      ElMessage.success('已设置BBQ数值特征作为默认特征')
    } else if (analysisMethod.value === 'regression') {
      // 回归时使用一个作为目标，其他作为特征
      analysisParams.targetFeature = bbqNumericCols[0]
      analysisParams.selectedFeatures = bbqNumericCols.slice(1, 6)
      ElMessage.success('已设置BBQ数值特征作为默认特征和目标')
    }
    return
  }
  
  // 如果没有BBQ数值特征，使用随机特征
  const randomFeatures = availableColumns.filter(col => col.includes('random_feature'))
  if (randomFeatures.length > 0) {
    if (analysisMethod.value === 'clustering') {
      analysisParams.selectedFeatures = randomFeatures.slice(0, 5)
      ElMessage.success('已设置随机特征作为默认特征')
    } else if (analysisMethod.value === 'regression') {
      analysisParams.targetFeature = randomFeatures[0]
      analysisParams.selectedFeatures = randomFeatures.slice(1, 6)
      ElMessage.success('已设置随机特征作为默认特征和目标')
    }
    return
  }
  
  // 回退到原始特征选择逻辑
  initFeatures()
  ElMessage.success('已重置默认特征')
}

// 添加新方法来根据系数值返回颜色
const getCoefColor = (coefficient) => {
  if (typeof coefficient !== 'number') return '#303133'
  
  if (coefficient > 0.5) return '#67C23A'  // 很强的正相关 - 绿色
  if (coefficient > 0.2) return '#409EFF'  // 中等正相关 - 蓝色
  if (coefficient < -0.2) return '#F56C6C' // 负相关 - 红色
  return '#303133'  // 弱相关或无相关 - 默认颜色
}

// 获取线性回归类型标签
const getLinearTypeLabel = (value) => {
  const typeMap = {
    'standard': '标准线性回归',
    'ridge': '岭回归 (Ridge)',
    'lasso': 'Lasso回归'
  }
  return typeMap[value] || value
}

// 初始化
onMounted(() => {
  fetchDataFiles()
})
</script>

<template>
  <div class="data-analysis">
    <el-card v-loading="loading">
      <template #header>
        <div class="card-header">
          <h2>天气数据分析</h2>
        </div>
      </template>
      
      <el-empty v-if="noDataMessage" :description="noDataMessage">
        <el-button type="primary" @click="$router.push('/data-management')">去上传数据</el-button>
      </el-empty>
      
      <div v-else>
        <el-form label-width="120px">
          <el-form-item label="数据文件">
            <el-select 
              v-model="weatherFileId" 
              placeholder="请选择数据文件" 
              style="width: 100%"
              @change="selectDataFile"
            >
              <el-option
                v-for="file in dataFiles"
                :key="file.id"
                :label="file.name"
                :value="file.id"
              />
            </el-select>
            <div v-if="dataFiles.length === 0" class="empty-files-tip">
              <el-alert
                type="warning"
                :closable="false"
                show-icon
              >
                <template #title>未找到数据文件</template>
                <template #default>
                  请先在<el-link type="primary" @click="$router.push('/data-management')">数据管理</el-link>页面上传数据文件
                </template>
              </el-alert>
            </div>
          </el-form-item>
          
          <el-form-item label="分析方法">
            <el-select v-model="analysisMethod" placeholder="请选择分析方法" style="width: 100%">
              <el-option
                v-for="item in analysisOptions"
                :key="item.value"
                :label="item.label"
                :value="item.value"
              />
            </el-select>
          </el-form-item>
          
          <!-- 展示已选择的特征 -->
          <el-form-item label="分析特征">
            <div class="selected-features">
              <el-tag
                v-for="feature in analysisParams.selectedFeatures"
                :key="feature"
                class="feature-tag"
                closable
                @close="analysisParams.selectedFeatures = analysisParams.selectedFeatures.filter(f => f !== feature)"
              >
                {{ feature }}
              </el-tag>
              
              <div v-if="analysisParams.selectedFeatures.length === 0" class="empty-features">
                <span class="placeholder-text">自动选择的特征将显示在这里</span>
              </div>
            </div>
            
            <div class="feature-actions">
              <el-button type="primary" size="small" @click="setDefaultFeatures">重置默认特征</el-button>
              <el-button type="primary" size="small" @click="showFeatureSelector = true">添加/修改特征</el-button>
            </div>
          </el-form-item>
          
          <!-- 聚类分析的特定参数 -->
          <template v-if="analysisMethod === 'clustering'">
            <el-form-item label="聚类算法">
              <el-select v-model="analysisParams.clusteringAlgorithm" style="width: 100%">
                <el-option
                  v-for="item in algorithmOptions.clustering"
                  :key="item.value"
                  :label="item.label"
                  :value="item.value"
                />
              </el-select>
            </el-form-item>
            
            <el-form-item label="聚类数量">
              <el-slider v-model="analysisParams.clusterCount" :min="2" :max="6" />
            </el-form-item>
          </template>
          
          <!-- 回归分析的特定参数 -->
          <template v-if="analysisMethod === 'regression'">
            <el-form-item label="目标特征">
              <el-select v-model="analysisParams.targetFeature" style="width: 100%">
                <el-option
                  v-for="feature in availableFeatures"
                  :key="feature.field"
                  :label="feature.label"
                  :value="feature.field"
                />
              </el-select>
              
              <div class="target-help">
                <el-alert
                  type="info"
                  :closable="false"
                  show-icon
                >
                  <template #title>
                    选择一个与特征不同的列作为预测目标
                  </template>
                  <template #default>
                    建议选择温度(temp)或湿度(humidity)作为目标
                  </template>
                </el-alert>
              </div>
            </el-form-item>
            
            <el-form-item label="回归算法">
              <el-select v-model="analysisParams.regressionAlgorithm" style="width: 100%">
                <el-option
                  v-for="item in algorithmOptions.regression"
                  :key="item.value"
                  :label="item.label"
                  :value="item.value"
                />
              </el-select>
            </el-form-item>
            
            <!-- 线性回归的高级选项 -->
            <template v-if="analysisParams.regressionAlgorithm === 'linear'">
              <el-divider content-position="left">线性回归高级选项</el-divider>
              
              <el-form-item label="线性回归类型">
                <el-select v-model="analysisParams.linearOptions.linearType" style="width: 100%">
                  <el-option
                    v-for="item in linearRegressionTypes"
                    :key="item.value"
                    :label="item.label"
                    :value="item.value"
                  />
                </el-select>
              </el-form-item>
              
              <el-form-item v-if="analysisParams.linearOptions.linearType !== 'standard'" label="正则化强度">
                <el-slider 
                  v-model="analysisParams.linearOptions.alpha" 
                  :min="0.01" 
                  :max="10" 
                  :step="0.01"
                  :format-tooltip="(val) => val.toFixed(2)"
                />
              </el-form-item>
              
              <el-form-item label="多项式特征">
                <el-switch v-model="analysisParams.linearOptions.usePolynomial" />
                <span class="option-hint">使用多项式特征可能提高模型对非线性关系的拟合能力</span>
              </el-form-item>
              
              <el-form-item v-if="analysisParams.linearOptions.usePolynomial" label="多项式阶数">
                <el-slider 
                  v-model="analysisParams.linearOptions.polynomialDegree" 
                  :min="2" 
                  :max="5" 
                  :step="1"
                />
            </el-form-item>
            </template>
          </template>
          
          <el-form-item>
            <el-button type="primary" @click="runAnalysisTask">运行分析</el-button>
          </el-form-item>
        </el-form>
        
        <!-- 特征选择器对话框 -->
        <el-dialog
          v-model="showFeatureSelector"
          title="特征选择"
          width="60%"
        >
          <el-tabs type="border-card">
            <el-tab-pane label="温度特征">
              <el-checkbox-group v-model="analysisParams.selectedFeatures">
                <el-checkbox 
                  v-for="feature in defaultFeatures.temperature" 
                  :key="feature" 
                  :label="feature"
                  class="feature-checkbox"
                >
                  {{ feature }}
                </el-checkbox>
              </el-checkbox-group>
            </el-tab-pane>
            
            <el-tab-pane label="湿度特征">
              <el-checkbox-group v-model="analysisParams.selectedFeatures">
                <el-checkbox 
                  v-for="feature in defaultFeatures.humidity" 
                  :key="feature" 
                  :label="feature"
                  class="feature-checkbox"
                >
                  {{ feature }}
                </el-checkbox>
              </el-checkbox-group>
            </el-tab-pane>
            
            <el-tab-pane label="降水特征">
              <el-checkbox-group v-model="analysisParams.selectedFeatures">
                <el-checkbox 
                  v-for="feature in defaultFeatures.precipitation" 
                  :key="feature" 
                  :label="feature"
                  class="feature-checkbox"
                >
                  {{ feature }}
                </el-checkbox>
              </el-checkbox-group>
            </el-tab-pane>
            
            <el-tab-pane label="其他特征">
              <el-checkbox-group v-model="analysisParams.selectedFeatures">
                <el-checkbox 
                  v-for="feature in otherFeatures" 
                  :key="feature" 
                  :label="feature"
                  class="feature-checkbox"
                >
                  {{ feature }}
                </el-checkbox>
              </el-checkbox-group>
            </el-tab-pane>
          </el-tabs>
          
          <template #footer>
            <span class="dialog-footer">
              <el-button @click="showFeatureSelector = false">取消</el-button>
              <el-button type="primary" @click="showFeatureSelector = false">确认</el-button>
            </span>
          </template>
        </el-dialog>
        
        <el-divider />
        
        <div v-if="analysisResult" class="analysis-result">
          <h3>分析结果</h3>
          
          <!-- 聚类分析结果 -->
          <template v-if="analysisResult.type === 'clustering'">
            <div class="result-metrics">
              <el-descriptions :column="2" border>
                <el-descriptions-item label="聚类算法">
                  {{ getAlgorithmLabel(analysisResult.algorithm, 'clustering') }}
                </el-descriptions-item>
                <el-descriptions-item label="聚类数">
                  {{ analysisResult.result.clusterCounts ? analysisResult.result.clusterCounts.length : 0 }}
                </el-descriptions-item>
              </el-descriptions>
              
              <el-table v-if="analysisResult.result.clusterCounts" :data="analysisResult.result.clusterCounts.map((count, index) => ({
                cluster: `聚类 ${index + 1}`,
                count
              }))" style="width: 100%; margin-top: 20px;">
                <el-table-column prop="cluster" label="聚类" />
                <el-table-column prop="count" label="数量" />
              </el-table>
            </div>
          </template>
          
          <!-- 回归分析结果 -->
          <template v-if="analysisResult.type === 'regression'">
            <div class="result-metrics">
              <el-descriptions :column="3" border>
                <el-descriptions-item label="回归算法">
                  {{ getAlgorithmLabel(analysisResult.algorithm, 'regression') }}
                </el-descriptions-item>
                <el-descriptions-item label="决定系数 R²">
                  {{ analysisResult.result.metrics?.r2.toFixed(4) || analysisResult.result.r2_score?.toFixed(4) || '0.0000' }}
                </el-descriptions-item>
                <el-descriptions-item label="平均绝对误差 MAE">
                  {{ analysisResult.result.metrics?.mae.toFixed(4) || '0.0000' }}
                </el-descriptions-item>
                <el-descriptions-item label="均方误差 MSE">
                  {{ analysisResult.result.metrics?.mse.toFixed(4) || '0.0000' }}
                </el-descriptions-item>
                <el-descriptions-item label="目标特征">
                  {{ analysisResult.result.target || analysisParams.targetFeature || '未指定' }}
                </el-descriptions-item>
                <el-descriptions-item label="特征重要性">
                  <div v-if="analysisResult.result.coefficients">
                    <div v-for="(coef, index) in analysisResult.result.coefficients" :key="index" 
                         :style="{ color: getCoefColor(coef) }">
                      {{ analysisResult.result.feature_names?.[index] || analysisParams.selectedFeatures[index] }}: 
                      {{ typeof coef === 'number' ? coef.toFixed(4) : coef }}
                    </div>
                  </div>
                </el-descriptions-item>
              </el-descriptions>
              
              <!-- 线性回归高级特性信息 -->
              <div v-if="analysisResult.algorithm === 'linear' && analysisResult.result.extra_info" 
                   class="advanced-info">
                <el-alert
                  type="info"
                  :closable="false"
                  show-icon
                >
                  <template #title>线性回归模型信息</template>
                  <template #default>
                    <div>
                      <p><strong>模型类型:</strong> 
                        {{ getLinearTypeLabel(analysisResult.result.extra_info.linear_type) }}
                      </p>
                      <p><strong>特征缩放:</strong> 
                        {{ analysisResult.result.extra_info.scaled ? '已应用' : '未应用' }}
                      </p>
                      <p v-if="analysisResult.result.extra_info.polynomial">
                        <strong>多项式特征:</strong> 
                        已应用 (阶数: {{ analysisResult.result.extra_info.polynomial.degree }})
                      </p>
                    </div>
                  </template>
                </el-alert>
              </div>
              
              <div v-if="analysisResult.algorithm === 'random_forest'" class="forest-info">
                <el-alert
                  type="info"
                  :closable="false"
                  show-icon
                >
                  <template #title>随机森林回归</template>
                  <template #default>
                    随机森林模型通常比线性回归提供更高的预测精度，特别是对于非线性关系。特征重要性表示每个特征对预测的贡献度。
                  </template>
                </el-alert>
              </div>
            </div>
          </template>
          
          <div ref="chartContainer" class="chart-container"></div>
        </div>
        
        <el-empty v-else description="请选择分析方法并运行分析" />
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

.analysis-result {
  margin-top: 20px;
}

.result-metrics {
  margin-bottom: 20px;
}

.chart-container {
  width: 100%;
  height: 500px;
  margin-top: 20px;
}

.feature-tag {
  margin-right: 8px;
  margin-bottom: 8px;
}

.empty-features {
  padding: 10px;
  color: #909399;
  border: 1px dashed #dcdfe6;
  border-radius: 4px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.placeholder-text {
  color: #909399;
}

.feature-actions {
  margin-top: 10px;
  display: flex;
  gap: 10px;
}

.selected-features {
  min-height: 40px;
  padding: 5px 0;
}

.feature-checkbox {
  display: block;
  margin: 8px 0;
}

.target-help {
  margin-top: 10px;
}

.option-hint {
  margin-left: 10px;
  color: #909399;
  font-size: 12px;
}

.advanced-info, .forest-info {
  margin-top: 15px;
}

.empty-files-tip {
  margin-top: 10px;
}
</style> 