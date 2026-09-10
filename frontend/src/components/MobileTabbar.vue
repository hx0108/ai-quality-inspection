<template>
  <van-tabbar v-model="activeTab" route>
    <van-tabbar-item to="/dashboard">
      <span>概览</span>
      <template #icon>
        <svg viewBox="0 0 16 16" class="tb-icon"><rect x="2" y="2" width="5" height="5" rx="1" /><rect x="9" y="2" width="5" height="5" rx="1" /><rect x="2" y="9" width="5" height="5" rx="1" /><rect x="9" y="9" width="5" height="5" rx="1" /></svg>
      </template>
    </van-tabbar-item>
    <van-tabbar-item to="/tasks">
      <span>任务</span>
      <template #icon>
        <svg viewBox="0 0 16 16" class="tb-icon"><path d="M2 4h12M2 8h12M2 12h8" /></svg>
      </template>
    </van-tabbar-item>
    <van-tabbar-item to="/reports">
      <span>报告</span>
      <template #icon>
        <svg viewBox="0 0 16 16" class="tb-icon"><rect x="2.5" y="1.5" width="11" height="13" rx="1.5" /><path d="M5.5 5h5M5.5 8h5M5.5 11h3" /></svg>
      </template>
    </van-tabbar-item>
    <van-tabbar-item to="/rectification">
      <span>整改</span>
      <template #icon>
        <svg viewBox="0 0 16 16" class="tb-icon"><path d="M13.5 8a5.5 5.5 0 11-1.6-3.9" /><path d="M13.5 2.5V5H11" /></svg>
      </template>
    </van-tabbar-item>
    <van-tabbar-item to="/analysis-mobile">
      <span>分析</span>
      <template #icon>
        <svg viewBox="0 0 16 16" class="tb-icon"><path d="M2 14V9M6.3 14V4M10.6 14v-7M15 14V2" /></svg>
      </template>
    </van-tabbar-item>
  </van-tabbar>
</template>

<script setup>
import { ref } from 'vue'

const activeTab = ref(0)
</script>

<style scoped>
/* 原型 .m-tab 图标形态：细线描边，继承文字色（激活=青绿） */
.tb-icon {
  width: 20px;
  height: 20px;
  stroke: currentColor;
  fill: none;
  stroke-width: 1.6;
  stroke-linecap: round;
  stroke-linejoin: round;
}
</style>
