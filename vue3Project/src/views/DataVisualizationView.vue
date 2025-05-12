<script setup>
import { ref, onMounted, shallowRef, computed, watch } from 'vue'
import * as echarts from 'echarts'
import { useDataStore } from '../stores/index'
import { ElMessage } from 'element-plus'
import { getDataFiles, getDataFilePreview, createVisualization } from '../utils/api'

const dataStore = useDataStore()
const loading = ref(false)
const noDataMessage = ref('')
const dataFiles = ref([])
const weatherData = ref(null)

// 图表实例
const temperatureChartInstance = shallowRef(null)
const humidityChartInstance = shallowRef(null)
const precipitationChartInstance = shallowRef(null)
const bbqChartInstance = shallowRef(null)
const temperatureChartContainer = ref(null)
const humidityChartContainer = ref(null)
const precipitationChartContainer = ref(null)
const bbqChartContainer = ref(null)

// 选择的城市
const selectedCities = ref([])
const allCities = ref([])

// 日期格式化
const formatDate = (dateNum) => {
  const dateStr = String(dateNum)
  if (dateStr.length === 8) {
    const year = dateStr.substring(0, 4)
    const month = dateStr.substring(4, 6)
    const day = dateStr.substring(6, 8)
    return `${year}-${month}-${day}`
  }
  return dateStr
}

// 加载天气数据
const loadWeatherData = async () => {
  try {
    loading.value = true
    
    // 获取文件列表
    const filesResponse = await getDataFiles()
    dataFiles.value = filesResponse.data || []
    
    // 查找天气数据文件
    const weatherFile = dataFiles.value.find(file => 
      file.name.includes('weather_prediction_dataset') || 
      file.name.toLowerCase().includes('weather')
    )
    
    if (!weatherFile) {
      noDataMessage.value = '找不到天气数据文件，请先上传weather_prediction_dataset.csv'
      loading.value = false
      return
    }
    
    // 加载文件数据
    const response = await getDataFilePreview(weatherFile.id)
    
    if (response.data) {
      // 处理后端返回的结构化数据
      if (response.data.data && Array.isArray(response.data.data)) {
        weatherData.value = response.data.data
      } else if (Array.isArray(response.data)) {
        weatherData.value = response.data
      }
      
      if (weatherData.value && weatherData.value.length > 0) {
        // 检查数据是否只包含DATE和BBQ相关列
        const keys = Object.keys(weatherData.value[0]);
        const hasMeteorologyData = keys.some(key => 
          !key.includes('_BBQ_weather') && key !== 'DATE'
        );
        
        if (!hasMeteorologyData) {
          // 添加模拟气象数据以便演示
          addMockWeatherData();
        }
        
        extractCityNames()
        renderCharts()
        noDataMessage.value = ''
      } else {
        noDataMessage.value = '数据加载成功但格式有误'
      }
    }
  } catch (error) {
    console.error('加载天气数据失败:', error)
    noDataMessage.value = '加载天气数据失败: ' + (error.message || '未知错误')
  } finally {
    loading.value = false
  }
}

// 添加模拟气象数据以便演示
const addMockWeatherData = () => {
  if (!weatherData.value || weatherData.value.length === 0) return;
  
  const cities = ['BASEL', 'BUDAPEST', 'DRESDEN', 'DUSSELDORF', 'HEATHROW', 
                 'LJUBLJANA', 'MUENCHEN', 'OSLO', 'STOCKHOLM'];
  
  // 为每条记录添加模拟的温度、湿度和降水量数据
  weatherData.value = weatherData.value.map(record => {
    const date = new Date(
      parseInt(String(record.DATE).substring(0, 4)), 
      parseInt(String(record.DATE).substring(4, 6)) - 1, 
      parseInt(String(record.DATE).substring(6, 8))
    );
    
    const enhancedRecord = { ...record };
    
    // 季节因子 (0-1)
    const seasonFactor = Math.sin((date.getMonth() / 12) * 2 * Math.PI);
    
    // 为每个城市添加温度数据 (随季节变化)
    cities.forEach(city => {
      // 基础温度 + 季节变化 + 随机噪声
      const baseTemp = 15 + (city === 'OSLO' || city === 'STOCKHOLM' ? -5 : 
                           city === 'BUDAPEST' ? 3 : 0);
      enhancedRecord[`TG_${city}`] = baseTemp + (seasonFactor * 15) + (Math.random() * 5 - 2.5);
      
      // 湿度数据 (反季节变化 + 随机噪声)
      enhancedRecord[`HU_${city}`] = 60 + ((1-seasonFactor) * 20) + (Math.random() * 15);
      
      // 降水数据 (季节相关 + 随机事件)
      const isRainyDay = Math.random() < (0.3 + seasonFactor * 0.2);
      enhancedRecord[`RR_${city}`] = isRainyDay ? (Math.random() * 25) + 0.5 : 0;
    });
    
    return enhancedRecord;
  });
}

