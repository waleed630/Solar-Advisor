import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { createRouter, createWebHistory } from 'vue-router'
import App from './App.vue'
import HomeView from './views/HomeView.vue'
import PlanView from './views/PlanView.vue'
import PricesView from './views/PricesView.vue'
import ModelView from './views/ModelView.vue'
import { useAuthStore } from './auth'
import './style.css'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: HomeView },
    { path: '/plan', component: PlanView },
    { path: '/prices', component: PricesView },
    { path: '/model', component: ModelView, meta: { admin: true } },
  ],
})

// Admin-only pages: without login, stay where you are (or go home) and ask for the password
router.beforeEach((to, from) => {
  const auth = useAuthStore()
  if (!to.meta.admin || auth.isAdmin) return true
  auth.openLogin(to.fullPath)
  return from.matched.length ? false : '/'
})

createApp(App).use(createPinia()).use(router).mount('#app')
