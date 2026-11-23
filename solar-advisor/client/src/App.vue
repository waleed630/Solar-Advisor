<script setup>
import { onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppLogo from './components/AppLogo.vue'
import AdminLink from './components/AdminLink.vue'
import LoginDialog from './components/LoginDialog.vue'
import { useAuthStore } from './auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const links = [
  { to: '/plan', label: 'Get My Plan', short: 'My Plan', icon: 'receipt_long' },
  { to: '/prices', label: 'Tariff & Prices', short: 'Tariff & Prices', icon: 'payments' },
  { to: '/model', label: 'ML Model & Accuracy', short: 'ML Model', icon: 'analytics', admin: true },
]
const isActive = (to) => route.path === to

onMounted(() => auth.check())
// Logging out on an admin-only page leaves it
watch(() => auth.isAdmin, (admin) => {
  if (!admin && route.meta.admin) router.replace('/')
})
</script>

<template>
  <header class="sticky top-0 z-50 bg-surface/80 backdrop-blur-xl shadow-[0_1px_8px_rgba(0,0,0,0.04)]">
    <div class="max-w-7xl mx-auto h-16 sm:h-20 px-4 md:px-8 flex items-center justify-between gap-4">
      <div class="flex items-center gap-4 min-w-0">
        <RouterLink to="/" class="flex items-center gap-2 shrink-0">
          <AppLogo class="h-8 w-8 shrink-0" />
          <span class="font-display text-headline-sm font-semibold tracking-tight text-on-surface">SolarAdvisor</span>
          <span class="hidden sm:inline chip-plain border border-outline-variant/30 font-medium">Beta</span>
        </RouterLink>
        <nav class="hidden lg:flex items-center gap-1 ml-4">
          <component
            :is="l.admin ? AdminLink : 'RouterLink'"
            v-for="l in links" :key="l.to" :to="l.to"
            class="px-4 py-1.5 rounded-lg text-label-md transition-colors"
            :class="isActive(l.to) ? 'bg-surface-container text-on-surface font-semibold' : 'text-on-surface-variant hover:text-on-surface hover:bg-surface-container'"
          >{{ l.label }}</component>
        </nav>
      </div>
      <div class="flex items-center gap-2 sm:gap-3 shrink-0">
        <template v-if="auth.isAdmin">
          <span class="hidden sm:inline-flex chip-jade"><span class="icon text-[14px]">admin_panel_settings</span>Admin</span>
          <button class="btn-white px-3 sm:px-4" title="Log out" @click="auth.logout()">
            <span class="icon text-[18px]">logout</span><span class="hidden sm:inline">Log out</span>
          </button>
        </template>
        <button v-else class="btn-white px-3 sm:px-4" title="Admin login" @click="auth.openLogin()">
          <span class="icon text-[18px]">login</span><span class="hidden sm:inline">Login</span>
        </button>
        <RouterLink to="/plan" class="btn px-4 sm:px-6">Start Solar Plan</RouterLink>
      </div>
    </div>
    <!-- Phone and tablet: the same links as icon tabs -->
    <nav class="lg:hidden flex border-t border-outline-variant/30 px-2">
      <component
        :is="l.admin ? AdminLink : 'RouterLink'"
        v-for="l in links" :key="l.to" :to="l.to" v-bind="l.admin ? { wrapClass: 'flex-1' } : {}"
        class="flex-1 flex items-center justify-center gap-1 py-2 text-label-sm font-semibold border-b-2 transition-colors"
        :class="isActive(l.to) ? 'border-on-surface text-on-surface' : 'border-transparent text-on-surface-variant'"
      ><span class="icon text-[18px]">{{ l.icon }}</span>{{ l.short }}</component>
    </nav>
  </header>

  <main class="max-w-7xl mx-auto px-4 md:px-8 py-8 md:py-10">
    <RouterView />
  </main>

  <footer class="bg-surface-container-low">
    <div class="max-w-7xl mx-auto px-4 md:px-8 py-10">
      <div class="p-6 rounded-xl bg-surface-container-lowest mb-6 flex items-start gap-3">
        <span class="icon text-on-surface-variant shrink-0 mt-0.5">shield</span>
        <p class="text-body-sm text-on-surface-variant leading-relaxed">
          Estimates only. Based on the saved tariff and equipment prices and local solar output. Prices and tariffs
          change often; check with your installer and DISCO. Independent advice: we do not sell panels or take
          installer commissions.
        </p>
      </div>
      <div class="flex flex-col md:flex-row items-center justify-between gap-4">
        <span class="text-body-sm text-on-surface-variant">© {{ new Date().getFullYear() }} SolarAdvisor</span>
        <div class="flex flex-wrap items-center justify-center gap-6">
          <component
            :is="l.admin ? AdminLink : 'RouterLink'"
            v-for="l in links" :key="l.to" :to="l.to" v-bind="l.admin ? { tipUp: true } : {}"
            class="text-label-sm font-semibold text-on-surface-variant hover:text-on-surface transition-colors"
          >{{ l.label }}</component>
        </div>
      </div>
    </div>
  </footer>

  <LoginDialog />
</template>
