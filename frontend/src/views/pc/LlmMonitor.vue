<template>
  <div class="llm-monitor-page dash-premium">
    <div v-if="loading" class="loading-wrap">
      <el-skeleton :rows="8" animated />
    </div>

    <template v-else>
      <!-- 页面标题 -->
      <div class="phdr phdr-dash"><div>
        <div class="eyebrow">AI Engine · 模型监控</div>
        <h1>模型<span class="g-text">监控台</span></h1>
        <div class="phdr-sub">5 个 Agent 的大模型调用量、效能与费用全览</div>
      </div>
      <div class="phdr-acts">
        <el-radio-group v-model="trendDays" size="default" @change="onDaysChange" class="range-pills">
          <el-radio-button value="7">近7天</el-radio-button>
          <el-radio-button value="30">近30天</el-radio-button>
          <el-radio-button value="90">近90天</el-radio-button>
        </el-radio-group>
        <el-date-picker v-if="trendDays === 'custom'" v-model="customDateRange" type="daterange"
          range-separator="至" start-placeholder="开始" end-placeholder="结束" size="default"
          style="width: 240px" @change="onCustomDateChange" />
      </div></div>

      <!-- KPI 指标卡片（玻璃横条） -->
      <div class="kstrip">
      <div class="kpi-row cols-5">
        <div class="kpi">
          <div class="kpi-lbl">本月调用（次）</div>
          <div class="kpi-num">{{ overview.month.calls || 0 }}</div>
          <div class="kpi-tags">
            <span v-if="callsChange !== null" :class="['kt', callsChange >= 0 ? 'kt-teal' : 'kt-err']">
              {{ callsChange >= 0 ? '↑' : '↓' }} {{ Math.abs(callsChange) }}%
            </span>
            <span class="kt kt-muted">今日 {{ overview.today.calls || 0 }} 次</span>
          </div>
        </div>
        <div class="kpi">
          <div class="kpi-lbl">本月 Tokens（tokens）</div>
          <div class="kpi-num">{{ formatTokens(overview.month.tokens || 0).replace(/([A-Z])$/, '') }}<span class="kpi-unit">{{ (overview.month.tokens || 0) >= 1000000 ? 'M' : (overview.month.tokens || 0) >= 1000 ? 'K' : '' }}</span></div>
          <div class="kpi-tags">
            <span v-if="tokensChange !== null" :class="['kt', tokensChange >= 0 ? 'kt-teal' : 'kt-err']">
              {{ tokensChange >= 0 ? '↑' : '↓' }} {{ Math.abs(tokensChange) }}%
            </span>
          </div>
        </div>
        <div class="kpi">
          <div class="kpi-lbl">本月平均耗时</div>
          <div class="kpi-num">{{ formatDuration(overview.month_avg_duration_ms || 0) }}</div>
        </div>
        <div class="kpi">
          <div class="kpi-lbl">本月成功率（%）</div>
          <div class="kpi-num">{{ overview.month_success_rate || 100 }}<span class="kpi-unit">%</span></div>
          <div class="kpi-tags">
            <span class="kt kt-ok">正常</span>
          </div>
        </div>
        <div class="kpi">
          <div class="kpi-lbl">本月费用估算（¥）</div>
          <div class="kpi-num">¥{{ costData.total_estimate || '0.00' }}</div>
          <div class="kpi-tags">
            <span class="kt kt-muted">基于公开定价</span>
          </div>
        </div>
      </div>
      </div><!-- /kstrip -->

      <!-- 失败记录提醒 -->
      <div class="failure-banner" v-if="failedRecordsCount > 0">
        <div class="failure-banner-left">
          <el-icon color="#c53a3f" :size="18"><WarningFilled /></el-icon>
          <span>近{{ trendDays }}天共有 <strong>{{ failedRecordsCount }}</strong> 次失败调用（失败率 {{ failedRate }}%）</span>
        </div>
        <el-button size="small" text type="danger" @click="showFailedOnly">
          查看失败记录
          <el-icon style="margin-left: 4px"><ArrowRight /></el-icon>
        </el-button>
      </div>

      <!-- 趋势图 -->
      <div class="card">
        <div class="card-h">
          <span class="card-t">调用量与成功率趋势</span>
          <span class="card-d">每日调用次数 / Token消耗 / 成功率 / 平均耗时</span>
        </div>
        <div ref="trendChartRef" class="chart-area"></div>
      </div>

      <!-- Token占比饼图 + 耗时分布 -->
      <div class="charts">
        <div class="card">
          <div class="card-h">
            <span class="card-t">Token 占比</span>
            <span class="card-d">按模型分布（{{ periodLabel }}）</span>
          </div>
          <div ref="pieChartRef" class="chart-area chart-area-sm"></div>
        </div>
        <div class="card">
          <div class="card-h">
            <span class="card-t">耗时分布</span>
            <span class="card-d">各耗时区间调用次数</span>
          </div>
          <div ref="durationChartRef" class="chart-area chart-area-sm"></div>
        </div>
      </div>

      <!-- 模型统计 + 调用类型统计 -->
      <div class="grid-2">
        <div class="card">
          <div class="card-h"><span class="card-t">模型统计</span><span class="card-d">{{ periodLabel }}</span></div>
          <el-table :data="overview.by_model" stripe size="small">
            <el-table-column prop="model" label="模型" min-width="130">
              <template #default="{ row }">
                <span class="model-dot on"></span>
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
            <el-table-column prop="avg_duration_ms" label="平均耗时" align="right" width="80">
              <template #default="{ row }">
                <span class="num-gray">{{ row.avg_duration_ms }}ms</span>
              </template>
            </el-table-column>
            <el-table-column prop="success_rate" label="成功率" align="center" width="75">
              <template #default="{ row }">
                <span :class="['sp', row.success_rate >= 99 ? 'sp-hi' : 'sp-mid']">{{ row.success_rate }}%</span>
              </template>
            </el-table-column>
          </el-table>
        </div>

        <div class="card">
          <div class="card-h"><span class="card-t">调用类型统计</span></div>
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
                <span :class="['sp', row.success_rate >= 99 ? 'sp-hi' : 'sp-mid']">{{ row.success_rate }}%</span>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </div>

      <!-- 模型费用明细 -->
      <div class="card">
        <div class="card-h">
          <span class="card-t">模型费用明细</span>
          <span class="card-d">{{ periodLabel }}</span>
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
              <span :class="['sp', row.success_rate >= 99 ? 'sp-hi' : 'sp-mid']">{{ row.success_rate }}%</span>
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
              <span class="num cost-total">¥{{ row.total_cost }}</span>
            </template>
          </el-table-column>
        </el-table>
        <div class="cost-summary">
          <span>估算总费用：<strong>¥{{ costData.total_estimate }}</strong></span>
          <span class="cost-note">* 基于各模型官方定价精准计算，DeepSeek三档计费（Cache Hit ¥0.0002/千 / Cache Miss ¥0.002/千 / Output ¥0.003/千）</span>
        </div>
      </div>

      <!-- 调用记录明细 -->
      <div class="card">
        <div class="card-h">
          <span class="card-t">调用记录明细</span>
          <span class="card-d">最近 API 调用详情</span>
        </div>
        <div style="padding: 14px 22px 0" v-if="records.length">
          <div class="term">
            <div v-for="(r, i) in records.slice(0, 4)" :key="i">
              <b>{{ (r.timestamp || '').slice(11, 19) }}</b> · {{ r.model_name }} · {{ formatTokens((r.prompt_tokens || 0) + (r.completion_tokens || 0)) }} tok
            </div>
          </div>
        </div>
        <div class="card-body">
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
                <span :class="['sp', row.success ? 'sp-hi' : 'sp-lo']">{{ row.success ? '成功' : '失败' }}</span>
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
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import echarts from '../../utils/echarts'
import { getLlmOverview, getLlmTrend, getLlmRecords, getLlmModels, getLlmCostEstimate, getLlmDurationDistribution } from '../../api/llm'

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