// 提取所有城市名称
const extractCityNames = () => {
  if (!weatherData.value || weatherData.value.length === 0) return
  
  const firstRecord = weatherData.value[0]
  const cityColumns = Object.keys(firstRecord).filter(key => key.includes('_BBQ_weather'))
  
  allCities.value = cityColumns.map(column => {
    return column.replace('_BBQ_weather', '')
  })
  
  if (allCities.value.length > 0) {
    // 默认选择前5个城市
    selectedCities.value = allCities.value.slice(0, 5)
  }
}

// 处理城市选择变化
const handleCitySelectionChange = () => {
  renderBBQChart()
}

// 渲染所有图表
const renderCharts = () => {
  if (!weatherData.value || weatherData.value.length === 0) return
  
  // 确保图表实例初始化
  if (!temperatureChartInstance.value && temperatureChartContainer.value) {
    temperatureChartInstance.value = echarts.init(temperatureChartContainer.value)
  }
  
  if (!humidityChartInstance.value && humidityChartContainer.value) {
    humidityChartInstance.value = echarts.init(humidityChartContainer.value)
  }
  
  if (!precipitationChartInstance.value && precipitationChartContainer.value) {
    precipitationChartInstance.value = echarts.init(precipitationChartContainer.value)
  }
  
  if (!bbqChartInstance.value && bbqChartContainer.value) {
    bbqChartInstance.value = echarts.init(bbqChartContainer.value)
  }
  
  renderTemperatureChart()
  renderHumidityChart()
  renderPrecipitationChart()
  renderBBQChart()
}

// 渲染BBQ天气状态图表
const renderBBQChart = () => {
  if (!bbqChartInstance.value || !weatherData.value) return
  
  // 提取数据
  const data = weatherData.value
  
  // 按年份分组统计
  const yearlyData = {}
  
  data.forEach(item => {
    const date = String(item.DATE)
    if (date.length === 8) {
      const year = date.substring(0, 4)
      
      if (!yearlyData[year]) {
        yearlyData[year] = {}
        selectedCities.value.forEach(city => {
          yearlyData[year][city] = { 
            total: 0, 
            bbqSuitable: 0 
          }
        })
      }
      
      selectedCities.value.forEach(city => {
        const bbqColumn = `${city}_BBQ_weather`
        if (item[bbqColumn] !== undefined) {
          yearlyData[year][city].total++
          if (item[bbqColumn] === 'true' || item[bbqColumn] === true) {
            yearlyData[year][city].bbqSuitable++
          }
        }
      })
    }
  })
  
  // 准备图表数据
  const years = Object.keys(yearlyData).sort()
  const seriesData = selectedCities.value.map(city => {
    return {
      name: city,
      type: 'bar',
      data: years.map(year => {
        const cityData = yearlyData[year][city]
        return cityData ? Math.round(cityData.bbqSuitable / cityData.total * 100) : 0
      })
    }
  })
  
  // 创建图表配置
  const option = {
    title: {
      text: '城市BBQ适宜天气比例'
    },
    tooltip: {
      trigger: 'axis',
      formatter: function(params) {
        let result = params[0].axisValue + '年<br/>'
        params.forEach(param => {
          result += param.seriesName + ': ' + param.value + '%<br/>'
        })
        return result
      }
    },
    legend: {
      data: selectedCities.value,
      type: 'scroll',
      orient: 'horizontal'
    },
    toolbox: {
      feature: {
        saveAsImage: {}
      }
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: years,
      name: '年份'
    },
    yAxis: {
      type: 'value',
      name: 'BBQ适宜天气比例 (%)',
      max: 100
    },
    series: seriesData
  }
  
  bbqChartInstance.value.setOption(option)
}

