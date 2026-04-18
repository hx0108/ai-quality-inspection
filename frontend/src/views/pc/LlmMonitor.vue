<template>
  <div class="llm-monitor-page">
    <div v-if="loading" class="loading-wrap">
      <el-skeleton :rows="8" animated />
    </div>

    <template v-else>
      <!-- 页面标题 -->
      <div class="page-header">
        <div class="page-header-left">
          <h2 class="page-title">AI 能力分析</h2>
          <p class="page-desc">大模型调用量、效能与费用全览</p>
        </div>
        <div class="header-actions">
          <el-radio-group v-model="trendDays" size="default" @change="onDaysChange">
            <el-radio-button value="7">近7天</el-radio-button>
            <el-radio-button value="30">近30天</el-radio-button>
            <el-radio-button value="90">近90天</el-radio-button>
            <el-radio-button value="custom">自定义</el-radio-button>
          </el-radio-group>
          <el-date-picker
            v-if="trendDays === 'custom'"
            v-model="customDateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            size="default"
            style="margin-left: 8px; width: 240px;"
            @change="onCustomDateChange"
          />
        </div>
      </div>

      <!-- 核心指标卡片 -->
      <div class="stat-grid">
        <div class="stat-card" style="--accent: #7c3aed; --accent-light: #F5F3FF; --accent-grad: linear-gradient(135deg, #7c3aed 0%, #A78BFA 100%)">
          <div class="stat-icon-box"><el-icon :size="22"><Cpu /></el-icon></div>
          <div class="stat-body">
            <span class="stat-label">本月调用</span>
            <span class="stat-value">{{ overview.month.calls || 0 }}<span class="stat-unit">次</span></span>
            <div class="stat-tags">
              <span class="stat-tag">今日 {{ overview.today.calls || 0 }} 次</span>
              <span v-if="callsChange !== null" :class="['stat-tag', callsChange >= 0 ? 'tag-green' : 'tag-red']">
                环比 {{ callsChange >= 0 ? '+' : '' }}{{ callsChange }}%
              </span>
            </div>
          </div>
        </div>

        <div class="stat-card" style="--accent: #059669; --accent-light: #ECFDF5; --accent-grad: linear-gradient(135deg, #059669 0%, #10b981 100%)">
          <div class="stat-icon-box"><el-icon :size="22"><Tickets /></el-icon></div>
          <div class="stat-body">
            <span class="stat-label">本月 Tokens</span>
            <span class="stat-value">{{ formatTokens(overview.month.tokens || 0) }}<span class="stat-unit">tokens</span></span>
            <div class="stat-tags">
              <span v-if="tokensChange !== null" :class="['stat-tag', tokensChange >= 0 ? 'tag-green' : 'tag-red']">
                环比 {{ tokensChange >= 0 ? '+' : '' }}{{ tokensChange }}%
              </span>
            </div>
          </div>
        </div>

        <div class="stat-card" style="--accent: #2563eb; --accent-light: #EFF6FF; --accent-grad: linear-gradient(135deg, #2563eb 0%, #3b82f6 100%)">
          <div class="stat-icon-box"><el-icon :size="22"><Timer /></el-icon></div>
          <div class="stat-body">
            <span class="stat-label">本月平均耗时</span>
            <span class="stat-value">{{ formatDuration(overview.month_avg_duration_ms || 0) }}</span>
            <div class="stat-tags">
              <span class="stat-tag">成功率 {{ overview.month_success_rate || 100 }}%</span>
            </div>
          </div>
        </div>

        <div class="stat-card" style="--accent: #f59e0b; --accent-light: #FFFBEB; --accent-grad: linear-gradient(135deg, #f59e0b 0%, #fbbf24 100%)">
          <div class="stat-icon-box"><el-icon :size="22"><Money /></el-icon></div>
          <div class="stat-body">
            <span class="stat-label">本月费用估算</span>
            <span class="stat-value">¥{{ costData.total_estimate || '0.00' }}</span>
            <div class="stat-tags">
              <span class="stat-tag tag-orange">基于公开定价</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 失败记录提醒 -->
      <div class="failure-banner" v-if="failedRecordsCount > 0">
        <div class="failure-banner-left">
          <el-icon color="#dc2626" :size="18"><WarningFilled /></el-icon>
          <span>近{{ trendDays }}天共有 <strong>{{ failedRecordsCount }}</strong> 次失败调用（失败率 {{ failedRate }}%）</span>
        </div>
        <el-button size="small" text type="danger" @click="showFailedOnly">
          查看失败记录
          <el-icon style="margin-left: 4px"><ArrowRight /></el-icon>
        </el-button>
      </div>

      <!-- 趋势图 + Token占比饼图 + 耗时分布 -->
      <div class="chart-grid">
        <div class="chart-card main-chart">
          <div class="chart-header">
            <div class="chart-header-top">
              <span class="chart-title">调用量与成功率趋势</span>
              <div class="chart-meta">
                <span class="meta-item">
                  <span class="meta-label">日均调用</span>
                  <span class="meta-value">{{ dailyAvg }}</span>
                  <span class="meta-unit">次</span>
                </span>
                <span class="meta-divider">|</span>
                <span class="meta-item">
                  <span class="meta-label">日均Token</span>
                  <span class="meta-value">{{ formatTokens(dailyAvgTokens) }}</span>
                </span>
                <span class="meta-divider">|</span>
                <span class="meta-item">
                  <span class="meta-label">累计调用</span>
                  <span class="meta-value">{{ totalCalls }}</span>
                  <span class="meta-unit">次</span>
                </span>
              </div>
            </div>
            <span class="chart-sub">每日调用次数 / Token消耗 / 成功率 / 平均耗时</span>
          </div>
          <div ref="trendChartRef" class="chart-container"></div>
        </div>
        <div class="chart-side-stack">
          <div class="chart-card">
            <div class="chart-header">
              <span class="chart-title">Token 占比</span>
              <span class="chart-sub">按模型分布（{{ periodLabel }}）</span>
            </div>
            <div ref="pieChartRef" class="chart-container-sm"></div>
          </div>
          <div class="chart-card">
            <div class="chart-header">
              <span class="chart-title">耗时分布</span>
              <span class="chart-sub">各耗时区间调用次数</span>
            </div>
            <div ref="durationChartRef" class="chart-container-sm"></div>
          </div>
        </div>
      </div>

      <!-- 模型性能对比 + 按调用类型统计 -->
      <div class="bottom-grid">
        <div class="card">
          <div class="card-header">
            <span class="card-title">模型统计</span>
            <span class="chart-sub">{{ periodLabel }}</span>
          </div>
          <el-table :data="overview.by_model" stripe size="small">
            <el-table-column prop="model" label="模型" min-width="130">
              <template #default="{ row }">
                <span class="model-badge">{{ row.model }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="calls" label="调用次数" align="right" width="75">
              <template #default="{ row }">
                <span class="num">{{ row.calls }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="tokens" label="Token总量" align="right" width="80">
              <template #default="{ row }">
                <span class="num-gray">{{ formatTokens(row.tokens) }}</span>
              </template>
            </el-table-column>
            <el-table-column label="Cache Miss / Prompt" align="right" width="115">
              <template #default="{ row }">
                <span class="num-gray">{{ formatTokens(row.cache_miss_tokens || row.prompt_tokens) }}</span>
              </template>
            </el-table-column>
            <el-table-column label="Cache Hit" align="right" width="90">
              <template #default="{ row }">
                <span class="num-gray">{{ (row.cache_hit_tokens || 0) > 0 ? formatTokens(row.cache_hit_tokens) : '-' }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="completion_tokens" label="Output" align="right" width="80">
              <template #default="{ row }">
                <span class="num-gray">{{ formatTokens(row.completion_tokens) }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="avg_duration_ms" label="平均耗时" align="right" width="80">
              <template #default="{ row }">
                <span class="num-gray">{{ row.avg_duration_ms }}ms</span>
              </template>
            </el-table-column>
            <el-table-column prop="success_rate" label="成功率" align="center" width="75">
              <template #default="{ row }">
                <el-tag :type="row.success_rate >= 99 ? 'success' : 'warning'" size="small">
                  {{ row.success_rate }}%
                </el-tag>
              </template>
            </el-table-column>
          </el-table>
        </div>

        <div class="card">
          <div class="card-header">
            <span class="card-title">模型统计</span>
          </div>
          <el-table :data="overview.by_type" stripe size="small">
            <el-table-column prop="type" label="调用类型" min-width="130">
              <template #default="{ row }">
                <span class="type-badge" :class="'type-' + row.type">{{ getTypeName(row.type) }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="calls" label="调用次数" align="right" width="90">
              <template #default="{ row }">
                <span class="num">{{ row.calls }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="tokens" label="Token 总量" align="right" width="100">
              <template #default="{ row }">
                <span class="num-gray">{{ formatTokens(row.tokens) }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="avg_duration_ms" label="平均耗时" align="right" width="100">
              <template #default="{ row }">
                <span class="num-gray">{{ row.avg_duration_ms }}ms</span>
              </template>
            </el-table-column>
            <el-table-column prop="success_rate" label="成功率" align="center" width="80">
              <template #default="{ row }">
                <el-tag :type="row.success_rate >= 99 ? 'success' : 'warning'" size="small">
                  {{ row.success_rate }}%
                </el-tag>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </div>

      <!-- 模型费用明细（单独一行） -->
      <div class="card" style="margin-top: 16px;">
        <div class="card-header">
          <span class="card-title">模型统计</span>
          <span class="chart-sub">{{ periodLabel }}</span>
        </div>
        <el-table :data="costData.models" stripe size="small">
          <el-table-column prop="model" label="模型" min-width="110">
            <template #default="{ row }">
              <span class="model-badge">{{ row.model }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="model_name_cn" label="名称" min-width="100" />
          <el-table-column prop="call_count" label="调用" align="right" width="60">
            <template #default="{ row }">
              <span class="num">{{ row.call_count }}</span>
            </template>
          </el-table-column>
          <el-table-column label="Cache Miss / Prompt" align="right" width="110">
            <template #default="{ row }">
              <span class="num-gray">{{ formatTokens(row.cache_miss_tokens || row.prompt_tokens) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="Cache Hit" align="right" width="85">
            <template #default="{ row }">
              <span class="num-gray">{{ (row.cache_hit_tokens || 0) > 0 ? formatTokens(row.cache_hit_tokens) : '-' }}</span>
            </template>
          </el-table-column>
          <el-table-column label="Output" align="right" width="75">
            <template #default="{ row }">
              <span class="num-gray">{{ formatTokens(row.completion_tokens) }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="success_rate" label="成功率" align="center" width="70">
            <template #default="{ row }">
              <el-tag :type="row.success_rate >= 99 ? 'success' : 'warning'" size="small">
                {{ row.success_rate }}%
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="avg_duration_ms" label="耗时" align="right" width="65">
            <template #default="{ row }">
              <span class="num-gray">{{ row.avg_duration_ms }}ms</span>
            </template>
          </el-table-column>
          <el-table-column label="Cache Miss费" align="right" width="85">
            <template #default="{ row }">
              <span class="num-gray">{{ row.cache_miss_cost != null ? '¥' + row.cache_miss_cost : '-' }}</span>
            </template>
          </el-table-column>
          <el-table-column label="Cache Hit费" align="right" width="80">
            <template #default="{ row }">
              <span class="num-gray">{{ row.cache_hit_cost != null ? '¥' + row.cache_hit_cost : '-' }}</span>
            </template>
          </el-table-column>
          <el-table-column label="Output费" align="right" width="75">
            <template #default="{ row }">
              <span class="num-gray">{{ row.output_cost != null ? '¥' + row.output_cost : '¥' + row.completion_cost }}</span>
            </template>
          </el-table-column>
          <el-table-column label="Prompt费" align="right" width="75">
            <template #default="{ row }">
              <span class="num-gray">{{ row.prompt_cost != null ? '¥' + row.prompt_cost : '-' }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="total_cost" label="费用合计" align="right" width="85">
            <template #default="{ row }">
              <span class="num" style="color: #dc2626; font-weight: 600;">¥{{ row.total_cost }}</span>
            </template>
          </el-table-column>
        </el-table>
        <div class="cost-summary">
          <span>估算总费用：<strong>¥{{ costData.total_estimate }}</strong></span>
          <span class="cost-note">* 基于各模型官方定价精准计算，DeepSeek三档计费（Cache Hit ¥0.0002/千 / Cache Miss ¥0.002/千 / Output ¥0.003/千）</span>
        </div>
      </div>

      <!-- 调用记录明细 -->
      <div class="card" style="margin-top: 16px;">
        <div class="card-header">
          <span class="card-title">调用记录明细</span>
          <div class="table-filters">
            <el-select v-model="filterModel" placeholder="全部模型" clearable size="small" style="width: 150px;" @change="fetchRecords">
              <el-option v-for="m in modelOptions" :key="m" :label="m" :value="m" />
            </el-select>
            <el-select v-model="filterType" placeholder="全部类型" clearable size="small" style="width: 130px;" @change="fetchRecords">
              <el-option v-for="t in typeOptions" :key="t.value" :label="t.label" :value="t.value" />
            </el-select>
            <el-select v-model="filterSuccess" placeholder="全部状态" clearable size="small" style="width: 110px;" @change="fetchRecords">
              <el-option label="成功" value="true" />
              <el-option label="失败" value="false" />
            </el-select>
          </div>
        </div>
        <el-table :data="records" stripe size="small">
          <el-table-column prop="timestamp" label="时间" width="155" />
          <el-table-column prop="model_name" label="模型" min-width="120">
            <template #default="{ row }">
              <span class="model-badge">{{ row.model_name }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="call_type" label="类型" width="120">
            <template #default="{ row }">
              <span class="type-badge" :class="'type-' + row.call_type">{{ getTypeName(row.call_type) }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="prompt_tokens" label="Prompt" align="right" min-width="80">
            <template #default="{ row }">
              <span class="num-gray">{{ formatTokens(row.prompt_tokens) }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="completion_tokens" label="Completion" align="right" min-width="100">
            <template #default="{ row }">
              <span class="num-gray">{{ formatTokens(row.completion_tokens) }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="total_tokens" label="Total" align="right" min-width="80">
            <template #default="{ row }">
              <span class="num">{{ formatTokens(row.total_tokens) }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="duration_ms" label="耗时" align="right" min-width="80">
            <template #default="{ row }">
              <span class="num-gray">{{ row.duration_ms }}ms</span>
            </template>
          </el-table-column>
          <el-table-column prop="task_id" label="关联任务" min-width="130" show-overflow-tooltip />
          <el-table-column label="状态" width="70" align="center">
            <template #default="{ row }">
              <el-tag :type="row.success ? 'success' : 'danger'" size="small">
                {{ row.success ? '成功' : '失败' }}
              </el-tag>
            </template>
          </el-table-column>
        </el-table>
        <div class="pagination-wrap">
          <el-pagination
            v-model:current-page="recordsPage"
            v-model:page-size="recordsPageSize"
            :total="recordsTotal"
            :page-sizes="[10, 20, 50, 100]"
            layout="total, sizes, prev, pager, next"
            @size-change="fetchRecords"
            @current-change="fetchRecords"
          />
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import echarts from '../../utils/echarts'
import { getLlmOverview, getLlmTrend, getLlmRecords, getLlmModels, getLlmCostEstimate } from '../../api/llm'

const loading = ref(false)
const trendDays = ref('7')
const customDateRange = ref(null)
const trendChartRef = ref(null)
const pieChartRef = ref(null)
const durationChartRef = ref(null)
let trendChart = null
let pieChart = null
let durationChart = null

const overview = ref({ total: {}, today: {}, month: {}, last_month: {}, by_model: [], by_type: [] })
const costData = ref({ total_estimate: 0, models: [] })
const records = ref([])
const recordsPage = ref(1)
const recordsPageSize = ref(20)
const recordsTotal = ref(0)
const modelOptions = ref([])
const filterModel = ref('')
const filterType = ref('')
const filterSuccess = ref('')

const typeOptions = [
  { value: 'scoring', label: 'AI评分' },
  { value: 'analysis', label: '分析' },
  { value: 'report', label: '报告' },
  { value: 'rectification_check', label: '整改核查' },
]

const typeNames = {
  scoring: 'AI评分',
  analysis: '分析',
  report: '报告',
  rectification_check: '整改核查',
}

const getTypeName = (type) => typeNames[type] || type

const periodLabel = computed(() => {
  if (trendDays.value === 'custom' && customDateRange.value && customDateRange.value.length === 2) {
    const [start, end] = customDateRange.value
    const startStr = start instanceof Date ? start.toLocaleDateString('zh-CN') : start
    const endStr = end instanceof Date ? end.toLocaleDateString('zh-CN') : end
    return `${startStr} 至 ${endStr}`
  }
  return `近${trendDays.value}天`
})

// 日均调用
const dailyAvg = computed(() => {
  const days = new Date().getDate()
  return days > 0 ? Math.round((overview.value.month?.calls || 0) / days) : 0
})

const dailyAvgTokens = computed(() => {
  const days = new Date().getDate()
  return days > 0 ? Math.round((overview.value.month?.tokens || 0) / days) : 0
})

// 失败记录统计
const failedRecordsCount = computed(() => records.value.filter(r => !r.success).length)
const failedRate = computed(() => {
  if (!records.value.length) return 0
  return ((failedRecordsCount.value / records.value.length) * 100).toFixed(1)
})

// 累计调用
const totalCalls = computed(() => overview.value.total?.all_calls || 0)

// 环比计算
const callsChange = computed(() => {
  const cur = overview.value.month?.calls || 0
  const prev = overview.value.last_month?.calls || 0
  if (prev === 0) return cur > 0 ? null : 0
  return Math.round((cur - prev) / prev * 1000) / 10
})

const tokensChange = computed(() => {
  const cur = overview.value.month?.tokens || 0
  const prev = overview.value.last_month?.tokens || 0
  if (prev === 0) return cur > 0 ? null : 0
  return Math.round((cur - prev) / prev * 1000) / 10
})

const formatTokens = (n) => {
  if (!n) return '0'
  if (n >= 1000000) return (n / 1000000).toFixed(1) + 'M'
  if (n >= 1000) return (n / 1000).toFixed(1) + 'K'
  return String(n)
}

const formatDuration = (ms) => {
  if (!ms) return '0ms'
  if (ms >= 60000) return (ms / 60000).toFixed(1) + 'min'
  if (ms >= 1000) return (ms / 1000).toFixed(1) + 's'
  return ms.toFixed(0) + 'ms'
}

const fetchOverview = async () => {
  try {
    const res = await getLlmOverview()
    overview.value = res || {}
  } catch (e) {
    console.error('获取LLM总览失败:', e)
  }
}

const fetchTrend = async () => {
  try {
    let days = trendDays.value
    if (trendDays.value === 'custom' && customDateRange.value && customDateRange.value.length === 2) {
      const [start, end] = customDateRange.value
      const diff = Math.ceil((end - start) / (1000 * 60 * 60 * 24)) + 1
      days = String(Math.min(diff, 365))
    }
    const res = await getLlmTrend(days)
    renderTrendChart(res.trend || [])
  } catch (e) {
    console.error('获取趋势失败:', e)
  }
}

const fetchCost = async () => {
  try {
    let days = trendDays.value
    if (trendDays.value === 'custom' && customDateRange.value && customDateRange.value.length === 2) {
      const [start, end] = customDateRange.value
      const diff = Math.ceil((end - start) / (1000 * 60 * 60 * 24)) + 1
      days = String(Math.min(diff, 365))
    }
    const res = await getLlmCostEstimate(days)
    costData.value = res || {}
  } catch (e) {
    console.error('获取费用估算失败:', e)
  }
}

const fetchRecords = async () => {
  try {
    const params = {
      page: recordsPage.value,
      page_size: recordsPageSize.value,
    }
    if (filterModel.value) params.model = filterModel.value
    if (filterType.value) params.call_type = filterType.value
    if (filterSuccess.value) params.success = filterSuccess.value

    const res = await getLlmRecords(params)
    records.value = res.records || []
    recordsTotal.value = res.total || 0
  } catch (e) {
    console.error('获取记录失败:', e)
  }
}

const fetchModels = async () => {
  try {
    const res = await getLlmModels()
    modelOptions.value = (res.models || []).map(m => m.name)
  } catch (e) {
    console.error('获取模型列表失败:', e)
  }
}

const onDaysChange = async () => {
  customDateRange.value = null
  await Promise.all([fetchTrend(), fetchCost()])
  renderPieChart()
  renderDurationChart()
}

const onCustomDateChange = async () => {
  if (customDateRange.value && customDateRange.value.length === 2) {
    const [start, end] = customDateRange.value
    if (start && end) {
      trendDays.value = 'custom'
      await Promise.all([fetchTrend(), fetchCost()])
      renderPieChart()
      renderDurationChart()
    }
  }
}

// 查看失败记录
const showFailedOnly = () => {
  filterSuccess.value = 'false'
  recordsPage.value = 1
  fetchRecords()
}

const renderTrendChart = (trend) => {
  nextTick(() => {
    if (!trendChartRef.value) return
    if (!trendChart) {
      trendChart = echarts.init(trendChartRef.value)
    }

    const dates = trend.map(t => t.date)
    const calls = trend.map(t => t.total_calls)
    const tokens = trend.map(t => t.total_tokens)
    const successRates = trend.map(t => t.success_rate ?? 100)
    const avgDurations = trend.map(t => t.avg_duration_ms ?? 0)

    trendChart.setOption({
      tooltip: {
        trigger: 'axis',
        backgroundColor: 'rgba(255, 255, 255, 0.96)',
        borderColor: '#E2E8F0',
        borderWidth: 1,
        textStyle: { color: '#334155', fontSize: 13 },
        extraCssText: 'box-shadow: 0 4px 12px rgba(0,0,0,0.08); border-radius: 8px;',
        formatter: (params) => {
          let html = `<div style="font-weight:600;margin-bottom:6px">${params[0].axisValue}</div>`
          params.forEach(p => {
            let val = p.value
            if (p.seriesName === '成功率') val = val + '%'
            else if (p.seriesName === '平均耗时') val = val + 'ms'
            else if (p.seriesName === 'Token消耗') val = formatTokens(val)
            html += `<div style="display:flex;align-items:center;gap:6px;margin:3px 0">
              ${p.marker}<span style="color:#64748b">${p.seriesName}</span>
              <span style="margin-left:auto;font-weight:600;color:#1e293b">${val}</span>
            </div>`
          })
          return html
        }
      },
      legend: {
        data: [
          { name: '调用次数', icon: 'roundRect' },
          { name: 'Token消耗', icon: 'circle' },
          { name: '成功率', icon: 'diamond' },
          { name: '平均耗时', icon: 'circle' },
        ],
        top: 0,
        right: 10,
        itemGap: 16,
        itemWidth: 14,
        itemHeight: 10,
        textStyle: { color: '#64748B', fontSize: 11 }
      },
      grid: { left: 56, right: 56, top: 44, bottom: 32 },
      xAxis: {
        type: 'category',
        data: dates,
        axisLine: { lineStyle: { color: '#E2E8F0' } },
        axisTick: { show: false },
        axisLabel: {
          color: '#94A3B8',
          fontSize: 11,
          rotate: dates.length > 15 ? 35 : 0,
          formatter: (val) => val.slice(5)
        }
      },
      yAxis: [
        {
          type: 'value',
          position: 'left',
          axisLine: { show: false },
          axisTick: { show: false },
          splitLine: { lineStyle: { color: '#F1F5F9', type: 'dashed' } },
          axisLabel: { color: '#94A3B8', fontSize: 11, splitNumber: 5 }
        },
        {
          type: 'value',
          position: 'right',
          axisLine: { show: false },
          axisTick: { show: false },
          splitLine: { show: false },
          axisLabel: {
            color: '#94A3B8',
            fontSize: 11,
            splitNumber: 5,
            formatter: (val) => {
              if (val >= 1000000) return (val / 1000000).toFixed(1) + 'M'
              if (val >= 1000) return (val / 1000).toFixed(0) + 'K'
              return val
            }
          }
        }
      ],
      series: [
        {
          name: '调用次数',
          type: 'bar',
          data: calls,
          yAxisIndex: 0,
          itemStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: '#7c3aed' },
              { offset: 1, color: '#c4b5fd' }
            ]),
            borderRadius: [3, 3, 0, 0]
          },
          barMaxWidth: 20,
        },
        {
          name: 'Token消耗',
          type: 'line',
          yAxisIndex: 1,
          data: tokens,
          smooth: true,
          symbol: 'circle',
          symbolSize: 5,
          lineStyle: { color: '#10b981', width: 2.5 },
          itemStyle: { color: '#10b981', borderWidth: 2, borderColor: '#fff' },
          areaStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: 'rgba(16, 185, 129, 0.12)' },
              { offset: 1, color: 'rgba(16, 185, 129, 0)' }
            ])
          }
        },
        {
          name: '成功率',
          type: 'line',
          yAxisIndex: 0,
          data: successRates,
          smooth: true,
          symbol: 'diamond',
          symbolSize: 5,
          lineStyle: { color: '#f59e0b', width: 1.5, type: [4, 3] },
          itemStyle: { color: '#f59e0b' },
          tooltip: { valueFormatter: (val) => val + '%' }
        },
        {
          name: '平均耗时',
          type: 'line',
          yAxisIndex: 0,
          data: avgDurations,
          smooth: true,
          symbol: 'emptyCircle',
          symbolSize: 4,
          lineStyle: { color: '#ec4899', width: 1.5 },
          itemStyle: { color: '#ec4899' },
          tooltip: { valueFormatter: (val) => val + 'ms' }
        }
      ]
    })
  })
}

const renderDurationChart = () => {
  nextTick(() => {
    if (!durationChartRef.value) return
    const recs = records.value
    if (!recs.length) return

    if (!durationChart) {
      durationChart = echarts.init(durationChartRef.value)
    }

    // 分桶：<500ms, 500-1s, 1-2s, 2-5s, >5s
    const buckets = [
      { label: '<500ms', min: 0, max: 500, count: 0 },
      { label: '500ms-1s', min: 500, max: 1000, count: 0 },
      { label: '1s-2s', min: 1000, max: 2000, count: 0 },
      { label: '2s-5s', min: 2000, max: 5000, count: 0 },
      { label: '>5s', min: 5000, max: Infinity, count: 0 },
    ]

    recs.forEach(r => {
      const d = r.duration_ms || 0
      for (const b of buckets) {
        if (d >= b.min && d < b.max) {
          b.count++
          break
        }
      }
    })

    const labels = buckets.map(b => b.label)
    const counts = buckets.map(b => b.count)

    durationChart.setOption({
      tooltip: {
        trigger: 'axis',
        backgroundColor: 'rgba(255, 255, 255, 0.96)',
        borderColor: '#E2E8F0',
        borderWidth: 1,
        textStyle: { color: '#334155', fontSize: 13 },
        extraCssText: 'box-shadow: 0 4px 12px rgba(0,0,0,0.08); border-radius: 8px;',
      },
      grid: { left: 60, right: 20, top: 10, bottom: 25 },
      xAxis: {
        type: 'category',
        data: labels,
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: { color: '#94A3B8', fontSize: 11 }
      },
      yAxis: {
        type: 'value',
        axisLine: { show: false },
        axisTick: { show: false },
        splitLine: { lineStyle: { color: '#F1F5F9', type: 'dashed' } },
        axisLabel: { color: '#94A3B8', fontSize: 11 }
      },
      series: [{
        type: 'bar',
        data: counts,
        itemStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: '#7c3aed' },
            { offset: 1, color: '#ec4899' }
          ]),
          borderRadius: [4, 4, 0, 0]
        },
        barWidth: 28,
      }]
    })
  })
}

const renderPieChart = () => {
  nextTick(() => {
    if (!pieChartRef.value) return
    const models = costData.value.models || []
    if (!models.length) return

    if (!pieChart) {
      pieChart = echarts.init(pieChartRef.value)
    }

    const colors = ['#7c3aed', '#2563eb', '#059669', '#f59e0b', '#dc2626', '#06b6d4']
    const data = models.map((m, i) => ({
      name: m.model_name_cn || m.model,
      value: (m.prompt_tokens || 0) + (m.completion_tokens || 0),
      itemStyle: { color: colors[i % colors.length] }
    }))

    pieChart.setOption({
      tooltip: {
        trigger: 'item',
        backgroundColor: 'rgba(255, 255, 255, 0.96)',
        borderColor: '#E2E8F0',
        borderWidth: 1,
        textStyle: { color: '#334155', fontSize: 13 },
        formatter: (p) => `${p.name}<br/>Tokens: ${formatTokens(p.value)} (${p.percent}%)`
      },
      series: [{
        type: 'pie',
        radius: ['45%', '72%'],
        center: ['50%', '50%'],
        data,
        label: {
          fontSize: 11,
          color: '#475569',
          formatter: '{b}\n{d}%'
        },
        labelLine: { length: 12, length2: 8 },
        emphasis: {
          itemStyle: {
            shadowBlur: 10,
            shadowOffsetX: 0,
            shadowColor: 'rgba(0, 0, 0, 0.15)'
          }
        }
      }]
    })
  })
}

const handleResize = () => {
  trendChart?.resize()
  pieChart?.resize()
  durationChart?.resize()
}

onMounted(async () => {
  loading.value = true
  await Promise.all([fetchOverview(), fetchTrend(), fetchCost(), fetchModels(), fetchRecords()])
  loading.value = false
  renderPieChart()
  renderDurationChart()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  trendChart?.dispose()
  pieChart?.dispose()
  durationChart?.dispose()
})
</script>

<style scoped>
.llm-monitor-page {
  padding: 24px;
  max-width: 1400px;
}

.loading-wrap {
  padding: 40px 0;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
}

.page-header-left .page-title {
  font-size: 22px;
  font-weight: 600;
  color: #1e293b;
  margin: 0 0 4px;
}

.page-header-left .page-desc {
  font-size: 13px;
  color: #94a3b8;
  margin: 0;
}

.stat-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 20px;
}

.stat-card {
  background: var(--accent-light);
  border-radius: 12px;
  padding: 16px;
  display: flex;
  align-items: center;
  gap: 12px;
  position: relative;
  overflow: hidden;
  border: 1px solid rgba(0,0,0,0.04);
  transition: transform 0.2s, box-shadow 0.2s;
}

.stat-card::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 3px;
  background: var(--accent-grad);
}

.stat-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0,0,0,0.08);
}

.stat-icon-box {
  width: 44px;
  height: 44px;
  border-radius: 10px;
  background: var(--accent-light);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--accent);
  flex-shrink: 0;
}

