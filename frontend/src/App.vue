<template>
  <router-view />
</template>

<script setup>
import { onMounted, onUnmounted } from 'vue'
import { globalSyncAll } from './utils/syncManager'

const onGlobalOnline = () => {
  globalSyncAll()
}

const onGlobalVisibility = () => {
  if (document.visibilityState === 'visible' && navigator.onLine) {
    globalSyncAll()
  }
}

onMounted(() => {
  window.addEventListener('online', onGlobalOnline)
  document.addEventListener('visibilitychange', onGlobalVisibility)
  // 启动时如有网络，尝试同步残留的离线数据
  if (navigator.onLine) {
    globalSyncAll()
  }
})

onUnmounted(() => {
  window.removeEventListener('online', onGlobalOnline)
  document.removeEventListener('visibilitychange', onGlobalVisibility)
})
</script>

<style>
/* ===== 设计系统变量 ===== */
:root {
  --bg: #fafaf8;
  --bg-card: #fff;
  --bg-hover: #f3f2ef;
  --bg-muted: #f5f4f1;
  --ink-900: #18181b;
  --ink-800: #27272a;
  --ink-600: #52525b;
  --ink-400: #a1a1aa;
  --ink-300: #d4d4d8;
  --ink-200: #e4e4e7;
  --ink-100: #f4f4f5;
  --teal-700: #0f766e;
  --teal-600: #0d9488;
  --teal-500: #14b8a6;
  --teal-400: #2dd4bf;
  --teal-100: #ccfbf1;
  --teal-50: #f0fdfa;
  --orange: #ea580c;
  --orange-hover: #c2410c;
  --orange-light: #fff7ed;
  --ok: #16a34a;
  --ok-bg: #dcfce7;
  --warn: #ca8a04;
  --warn-bg: #fef9c3;
  --err: #dc2626;
  --err-bg: #fee2e2;
  --blue: #2563eb;
  --blue-bg: #eff6ff;
  --amber: #d97706;
  --sans: 'Plus Jakarta Sans', -apple-system, 'PingFang SC', 'Noto Sans SC', 'Microsoft YaHei', sans-serif;
  --mono: 'JetBrains Mono', ui-monospace, 'Cascadia Code', monospace;
  --r: 6px;
  --r-sm: 4px;
  --r-lg: 10px;
  --ease: cubic-bezier(.25,.1,.25,1);
}

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: var(--sans);
  background-color: var(--bg);
  color: var(--ink-800);
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  -webkit-tap-highlight-color: transparent;
}

/* ===== Element Plus 浅色主题覆盖 ===== */

/* Card */
.el-card {
  border-radius: var(--r-lg) !important;
  border: 1px solid var(--ink-200) !important;
}

/* Table */
.el-table {
  --el-table-border-color: var(--ink-200);
  --el-table-header-bg-color: var(--bg-muted);
  --el-table-row-hover-bg-color: var(--bg-hover);
  --el-table-bg-color: var(--bg-card);
  --el-table-tr-bg-color: var(--bg-card);
  --el-table-text-color: var(--ink-800);
  --el-table-header-text-color: var(--ink-400);
}

.el-table th.el-table__cell {
  font-weight: 600;
  font-size: 13px;
  color: var(--ink-400);
}

.el-table--striped .el-table__body tr.el-table__row--striped td.el-table__cell {
  background: var(--bg-muted);
}

/* Button */
.el-button--primary {
  --el-button-bg-color: var(--blue);
  --el-button-border-color: var(--blue);
  --el-button-hover-bg-color: #1d4ed8;
  --el-button-hover-border-color: #1d4ed8;
  --el-button-active-bg-color: #1e40af;
  --el-button-active-border-color: #1e40af;
}

.el-button--success {
  --el-button-bg-color: var(--ok);
  --el-button-border-color: var(--ok);
  --el-button-hover-bg-color: #15803d;
  --el-button-hover-border-color: #15803d;
}

.el-button--danger {
  --el-button-bg-color: var(--err);
  --el-button-border-color: var(--err);
  --el-button-hover-bg-color: #b91c1c;
  --el-button-hover-border-color: #b91c1c;
}

.el-button--warning {
  --el-button-bg-color: var(--warn);
  --el-button-border-color: var(--warn);
  --el-button-hover-bg-color: #a16207;
  --el-button-hover-border-color: #a16207;
}

/* Tag */
.el-tag--info {
  --el-tag-bg-color: var(--ink-100);
  --el-tag-border-color: var(--ink-200);
  --el-tag-text-color: var(--ink-400);
}

.el-tag--success {
  --el-tag-bg-color: var(--ok-bg);
  --el-tag-border-color: #bbf7d0;
  --el-tag-text-color: var(--ok);
}

.el-tag--warning {
  --el-tag-bg-color: var(--warn-bg);
  --el-tag-border-color: #fde68a;
  --el-tag-text-color: var(--warn);
}

.el-tag--danger {
  --el-tag-bg-color: var(--err-bg);
  --el-tag-border-color: #fecaca;
  --el-tag-text-color: var(--err);
}

.el-tag--dark.el-tag--info {
  --el-tag-bg-color: var(--ink-400);
  --el-tag-border-color: var(--ink-400);
  --el-tag-text-color: #ffffff;
}

.el-tag--dark.el-tag--success {
  --el-tag-bg-color: var(--ok);
  --el-tag-border-color: var(--ok);
  --el-tag-text-color: #ffffff;
}