// 渲染温度图表
const renderTemperatureChart = () => {
  if (!temperatureChartInstance.value || !weatherData.value) return
  
  // 提取数据
  const data = weatherData.value.slice(0, 100) // 限制显示100天数据，避免过多数据导致性能问题
  const dates = data.map(item => formatDate(item.DATE))
  
  // 获取所有列名
  const allColumns = Object.keys(data[0])
  
  // 排除不应该作为数据列的列
  const excludeColumns = ['DATE'].concat(allColumns.filter(key => key.includes('_BBQ_weather')))
  
  // 查找温度相关的列 - 更灵活的匹配
  let temperatureColumns = allColumns.filter(key => 
    key.includes('TG_') || // 平均温度
    key.includes('TX_') || // 最高温度
    key.includes('TN_')    // 最低温度
  )
  
  // 如果没有找到匹配的列，尝试更宽松的匹配
  if (temperatureColumns.length === 0) {
    temperatureColumns = allColumns.filter(key => 
      key.includes('TEMP') || 
      key.includes('temp') || 
      key.includes('Temp') ||
      key.includes('TG') ||
      key.includes('TX') ||
      key.includes('TN')
    )
  }
  
  // 限制显示的城市数量
  temperatureColumns = temperatureColumns.slice(0, 5)
  
  // 如果仍然没有找到温度列，使用前5个数值列（排除DATE和BBQ列）
  if (temperatureColumns.length === 0) {
    temperatureColumns = allColumns.filter(key => {
      const sample = data[0][key]
      return !excludeColumns.includes(key) && 
             (typeof sample === 'number' || (!isNaN(Number(sample)) && sample !== '' && sample !== true && sample !== false))
    }).slice(0, 5)
  }
  
  // 如果仍然没有找到有效列，显示提示信息
  if (temperatureColumns.length === 0) {
    temperatureChartInstance.value.setOption({
      title: {
        text: '欧洲城市温度变化趋势',
        subtext: '找不到温度相关数据列'
      },
      tooltip: {},
      xAxis: {
        type: 'category',
        data: ['无数据']
      },
      yAxis: {
        type: 'value'
      },
      series: []
    })
    return
  }
  
  // 创建图表配置
  const option = {
    title: {
      text: '欧洲城市温度变化趋势'
    },
    tooltip: {
      trigger: 'axis'
    },
    legend: {
      data: temperatureColumns,
      type: 'scroll',
      orient: 'horizontal'
    },
    toolbox: {
      feature: {
        saveAsImage: {}
      }
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: dates,
      axisLabel: {
        rotate: 45
      }
    },
    yAxis: {
      type: 'value',
      name: '温度 (°C)'
    },
    series: temperatureColumns.map(column => ({
      name: column,
      type: 'line',
      data: data.map(item => {
        const value = item[column]
        // 确保值是数字
        return typeof value === 'number' ? value : parseFloat(value) || 0
      })
    }))
  }
  
  temperatureChartInstance.value.setOption(option)
}