.stat-body {
  flex: 1;
  min-width: 0;
}

.stat-label {
  font-size: 12px;
  color: #64748b;
  display: block;
  margin-bottom: 2px;
}

.stat-value {
  font-size: 22px;
  font-weight: 700;
  color: #1e293b;
  display: block;
  line-height: 1.2;
}

.stat-unit {
  font-size: 12px;
  font-weight: 400;
  color: #94a3b8;
  margin-left: 2px;
}

.stat-tags {
  margin-top: 4px;
}

.stat-tag {
  font-size: 11px;
  background: rgba(0,0,0,0.04);
  color: #64748b;
  padding: 1px 6px;
  border-radius: 4px;
  margin-right: 4px;
}

.stat-tag.tag-green { background: #ecfdf5; color: #059669; }
.stat-tag.tag-red { background: #fef2f2; color: #dc2626; }
.stat-tag.tag-orange { background: #fff7ed; color: #ea580c; }

/* 失败记录横幅 */
.failure-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: 10px;
  padding: 12px 16px;
  margin-bottom: 16px;
}

.failure-banner-left {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: #991b1b;
}

.failure-banner-left strong {
  color: #dc2626;
  font-weight: 700;
}

/* 趋势图 + 饼图/耗时分布 */
.chart-grid {
  display: grid;
  grid-template-columns: 1fr 340px;
  gap: 16px;
  margin-bottom: 20px;
}

.chart-side-stack {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.chart-card {
  background: #fff;
  border-radius: 12px;
  padding: 20px;
  border: 1px solid #e2e8f0;
}

.chart-container-sm {
  width: 100%;
  height: 180px;
}

.chart-header {
  margin-bottom: 16px;
}

.chart-header-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 4px;
}

.chart-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 4px;
}

.meta-label {
  color: #94a3b8;
}

.meta-value {
  color: #1e293b;
  font-weight: 600;
  font-family: monospace;
}

.meta-unit {
  color: #64748b;
  font-size: 11px;
}

.meta-divider {
  color: #e2e8f0;
}

.chart-title {
  font-size: 15px;
  font-weight: 600;
  color: #1e293b;
}

.chart-sub {
  font-size: 12px;
  color: #94a3b8;
}

.chart-container {
  width: 100%;
  height: 420px;
}

.bottom-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.card {
  background: #fff;
  border-radius: 12px;
  padding: 20px;
  border: 1px solid #e2e8f0;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.card-title {
  font-size: 15px;
  font-weight: 600;
  color: #1e293b;
}

.table-filters {
  display: flex;
  gap: 8px;
  align-items: center;
}

.model-badge {
  display: inline-block;
  background: #f1f5f9;
  color: #475569;
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 6px;
  font-weight: 500;
  font-family: monospace;
}

.type-badge {
  display: inline-block;
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 6px;
  font-weight: 500;
}

.type-scoring { background: #eff6ff; color: #2563eb; }
.type-analysis { background: #f5f3ff; color: #7c3aed; }
.type-report { background: #ecfdf5; color: #059669; }
.type-rectification_check { background: #fff7ed; color: #ea580c; }

.num {
  font-weight: 600;
  color: #1e293b;
  font-family: monospace;
}

.num-gray {
  color: #64748b;
  font-family: monospace;
  font-size: 12px;
}

.cost-summary {
  margin-top: 12px;
  padding: 12px 16px;
  background: #f8fafc;
  border-radius: 8px;
  font-size: 13px;
  color: #475569;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.cost-summary strong {
  color: #dc2626;
  font-size: 16px;
}

.cost-note {
  font-size: 11px;
  color: #94a3b8;
}

.pagination-wrap {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}

@media (max-width: 1200px) {
  .stat-grid { grid-template-columns: repeat(3, 1fr); }
  .chart-grid { grid-template-columns: 1fr; }
  .bottom-grid { grid-template-columns: 1fr; }
}

@media (max-width: 900px) {
  .stat-grid { grid-template-columns: repeat(2, 1fr); }
}
</style>
