<template>
  <div class="kpi-row cols-5">
    <div class="kpi kpi-click" :class="{ 'kpi-active': activeKpi === 'tasks' }" @click="$emit('open-task'); activeKpi = 'tasks'">
      <div class="kpi-lbl">检查任务</div>
      <div class="kpi-num">{{ summary.total_tasks || 0 }}</div>
      <div class="kpi-tags">
        <span class="ktag ktag-muted">待处理 {{ summary.pending_tasks || 0 }}</span>
        <span class="ktag ktag-brand">进行中 {{ summary.in_progress_tasks || 0 }}</span>
      </div>
      <span class="kpi-go"><svg viewBox="0 0 16 16"><path d="M6 3l5 5-5 5" /></svg></span>
    </div>
    <div class="kpi kpi-click" :class="{ 'kpi-active': activeKpi === 'coverage' }" @click="$emit('open-coverage'); activeKpi = 'coverage'">
      <div class="kpi-lbl">本月覆盖率</div>
      <div class="kpi-num">{{ summary.coverage_rate || 0 }}<span class="kpi-unit">%</span></div>
      <div class="kpi-tags">
        <span class="ktag ktag-muted">{{ summary.monthly_checked_projects || 0 }} / {{ summary.total_projects || 0 }} 项目</span>
      </div>
      <span class="kpi-go"><svg viewBox="0 0 16 16"><path d="M6 3l5 5-5 5" /></svg></span>
    </div>
    <div class="kpi kpi-click" :class="{ 'kpi-active': activeKpi === 'issues' }" @click="$emit('open-issue'); activeKpi = 'issues'">
      <div class="kpi-lbl">问题总数</div>
      <div class="kpi-num">{{ summary.total_issues || 0 }}</div>
      <div class="kpi-tags">
        <span class="ktag ktag-err">严重 {{ summary.serious_issues || 0 }}</span>
        <span class="ktag ktag-warn">一般 {{ summary.general_issues || 0 }}</span>
      </div>
      <span class="kpi-go"><svg viewBox="0 0 16 16"><path d="M6 3l5 5-5 5" /></svg></span>
    </div>
    <div class="kpi kpi-click" :class="{ 'kpi-active': activeKpi === 'pending' }" @click="$emit('open-rect'); activeKpi = 'pending'">
      <div class="kpi-lbl">待整改</div>
      <div class="kpi-num" :class="{ 'kpi-err': (summary.serious_issues || 0) > 5 }">{{ summary.pending_rectifications || 0 }}</div>
      <div class="kpi-tags">
        <span class="ktag ktag-muted">已提交 {{ summary.submitted_rectifications || 0 }}</span>
      </div>
      <span class="kpi-go"><svg viewBox="0 0 16 16"><path d="M6 3l5 5-5 5" /></svg></span>
    </div>
    <div class="kpi kpi-click" :class="{ 'kpi-active': activeKpi === 'rate' }" @click="$emit('open-rect'); activeKpi = 'rate'">
      <div class="kpi-lbl">整改完成率</div>
      <div class="kpi-num">{{ summary.rectification_rate || 0 }}<span class="kpi-unit">%</span></div>
      <div class="kpi-tags">
        <span class="ktag ktag-ok">已通过 {{ summary.approved_rectifications || 0 }}</span>
      </div>
      <span class="kpi-go"><svg viewBox="0 0 16 16"><path d="M6 3l5 5-5 5" /></svg></span>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

defineProps({
  summary: { type: Object, default: () => ({}) }
})

defineEmits(['open-task', 'open-coverage', 'open-issue', 'open-rect'])

const activeKpi = ref('')
</script>

<!-- 样式由全局 design-upgrade.css v2 提供（.kpi-row/.kpi/.ktag/.kpi-go） -->