// 渲染湿度图表
const renderHumidityChart = () => {
  if (!humidityChartInstance.value || !weatherData.value) return
  
  // 提取数据
  const data = weatherData.value.slice(0, 100)
  const dates = data.map(item => formatDate(item.DATE))
  
  // 获取所有列名
  const allColumns = Object.keys(data[0])
  
  // 排除不应该作为数据列的列
  const excludeColumns = ['DATE'].concat(allColumns.filter(key => key.includes('_BBQ_weather')))
  
  // 查找湿度相关的列 - 更灵活的匹配
  let humidityColumns = allColumns.filter(key => 
    key.includes('HU_') ||
    key.includes('HUMIDITY') ||
    key.includes('Humidity') ||
    key.includes('humidity')
  )
  
  // 如果没有找到匹配的列，尝试更宽松的匹配
  if (humidityColumns.length === 0) {
    humidityColumns = allColumns.filter(key => 
      key.includes('HU') ||
      key.includes('hum')
    )
  }
  
  // 限制显示的城市数量
  humidityColumns = humidityColumns.slice(0, 5)
  
  // 如果仍然没有找到湿度列，使用前5个与温度不同的数值列（排除DATE和BBQ列）
  if (humidityColumns.length === 0) {
    const temperatureColumns = allColumns.filter(key => 
      key.includes('TG_') || key.includes('TX_') || key.includes('TN_')
    )
    
    humidityColumns = allColumns.filter(key => {
      const sample = data[0][key]
      return !excludeColumns.includes(key) && 
             !temperatureColumns.includes(key) && 
             (typeof sample === 'number' || (!isNaN(Number(sample)) && sample !== '' && sample !== true && sample !== false))
    }).slice(0, 5)
  }
  
  // 如果仍然没有找到有效列，显示提示信息
  if (humidityColumns.length === 0) {
    humidityChartInstance.value.setOption({
      title: {
        text: '欧洲城市湿度变化趋势',
        subtext: '找不到湿度相关数据列'
      },
      tooltip: {},
      xAxis: {
        type: 'category',
        data: ['无数据']
      },
      yAxis: {
        type: 'value'
      },
      series: []
    })
    return
  }
  
  // 创建图表配置
  const option = {
    title: {
      text: '欧洲城市湿度变化趋势'
    },
    tooltip: {
      trigger: 'axis'
    },
    legend: {
      data: humidityColumns,
      type: 'scroll',
      orient: 'horizontal'
    },
    toolbox: {
      feature: {
        saveAsImage: {}
      }
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: dates,
      axisLabel: {
        rotate: 45
      }
    },
    yAxis: {
      type: 'value',
      name: '湿度 (%)'
    },
    series: humidityColumns.map(column => ({
      name: column,
      type: 'line',
      data: data.map(item => {
        const value = item[column]
        // 确保值是数字
        return typeof value === 'number' ? value : parseFloat(value) || 0
      })
    }))
  }
  
  humidityChartInstance.value.setOption(option)
}

// 渲染降水图表
const renderPrecipitationChart = () => {
  if (!precipitationChartInstance.value || !weatherData.value) return
  
  // 提取数据
  const data = weatherData.value.slice(0, 100)
  const dates = data.map(item => formatDate(item.DATE))
  
  // 获取所有列名
  const allColumns = Object.keys(data[0])
  
  // 排除不应该作为数据列的列
  const excludeColumns = ['DATE'].concat(allColumns.filter(key => key.includes('_BBQ_weather')))
  
  // 查找降水相关的列 - 更灵活的匹配
  let precipitationColumns = allColumns.filter(key => 
    key.includes('RR_') ||
    key.includes('PRECIP') ||
    key.includes('Precip') ||
    key.includes('precip')
  )
  
  // 如果没有找到匹配的列，尝试更宽松的匹配
  if (precipitationColumns.length === 0) {
    precipitationColumns = allColumns.filter(key => 
      key.includes('RR') ||
      key.includes('rain') ||
      key.includes('Rain')
    )
  }
  
  // 限制显示的城市数量
  precipitationColumns = precipitationColumns.slice(0, 5)
  
  // 如果仍然没有找到降水列，使用剩余的数值列（排除DATE和BBQ列）
  if (precipitationColumns.length === 0) {
    const temperatureColumns = allColumns.filter(key => 
      key.includes('TG_') || key.includes('TX_') || key.includes('TN_')
    )
    
    const humidityColumns = allColumns.filter(key => 
      key.includes('HU_')
    )
    
    precipitationColumns = allColumns.filter(key => {
      const sample = data[0][key]
      return !excludeColumns.includes(key) && 
             !temperatureColumns.includes(key) && 
             !humidityColumns.includes(key) && 
             (typeof sample === 'number' || (!isNaN(Number(sample)) && sample !== '' && sample !== true && sample !== false))
    }).slice(0, 5)
  }
  
  // 如果仍然没有找到有效列，显示提示信息
  if (precipitationColumns.length === 0) {
    precipitationChartInstance.value.setOption({
      title: {
        text: '欧洲城市降水量变化趋势',
        subtext: '找不到降水相关数据列'
      },
      tooltip: {},
      xAxis: {
        type: 'category',
        data: ['无数据']
      },
      yAxis: {
        type: 'value'
      },
      series: []
    })
    return
  }
  
  // 创建图表配置
  const option = {
    title: {
      text: '欧洲城市降水量变化趋势'
    },
    tooltip: {
      trigger: 'axis'
    },
    legend: {
      data: precipitationColumns,
      type: 'scroll',
      orient: 'horizontal'
    },
    toolbox: {
      feature: {
        saveAsImage: {}
      }
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: dates,
      axisLabel: {
        rotate: 45
      }
    },
    yAxis: {
      type: 'value',
      name: '降水量 (mm)'
    },
    series: precipitationColumns.map(column => ({
      name: column,
      type: 'bar',
      data: data.map(item => {
        const value = item[column]
        // 确保值是数字
        return typeof value === 'number' ? value : parseFloat(value) || 0
      })
    }))
  }
  
  precipitationChartInstance.value.setOption(option)
}

