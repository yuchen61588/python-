<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore, useDataStore } from '../stores/index'
import { login, register, getDataFiles } from '../utils/api'
import { ElMessage } from 'element-plus'

const router = useRouter()
const authStore = useAuthStore()
const dataStore = useDataStore()

const activeTab = ref('login')
const loading = ref(false)
const dataFiles = ref([])

// 登录表单
const loginForm = ref({
  username: '',
  password: ''
})

// 注册表单
const registerForm = ref({
  username: '',
  email: '',
  password: '',
  confirmPassword: ''
})

// 登录规则
const loginRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' }
  ]
}

// 注册规则
const registerRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' }
  ],
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入正确的邮箱格式', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码长度至少为6个字符', trigger: 'blur' }
  ],
  confirmPassword: [
    { required: true, message: '请确认密码', trigger: 'blur' },
    { 
      validator: (rule, value, callback) => {
        if (value !== registerForm.value.password) {
          callback(new Error('两次输入的密码不一致'))
        } else {
          callback()
        }
      }, 
      trigger: 'blur' 
    }
  ]
}

// 判断是否已登录
const isLoggedIn = computed(() => authStore.isAuthenticated)
const username = computed(() => authStore.username)

// 处理登录
const handleLogin = async (formEl) => {
  if (!formEl) return
  
  await formEl.validate(async (valid) => {
    if (valid) {
      loading.value = true
      
      // 直接添加调试输出
      const credentials = {
        username: loginForm.value.username,
        password: loginForm.value.password
      }
      console.log('===准备发送登录请求===', credentials)
      
      try {
        // 使用更直接的fetch调用
        const directResponse = await fetch('http://localhost:8000/api/login/', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(credentials)
        })
        
        const responseData = await directResponse.json()
        console.log('===登录响应数据===', responseData)
        
        if (responseData.token) {
          authStore.setToken(responseData.token)
          authStore.setUser({
            id: responseData.user_id,
            username: responseData.username,
            email: responseData.email
          })
          
          ElMessage.success('登录成功')
          // 获取数据文件列表
          fetchDataFiles()
        } else {
          console.error('登录失败:', responseData)
          ElMessage.error('登录失败: ' + (responseData.error || '请查看控制台获取详细信息'))
        }
      } catch (error) {
        console.error('===登录详细错误===', error)
        ElMessage.error('登录失败: ' + (error.message || '用户名或密码错误，请查看控制台'))
      } finally {
        loading.value = false
      }
    }
  })
}

// 处理注册
const handleRegister = async (formEl) => {
  if (!formEl) return
  
  await formEl.validate(async (valid) => {
    if (valid) {
      loading.value = true
      
      // 直接添加调试输出
      const userData = {
        username: registerForm.value.username,
        email: registerForm.value.email,
        password: registerForm.value.password,
        first_name: '',
        last_name: ''
      }
      console.log('===准备发送注册请求===', userData)
      
      try {
        // 使用更直接的axios调用
        const directResponse = await fetch('http://localhost:8000/api/register/', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(userData)
        })
        
        const responseData = await directResponse.json()
        console.log('===注册响应数据===', responseData)
        
        if (responseData.token) {
          authStore.setToken(responseData.token)
          authStore.setUser(responseData.user)
          
          ElMessage.success('注册成功')
          // 获取数据文件列表
          fetchDataFiles()
        } else {
          console.error('注册失败:', responseData)
          ElMessage.error('注册失败: ' + (responseData.error || '请查看控制台获取详细信息'))
        }
      } catch (error) {
        console.error('===注册详细错误===', error)
        ElMessage.error('注册失败: ' + (error.message || '未知错误，请查看控制台'))
      } finally {
        loading.value = false
      }
    }
  })
}

// 登出
const handleLogout = () => {
  authStore.logout()
  ElMessage.success('已退出登录')
}

// 获取文件列表
const fetchDataFiles = async () => {
  try {
    loading.value = true
    const response = await getDataFiles()
    dataFiles.value = response.data || []
  } catch (error) {
    console.error('获取文件列表失败:', error)
  } finally {
    loading.value = false
  }
}

// 跳转到功能页面
const navigateTo = (path) => {
  router.push(path)
}

