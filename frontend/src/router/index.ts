import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '@/stores/user'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', component: () => import('@/views/Login.vue'), meta: { public: true } },
    {
      path: '/',
      component: () => import('@/layouts/MainLayout.vue'),
      children: [
        { path: '', redirect: '/cards' },
        { path: 'cards', component: () => import('@/views/CardScan.vue'), meta: { title: '名片识别' } },
        { path: 'records', component: () => import('@/views/Records.vue'), meta: { title: '录入记录' } },
        { path: 'categories', component: () => import('@/views/Categories.vue'), meta: { title: '名片分类', admin: true } },
        { path: 'models', component: () => import('@/views/VisionModels.vue'), meta: { title: '视觉模型', admin: true } },
        { path: 'search', component: () => import('@/views/Search.vue'), meta: { title: '联网检索', admin: true } },
        { path: 'kdocs', component: () => import('@/views/Kdocs.vue'), meta: { title: '金山文档', admin: true } },
        { path: 'users', component: () => import('@/views/Users.vue'), meta: { title: '用户管理', admin: true } },
      ],
    },
  ],
})

router.beforeEach(async (to) => {
  const store = useUserStore()
  if (to.meta.public) return true
  if (!store.token) return '/login'
  if (!store.user) await store.fetchMe()
  if (!store.user) return '/login'
  if (to.meta.admin && !store.isAdmin) return '/cards'
  return true
})

export default router
