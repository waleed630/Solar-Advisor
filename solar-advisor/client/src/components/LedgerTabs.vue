<script setup>
// Shared header for the Model and Prices pages, with the two tabs from the theme.
// The ML Model tab is locked until admin login.
import AdminLink from './AdminLink.vue'

defineProps({ title: String, text: String, crumb: String })
const tabs = [
  { to: '/prices', icon: 'verified_user', label: 'Tariff & Prices' },
  { to: '/model', icon: 'neurology', label: 'ML Model', admin: true },
]
</script>

<template>
  <div class="flex flex-col lg:flex-row lg:items-end justify-between gap-4 mb-6">
    <div class="flex flex-col gap-1">
      <div class="flex items-center gap-1.5 eyebrow">
        <span>Transparency</span><span>/</span><span class="text-on-surface">{{ crumb }}</span>
      </div>
      <h1 class="font-display text-headline-lg font-semibold tracking-tight text-on-surface">{{ title }}</h1>
      <p class="text-body-md text-on-surface-variant max-w-2xl">{{ text }}</p>
    </div>
    <div class="inline-flex p-1.5 rounded-xl bg-surface-container shadow-sm self-start lg:self-auto">
      <component
        :is="t.admin ? AdminLink : 'RouterLink'"
        v-for="t in tabs" :key="t.to" :to="t.to"
        class="flex items-center gap-1.5 px-4 py-2 rounded-lg text-label-md font-semibold transition-all"
        :class="$route.path === t.to ? 'bg-surface-container-lowest text-on-surface shadow-sm' : 'text-on-surface-variant hover:text-on-surface'"
      ><span class="icon text-[18px]">{{ t.icon }}</span>{{ t.label }}</component>
    </div>
  </div>
</template>
