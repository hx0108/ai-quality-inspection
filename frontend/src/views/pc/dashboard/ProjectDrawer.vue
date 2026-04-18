<template>
  <el-drawer v-model="drawerVisible" :title="title" size="55%" :destroy-on-close="true" @close="$emit('update:visible', false)">
    <div class="project-drawer-content">
      <div class="mini-chart-label">历史得分趋势</div>
      <div ref="miniChartRef" class="mini-chart-box"></div>
      <div class="mini-chart-label" style="margin-top: 16px">最近检查模块得分</div>
      <el-table :data="modules" stripe size="small" v-loading="loading" row-key="module_name" class="drawer-table" @expand-change="handleModuleExpand">
        <el-table-column type="expand">
          <template #default="{ row }">
            <el-table :data="row.items" stripe size="small" v-loading="row._loading" style="margin: 8px 20px">
              <el-table-column prop="item_name" label="检查项" />
              <el-table-column prop="score" label="得分" width="90" align="center">
                <template #default="{ row: item }">
                  <span :class="getScoreClass(item.score)">{{ item.score }}</span>
                  <el-tag v-if="item.is_fallback" type="warning" size="small" style="margin-left:2px">降级</el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="weight" label="权重" width="70" align="center" />
              <el-table-column prop="scoring_basis" label="评分依据" show-overflow-tooltip />
            </el-table>
          </template>
        </el-table-column>
        <el-table-column prop="module_name" label="模块名称" />
        <el-table-column prop="module_pct_score" label="模块得分" width="100" align="center">
          <template #default="{ row }">
            <span :class="getScoreClass(row.module_pct_score)">{{ row.module_pct_score }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="weight_ratio" label="权重占比" width="90" align="center" />
        <el-table-column prop="items_count" label="检查项数" width="90" align="center" />
      </el-table>
    </div>
  </el-drawer>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  visible: Boolean,
  title: { type: String, default: '' },
  modules: { type: Array, default: () => [] },
  loading: Boolean
})

const emit = defineEmits(['update:visible', 'expand-module'])

const drawerVisible = computed({
  get: () => props.visible,
  set: (val) => emit('update:visible', val)
})

const miniChartRef = ref(null)

function getScoreClass(score) {
  if (score == null) return ''
  if (score >= 90) return 'score-excellent'
  if (score >= 80) return 'score-good'
  if (score >= 70) return 'score-fair'
  return 'score-poor'
}

function handleModuleExpand(row, expandedRows) {
  // handled by parent
}

defineExpose({ miniChartRef })
</script>
