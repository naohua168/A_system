<template>
  <div class="app-layout">
    <AppHeader />
    <main class="main-content">
      <transition name="page" mode="out-in">
        <router-view />
      </transition>
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
