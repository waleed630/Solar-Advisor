<script setup>
import { useRoute } from 'vue-router'
import AppLogo from './components/AppLogo.vue'

const route = useRoute()
const links = [
  { to: '/plan', label: 'Get My Plan', icon: 'receipt_long' },
  { to: '/model', label: 'ML Model & Accuracy', icon: 'analytics' },
  { to: '/prices', label: 'Tariff & Prices', icon: 'payments' },
]
const isActive = (to) => route.path === to
</script>

<template>
  <header class="sticky top-0 z-50 bg-surface/80 backdrop-blur-xl shadow-[0_1px_8px_rgba(0,0,0,0.04)]">
    <div class="max-w-7xl mx-auto h-16 sm:h-20 px-4 md:px-8 flex items-center justify-between gap-4">
      <div class="flex items-center gap-4 min-w-0">
        <RouterLink to="/" class="flex items-center gap-2 shrink-0">
          <AppLogo class="h-8 w-8 shrink-0" />
          <span class="font-display text-headline-sm font-semibold tracking-tight text-on-surface">SolarAdvisor</span>
          <span class="hidden sm:inline chip-plain border border-outline-variant/30 font-medium">Lahore / LESCO Beta</span>
        </RouterLink>
        <nav class="hidden lg:flex items-center gap-1 ml-4">
          <RouterLink
            v-for="l in links" :key="l.to" :to="l.to"
            class="px-4 py-1.5 rounded-lg text-label-md transition-colors"
            :class="isActive(l.to) ? 'bg-surface-container text-on-surface font-semibold' : 'text-on-surface-variant hover:text-on-surface hover:bg-surface-container'"
          >{{ l.label }}</RouterLink>
        </nav>
      </div>
      <div class="flex items-center gap-3 shrink-0">
        <div class="hidden md:flex items-center gap-1.5 px-4 py-1 rounded-full bg-secondary-container/40 text-on-secondary-container text-label-sm font-semibold border border-secondary-container">
          <span class="w-1.5 h-1.5 rounded-full bg-secondary"></span>100% Neutral &amp; Independent
        </div>
        <RouterLink to="/plan" class="btn px-4 sm:px-6">Start Solar Plan</RouterLink>
      </div>
    </div>
    <!-- Phone and tablet: the same links as icon tabs -->
    <nav class="lg:hidden flex border-t border-outline-variant/30 px-2">
      <RouterLink
        v-for="l in links" :key="l.to" :to="l.to"
        class="flex-1 flex items-center justify-center gap-1 py-2 text-label-sm font-semibold border-b-2 transition-colors"
        :class="isActive(l.to) ? 'border-on-surface text-on-surface' : 'border-transparent text-on-surface-variant'"
      ><span class="icon text-[18px]">{{ l.icon }}</span>{{ l.label.replace(' & Accuracy', '').replace('Get My ', 'My ') }}</RouterLink>
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
          Estimates only. Based on the saved tariff and equipment prices and Lahore solar output. Prices and tariffs
          change often; check with your installer and DISCO. Independent advice: we do not sell panels or take
          installer commissions.
        </p>
      </div>
      <div class="flex flex-col md:flex-row items-center justify-between gap-4">
        <span class="text-body-sm text-on-surface-variant">© {{ new Date().getFullYear() }} SolarAdvisor</span>
        <div class="flex flex-wrap items-center justify-center gap-6">
          <RouterLink v-for="l in links" :key="l.to" :to="l.to" class="text-label-sm font-semibold text-on-surface-variant hover:text-on-surface transition-colors">{{ l.label }}</RouterLink>
        </div>
      </div>
    </div>
  </footer>
</template>