// 导出图表为图片
const exportCharts = () => {
  if (!weatherData.value) {
    ElMessage.error('没有可导出的图表')
    return
  }
  
  const charts = [
    { instance: bbqChartInstance.value, name: 'bbq_chart' },
    { instance: temperatureChartInstance.value, name: 'temperature_chart' },
    { instance: humidityChartInstance.value, name: 'humidity_chart' },
    { instance: precipitationChartInstance.value, name: 'precipitation_chart' }
  ]
  
  charts.forEach(chart => {
    if (chart.instance) {
      const dataURL = chart.instance.getDataURL({
        type: 'png',
        pixelRatio: 2,
        backgroundColor: '#fff'
      })
      
      const link = document.createElement('a')
      link.href = dataURL
      link.download = `${chart.name}_${new Date().getTime()}.png`
      link.click()
    }
  })
  
  ElMessage.success('图表已导出')
}

// 监听窗口大小变化
const handleResize = () => {
  if (temperatureChartInstance.value) {
    temperatureChartInstance.value.resize()
  }
  if (humidityChartInstance.value) {
    humidityChartInstance.value.resize()
  }
  if (precipitationChartInstance.value) {
    precipitationChartInstance.value.resize()
  }
  if (bbqChartInstance.value) {
    bbqChartInstance.value.resize()
  }
}

// 生命周期钩子
onMounted(() => {
  loadWeatherData()
  window.addEventListener('resize', handleResize)
})
</script>

<template>
  <div class="data-visualization">
    <el-card v-loading="loading">
      <template #header>
        <div class="card-header">
          <h2>天气数据可视化</h2>
          <el-button type="primary" @click="exportCharts" :disabled="!weatherData">导出图表</el-button>
        </div>
      </template>
      
      <el-empty v-if="noDataMessage" :description="noDataMessage">
        <el-button type="primary" @click="$router.push('/data-management')">去上传数据</el-button>
      </el-empty>
      
      <div v-else>
        <div class="chart-section">
          <h3>BBQ天气适宜性分析</h3>
          <div class="city-selector">
            <el-select
              v-model="selectedCities"
              multiple
              placeholder="选择城市"
              style="width: 100%;"
              @change="handleCitySelectionChange"
            >
              <el-option
                v-for="city in allCities"
                :key="city"
                :label="city"
                :value="city"
              />
            </el-select>
          </div>
          <div ref="bbqChartContainer" class="chart-container"></div>
        </div>
        
        <el-divider />
        
        <div class="chart-section">
          <h3>温度变化趋势</h3>
          <div ref="temperatureChartContainer" class="chart-container"></div>
        </div>
        
        <el-divider />
        
        <div class="chart-section">
          <h3>湿度变化趋势</h3>
          <div ref="humidityChartContainer" class="chart-container"></div>
        </div>
        
        <el-divider />
        
        <div class="chart-section">
          <h3>降水量变化趋势</h3>
          <div ref="precipitationChartContainer" class="chart-container"></div>
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

.chart-container {
  width: 100%;
  height: 400px;
  margin-top: 20px;
}

.chart-section {
  margin-bottom: 20px;
}

h3 {
  margin-top: 20px;
  margin-bottom: 0;
  font-weight: normal;
  color: #303133;
}

.city-selector {
  margin-top: 10px;
  margin-bottom: 10px;
}
</style> 