import { defineStore } from 'pinia'

export const useDataStore = defineStore('data', {
  state: () => ({
    currentData: null,
    dataHistory: [],
    isLoading: false,
    error: null,
    currentFile: null,
    cleanedData: null
  }),
  
  actions: {
    setCurrentData(data) {
      this.currentData = data
      this.dataHistory.push({
        id: Date.now(),
        data: data,
        timestamp: new Date().toISOString()
      })
    },
    
    setCurrentFile(file) {
      this.currentFile = file
    },
    
    setCleanedData(data) {
      this.cleanedData = data
    },
    
    clearData() {
      this.currentData = null
    },
    
    setLoading(status) {
      this.isLoading = status
    },
    
    setError(error) {
      this.error = error
    }
  },
  
  getters: {
    hasData: (state) => !!state.currentData,
    historyCount: (state) => state.dataHistory.length
  }
})

export const useAuthStore = defineStore('auth', {
  state: () => ({
    user: null,
    token: localStorage.getItem('token') || null,
    isLoading: false,
    error: null
  }),
  
  actions: {
    setUser(user) {
      this.user = user
    },
    
    setToken(token) {
      this.token = token
      if (token) {
        localStorage.setItem('token', token)
      } else {
        localStorage.removeItem('token')
      }
    },
    
    setLoading(status) {
      this.isLoading = status
    },
    
    setError(error) {
      this.error = error
    },
    
    logout() {
      this.user = null
      this.token = null
      localStorage.removeItem('token')
    },
    
    async checkAuth() {
      if (!this.token) return false
      
      try {
        this.setLoading(true)
        // 可以在这里添加验证token有效性的请求
        return true
      } catch (error) {
        this.logout()
        return false
      } finally {
        this.setLoading(false)
      }
    }
  },
  
  getters: {
    isAuthenticated: (state) => !!state.token,
    username: (state) => state.user?.username || '游客'
  }
}) 