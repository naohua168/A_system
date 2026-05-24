import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { UserInfo } from '@/types'
import { login as apiLogin, getUserInfo, register as apiRegister } from '@/api/user'

export const useUserStore = defineStore('user', () => {
  const token = ref<string | null>(localStorage.getItem('token'))
  const userInfo = ref<UserInfo | null>(null)

  const isLoggedIn = computed(() => !!token.value)

  async function login(username: string, password: string) {
    const res = await apiLogin(username, password)
    token.value = res.token
    userInfo.value = res.user
    localStorage.setItem('token', res.token)
    return res
  }

  async function register(username: string, password: string, email?: string) {
    const res = await apiRegister({ username, password, email })
    return res
  }

  async function fetchUserInfo() {
    if (token.value) {
      try {
        userInfo.value = await getUserInfo()
      } catch {
        // 后端返回错误（如 token 过期/无效），清除登录状态
        token.value = null
        userInfo.value = null
        localStorage.removeItem('token')
      }
    }
  }

  function logout() {
    token.value = null
    userInfo.value = null
    localStorage.removeItem('token')
  }

  return { token, userInfo, isLoggedIn, login, register, fetchUserInfo, logout }
})
