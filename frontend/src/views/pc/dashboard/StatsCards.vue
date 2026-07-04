<template>
  <div class="kpi-row cols-5">
    <div class="kpi clickable" :class="{ active: activeKpi === 'tasks' }" @click="$emit('open-task'); activeKpi = 'tasks'">
      <div class="kpi-lbl">检查任务</div>
      <div class="kpi-num">{{ summary.total_tasks || 0 }}</div>
      <div class="kpi-tags">
        <span class="kt kt-muted">待处理 {{ summary.pending_tasks || 0 }}</span>
        <span class="kt kt-blue">进行中 {{ summary.in_progress_tasks || 0 }}</span>
      </div>
      <div class="kpi-arrow"><svg viewBox="0 0 16 16"><path d="M6 3l5 5-5 5" /></svg></div>
    </div>
    <div class="kpi clickable" :class="{ active: activeKpi === 'coverage' }" @click="$emit('open-coverage'); activeKpi = 'coverage'">
      <div class="kpi-lbl">本月覆盖率</div>
      <div class="kpi-num">{{ summary.coverage_rate || 0 }}<span class="kpi-unit">%</span></div>
      <div class="kpi-tags">
        <span class="kt kt-muted">{{ summary.monthly_checked_projects || 0 }} / {{ summary.total_projects || 0 }} 项目</span>
      </div>
      <div class="kpi-arrow"><svg viewBox="0 0 16 16"><path d="M6 3l5 5-5 5" /></svg></div>
    </div>
    <div class="kpi clickable" :class="{ active: activeKpi === 'issues' }" @click="$emit('open-issue'); activeKpi = 'issues'">
      <div class="kpi-lbl">问题总数</div>
      <div class="kpi-num">{{ summary.total_issues || 0 }}</div>
      <div class="kpi-tags">
        <span class="kt kt-err">严重 {{ summary.serious_issues || 0 }}</span>
        <span class="kt kt-warn">一般 {{ summary.general_issues || 0 }}</span>
      </div>
      <div class="kpi-arrow"><svg viewBox="0 0 16 16"><path d="M6 3l5 5-5 5" /></svg></div>
    </div>
    <div class="kpi clickable" :class="{ active: activeKpi === 'pending' }" @click="$emit('open-rect'); activeKpi = 'pending'">
      <div class="kpi-lbl">待整改</div>
      <div class="kpi-num">{{ summary.pending_rectifications || 0 }}</div>
      <div class="kpi-tags">
        <span class="kt kt-warn">已提交 {{ summary.submitted_rectifications || 0 }}</span>
      </div>
      <div class="kpi-arrow"><svg viewBox="0 0 16 16"><path d="M6 3l5 5-5 5" /></svg></div>
    </div>
    <div class="kpi clickable" :class="{ active: activeKpi === 'rate' }" @click="$emit('open-rect'); activeKpi = 'rate'">
      <div class="kpi-lbl">整改完成率</div>
      <div class="kpi-num">{{ summary.rectification_rate || 0 }}<span class="kpi-unit">%</span></div>
      <div class="kpi-tags">
        <span class="kt kt-ok">已通过 {{ summary.approved_rectifications || 0 }}</span>
      </div>
      <div class="kpi-arrow"><svg viewBox="0 0 16 16"><path d="M6 3l5 5-5 5" /></svg></div>
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

<style scoped>
.kpi-row {
  display: grid;
  gap: 12px;
  margin-bottom: 20px;
}

.kpi-row.cols-5 {
  grid-template-columns: repeat(5, 1fr);
}

.kpi {
  background: var(--bg-card);
  border: 1px solid var(--ink-100);
  border-radius: var(--r-lg);
  padding: 18px 20px;
  cursor: default;
  transition: all 0.15s var(--ease);
  animation: kpiIn 0.3s var(--ease) both;
}

.kpi:nth-child(2) { animation-delay: 30ms; }
.kpi:nth-child(3) { animation-delay: 60ms; }
.kpi:nth-child(4) { animation-delay: 90ms; }
.kpi:nth-child(5) { animation-delay: 120ms; }

.kpi:hover {
  border-color: var(--ink-200);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

.kpi.clickable {
  cursor: pointer;
  position: relative;
}

.kpi.clickable:hover {
  border-color: var(--blue);
  box-shadow: 0 2px 12px rgba(37, 99, 235, 0.1);
}

.kpi.clickable.active {
  border-color: var(--blue);
  background: var(--blue-bg);
}

.kpi-lbl {
  font-size: 13px;
  font-weight: 600;
  color: var(--ink-400);
  margin-bottom: 6px;
}

.kpi-num {
  font-family: var(--mono);
  font-size: 32px;
  font-weight: 700;
  color: var(--ink-900);
  line-height: 1;
  margin-bottom: 6px;
  letter-spacing: -1.5px;
}

.kpi-unit {
  font-size: 16px;
  font-weight: 500;
  color: var(--ink-400);
  letter-spacing: 0;
}

.kpi-tags {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.kt {
  font-size: 11px;
  font-family: var(--mono);
  font-weight: 600;
  padding: 2px 7px;
  border-radius: 3px;
}

.kt-ok { background: var(--ok-bg); color: var(--ok); }
.kt-warn { background: var(--warn-bg); color: var(--warn); }
.kt-err { background: var(--err-bg); color: var(--err); }
.kt-teal { background: var(--teal-50); color: var(--teal-700); }
.kt-muted { background: var(--bg-muted); color: var(--ink-600); }
.kt-blue { background: var(--blue-bg); color: var(--blue); }

.kpi-arrow {
  position: absolute;
  right: 16px;
  top: 50%;
  transform: translateY(-50%);
  color: var(--ink-300);
  opacity: 0;
  transition: all 0.15s;
}

.kpi.clickable:hover .kpi-arrow {
  opacity: 1;
  color: var(--blue);
}

.kpi-arrow svg {
  width: 14px;
  height: 14px;
  stroke: currentColor;
  fill: none;
  stroke-width: 2;
}

@keyframes kpiIn {
  from { opacity: 0; transform: translateY(4px); }
  to { opacity: 1; transform: translateY(0); }
}

@media (max-width: 1200px) {
  .kpi-row.cols-5 { grid-template-columns: repeat(3, 1fr); }
}

@media (max-width: 900px) {
  .kpi-row.cols-5 { grid-template-columns: repeat(2, 1fr); }
}
</style>
