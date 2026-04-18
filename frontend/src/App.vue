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
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: system-ui, -apple-system, "SF Pro Text", "PingFang SC", "Microsoft YaHei", sans-serif;
  background-color: #f5f7fa;
  color: #1a1d26;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  -webkit-tap-highlight-color: transparent;
}

/* ===== Element Plus 浅色主题覆盖 ===== */

/* Card */
.el-card {
  border-radius: 10px !important;
  border: 1px solid #e5e7eb !important;
}

/* Table */
.el-table {
  --el-table-border-color: #e5e7eb;
  --el-table-header-bg-color: #f9fafb;
  --el-table-row-hover-bg-color: #f5f7fa;
  --el-table-bg-color: #ffffff;
  --el-table-tr-bg-color: #ffffff;
  --el-table-text-color: #1a1d26;
  --el-table-header-text-color: #5c6477;
}

.el-table th.el-table__cell {
  font-weight: 600;
  font-size: 13px;
  color: #5c6477;
}

.el-table--striped .el-table__body tr.el-table__row--striped td.el-table__cell {
  background: #f9fafb;
}

/* Button */
.el-button--primary {
  --el-button-bg-color: #2563eb;
  --el-button-border-color: #2563eb;
  --el-button-hover-bg-color: #1d4ed8;
  --el-button-hover-border-color: #1d4ed8;
  --el-button-active-bg-color: #1e40af;
  --el-button-active-border-color: #1e40af;
}

.el-button--success {
  --el-button-bg-color: #059669;
  --el-button-border-color: #059669;
  --el-button-hover-bg-color: #047857;
  --el-button-hover-border-color: #047857;
}

.el-button--danger {
  --el-button-bg-color: #dc2626;
  --el-button-border-color: #dc2626;
  --el-button-hover-bg-color: #b91c1c;
  --el-button-hover-border-color: #b91c1c;
}

.el-button--warning {
  --el-button-bg-color: #d97706;
  --el-button-border-color: #d97706;
  --el-button-hover-bg-color: #b45309;
  --el-button-hover-border-color: #b45309;
}

/* Tag */
.el-tag--info {
  --el-tag-bg-color: #f1f5f9;
  --el-tag-border-color: #e2e8f0;
  --el-tag-text-color: #64748b;
}

.el-tag--success {
  --el-tag-bg-color: #ecfdf5;
  --el-tag-border-color: #a7f3d0;
  --el-tag-text-color: #059669;
}

.el-tag--warning {
  --el-tag-bg-color: #fffbeb;
  --el-tag-border-color: #fde68a;
  --el-tag-text-color: #d97706;
}

.el-tag--danger {
  --el-tag-bg-color: #fef2f2;
  --el-tag-border-color: #fecaca;
  --el-tag-text-color: #dc2626;
}

.el-tag--dark.el-tag--info {
  --el-tag-bg-color: #64748b;
  --el-tag-border-color: #64748b;
  --el-tag-text-color: #ffffff;
}

.el-tag--dark.el-tag--success {
  --el-tag-bg-color: #059669;
  --el-tag-border-color: #059669;
  --el-tag-text-color: #ffffff;
}

.el-tag--dark.el-tag--warning {
  --el-tag-bg-color: #d97706;
  --el-tag-border-color: #d97706;
  --el-tag-text-color: #ffffff;
}

.el-tag--dark.el-tag--danger {
  --el-tag-bg-color: #dc2626;
  --el-tag-border-color: #dc2626;
  --el-tag-text-color: #ffffff;
}

/* Progress */
.el-progress-bar__outer {
  background-color: #e5e7eb;
}

/* Pagination */
.el-pagination {
  --el-pagination-bg-color: transparent;
  --el-pagination-text-color: #5c6477;
  --el-pagination-hover-color: #2563eb;
}

.el-pagination .el-pager li.is-active {
  color: #2563eb;
}

/* Input */
.el-input__wrapper {
  box-shadow: 0 0 0 1px #e5e7eb inset !important;
  background: #ffffff !important;
}

.el-input__wrapper:hover {
  box-shadow: 0 0 0 1px #d1d5db inset !important;
}

.el-input__wrapper.is-focus {
  box-shadow: 0 0 0 1px #2563eb inset, 0 0 0 3px rgba(37, 99, 235, 0.1) inset !important;
}

.el-input__inner {
  color: #1a1d26 !important;
}

.el-input__inner::placeholder {
  color: #9ba3af !important;
}

/* Select */
.el-select .el-input__wrapper {
  background: #ffffff !important;
}

/* Select dropdown */
.el-select-dropdown {
  border: 1px solid #e5e7eb !important;
}

.el-select-dropdown__item.selected {
  color: #2563eb !important;
  font-weight: 600;
}

.el-select-dropdown__item:hover {
  background-color: #f5f7fa !important;
}

/* Dialog */
.el-dialog {
  border-radius: 10px !important;
}

.el-dialog__header {
  border-bottom: 1px solid #e5e7eb;
  padding: 16px 20px !important;
}

.el-dialog__title {
  color: #1a1d26 !important;
  font-weight: 600;
}

.el-dialog__body {
  color: #5c6477;
}

.el-dialog__footer {
  border-top: 1px solid #e5e7eb;
}

/* Drawer */
.el-drawer__header {
  border-bottom: 1px solid #e5e7eb;
  margin-bottom: 0 !important;
  padding: 16px 20px !important;
}

/* Form */
.el-form-item__label {
  color: #5c6477 !important;
}

/* Tabs */
.el-tabs__active-bar {
  background-color: #2563eb;
}

.el-tabs__item.is-active {
  color: #2563eb;
}

.el-tabs__item:hover {
  color: #2563eb;
}

/* Dropdown */
.el-dropdown-menu {
  border: 1px solid #e5e7eb !important;
}

.el-dropdown-menu__item:hover {
  background-color: #f5f7fa !important;
  color: #2563eb !important;
}

/* MessageBox */
.el-message-box {
  border-radius: 10px;
}

/* Loading */
.el-loading-mask {
  background-color: rgba(255, 255, 255, 0.8) !important;
}

/* Empty */
.el-empty__description p {
  color: #9ba3af !important;
}

/* Descriptions */
.el-descriptions__label {
  color: #5c6477 !important;
}

/* Collapse */
.el-collapse-item__header {
  color: #1a1d26;
}

/* Scrollbar */
::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}

::-webkit-scrollbar-track {
  background: #f5f7fa;
}

::-webkit-scrollbar-thumb {
  background: #d1d5db;
  border-radius: 3px;
}

::-webkit-scrollbar-thumb:hover {
  background: #9ba3af;
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
  --van-primary-color: #2563eb;
  --van-success-color: #059669;
  --van-warning-color: #d97706;
  --van-danger-color: #dc2626;
  --van-text-color: #1a1d26;
  --van-text-color-2: #5c6477;
  --van-text-color-3: #9ba3af;
  --van-border-color: #e5e7eb;
  --van-background: #f5f7fa;
  --van-background-2: #ffffff;
}
</style>
