import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/LoginView.vue'),
    meta: { title: '登录', noAuth: true },
  },
  {
    path: '/',
    component: () => import('@/components/common/AppLayout.vue'),
    redirect: '/home',
    children: [
      {
        path: 'home',
        name: 'Home',
        component: () => import('@/views/HomeView.vue'),
        meta: { title: '首页' },
      },
      {
        path: 'stocks',
        name: 'StockList',
        component: () => import('@/views/StockListView.vue'),
        meta: { title: '股票' },
      },
      {
        path: 'portfolio',
        name: 'Portfolio',
        component: () => import('@/views/PortfolioView.vue'),
        meta: { title: '持有' },
      },
      {
        path: 'watchlist',
        name: 'Watchlist',
        component: () => import('@/views/WatchlistView.vue'),
        meta: { title: '自选' },
      },
      {
        path: 'stock/:code',
        name: 'StockDetail',
        component: () => import('@/views/StockDetailView.vue'),
        meta: { title: '股票详情' },
      },
      {
        path: 'index/:code',
        name: 'IndexDetail',
        component: () => import('@/views/IndexDetailView.vue'),
        meta: { title: '指数详情' },
      },
      {
        path: 'chat',
        name: 'Chat',
        component: () => import('@/views/ChatView.vue'),
        meta: { title: 'AI分析' },
      },
      {
        path: 'news',
        name: 'News',
        component: () => import('@/views/NewsView.vue'),
        meta: { title: '资讯' },
      },
      // ====== 信号层页面（a-stock-data 新增）======
      {
        path: 'hot-reason',
        name: 'HotReason',
        component: () => import('@/views/HotReasonView.vue'),
        meta: { title: '题材热点' },
      },
      {
        path: 'northbound',
        name: 'Northbound',
        component: () => import('@/views/NorthboundView.vue'),
        meta: { title: '北向资金' },
      },
      {
        path: 'dragon-tiger',
        name: 'DragonTiger',
        component: () => import('@/views/DragonTigerView.vue'),
        meta: { title: '龙虎榜' },
      },
      {
        path: 'industry-compare',
        name: 'IndustryCompare',
        component: () => import('@/views/IndustryCompareView.vue'),
        meta: { title: '行业对比' },
      },
      {
        path: 'fund-flow',
        name: 'FundFlow',
        component: () => import('@/views/FundFlowView.vue'),
        meta: { title: '资金流向' },
      },
      {
        path: 'lockup',
        name: 'Lockup',
        component: () => import('@/views/LockupView.vue'),
        meta: { title: '限售解禁' },
      },
      // ====== 系统架构详情页（L1~L6）======
      {
        path: 'layers',
        name: 'LayerDetail',
        component: () => import('@/views/LayerDetailView.vue'),
        meta: { title: '系统架构' },
      },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to, _from, next) => {
  const token = localStorage.getItem('token')
  if (to.meta.noAuth) {
    next()
  } else if (!token && to.name !== 'Login') {
    next({ name: 'Login' })
  } else {
    next()
  }
})

export default router
