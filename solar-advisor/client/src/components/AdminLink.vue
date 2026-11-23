<script setup>
// A link to an admin-only page. Before admin login it is faded, cannot be clicked
// and shows a tooltip; after login it is a normal link.
import { useAuthStore } from '../auth'

defineOptions({ inheritAttrs: false }) // class goes on the link itself, not the tooltip wrapper
defineProps({
  to: { type: String, required: true },
  tip: { type: String, default: 'Admin login required' },
  tipUp: Boolean, // tooltip above instead of below (for links near the bottom of the page)
  wrapClass: { type: String, default: '' }, // layout classes for the wrapper when locked (e.g. flex-1)
})
const auth = useAuthStore()
</script>

<template>
  <RouterLink v-if="auth.isAdmin" :to="to" v-bind="$attrs"><slot /></RouterLink>
  <span v-else class="relative inline-flex group/tip" :class="wrapClass">
    <span
      v-bind="$attrs"
      class="!cursor-not-allowed opacity-40 select-none"
      role="link" aria-disabled="true" tabindex="0" :aria-label="tip"
    ><slot /></span>
    <span
      class="pointer-events-none absolute left-1/2 -translate-x-1/2 z-60 whitespace-nowrap rounded-md bg-inverse-surface px-2.5 py-1.5 text-label-sm font-semibold text-inverse-on-surface shadow-lg opacity-0 transition-opacity group-hover/tip:opacity-100 group-focus-within/tip:opacity-100 flex items-center gap-1"
      :class="tipUp ? 'bottom-full mb-2' : 'top-full mt-2'"
    ><span class="icon text-[14px]">lock</span>{{ tip }}</span>
  </span>
</template>
