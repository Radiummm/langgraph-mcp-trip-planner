<template>
  <div id="app">
    <a-layout class="app-layout">
      <a-layout-header class="app-header">
        <div class="brand">行程规划</div>
        <div class="header-meta">目的地 / 日期 / 预算 / 地图</div>
      </a-layout-header>
      <a-layout-content class="app-content">
        <router-view />
      </a-layout-content>
    </a-layout>
  </div>
</template>

<script setup lang="ts">
</script>

<style>
#app {
  font-family: Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial,
    'Noto Sans', sans-serif;
  color: #111827;
}

.app-layout {
  min-height: 100vh;
  background: #f4f6f8;
}

.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 56px;
  padding: 0 32px;
  border-bottom: 1px solid #d8dee8;
  background: #ffffff !important;
  line-height: 56px;
}

.brand {
  color: #111827;
  font-size: 17px;
  font-weight: 750;
}

.header-meta {
  color: #667085;
  font-size: 13px;
}

.app-content {
  padding: 0;
}

@media (max-width: 768px) {
  .app-header {
    padding: 0 16px;
  }

  .header-meta {
    display: none;
  }
}
</style>
