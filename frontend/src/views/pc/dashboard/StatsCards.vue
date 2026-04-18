<template>
  <div class="stat-grid">
    <div class="stat-card" style="--accent: #2563eb; --accent-light: #EFF6FF; --accent-grad: linear-gradient(135deg, #2563eb 0%, #3b82f6 100%)" @click="$emit('open-task')">
      <div class="stat-icon-box">
        <el-icon :size="22"><List /></el-icon>
      </div>
      <div class="stat-body">
        <span class="stat-label">检查任务</span>
        <span class="stat-value">{{ summary.total_tasks || 0 }}</span>
        <div class="stat-tags">
          <span class="stat-tag tag-gray">待处理 {{ summary.pending_tasks || 0 }}</span>
          <span class="stat-tag tag-blue">进行中 {{ summary.in_progress_tasks || 0 }}</span>
        </div>
      </div>
      <el-icon class="stat-arrow"><ArrowRight /></el-icon>
    </div>

    <div class="stat-card" style="--accent: #059669; --accent-light: #ECFDF5; --accent-grad: linear-gradient(135deg, #059669 0%, #10b981 100%)" @click="$emit('open-coverage')">
      <div class="stat-icon-box">
        <el-icon :size="22"><PieChart /></el-icon>
      </div>
      <div class="stat-body">
        <span class="stat-label">本月覆盖率</span>
        <span class="stat-value">{{ summary.coverage_rate || 0 }}<span class="stat-unit">%</span></span>
        <div class="stat-tags">
          <span class="stat-tag">{{ summary.monthly_checked_projects || 0 }} / {{ summary.total_projects || 0 }} 项目</span>
        </div>
      </div>
      <el-icon class="stat-arrow"><ArrowRight /></el-icon>
    </div>

    <div class="stat-card" style="--accent: #dc2626; --accent-light: #FEF2F2; --accent-grad: linear-gradient(135deg, #dc2626 0%, #ef4444 100%)" @click="$emit('open-issue')">
      <div class="stat-icon-box">
        <el-icon :size="22"><WarningFilled /></el-icon>
      </div>
      <div class="stat-body">
        <span class="stat-label">问题总数</span>
        <span class="stat-value">{{ summary.total_issues || 0 }}</span>
        <div class="stat-tags">
          <span class="stat-tag tag-red">严重 {{ summary.serious_issues || 0 }}</span>
          <span class="stat-tag tag-orange">一般 {{ summary.general_issues || 0 }}</span>
        </div>
      </div>
      <el-icon class="stat-arrow"><ArrowRight /></el-icon>
    </div>

    <div class="stat-card" style="--accent: #f59e0b; --accent-light: #FFFBEB; --accent-grad: linear-gradient(135deg, #f59e0b 0%, #fbbf24 100%)" @click="$emit('open-rect')">
      <div class="stat-icon-box">
        <el-icon :size="22"><Clock /></el-icon>
      </div>
      <div class="stat-body">
        <span class="stat-label">待整改</span>
        <span class="stat-value">{{ summary.pending_rectifications || 0 }}</span>
        <div class="stat-tags">
          <span class="stat-tag">已提交 {{ summary.submitted_rectifications || 0 }}</span>
        </div>
      </div>
      <el-icon class="stat-arrow"><ArrowRight /></el-icon>
    </div>

    <div class="stat-card" style="--accent: #059669; --accent-light: #ECFDF5; --accent-grad: linear-gradient(135deg, #059669 0%, #10b981 100%)" @click="$emit('open-rect')">
      <div class="stat-icon-box">
        <el-icon :size="22"><CircleCheck /></el-icon>
      </div>
      <div class="stat-body">
        <span class="stat-label">已通过整改</span>
        <span class="stat-value">{{ summary.approved_rectifications || 0 }}</span>
        <div class="stat-tags">
          <span class="stat-tag tag-green">完成率 {{ summary.rectification_rate || 0 }}%</span>
        </div>
      </div>
      <el-icon class="stat-arrow"><ArrowRight /></el-icon>
    </div>
  </div>
</template>

<script setup>
import { List, ArrowRight, PieChart, WarningFilled, Clock, CircleCheck } from '@element-plus/icons-vue'

defineProps({
  summary: { type: Object, default: () => ({}) }
})

defineEmits(['open-task', 'open-coverage', 'open-issue', 'open-rect'])
</script>

<style scoped>
/* ==================== 统计卡片 ==================== */
.stat-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 14px;
  margin-bottom: 20px;
}

.stat-card {
  background: #fff;
  border-radius: 12px;
  padding: 20px;
  display: flex;
  align-items: center;
  gap: 16px;
  cursor: pointer;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04), 0 1px 2px rgba(0, 0, 0, 0.02);
  position: relative;
  overflow: hidden;
  animation: fadeInUp 0.4s ease-out both;
}

.stat-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: var(--accent-grad, var(--accent));
  border-radius: 12px 12px 0 0;
}

.stat-card:nth-child(1) { animation-delay: 0s; }
.stat-card:nth-child(2) { animation-delay: 0.05s; }
.stat-card:nth-child(3) { animation-delay: 0.1s; }
.stat-card:nth-child(4) { animation-delay: 0.15s; }
.stat-card:nth-child(5) { animation-delay: 0.2s; }

.stat-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 12px 24px rgba(0, 0, 0, 0.08);
}

.stat-icon-box {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  background: var(--accent-light);
  color: var(--accent);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: transform 0.25s;
}

.stat-card:hover .stat-icon-box {
  transform: scale(1.08);
}

.stat-body {
  flex: 1;
  min-width: 0;
}

.stat-label {
  display: block;
  font-size: 13px;
  color: #9ba3af;
  margin-bottom: 4px;
}

.stat-value {
  display: block;
  font-size: 28px;
  font-weight: 700;
  color: #1a1d26;
  line-height: 1.2;
}

.stat-unit {
  font-size: 14px;
  font-weight: 400;
  color: #9ba3af;
}

.stat-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 6px;
}

.stat-tag {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 10px;
  background: #F1F5F9;
  color: #64748B;
}

.tag-blue { background: #EFF6FF; color: #2563eb; }
.tag-red { background: #FEF2F2; color: #dc2626; }
.tag-orange { background: #FFF7ED; color: #ea580c; }
.tag-green { background: #ECFDF5; color: #059669; }
.tag-gray { background: #F8FAFC; color: #64748B; }

.stat-arrow {
  color: #CBD5E1;
  flex-shrink: 0;
  transition: transform 0.2s, color 0.2s;
  font-size: 16px;
}

.stat-card:hover .stat-arrow {
  transform: translateX(3px);
  color: var(--accent);
}

@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

@media (max-width: 1200px) {
  .stat-grid { grid-template-columns: repeat(3, 1fr); }
}

@media (max-width: 900px) {
  .stat-grid { grid-template-columns: repeat(2, 1fr); }
}
</style>
