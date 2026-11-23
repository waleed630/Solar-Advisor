// Admin login, shared by the header, the login dialog, the Prices page and the ML Model page
import { defineStore } from 'pinia'
import api, { errorText } from './api'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: localStorage.getItem('adminToken'),
    dialogOpen: false, // the password dialog
    afterLogin: null, // page to open after a successful login (e.g. /model)
  }),
  getters: {
    isAdmin: (s) => !!s.token,
  },
  actions: {
    openLogin(afterLogin = null) {
      this.afterLogin = afterLogin
      this.dialogOpen = true
    },
    closeLogin() {
      this.dialogOpen = false
      this.afterLogin = null
    },
    // Returns '' when the login worked, otherwise the error text
    async login(password) {
      try {
        const { data } = await api.post('/admin/login', { password })
        localStorage.setItem('adminToken', data.token)
        this.token = data.token
        this.dialogOpen = false
        return ''
      } catch (e) {
        return errorText(e)
      }
    },
    logout() {
      localStorage.removeItem('adminToken')
      this.token = null
    },
    // A saved login expires after 8 hours: check it once when the app starts
    async check() {
      if (!this.token) return
      try {
        await api.get('/admin/check')
      } catch {
        this.logout()
      }
    },
  },
})
