/**
 * Vue Router 配置
 */
import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'Home',
    component: () => import('../views/PaperList.vue'),
    meta: { title: '论文列表' }
  },
  {
    path: '/paper/:paperId',
    name: 'PaperDetail',
    component: () => import('../views/PaperDetail.vue'),
    meta: { title: '论文详情' },
    props: true
  },
  {
    path: '/stats',
    name: 'StatsReport',
    component: () => import('../views/StatsReport.vue'),
    meta: { title: '统计报表' }
  }
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes
})

// 路由守卫 - 设置页面标题
router.beforeEach((to, from, next) => {
  document.title = to.meta.title ? `${to.meta.title} - Paper AI` : 'Paper AI'
  next()
})

export default router