// 环比计算（后端可能返回字符串数字，统一 Number 化避免 NaN）
const callsChange = computed(() => {
  const cur = Number(overview.value.month?.calls) || 0
  const prev = Number(overview.value.last_month?.calls) || 0
  if (prev === 0) return null
  return Math.round((cur - prev) / prev * 1000) / 10
})

const tokensChange = computed(() => {
  const cur = Number(overview.value.month?.tokens) || 0
  const prev = Number(overview.value.last_month?.tokens) || 0
  if (prev === 0) return null
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
        borderColor: '#e4e4e9',
        borderWidth: 1,
        textStyle: { color: '#2c2c38', fontSize: 13 },
        extraCssText: 'box-shadow: 0 4px 12px rgba(0,0,0,0.08); border-radius: 8px;',
        formatter: (params) => {
          let html = `<div style="font-weight:600;margin-bottom:6px">${params[0].axisValue}</div>`
          params.forEach(p => {
            let val = p.value
            if (p.seriesName === '成功率') val = val + '%'
            else if (p.seriesName === '平均耗时') val = val + 'ms'
            else if (p.seriesName === 'Token消耗') val = formatTokens(val)
            html += `<div style="display:flex;align-items:center;gap:6px;margin:3px 0">
              ${p.marker}<span style="color:#474753">${p.seriesName}</span>
              <span style="margin-left:auto;font-weight:600;color:#2c2c38">${val}</span>
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
        textStyle: { color: '#474753', fontSize: 11 }
      },
      grid: { left: 56, right: 56, top: 44, bottom: 32 },
      xAxis: {
        type: 'category',
        data: dates,
        axisLine: { lineStyle: { color: '#e4e4e9' } },
        axisTick: { show: false },
        axisLabel: {
          color: '#a4a4af',
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
          splitLine: { lineStyle: { color: '#ececf0', type: 'dashed' } },
          axisLabel: { color: '#a4a4af', fontSize: 11, splitNumber: 5 }
        },
        {
          type: 'value',
          position: 'right',
          axisLine: { show: false },
          axisTick: { show: false },
          splitLine: { show: false },
          axisLabel: {
            color: '#a4a4af',
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
          itemStyle: { color: '#0f8a80', borderRadius: 12 },
          showBackground: true,
          backgroundStyle: { color: '#eef0f4', borderRadius: 12 },
          barMaxWidth: 26,
        },
        {
          name: 'Token消耗',
          type: 'line',
          yAxisIndex: 1,
          data: tokens,
          smooth: true,
          symbol: 'circle',
          symbolSize: 5,
          lineStyle: { color: '#35a398', width: 2.5 },
          itemStyle: { color: '#35a398', borderWidth: 2, borderColor: '#fff' },
          areaStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: 'rgba(53, 163, 152, 0.12)' },
              { offset: 1, color: 'rgba(53, 163, 152, 0)' }
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
          lineStyle: { color: '#b07a12', width: 1.5, type: [4, 3] },
          itemStyle: { color: '#b07a12' },
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
          lineStyle: { color: '#84848f', width: 1.5 },
          itemStyle: { color: '#84848f' },
          tooltip: { valueFormatter: (val) => val + 'ms' }
        }
      ]
    })
  })
}

const renderDurationChart = async () => {
  nextTick(async () => {
    if (!durationChartRef.value) return

    if (!durationChart) {
      durationChart = echarts.init(durationChartRef.value)
    }

    try {
      const res = await getLlmDurationDistribution(trendDays.value)
      const data = res.data || res
      const buckets = data.buckets || []

      const labels = buckets.map(b => b.label)
      const counts = buckets.map(b => b.count)

      durationChart.setOption({
        tooltip: {
          trigger: 'axis',
          backgroundColor: 'rgba(255, 255, 255, 0.96)',
          borderColor: '#e4e4e9',
          borderWidth: 1,
          textStyle: { color: '#2c2c38', fontSize: 13 },
          extraCssText: 'box-shadow: 0 4px 12px rgba(0,0,0,0.08); border-radius: 8px;',
        },
        grid: { left: 60, right: 20, top: 10, bottom: 25 },
        xAxis: {
          type: 'category',
          data: labels,
          axisLine: { show: false },
          axisTick: { show: false },
          axisLabel: { color: '#a4a4af', fontSize: 11 }
        },
        yAxis: {
          type: 'value',
          axisLine: { show: false },
          axisTick: { show: false },
          splitLine: { lineStyle: { color: '#ececf0', type: 'dashed' } },
          axisLabel: { color: '#a4a4af', fontSize: 11 }
        },
        series: [{
          type: 'bar',
          data: counts,
          itemStyle: { color: '#35a398', borderRadius: 12 },
          showBackground: true,
          backgroundStyle: { color: '#eef0f4', borderRadius: 12 },
          barWidth: 30,
        }]
      })
    } catch (e) {
      console.error('响应时长分布数据加载失败:', e)
    }
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

    const colors = ['#0f8a80', '#35a398', '#6fbcb2', '#0a6b62', '#a5d8d0', '#84848f']
    const data = models.map((m, i) => ({
      name: m.model_name_cn || m.model,
      value: (m.prompt_tokens || 0) + (m.completion_tokens || 0),
      itemStyle: { color: colors[i % colors.length] }
    }))

    pieChart.setOption({
      tooltip: {
        trigger: 'item',
        backgroundColor: 'rgba(255, 255, 255, 0.96)',
        borderColor: '#e4e4e9',
        borderWidth: 1,
        textStyle: { color: '#2c2c38', fontSize: 13 },
        formatter: (p) => `${p.name}<br/>Tokens: ${formatTokens(p.value)} (${p.percent}%)`
      },
      series: [{
        type: 'pie',
        radius: ['45%', '72%'],
        center: ['50%', '50%'],
        data,
        label: {
          fontSize: 11,
          color: '#2c2c38',
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
/* ── Page wrapper ── */
.llm-monitor-page {
  padding: 0;
  max-width: none;
}

.loading-wrap {
  padding: 40px 0;
}

/* ── Page header ── */

/* ── Filters ── */
.filters {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.radio-group {
  display: flex;
  gap: 2px;
  background: var(--bg-muted);
  border-radius: var(--r);
  padding: 3px;
}

/* ── KPI row ── */

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

/* ── Card ── */
.card {
  background: var(--bg-card);
  border: 1px solid var(--ink-100);
  border-radius: var(--r-lg);
  overflow: hidden;
  margin-bottom: 14px;
  animation: kpiIn 0.3s var(--ease) 0.05s both;
}

.card-h {
  padding: 14px 20px;
  border-bottom: 1px solid var(--ink-100);
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.card-t {
  font-size: 15px;
  font-weight: 700;
  color: var(--ink-900);
}

.card-d {
  font-size: 12px;
  color: var(--ink-400);
  margin-left: 8px;
}

.card-body {
  padding: 16px 20px;
}

/* ── Failure banner ── */
.failure-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: var(--err-bg);
  border: 1px solid var(--err-bg);
  border-radius: var(--r-lg);
  padding: 12px 16px;
  margin-bottom: 16px;
}

.failure-banner-left {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: var(--err);
}

.failure-banner-left strong {
  color: var(--err);
  font-weight: 800;
}

/* ── Chart areas ── */
.chart-area {
  width: 100%;
  height: 380px;
  padding: 0 4px;
}

.chart-area-sm {
  height: 240px;
}

.charts {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
  margin-bottom: 0;
}

.charts .card {
  animation-delay: 0.1s;
}

/* ── Grid 2-col ── */
.grid-2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
  margin-bottom: 0;
}

.grid-2 .card {
  animation-delay: 0.12s;
}

/* ── Table filters ── */
.table-filters {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-bottom: 12px;
}

/* ── Model dot ── */
.model-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  display: inline-block;
  margin-right: 4px;
}

.model-dot.on { background: var(--ok); }
.model-dot.off { background: var(--err); }
.model-dot.warn { background: var(--warn); }

/* ── Model badge ── */
.model-badge {
  display: inline-block;
  background: var(--ink-100);
  color: var(--ink-800);
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 6px;
  font-weight: 500;
  font-family: var(--mono);
}

/* ── Type badge ── */
.type-badge {
  display: inline-block;
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 6px;
  font-weight: 500;
}

.type-scoring { background: var(--blue-bg); color: var(--blue); }
.type-analysis { background: var(--bg-muted); color: var(--ink-600); }
.type-report { background: var(--ok-bg); color: var(--ok); }
.type-rectification_check { background: var(--orange-light); color: var(--orange); }

/* ── Score pill ── */
.sp {
  display: inline-block;
  min-width: 32px;
  padding: 2px 6px;
  border-radius: 3px;
  font-family: var(--mono);
  font-size: 13px;
  font-weight: 700;
  text-align: center;
}

.sp-hi { background: var(--ok-bg); color: var(--ok); }
.sp-mid { background: var(--warn-bg); color: var(--warn); }
.sp-lo { background: var(--err-bg); color: var(--err); }

/* ── Numbers ── */
.num {
  font-weight: 600;
  color: var(--ink-900);
  font-family: var(--mono);
}

.num-gray {
  color: var(--ink-600);
  font-family: var(--mono);
  font-size: 12px;
}

.cost-total {
  color: var(--err);
  font-weight: 700;
}

/* ── Cost summary ── */
.cost-summary {
  margin-top: 12px;
  padding: 12px 16px;
  background: var(--bg-muted);
  border-radius: 8px;
  font-size: 13px;
  color: var(--ink-800);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.cost-summary strong {
  color: var(--err);
  font-size: 16px;
}

.cost-note {
  font-size: 11px;
  color: var(--ink-400);
}

/* ── Pagination ── */
.pagination-wrap {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}

/* ── Animation ── */
@keyframes kpiIn {
  from { opacity: 0; transform: translateY(4px); }
  to { opacity: 1; transform: translateY(0); }
}

/* ── Responsive ── */
@media (max-width: 1200px) {
  .charts, .grid-2 { grid-template-columns: 1fr; }
}

@media (max-width: 900px) {
}

/* ===== REF-DASH 参考图仪表盘语法 ===== */
.phdr-dash {
  align-items: flex-end;
  margin-bottom: 26px;
}
.phdr-dash h1 {
  font-size: 30px;
  font-weight: 800;
  letter-spacing: -0.8px;
}
.phdr-dash .phdr-sub {
  font-size: 14px;
  margin-top: 6px;
}
.phdr-dash .phdr-acts {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 10px;
}

/* KPI：超大数字 + 细线分隔（无卡片） */
.llm-monitor-page .kpi-row {
  display: flex;
  background: transparent;
  gap: 0;
  margin-bottom: 24px;
}
.llm-monitor-page .kpi {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  border: none;
  border-left: 1px solid var(--ink-200);
  border-radius: 0;
  background: transparent;
  box-shadow: none;
  padding: 2px 0 2px 26px;
  animation: none;
}
.llm-monitor-page .kpi:first-child {
  border-left: none;
  padding-left: 0;
}
.llm-monitor-page .kpi-lbl { order: 2; font-size: 13px; margin-top: 8px; }
.llm-monitor-page .kpi-num { order: 1; font-size: 40px; letter-spacing: -1.2px; }
.llm-monitor-page .kpi-unit { font-size: 15px; }
.llm-monitor-page .kpi-tags { order: 3; margin-top: 8px; }

/* 磁贴 */
.llm-monitor-page .card {
  border-radius: 20px;
  border: 1px solid var(--ink-100);
  box-shadow: 0 1px 2px rgba(16, 40, 36, 0.04), 0 14px 36px -14px rgba(16, 40, 36, 0.10);
}
.llm-monitor-page .card-h { padding: 18px 22px 0; border-bottom: none; }
.llm-monitor-page .card-t { font-size: 16px; }
.llm-monitor-page .charts, .llm-monitor-page .grid-2 { gap: 18px; margin-bottom: 18px; }
.llm-monitor-page .chart-area { padding: 6px 14px 10px; }

</style>