.el-tag--dark.el-tag--warning {
  --el-tag-bg-color: var(--warn);
  --el-tag-border-color: var(--warn);
  --el-tag-text-color: #ffffff;
}

.el-tag--dark.el-tag--danger {
  --el-tag-bg-color: var(--err);
  --el-tag-border-color: var(--err);
  --el-tag-text-color: #ffffff;
}

/* Progress */
.el-progress-bar__outer {
  background-color: var(--ink-200);
}

/* Pagination */
.el-pagination {
  --el-pagination-bg-color: transparent;
  --el-pagination-text-color: var(--ink-400);
  --el-pagination-hover-color: var(--blue);
}

.el-pagination .el-pager li.is-active {
  color: var(--blue);
}

/* Input */
.el-input__wrapper {
  box-shadow: 0 0 0 1px var(--ink-200) inset !important;
  background: var(--bg-card) !important;
}

.el-input__wrapper:hover {
  box-shadow: 0 0 0 1px var(--ink-300) inset !important;
}

.el-input__wrapper.is-focus {
  box-shadow: 0 0 0 1px var(--blue) inset, 0 0 0 3px rgba(37, 99, 235, 0.1) inset !important;
}

.el-input__inner {
  color: var(--ink-800) !important;
}

.el-input__inner::placeholder {
  color: var(--ink-400) !important;
}

/* Select */
.el-select .el-input__wrapper {
  background: var(--bg-card) !important;
}

/* Select dropdown */
.el-select-dropdown {
  border: 1px solid var(--ink-200) !important;
}

.el-select-dropdown__item.selected {
  color: var(--blue) !important;
  font-weight: 600;
}

.el-select-dropdown__item:hover {
  background-color: var(--bg-hover) !important;
}

/* Dialog */
.el-dialog {
  border-radius: var(--r-lg) !important;
}

.el-dialog__header {
  border-bottom: 1px solid var(--ink-200);
  padding: 16px 20px !important;
}

.el-dialog__title {
  color: var(--ink-900) !important;
  font-weight: 600;
}

.el-dialog__body {
  color: var(--ink-600);
}

.el-dialog__footer {
  border-top: 1px solid var(--ink-200);
}

/* Drawer */
.el-drawer__header {
  border-bottom: 1px solid var(--ink-200);
  margin-bottom: 0 !important;
  padding: 16px 20px !important;
}

/* Form */
.el-form-item__label {
  color: var(--ink-600) !important;
}

/* Tabs */
.el-tabs__active-bar {
  background-color: var(--blue);
}

.el-tabs__item.is-active {
  color: var(--blue);
}

.el-tabs__item:hover {
  color: var(--blue);
}

/* Dropdown */
.el-dropdown-menu {
  border: 1px solid var(--ink-200) !important;
}

.el-dropdown-menu__item:hover {
  background-color: var(--bg-hover) !important;
  color: var(--blue) !important;
}

/* MessageBox */
.el-message-box {
  border-radius: var(--r-lg);
}

/* Loading */
.el-loading-mask {
  background-color: rgba(255, 255, 255, 0.8) !important;
}

/* Empty */
.el-empty__description p {
  color: var(--ink-400) !important;
}

/* Descriptions */
.el-descriptions__label {
  color: var(--ink-600) !important;
}

/* Collapse */
.el-collapse-item__header {
  color: var(--ink-900);
}

/* Scrollbar */
::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}

::-webkit-scrollbar-track {
  background: var(--bg-muted);
}

::-webkit-scrollbar-thumb {
  background: var(--ink-300);
  border-radius: 3px;
}

::-webkit-scrollbar-thumb:hover {
  background: var(--ink-400);
}

/* ===== 白色遮罩层彻底修复（3层防护） ===== */

/* 第1层：禁用 Toast 的 van-fade 动画，防止动画卡在中间状态 */
.van-toast.van-fade-enter-active,
.van-toast.van-fade-leave-active {
  animation: none !important;
  transition: none !important;
}

/* 第2层：强制 Toast 弹窗使用深色背景，覆盖 van-popup 的默认白色 */
.van-popup.van-toast {
  background: rgba(0, 0, 0, 0.7) !important;
}

/* 第3层：中和 van-toast--unclickable（我们从不使用 forbidClick，安全移除其效果） */
body.van-toast--unclickable {
  overflow: visible !important;
  cursor: auto !important;
}
body.van-toast--unclickable * {
  pointer-events: auto !important;
}

/* 隐藏 Vant 在 body 下创建的空挂载 div */
body > div:empty:not([data-v-app]) {
  display: none !important;
  pointer-events: none !important;
  width: 0 !important;
  height: 0 !important;
}

/* Vant overlay 保持深色 */
.van-overlay {
  background-color: rgba(0, 0, 0, 0.7) !important;
}

/* ===== Vant 主题变量（移动端） ===== */
:root {
  --van-primary-color: var(--blue);
  --van-success-color: var(--ok);
  --van-warning-color: var(--warn);
  --van-danger-color: var(--err);
  --van-text-color: var(--ink-800);
  --van-text-color-2: var(--ink-600);
  --van-text-color-3: var(--ink-400);
  --van-border-color: var(--ink-200);
  --van-background: var(--bg);
  --van-background-2: var(--bg-card);
}

/* ===== 移动端底部导航栏固定 ===== */
.van-tabbar--fixed {
  position: fixed !important;
  bottom: 0 !important;
  left: 0 !important;
  width: 100% !important;
  z-index: 100 !important;
}
</style>
