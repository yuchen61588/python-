<script setup>
import { RouterLink, RouterView } from 'vue-router'
</script>

<template>
  <el-config-provider>
    <div class="container">
      <el-container>
        <el-header>
          <h1>数据分析系统</h1>
          <div class="nav">
            <RouterLink to="/">首页</RouterLink>
            <RouterLink to="/data-management">数据管理</RouterLink>
            <RouterLink to="/data-analysis">数据分析</RouterLink>
            <RouterLink to="/data-visualization">数据可视化</RouterLink>
          </div>
        </el-header>
        <el-main>
          <RouterView />
        </el-main>
      </el-container>
    </div>
  </el-config-provider>
</template>

<style scoped>
.container {
  width: 100%;
  height: 100vh;
}

.el-header {
  background-color: #409EFF;
  color: white;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  }

.nav {
    display: flex;
  gap: 20px;
  }

.nav a {
  color: white;
  text-decoration: none;
  padding: 5px 10px;
  border-radius: 4px;
}

.nav a.router-link-active {
  background-color: rgba(255, 255, 255, 0.2);
}
</style>
