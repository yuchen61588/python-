import { defineStore } from "pinia";

export const useDataStore = defineStore("data", {
  state: () => ({
    currentData: null, //当前数据
    dataHistory: [], //数据记录
    isLoading: false, //是否正在加载
    error: null, //错误信息
    currentFile: null, //当前操作的文件
    cleanedData: null, //清洗后的数据
  }),

  actions: {
    setCurrentData(data) {
      //设置当前数据
      this.currentData = data;
      this.dataHistory.push({
        id: Date.now(),
        data: data,
        timestamp: new Date().toISOString(),
      }); //历史记录，记录当前时间戳
    },

    setCurrentFile(file) {
      this.currentFile = file;
    }, //设置当前文件

    setCleanedData(data) {
      this.cleanedData = data;
    }, //设置i清洗后的数据

    clearData() {
      this.currentData = null;
    }, //清空数据

    setLoading(status) {
      this.isLoading = status;
    }, //设置加载状态

    setError(error) {
      this.error = error; //设置错误
    },
  },
  //是否有数据
  getters: {
    hasData: (state) => !!state.currentData, //计算属性 动态生成值
    historyCount: (state) => state.dataHistory.length,
  },
});

export const useAuthStore = defineStore("auth", {
  state: () => ({
    user: null, //用户信息
    token: localStorage.getItem("token") || null, //用户认证token，使用类似字典的方式,可以共享访问
    isLoading: false,
    error: null,
  }),

  actions: {
    setUser(user) {
      this.user = user;
    },

    setToken(token) {
      this.token = token;
      if (token) {
        localStorage.setItem("token", token); //后端生成的token 存储在localStorage
      } else {
        localStorage.removeItem("token");
      }
    },

    setLoading(status) {
      this.isLoading = status;
    },

    setError(error) {
      this.error = error;
    },

    logout() {
      this.user = null;
      this.token = null;
      localStorage.removeItem("token");
    },

    async checkAuth() {
      if (!this.token) return false;

      try {
        this.setLoading(true);
        // 可以在这里添加验证token有效性的请求
        return true;
      } catch (error) {
        this.logout();
        return false;
      } finally {
        this.setLoading(false);
      }
    },
  },
  //计算数据
  getters: {
    isAuthenticated: (state) => !!state.token, // 判断用户是否已认证
    username: (state) => state.user?.username || "游客", // 获取用户名，未登录时显示“游客”
  },
});
