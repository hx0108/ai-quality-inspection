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
/* ===== 设计系统变量 v2（现代工具感 · 青绿品牌色）
     令牌值与 designs/qc-ui-redesign/qc-theme.css 对齐；变量名保持向后兼容 ===== */
:root {
  /* 中性（冷灰） */
  --bg: #f7f7f8;
  --bg-card: #fff;
  --bg-hover: #ececf0;
  --bg-muted: #f2f2f4;
  --ink-900: #191922;
  --ink-800: #2c2c38;
  --ink-700: #474753;
  --ink-600: #61616d;
  --ink-500: #84848f;
  --ink-400: #a4a4af;
  --ink-300: #c9c9d1;
  --ink-200: #e4e4e9;
  --ink-100: #f0f0f3;
  /* 深色侧栏 */
  --side-bg: #16161c;
  --side-hover: #1e1e26;
  --side-border: #24242d;
  --side-text: #8e8e9a;
  --side-text-strong: #f0f0f4;
  --side-active-bg: rgba(15, 138, 128, 0.16);
  --side-active-line: #2bb8aa;
  /* 品牌（青绿）—— --blue 为历史名，全部指向品牌色 */
  --blue: #0f8a80;
  --blue-hover: #14a094;
  --blue-active: #0c7168;
  --blue-bg: #e7f5f3;
  --brand-border: #b5e0da;
  --brand-ink: #0a6b62;
  /* 兼容旧 teal 系列 */
  --teal-700: #0a6b62;
  --teal-600: #0f8a80;
  --teal-500: #14a094;
  --teal-400: #3fb3a7;
  --teal-100: #d3ede9;
  --teal-50: #eef8f6;
  /* 语义色（好=绿 警示=琥珀 严重=红） */
  --ok: #27945b;
  --ok-strong: #1e7d4c;
  --ok-bg: #e5f4ec;
  --warn: #b07a12;
  --warn-strong: #93650d;
  --warn-bg: #faf1dd;
  --err: #e5484d;
  --err-strong: #c53a3f;
  --err-bg: #fdecec;
  --orange: #d97706;
  --orange-hover: #b45309;
  --orange-light: #fdf3e3;
  --amber: #b07a12;
  /* 图表 */
  --chart-1: #0f8a80;
  --chart-2: #35a398;
  --chart-3: #6fbcb2;
  --chart-4: #a5d8d0;
  --chart-grid: #ececf0;
  --chart-axis: #a4a4af;
  --chart-bar-track: #f0f0f3;
  --chart-ramp-1: #0a6b62;
  --chart-ramp-2: #0f8a80;
  --chart-ramp-3: #35a398;
  --chart-ramp-4: #6fbcb2;
  --chart-ramp-5: #a5d8d0;
  /* 字体（系统栈，无 CDN） */
  --sans: -apple-system, 'SF Pro Text', 'PingFang SC', 'HarmonyOS Sans SC', 'Noto Sans SC', 'Microsoft YaHei', sans-serif;
  --mono: ui-monospace, 'Cascadia Code', 'SF Mono', Consolas, monospace;
  /* 几何 */
  --r: 8px;
  --r-sm: 6px;
  --r-lg: 10px;
  --ease: cubic-bezier(.25,.1,.25,1);
  --gap-blk: 14px;
  /* 浮层阴影 / 焦点 */
  --shadow-pop: 0 4px 16px rgba(22,22,28,.10), 0 1px 3px rgba(22,22,28,.06);
  --shadow-overlay: 0 12px 32px rgba(22,22,28,.16), 0 2px 6px rgba(22,22,28,.08);
  --focus-ring: 0 0 0 3px rgba(15,138,128,.28);
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
  font-variant-numeric: tabular-nums;
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
  --el-button-hover-bg-color: var(--blue-hover);
  --el-button-hover-border-color: var(--blue-hover);
  --el-button-active-bg-color: var(--blue-active);
  --el-button-active-border-color: var(--blue-active);
}

.el-button--success {
  --el-button-bg-color: var(--ok);
  --el-button-border-color: var(--ok);
  --el-button-hover-bg-color: var(--ok-strong);
  --el-button-hover-border-color: var(--ok-strong);
}

.el-button--danger {
  --el-button-bg-color: var(--err);
  --el-button-border-color: var(--err);
  --el-button-hover-bg-color: var(--err-strong);
  --el-button-hover-border-color: var(--err-strong);
}

.el-button--warning {
  --el-button-bg-color: var(--warn);
  --el-button-border-color: var(--warn);
  --el-button-hover-bg-color: var(--warn-strong);
  --el-button-hover-border-color: var(--warn-strong);
}

/* Tag */
.el-tag--info {
  --el-tag-bg-color: var(--ink-100);
  --el-tag-border-color: var(--ink-200);
  --el-tag-text-color: var(--ink-400);
}

.el-tag--success {
  --el-tag-bg-color: var(--ok-bg);
  --el-tag-border-color: #b9e2cc;
  --el-tag-text-color: var(--ok-strong);
}

.el-tag--warning {
  --el-tag-bg-color: var(--warn-bg);
  --el-tag-border-color: #ecd9a8;
  --el-tag-text-color: var(--warn-strong);
}

.el-tag--danger {
  --el-tag-bg-color: var(--err-bg);
  --el-tag-border-color: #f6c6c8;
  --el-tag-text-color: var(--err-strong);
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
  box-shadow: 0 0 0 1px var(--blue) inset, 0 0 0 3px rgba(15, 138, 128, 0.12) inset !important;
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

/* ===== Vant 主题变量已迁移至 design-upgrade.css（保证加载顺序在 vant/lib/index.css 之后） ===== */

/* ===== 移动端底部导航栏固定 ===== */
.van-tabbar--fixed {
  position: fixed !important;
  bottom: 0 !important;
  left: 0 !important;
  width: 100% !important;
  z-index: 100 !important;
}

/* ===== 桌面宽屏下：移动路由收进居中手机栏（router.afterEach 标记 body.mobile-route） ===== */
@media (min-width: 768px) {
  body.mobile-route {
    background: var(--bg-muted);
  }
  body.mobile-route #app {
    max-width: 480px;
    min-height: 100vh;
    margin: 0 auto;
    background: var(--bg);
    box-shadow: 0 0 0 1px var(--ink-200), 0 16px 48px rgba(22, 22, 28, 0.10);
  }
  /* 固定定位的元素相对视口，需同步收窄并居中 */
  body.mobile-route .van-tabbar--fixed,
  body.mobile-route .van-nav-bar--fixed {
    left: 50% !important;
    transform: translateX(-50%);
    max-width: 480px !important;
  }
  /* 底部弹层/动作面板同样收进手机栏，避免桌面端全宽 */
  body.mobile-route .van-popup.van-popup--bottom,
  body.mobile-route .van-action-sheet {
    left: 50% !important;
    transform: translateX(-50%);
    width: 100%;
    max-width: 480px !important;
  }
  body.mobile-route .van-toast {
    left: 50% !important;
    transform: translateX(-50%);
    max-width: 320px;
  }
}
</style>
