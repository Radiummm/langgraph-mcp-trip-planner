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
:root {
  --font-sans-cn: "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", "Noto Sans CJK SC", sans-serif;
  --font-serif-cn: "Songti SC", "STSong", "Noto Serif CJK SC", "Source Han Serif SC", serif;
  --ink: #20262c;
  --paper: #fbfaf6;
  --canvas: #ece8df;
  --line: #d5cbbb;
  --accent: #8a5a2b;
}

* {
  box-sizing: border-box;
}

html {
  font-family: var(--font-sans-cn);
  font-synthesis: none;
  text-rendering: optimizeLegibility;
}

body {
  margin: 0;
  min-width: 320px;
  background: var(--canvas);
}

body,
button,
input,
textarea,
select,
.ant-app,
.ant-layout,
.ant-btn,
.ant-input,
.ant-select,
.ant-picker,
.ant-menu,
.ant-card {
  font-family: var(--font-sans-cn) !important;
}

#app {
  color: var(--ink);
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
  font-weight: 700;
  letter-spacing: 0.06em;
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
