<template>
  <div class="app-layout">
    <AppHeader />
    <main class="main-content">
      <router-view v-slot="{ Component }">
        <transition name="page" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </main>
  </div>
</template>

<script setup lang="ts">
import AppHeader from './AppHeader.vue'
</script>

<style scoped lang="scss">
.app-layout {
  min-height: 100vh;
  background: $canvas;
}

.main-content {
  padding-top: $nav-height;
  min-height: calc(100vh - #{$nav-height});
}
</style>
