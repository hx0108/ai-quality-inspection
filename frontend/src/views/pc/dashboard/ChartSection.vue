<template>
  <div class="charts-grid">
    <div class="dash-card">
      <div class="dash-card-header">
        <div class="dash-card-header-left">
          <span class="dash-card-title">问题按模块分布</span>
          <span class="dash-card-sub">点击查看详情</span>
        </div>
        <div class="dash-card-actions">
          <el-button size="small" text @click="$emit('export-chart', 'module', 'png')">
            <el-icon style="margin-right:4px"><Picture /></el-icon>导出图片
          </el-button>
          <el-button size="small" text @click="$emit('export-chart', 'module', 'excel')">
            <el-icon style="margin-right:4px"><Document /></el-icon>导出Excel
          </el-button>
        </div>
      </div>
      <div ref="moduleChartRef" class="chart-area"></div>
    </div>
    <div class="dash-card">
      <div class="dash-card-header">
        <div class="dash-card-header-left">
          <span class="dash-card-title">各项目整改完成率</span>
          <span class="dash-card-sub">已整改 vs 未整改</span>
        </div>
        <div class="dash-card-actions">
          <el-button size="small" text @click="$emit('export-chart', 'rect', 'png')">
            <el-icon style="margin-right:4px"><Picture /></el-icon>导出图片
          </el-button>
          <el-button size="small" text @click="$emit('export-chart', 'rect', 'excel')">
            <el-icon style="margin-right:4px"><Document /></el-icon>导出Excel
          </el-button>
        </div>
      </div>
      <div ref="rectChartRef" class="chart-area"></div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { Picture, Document } from '@element-plus/icons-vue'

defineProps({
  issueByModule: { type: Array, default: () => [] },
  projectRectStats: { type: Array, default: () => [] }
})

defineEmits(['export-chart'])

const moduleChartRef = ref(null)
const rectChartRef = ref(null)

defineExpose({ moduleChartRef, rectChartRef })
</script>
