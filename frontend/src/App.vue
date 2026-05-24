<template>
  <router-view v-slot="{ Component, route }">
    <transition name="page" mode="out-in">
      <component :is="Component" :key="route.fullPath" />
    </transition>
  </router-view>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useUserStore } from '@/stores/user'

onMounted(() => {
  const token = localStorage.getItem('token')
  if (token) {
    const userStore = useUserStore()
    userStore.fetchUserInfo()
  }
})
</script>
