import { defineStore } from 'pinia'
import { api, type User } from '@/api'

export const useUserStore = defineStore('user', {
  state: () => ({ user: null as User | null, token: localStorage.getItem('token') || '' }),
  getters: { isAdmin: (s) => s.user?.role === 'admin' },
  actions: {
    async login(username: string, password: string) {
      const { access_token } = await api.login(username, password)
      this.token = access_token
      localStorage.setItem('token', access_token)
      await this.fetchMe()
    },
    async fetchMe() {
      if (!this.token) return
      try {
        this.user = await api.me()
      } catch {
        this.logout()
      }
    },
    logout() {
      this.user = null
      this.token = ''
      localStorage.removeItem('token')
    },
  },
})
