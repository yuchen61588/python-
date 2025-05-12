import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '../views/HomeView.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'home',
      component: HomeView,
    },
    {
      path: '/data-management',
      name: 'dataManagement',
      component: () => import('../views/DataManagementView.vue'),
    },
    {
      path: '/data-analysis',
      name: 'dataAnalysis',
      component: () => import('../views/DataAnalysisView.vue'),
    },
    {
      path: '/data-visualization',
      name: 'dataVisualization',
      component: () => import('../views/DataVisualizationView.vue'),
    },
  ],
})

export default router
