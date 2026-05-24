<template>
  <div class="empty-state" :class="[size, { inline: inline }]">
    <div class="empty-icon" v-if="!noIcon">
      <slot name="icon">
        <svg v-if="type === 'empty'" width="64" height="64" viewBox="0 0 64 64" fill="none">
          <rect x="8" y="16" width="48" height="36" rx="4" stroke="currentColor" stroke-width="2" fill="none" opacity="0.2"/>
          <line x1="16" y1="28" x2="48" y2="28" stroke="currentColor" stroke-width="2" opacity="0.15"/>
          <line x1="16" y1="36" x2="40" y2="36" stroke="currentColor" stroke-width="2" opacity="0.12"/>
          <line x1="16" y1="44" x2="36" y2="44" stroke="currentColor" stroke-width="2" opacity="0.08"/>
          <circle cx="32" cy="12" r="6" stroke="currentColor" stroke-width="1.5" fill="none" opacity="0.25"/>
          <path d="M32 10v4M30 12h4" stroke="currentColor" stroke-width="1.5" opacity="0.25"/>
        </svg>
        <svg v-else-if="type === 'error'" width="64" height="64" viewBox="0 0 64 64" fill="none">
          <circle cx="32" cy="32" r="24" stroke="#ec4d4c" stroke-width="2" fill="none" opacity="0.3"/>
          <line x1="24" y1="24" x2="40" y2="40" stroke="#ec4d4c" stroke-width="2.5" opacity="0.6"/>
          <line x1="40" y1="24" x2="24" y2="40" stroke="#ec4d4c" stroke-width="2.5" opacity="0.6"/>
        </svg>
        <svg v-else-if="type === 'offline'" width="64" height="64" viewBox="0 0 64 64" fill="none">
          <path d="M16 36l16-16 16 16" stroke="currentColor" stroke-width="2" opacity="0.15" fill="none"/>
          <path d="M22 30l10-10 10 10" stroke="currentColor" stroke-width="2" opacity="0.2" fill="none"/>
          <path d="M28 24l4-4 4 4" stroke="#f59e0b" stroke-width="2" opacity="0.5" fill="none"/>
          <line x1="32" y1="20" x2="32" y2="44" stroke="#f59e0b" stroke-width="2" opacity="0.6"/>
          <circle cx="32" cy="48" r="2" fill="#f59e0b" opacity="0.5"/>
        </svg>
      </slot>
    </div>
    <div class="empty-title" v-if="title">{{ title }}</div>
    <div class="empty-desc" v-if="description">{{ description }}</div>
    <div class="empty-sub" v-if="sub">{{ sub }}</div>
    <div class="empty-actions" v-if="$slots.actions">
      <slot name="actions" />
    </div>
  </div>
</template>

<script setup lang="ts">
withDefaults(defineProps<{
  type?: 'empty' | 'error' | 'offline'
  title?: string
  description?: string
  sub?: string
  size?: 'sm' | 'md' | 'lg'
  inline?: boolean
  noIcon?: boolean
}>(), {
  type: 'empty',
  size: 'md',
  inline: false,
  noIcon: false,
})
</script>

<style scoped>
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  color: rgba(255,255,255,0.35);
}
.empty-state.inline { display: inline-flex; vertical-align: middle; }
.empty-state.sm { padding: 16px; gap: 6px; }
.empty-state.md { padding: 40px 24px; gap: 10px; }
.empty-state.lg { padding: 64px 32px; gap: 14px; }
.empty-icon { color: inherit; display: flex; align-items: center; justify-content: center; }
.empty-title { font-size: 15px; color: rgba(255,255,255,0.6); font-weight: 600; }
.empty-desc { font-size: 13px; color: rgba(255,255,255,0.35); max-width: 320px; line-height: 1.5; }
.empty-sub { font-size: 12px; color: rgba(255,255,255,0.2); }
.empty-actions { margin-top: 4px; }
</style>