// 处理登录表单提交
const handleLoginSubmit = async (event) => {
  loading.value = true
  
  // 直接添加调试输出
  const credentials = {
    username: loginForm.value.username,
    password: loginForm.value.password
  }
  console.log('===准备发送登录请求===', credentials)
  
  try {
    // 使用更直接的fetch调用
    const directResponse = await fetch('http://localhost:8000/api/login/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(credentials)
    })
    
    const responseData = await directResponse.json()
    console.log('===登录响应数据===', responseData)
    
    if (responseData.token) {
      authStore.setToken(responseData.token)
      authStore.setUser({
        id: responseData.user_id,
        username: responseData.username,
        email: responseData.email
      })
      
      ElMessage.success('登录成功')
      // 获取数据文件列表
      fetchDataFiles()
    } else {
      console.error('登录失败:', responseData)
      ElMessage.error('登录失败: ' + (responseData.error || '请查看控制台获取详细信息'))
    }
  } catch (error) {
    console.error('===登录详细错误===', error)
    ElMessage.error('登录失败: ' + (error.message || '用户名或密码错误，请查看控制台'))
  } finally {
    loading.value = false
  }
}

// 处理注册表单提交
const handleRegisterSubmit = async (event) => {
  // 验证密码是否一致
  if (registerForm.value.password !== registerForm.value.confirmPassword) {
    ElMessage.error('两次输入的密码不一致')
    return
  }
  
  loading.value = true
  
  // 直接添加调试输出
  const userData = {
    username: registerForm.value.username,
    email: registerForm.value.email,
    password: registerForm.value.password,
    first_name: '',
    last_name: ''
  }
  console.log('===准备发送注册请求===', userData)
  
  try {
    // 使用更直接的fetch调用
    const directResponse = await fetch('http://localhost:8000/api/register/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(userData)
    })
    
    const responseData = await directResponse.json()
    console.log('===注册响应数据===', responseData)
    
    if (responseData.token) {
      authStore.setToken(responseData.token)
      authStore.setUser(responseData.user)
      
      ElMessage.success('注册成功')
      // 获取数据文件列表
      fetchDataFiles()
    } else {
      console.error('注册失败:', responseData)
      ElMessage.error('注册失败: ' + (responseData.error || '请查看控制台获取详细信息'))
    }
  } catch (error) {
    console.error('===注册详细错误===', error)
    ElMessage.error('注册失败: ' + (error.message || '未知错误，请查看控制台'))
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  if (authStore.isAuthenticated) {
    fetchDataFiles()
  }
})
</script>

