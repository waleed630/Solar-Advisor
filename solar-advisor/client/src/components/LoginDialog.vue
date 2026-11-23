<script setup>
import { nextTick, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../auth'

const auth = useAuthStore()
const router = useRouter()
const password = ref('')
const error = ref('')
const busy = ref(false)
const input = ref(null)

// Fresh, focused password box every time the dialog opens
watch(() => auth.dialogOpen, async (open) => {
  if (!open) return
  password.value = ''
  error.value = ''
  await nextTick()
  input.value?.focus()
})

async function submit() {
  if (!password.value) {
    error.value = 'Please enter the admin password.'
    return
  }
  busy.value = true
  const next = auth.afterLogin
  error.value = await auth.login(password.value)
  busy.value = false
  if (!error.value && next) router.push(next)
}
</script>

<template>
  <Transition enter-from-class="opacity-0" leave-to-class="opacity-0">
    <div
      v-if="auth.dialogOpen"
      class="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-on-surface/40 backdrop-blur-sm transition-opacity duration-200"
      @click.self="auth.closeLogin()"
      @keydown.esc="auth.closeLogin()"
    >
      <form
        role="dialog" aria-modal="true" aria-labelledby="login-title"
        class="w-full max-w-sm card p-6 shadow-xl flex flex-col gap-4"
        @submit.prevent="submit"
      >
        <div class="flex items-start justify-between gap-3">
          <div class="flex items-center gap-3">
            <div class="w-10 h-10 rounded-lg bg-tertiary text-on-tertiary flex items-center justify-center shrink-0">
              <span class="icon">admin_panel_settings</span>
            </div>
            <div>
              <h2 id="login-title" class="card-title">Admin login</h2>
              <p class="text-body-sm text-on-surface-variant">Edit prices and see the ML model.</p>
            </div>
          </div>
          <button type="button" class="text-on-surface-variant hover:text-on-surface" aria-label="Close" @click="auth.closeLogin()">
            <span class="icon">close</span>
          </button>
        </div>

        <div>
          <label class="label" for="admin-pw">Password</label>
          <input id="admin-pw" ref="input" v-model="password" type="password" autocomplete="current-password" class="input" />
          <p v-if="error" class="note-red mt-2"><span class="icon text-[18px] shrink-0">error</span>{{ error }}</p>
        </div>

        <div class="flex justify-end gap-2">
          <button type="button" class="btn-light" @click="auth.closeLogin()">Cancel</button>
          <button type="submit" class="btn" :disabled="busy">
            <span class="icon text-[18px]" :class="busy && 'animate-spin'">{{ busy ? 'sync' : 'lock_open' }}</span>Log in
          </button>
        </div>
      </form>
    </div>
  </Transition>
</template>
