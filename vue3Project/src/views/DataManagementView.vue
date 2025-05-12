<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElLoading } from 'element-plus'
import { uploadFile, getDataFiles, getDataFilePreview, exportData } from '../utils/api'
import { useDataStore } from '../stores/index'
import DataCleaning from '../components/DataCleaning.vue'

const dataStore = useDataStore()
const fileList = ref([])
const tableData = ref([])
const columns = ref([])
const loading = ref(false)
const currentFile = ref(null)
const dataFiles = ref([]) // 存储已上传的文件列表
const pagination = reactive({
  currentPage: 1,
  pageSize: 10,
  total: 0
})

// 控制当前显示的步骤
const currentStep = ref('upload') // 'upload' 或 'cleaning'

// 获取已上传的文件列表
const fetchDataFiles = async () => {
  try {
    loading.value = true
    const response = await getDataFiles()
    dataFiles.value = response.data
  } catch (error) {
    ElMessage.error('获取文件列表失败: ' + (error.message || '未知错误'))
  } finally {
    loading.value = false
  }
}

// 预览文件数据
const previewFile = async (fileId) => {
  try {
    loading.value = true
    const response = await getDataFilePreview(fileId)
    if (response.data) {
      processData(response.data)
      
      // 设置当前文件
      const file = dataFiles.value.find(f => f.id === fileId)
      if (file) {
        currentFile.value = file
        dataStore.setCurrentFile(file)
      }
      
      ElMessage.success('数据预览成功')
    }
  } catch (error) {
    ElMessage.error('预览数据失败: ' + (error.message || '未知错误'))
  } finally {
    loading.value = false
  }
}

// 处理文件上传
const handleUpload = (file) => {
  if (!file) return false
  
  const fileType = file.raw.type
  const isCSV = fileType === 'text/csv'
  const isExcel = fileType === 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' || 
                 fileType === 'application/vnd.ms-excel'
  
  if (!isCSV && !isExcel) {
    ElMessage.error('只支持上传CSV或Excel文件!')
    return false
  }
  
  uploadSelectedFile(file.raw)
  return false
}

// 上传文件到服务器
const uploadSelectedFile = async (file) => {
  if (!file) return
  loading.value = true
  dataStore.setLoading(true)
  
  try {
    const loadingInstance = ElLoading.service({
      lock: true,
      text: '上传中...',
      background: 'rgba(0, 0, 0, 0.7)'
    })
    
    const response = await uploadFile(file, file.name, '用户上传的数据文件')
    
    if (response.data) {
      // 刷新文件列表
      await fetchDataFiles()
      
      // 预览上传的文件
      if (response.data.id) {
        await previewFile(response.data.id)
      }
      
      ElMessage.success('上传成功')
    }
    
    loadingInstance.close()
  } catch (error) {
    ElMessage.error('上传失败: ' + (error.message || '未知错误'))
    dataStore.setError(error.message || '上传失败')
    
    // 临时处理：当后端未实现时，模拟数据预览
    if (file.type === 'text/csv') {
      const reader = new FileReader()
      reader.onload = (e) => {
        const text = e.target.result
        const lines = text.split('\n')
        const headers = lines[0].split(',')
        
        columns.value = headers.map(header => ({
          prop: header.trim(),
          label: header.trim()
        }))
        
        const records = []
        for (let i = 1; i < Math.min(lines.length, 100); i++) {
          if (lines[i].trim()) {
            const values = lines[i].split(',')
            const record = {}
            headers.forEach((header, index) => {
              record[header.trim()] = values[index] ? values[index].trim() : ''
            })
            records.push(record)
          }
        }
        
        tableData.value = records
        pagination.total = records.length
        dataStore.setCurrentData(records)
        ElMessage.success('文件已预览（模拟数据）')
      }
      reader.readAsText(file)
    }
  } finally {
    loading.value = false
    dataStore.setLoading(false)
  }
}

// 处理返回的数据
const processData = (data) => {
  if (!data) {
    tableData.value = []
    columns.value = []
    return
  }
  
  // 检查数据格式，处理后端返回的结构化数据
  if (data.columns && data.data) {
    // 从响应中提取列信息
    columns.value = data.columns.map(col => ({
      prop: col,
      label: col
    }))
    
    // 从响应中提取数据
    tableData.value = data.data
    pagination.total = data.data.length
    dataStore.setCurrentData(data.data)
    return
  }
  
  // 处理旧格式的数据（兼容）
  if (!data.length) {
    tableData.value = []
    columns.value = []
    return
  }
  
  // 获取列名
  const firstRow = data[0]
  columns.value = Object.keys(firstRow).map(key => ({
    prop: key,
    label: key
  }))
  
  tableData.value = data
  pagination.total = data.length
  dataStore.setCurrentData(data)
}