<template>
  <main>
    <el-row justify="center">
      <el-col :span="18">
        <el-card shadow="hover" v-loading="loading">
          <template #header>
            <div class="card-header">
              <h2>交互式数据分析系统</h2>
              <div v-if="isLoggedIn" class="user-info">
                <span>欢迎，{{ username }}</span>
                <el-button type="danger" size="small" @click="handleLogout">退出登录</el-button>
              </div>
            </div>
          </template>
          
          <!-- 未登录状态 -->
          <div v-if="!isLoggedIn" class="login-container">
            <div class="login-tabs">
              <div class="tab-header">
                <button 
                  :class="{ active: activeTab === 'login' }" 
                  @click="activeTab = 'login'">登录</button>
                <button 
                  :class="{ active: activeTab === 'register' }" 
                  @click="activeTab = 'register'">注册</button>
              </div>
              
              <!-- 登录表单 -->
              <div v-if="activeTab === 'login'" class="tab-content">
                <form @submit.prevent="handleLoginSubmit">
                  <div class="form-group">
                    <label for="login-username">用户名</label>
                    <input 
                      id="login-username"
                      type="text" 
                      v-model="loginForm.username" 
                      placeholder="请输入用户名" 
                      required />
                  </div>
                  <div class="form-group">
                    <label for="login-password">密码</label>
                    <input 
                      id="login-password"
                      type="password" 
                      v-model="loginForm.password" 
                      placeholder="请输入密码" 
                      required />
                  </div>
                  <div class="form-group">
                    <button 
                      type="submit" 
                      class="submit-button"
                      :disabled="loading">
                      {{ loading ? '登录中...' : '登录' }}
                    </button>
                  </div>
                </form>
              </div>
              
              <!-- 注册表单 -->
              <div v-if="activeTab === 'register'" class="tab-content">
                <form @submit.prevent="handleRegisterSubmit">
                  <div class="form-group">
                    <label for="register-username">用户名</label>
                    <input 
                      id="register-username"
                      type="text" 
                      v-model="registerForm.username" 
                      placeholder="请输入用户名" 
                      required />
                  </div>
                  <div class="form-group">
                    <label for="register-email">邮箱</label>
                    <input 
                      id="register-email"
                      type="email" 
                      v-model="registerForm.email" 
                      placeholder="请输入邮箱" 
                      required />
                  </div>
                  <div class="form-group">
                    <label for="register-password">密码</label>
                    <input 
                      id="register-password"
                      type="password" 
                      v-model="registerForm.password" 
                      placeholder="请输入密码" 
                      required 
                      minlength="6" />
                  </div>
                  <div class="form-group">
                    <label for="register-confirm-password">确认密码</label>
                    <input 
                      id="register-confirm-password"
                      type="password" 
                      v-model="registerForm.confirmPassword" 
                      placeholder="请确认密码" 
                      required />
                  </div>
                  <div class="form-group">
                    <button 
                      type="submit" 
                      class="submit-button"
                      :disabled="loading">
                      {{ loading ? '注册中...' : '注册' }}
                    </button>
                  </div>
                </form>
              </div>
            </div>
          </div>
          
          <!-- 已登录状态 -->
          <div v-else class="card-content">
            <h3>系统功能</h3>
            
            <el-row :gutter="20" class="feature-cards">
              <el-col :span="8">
                <el-card shadow="hover" @click="navigateTo('/data-management')">
                  <div class="feature-card">
                    <el-icon :size="48" color="#409EFF"><Promotion /></el-icon>
                    <h3>数据管理</h3>
                    <p>上传、预览和导出数据文件</p>
                  </div>
                </el-card>
              </el-col>
              
              <el-col :span="8">
                <el-card shadow="hover" @click="navigateTo('/data-analysis')">
                  <div class="feature-card">
                    <el-icon :size="48" color="#67C23A"><DataAnalysis /></el-icon>
                    <h3>数据分析</h3>
                    <p>聚类、回归、分类和降维分析</p>
                  </div>
                </el-card>
              </el-col>
              
              <el-col :span="8">
                <el-card shadow="hover" @click="navigateTo('/data-visualization')">
                  <div class="feature-card">
                    <el-icon :size="48" color="#E6A23C"><PieChart /></el-icon>
                    <h3>数据可视化</h3>
                    <p>创建各种图表展示数据</p>
                  </div>
                </el-card>
              </el-col>
            </el-row>
            
            <!-- 最近文件列表 -->
            <div v-if="dataFiles.length > 0" class="recent-files">
              <h3>最近上传的文件</h3>
              <el-table :data="dataFiles.slice(0, 5)" border style="width: 100%">
                <el-table-column prop="name" label="文件名" />
                <el-table-column prop="file_type" label="文件类型" />
                <el-table-column prop="created_at" label="上传时间" width="180" />
                <el-table-column label="操作" width="180">
                  <template #default="scope">
                    <el-button size="small" @click="navigateTo('/data-management')">查看</el-button>
                  </template>
                </el-table-column>
              </el-table>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </main>
</template>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 10px;
}

.card-content {
  min-height: 400px;
}

.login-container {
  max-width: 400px;
  margin: 0 auto;
  padding: 20px 0;
}

.login-tabs {
  width: 100%;
}

.tab-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.tab-header button {
  flex: 1;
  padding: 12px 20px;
  border: none;
  background-color: #f0f0f0;
  cursor: pointer;
  transition: all 0.3s;
  font-size: 16px;
}

.tab-header button.active {
  background-color: #409EFF;
  color: #fff;
}

.tab-content {
  padding: 20px;
  background-color: #f9f9f9;
  border-radius: 4px;
}

.form-group {
  margin-bottom: 20px;
}

.form-group label {
  display: block;
  margin-bottom: 8px;
  font-weight: bold;
}

.form-group input {
  width: 100%;
  padding: 12px;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  font-size: 14px;
}

.submit-button {
  width: 100%;
  padding: 12px;
  background-color: #409EFF;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 16px;
}

.submit-button:hover {
  background-color: #66b1ff;
}

.submit-button:disabled {
  background-color: #a0cfff;
  cursor: not-allowed;
}

.feature-cards {
  margin: 20px 0 30px;
}

.feature-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 30px 20px;
  cursor: pointer;
  transition: all 0.3s;
}

.feature-card:hover {
  transform: translateY(-5px);
}

.feature-card h3 {
  margin: 15px 0 10px;
}

.feature-card p {
  color: #606266;
  margin: 0;
}

.recent-files {
  margin-top: 30px;
}
</style>