// 处理数据导出
const handleExport = async () => {
  if (!currentFile.value) {
    ElMessage.warning('请先选择要导出的数据文件')
    return
  }
  
  loading.value = true
  try {
    const response = await exportData(currentFile.value.id, 'csv')
    const url = window.URL.createObjectURL(new Blob([response.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', `${currentFile.value.name}_export_${new Date().getTime()}.csv`)
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    ElMessage.success('导出成功')
  } catch (error) {
    ElMessage.error('导出失败: ' + (error.message || '未知错误'))
    
    // 临时处理：当后端未实现时，前端导出CSV
    if (tableData.value && tableData.value.length > 0) {
      const csvContent = convertToCSV(tableData.value)
      const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', `data_export_${new Date().getTime()}.csv`)
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      ElMessage.success('文件已导出（前端生成）')
    }
  } finally {
    loading.value = false
  }
}

// 转换数据为CSV格式
const convertToCSV = (objArray) => {
  if (!objArray || !objArray.length) return ''
  
  const array = typeof objArray !== 'object' ? JSON.parse(objArray) : objArray
  let str = ''
  const headers = Object.keys(array[0])
  
  str += headers.join(',') + '\r\n'
  
  for (let i = 0; i < array.length; i++) {
    let line = ''
    for (let index in headers) {
      if (line !== '') line += ','
      let value = array[i][headers[index]]
      line += value !== undefined ? value : ''
    }
    str += line + '\r\n'
  }
  
  return str
}

// 处理页面变化
const handleCurrentChange = (val) => {
  pagination.currentPage = val
}

// 开始数据清洗
const startCleaning = () => {
  if (!tableData.value || tableData.value.length === 0) {
    ElMessage.warning('没有可清洗的数据')
    return
  }
  currentStep.value = 'cleaning'
}

// 数据清洗完成
const onCleaningComplete = (data) => {
  tableData.value = data
  pagination.total = data.length
  currentStep.value = 'upload'
  ElMessage.success('数据清洗已完成，可以继续处理或导出数据')
}

// 更新清洗后的数据
const updateCleanedData = (data) => {
  tableData.value = data
  pagination.total = data.length
  dataStore.setCurrentData(data)
}

// 选择文件查看
const selectFile = (file) => {
  previewFile(file.id)
}

// 监听数据存储变化
onMounted(() => {
  fetchDataFiles()
  
  if (dataStore.currentData) {
    processData(dataStore.currentData)
  }
})
</script>

<template>
  <div class="data-management">
    <div v-if="currentStep === 'upload'">
      <el-card v-loading="loading">
        <template #header>
          <div class="card-header">
            <h2>数据管理</h2>
            <div class="step-buttons" v-if="tableData.length > 0">
              <el-button type="primary" @click="startCleaning">开始数据清洗</el-button>
            </div>
          </div>
        </template>
        <el-row :gutter="20">
          <el-col :span="24">
            <el-upload
              class="upload-demo"
              drag
              action="#"
              :auto-upload="false"
              :on-change="handleUpload"
              :file-list="fileList"
              :multiple="false"
            >
              <el-icon class="el-icon--upload"><upload-filled /></el-icon>
              <div class="el-upload__text">拖拽文件到此处或 <em>点击上传</em></div>
              <template #tip>
                <div class="el-upload__tip">支持 CSV/Excel 格式文件</div>
              </template>
            </el-upload>
          </el-col>
        </el-row>
        
        <el-divider v-if="dataFiles.length > 0" />
        
        <!-- 显示已上传的文件列表 -->
        <el-row v-if="dataFiles.length > 0">
          <el-col :span="24">
            <h3>已上传的文件</h3>
            <el-table :data="dataFiles" border style="width: 100%">
              <el-table-column prop="name" label="文件名" />
              <el-table-column prop="file_type" label="文件类型" />
              <el-table-column prop="created_at" label="上传时间" width="180" />
              <el-table-column label="操作" width="180">
                <template #default="scope">
                  <el-button size="small" @click="selectFile(scope.row)">查看</el-button>
                </template>
              </el-table-column>
            </el-table>
          </el-col>
        </el-row>
        
        <el-divider />
        
        <el-row v-if="tableData.length > 0">
          <el-col :span="24">
            <div class="table-operations">
              <el-button type="primary" @click="handleExport" :loading="loading">导出数据</el-button>
            </div>
            <el-table :data="tableData.slice((pagination.currentPage - 1) * pagination.pageSize, pagination.currentPage * pagination.pageSize)" border style="width: 100%" height="400">
              <el-table-column 
                v-for="column in columns" 
                :key="column.prop" 
                :prop="column.prop" 
                :label="column.label" 
              />
            </el-table>
            <div class="pagination-container">
              <el-pagination
                v-if="tableData.length > pagination.pageSize"
                :current-page="pagination.currentPage"
                :page-size="pagination.pageSize"
                :total="pagination.total"
                layout="total, prev, pager, next"
                @current-change="handleCurrentChange"
              />
            </div>
          </el-col>
        </el-row>
        
        <el-empty v-else description="暂无数据，请上传文件或选择已有文件" />
      </el-card>
    </div>
    
    <div v-else-if="currentStep === 'cleaning'">
      <DataCleaning 
        :data="tableData" 
        @update:data="updateCleanedData" 
        @cleaning-complete="onCleaningComplete" 
      />
    </div>
  </div>
</template>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.table-operations {
  margin-bottom: 20px;
  display: flex;
  justify-content: flex-end;
}

.pagination-container {
  margin-top: 20px;
  display: flex;
  justify-content: center;
}

.step-buttons {
  display: flex;
  gap: 10px;
}
</style> 