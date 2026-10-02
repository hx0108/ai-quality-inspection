<template>
  <div class="tasks-page">
    <!-- Page header -->
    <div class="phdr">
      <div>
        <h1>巡检任务</h1>
        <div class="phdr-sub">物业品质检查任务创建、分配与跟踪</div>
      </div>
      <div class="phdr-acts">
        <button class="btn" :disabled="total === 0" @click="openBatchExport">
          <svg viewBox="0 0 16 16"><path d="M8 2v8M5 7l3 3 3-3M3 12v2h10v-2"/></svg>导出
        </button>
        <button v-if="authStore.isAdmin" class="btn" @click="openBatchCreate">
          <svg viewBox="0 0 16 16"><path d="M5 3v10M11 3v10M2 6h4M10 6h4"/></svg>批量创建
        </button>
        <button v-if="authStore.isAdmin" class="btn" :disabled="selectedTaskIds.length === 0" @click="openBatchAssign">
          <svg viewBox="0 0 16 16"><path d="M8 3a2.5 2.5 0 100 5 2.5 2.5 0 000-5zM3 13c0-2.2 2.2-4 5-4s5 1.8 5 4"/></svg>批量分配{{ selectedTaskIds.length ? `（${selectedTaskIds.length}）` : '' }}
        </button>
        <button v-if="authStore.canManage" class="btn btn-primary" @click="openCreate">
          <svg viewBox="0 0 16 16"><path d="M8 3v10M3 8h10"/></svg>创建任务
        </button>
      </div>
    </div>

    <!-- Filters -->
    <div class="filters">
      <select class="f-sel" v-model="filters.project_id" @change="onSearch">
        <option :value="null">全部项目</option>
        <option v-for="p in projects" :key="p.id" :value="p.id">{{ p.name }}</option>
      </select>
      <select class="f-sel" v-model="filters.status" @change="onSearch">
        <option :value="null">全部状态</option>
        <option value="pending">待开始</option>
        <option value="in_progress">进行中</option>
        <option value="completed">已完成</option>
      </select>
      <button class="f-reset" @click="resetFilters">
        <svg viewBox="0 0 16 16"><path d="M3 3l10 10M13 3L3 13"/></svg>重置
      </button>
      <span v-if="selectedTaskIds.length" class="selection-count">已选 {{ selectedTaskIds.length }} 项</span>
    </div>

    <!-- Task table -->
    <div class="card">
      <table class="tbl">
        <thead>
          <tr>
            <th class="select-col">
              <input
                type="checkbox"
                class="task-checkbox"
                :checked="isCurrentPageAllSelected"
                :indeterminate="isCurrentPagePartlySelected"
                :disabled="currentPageSelectableIds.length === 0"
                aria-label="选择当前页全部任务"
                @change="toggleCurrentPage"
              />
            </th>
            <th>任务编号</th>
            <th>项目名称</th>
            <th>检查标准</th>
            <th>检查日期</th>
            <th>状态</th>
            <th>模块进度</th>
            <th>项目总分</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading">
            <td colspan="9" style="text-align:center;padding:40px;color:var(--ink-400)">加载中...</td>
          </tr>
          <tr v-else-if="tasks.length === 0">
            <td colspan="9" style="text-align:center;padding:40px;color:var(--ink-400)">暂无数据</td>
          </tr>
          <tr v-for="row in tasks" :key="row.task_id">
            <td class="select-col">
              <input
                type="checkbox"
                class="task-checkbox"
                :checked="isTaskSelected(row.task_id)"
                title="选择此任务"
                :aria-label="`选择任务 ${row.task_id}`"
                @change="toggleTask(row.task_id)"
              />
            </td>
            <td class="task-id-cell">{{ row.task_id }}</td>
            <td style="text-align:left;font-family:var(--sans);font-weight:600;color:var(--ink-900)">{{ row.project_name || '-' }}</td>
            <td>
              <span v-if="row.standard_type === 'diecheng'" class="kt kt-blue">蝶城</span>
              <span v-else-if="row.standard_type === 'lizhi'" class="kt kt-lizhi">砺质</span>
              <span v-else-if="row.standard_type === 'feidiecheng'" class="kt kt-warn">非蝶城</span>
              <span v-else class="kt kt-blue" :title="row.standard_type">{{ standardLabel(row.standard_type) }}</span>
            </td>
            <td>{{ row.check_date || '-' }}</td>
            <td><span class="st" :class="statusClass(row.status)">{{ statusText(row.status) }}</span></td>
            <td>
              <div class="prog-wrap">
                <div class="prog-bar"><div class="prog-fill" :style="{ width: Math.round((row.completed_modules || 0) / moduleTotal(row.standard_type) * 100) + '%' }"></div></div>
                <span class="prog-txt">{{ row.completed_modules || 0 }}/{{ moduleTotal(row.standard_type) }}</span>
              </div>
            </td>
            <td>
              <!-- 已有评分结果 -->
              <span v-if="row.total_score && row.total_score > 0"
                class="sp score-link"
                :class="scoreClass(row.total_score)"
                @click="viewScoring(row)"
              >{{ row.total_score.toFixed(1) }}</span>
              <!-- 已完成但评分中 -->
              <span v-else-if="scoringStatusMap[row.task_id] === 'scoring'" class="scoring-tag scoring" @click="viewScoring(row)">
                <el-icon class="is-loading"><Loading /></el-icon> 评分中
              </span>
              <!-- 已完成未评分 -->
              <span v-else-if="row.status === 'completed'" class="act" @click="viewScoring(row)">查看评分</span>
              <!-- 未完成 -->
              <span v-else style="font-family:var(--mono);font-size:13px;color:var(--ink-300)">—</span>
            </td>
            <td>
              <button v-if="authStore.canManage" class="act" @click="openAssign(row)">分配</button>
              <button class="act" @click="viewTask(row)">检查</button>
              <button v-if="authStore.isAdmin && row.status === 'completed'" class="act act-warn" @click="onRunPipeline(row)">重新执行</button>
              <button v-if="authStore.isAdmin" class="act act-err" @click="onDelete(row)">删除</button>
            </td>
          </tr>
        </tbody>
      </table>
      <div class="pagi">
        <div class="pagi-info">共 <b>{{ total }}</b> 条</div>
        <div class="pagi-btns">
          <button class="pg" :disabled="page <= 1" @click="goPage(page - 1)"><svg viewBox="0 0 16 16"><path d="M10 3L5 8l5 5"/></svg></button>
          <button v-for="p in pageNumbers" :key="p" class="pg" :class="{ on: p === page }" @click="goPage(p)">{{ p }}</button>
          <button class="pg" :disabled="page >= totalPages" @click="goPage(page + 1)"><svg viewBox="0 0 16 16"><path d="M6 3l5 5-5 5"/></svg></button>
        </div>
      </div>
    </div>

    <!-- 批量导出评分结果 -->
    <el-dialog v-model="showBatchExport" title="导出AI评分结果" width="520px" class="styled-dialog">
      <el-radio-group v-model="batchExportScope" class="batch-export-options">
        <el-radio value="selected" :disabled="selectedTaskIds.length === 0">
          导出已选任务（{{ selectedTaskIds.length }}项）
        </el-radio>
        <el-radio value="filtered">
          导出当前筛选全部（共{{ total }}项，跨全部分页）
        </el-radio>
      </el-radio-group>
      <el-alert
        title="仅导出已有AI评分结果的任务；未评分任务会自动跳过并在完成后提示数量。"
        type="info"
        :closable="false"
        show-icon
      />
      <template #footer>
        <el-button @click="showBatchExport = false">取消</el-button>
        <el-button type="primary" :loading="exportingBatch" @click="onBatchExport">确认导出</el-button>
      </template>
    </el-dialog>

    <!-- 创建任务弹窗 -->
    <el-dialog v-model="showCreate" title="创建检查任务" width="500px" class="styled-dialog">
      <el-form :model="newTask" label-width="100px" class="styled-form">
        <el-form-item label="项目名称" required>
          <el-select v-model="newTask.project_id" placeholder="选择项目" style="width: 100%">
            <el-option v-for="p in projects" :key="p.id" :label="p.name" :value="p.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="检查标准" required>
          <el-select v-model="newTask.standard_type" placeholder="选择检查标准" style="width: 100%">
            <el-option v-for="s in standardTypes" :key="s.value" :label="s.label" :value="s.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="检查日期" required>
          <el-date-picker v-model="newTask.check_date" type="date" placeholder="选择日期"
            value-format="YYYY-MM-DD" style="width: 100%" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreate = false">取消</el-button>
        <el-button type="primary" @click="onCreateTask" :loading="creating">创建</el-button>
      </template>
    </el-dialog>

    <!-- 批量创建任务弹窗 -->
    <el-dialog v-model="showBatchCreate" title="批量创建检查任务" width="520px" class="styled-dialog">
      <el-form :model="batchTask" label-width="100px" class="styled-form">
        <el-form-item label="项目名称" required>
          <el-select v-model="batchTask.project_ids" multiple filterable placeholder="选择项目（可多选）" style="width: 100%">
            <el-option v-for="p in projects" :key="p.id" :label="p.name" :value="p.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="检查标准" required>
          <el-select v-model="batchTask.standard_type" placeholder="选择检查标准" style="width: 100%">
            <el-option v-for="s in standardTypes" :key="s.value" :label="s.label" :value="s.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="检查日期" required>
          <el-date-picker v-model="batchTask.check_date" type="date" placeholder="选择日期"
            value-format="YYYY-MM-DD" style="width: 100%" />
        </el-form-item>
      </el-form>
      <el-alert
        title="为所选的每个项目各创建一个任务；项目当日同标准已有任务时自动跳过，不会重复创建。"
        type="info"
        :closable="false"
        show-icon
      />
      <template #footer>
        <el-button @click="showBatchCreate = false">取消</el-button>
        <el-button type="primary" @click="onBatchCreateTask" :loading="batchCreating">批量创建</el-button>
      </template>
    </el-dialog>

    <!-- 批量分配弹窗 -->
    <el-dialog v-model="showBatchAssign" title="批量分配检查员" width="700px" class="styled-dialog">
      <el-alert
        :title="`将把下面的分配方案应用到已选的 ${selectedTaskIds.length} 个任务；已有分配记录的任务会自动跳过。`"
        type="info"
        :closable="false"
        show-icon
        style="margin-bottom: 12px"
      />
      <el-table :data="batchAssignModules" border class="styled-table">
        <el-table-column prop="name" label="检查模块" width="150" />
        <el-table-column label="检查员" min-width="200">
          <template #default="{ row }">
            <el-select v-model="row.inspector_id" placeholder="选择检查员（留空则不分配该模块）" clearable style="width: 100%">
              <el-option v-for="u in inspectors" :key="u.id" :label="`${u.real_name} (${u.role === 'site_supervisor' ? '阵地督导' : u.role === 'field_supervisor' ? '驻场经理' : '检查员'})`" :value="u.id" />
            </el-select>
          </template>
        </el-table-column>
      </el-table>
      <template #footer>
        <el-button @click="showBatchAssign = false">取消</el-button>
        <el-button type="primary" @click="onBatchAssign" :loading="batchAssigning">保存分配</el-button>
      </template>
    </el-dialog>

    <!-- 分配模块弹窗 -->
    <el-dialog v-model="showAssign" title="模块分配" width="700px" class="styled-dialog">
      <el-table :data="moduleList" border class="styled-table">
        <el-table-column prop="name" label="检查模块" width="150" />
        <el-table-column label="检查员" min-width="200">
          <template #default="{ row }">
            <el-select v-model="row.inspector_id" placeholder="选择检查员" clearable style="width: 100%">
              <el-option v-for="u in inspectors" :key="u.id" :label="`${u.real_name} (${u.role === 'site_supervisor' ? '阵地督导' : u.role === 'field_supervisor' ? '驻场经理' : '检查员'})`" :value="u.id" />
            </el-select>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag v-if="row.inspector_id" type="success">已分配</el-tag>
            <el-tag v-else type="info">待分配</el-tag>
          </template>
        </el-table-column>
      </el-table>
      <template #footer>
        <el-button @click="showAssign = false">关闭</el-button>
        <el-button type="primary" @click="saveAssignments" :loading="savingAssign">保存分配</el-button>
      </template>
    </el-dialog>

    <!-- AI评分结果弹窗 -->
    <el-dialog v-model="showScoring" title="AI 评分结果" width="950px" top="5vh" destroy-on-close class="scoring-dialog">
      <!-- 评分中 -->
      <div v-if="dialogState === 'scoring'" class="scoring-progress-area">
        <div class="scoring-progress-header">
          <div class="scoring-pulse"></div>
          <el-icon class="is-loading" :size="28" color="var(--blue)"><Loading /></el-icon>
          <span>AI 正在评分中...</span>
        </div>
        <el-progress :percentage="scoringPct" :stroke-width="16" :text-inside="true" style="margin: 20px 0" />
        <p class="scoring-detail">已完成 {{ scoringDone }}/{{ scoringTotal }} 个模块</p>
        <p v-if="scoringCurrent" class="scoring-current">正在评分：{{ scoringCurrent }}</p>
        <p class="scoring-tip">每个模块约10-15秒，支持并发评分（最多4个模块同时评分）</p>
      </div>

      <!-- 评分结果 -->
      <div v-else-if="dialogState === 'done'" class="scoring-result">
        <!-- 总分区域 -->
        <div class="score-header">
          <div class="total-score">
            <span class="score-label">项目总分</span>
            <span class="score-value">{{ scoringData.total_score.toFixed(2) }}</span>
            <span class="score-unit">/ 100</span>
          </div>
          <div class="score-meta">
            <span>评分模型：Qwen-plus</span>
          </div>
        </div>

        <!-- 模块折叠面板 -->
        <el-collapse v-model="expandedModules" class="module-collapse" @change="onCollapseChange">
          <el-collapse-item
            v-for="mod in scoringData.modules"
            :key="mod.module_name"
            :name="mod.module_name"
          >
            <template #title>
              <div class="module-title">
                <span class="module-name">{{ mod.module_name }}</span>
                <span class="module-score" :class="getScoreClass(mod.module_pct_score)">
                  {{ mod.module_pct_score.toFixed(2) }} 分
                </span>
                <el-tag size="small" type="info" style="margin-left: 8px">
                  权重 {{ (mod.weight_ratio * 100).toFixed(0) }}%
                </el-tag>
                <span class="module-items-count">{{ mod.items_count || (mod.items ? mod.items.length : 0) }} 项</span>
                <el-button
                  size="small"
                  type="warning"
                  link
                  style="margin-left: 12px"
                  @click.stop="onRescoreModule(mod.module_name)"
                >
                  重新评分
                </el-button>
                <el-button
                  v-if="authStore.isAdmin"
                  size="small"
                  type="danger"
                  link
                  style="margin-left: 8px"
                  @click.stop="onRecallModule(mod)"
                >
                  退回重填
                </el-button>
                <span v-if="isModuleLoading(mod.module_name)" class="module-loading-hint">
                  <el-icon class="is-loading"><Loading /></el-icon> 加载中...
                </span>
              </div>
            </template>

            <!-- 加载中状态 -->
            <div v-if="isModuleLoading(mod.module_name)" class="module-loading-area">
              <el-icon class="is-loading" :size="20" color="var(--blue)"><Loading /></el-icon>
              <span>正在加载检查项详情...</span>
            </div>

            <!-- 检查项明细表格 -->
            <el-table v-else :data="mod.items || []" border size="small" :row-class-name="itemRowClass">
              <el-table-column prop="item_name" label="检查项" min-width="160" />
              <el-table-column label="检查标准" min-width="180">
                <template #default="{ row }">
                  <span class="cell-text">{{ row.check_standard || '—' }}</span>
                </template>
              </el-table-column>
              <el-table-column label="检查方法" min-width="140">
                <template #default="{ row }">
                  <span class="cell-text">{{ row.check_method || '—' }}</span>
                </template>
              </el-table-column>
              <el-table-column label="评分规则" min-width="120">
                <template #default="{ row }">
                  <span class="cell-text">{{ row.scoring_rule || '—' }}</span>
                </template>
              </el-table-column>
              <el-table-column label="权重" width="80" align="center">
                <template #default="{ row }">
                  <span>{{ Number(row.weight).toFixed(4) }}</span>
                </template>
              </el-table-column>
              <el-table-column label="得分" width="120" align="center">
                <template #default="{ row }">
                  <span v-if="row.is_skipped" class="text-muted">已跳过</span>
                  <span v-else class="editable-score" :class="getItemScoreClass(row.score)" @click="openEditDialog(row, mod)">
                    {{ Number(row.score).toFixed(2) }}
                    <template v-if="scoringData.standard_type !== 'lizhi'"> / 5</template>
                    <template v-else-if="mod.role !== 'deduction'"> / {{ Number(row.max_score ?? mod.max_score).toFixed(2) }}</template>
                    <el-icon v-if="row.is_edited" size="12" color="var(--blue)"><Edit /></el-icon>
                  </span>
                  <el-tag v-if="row.is_fallback" type="warning" size="small" effect="dark" style="margin-left:4px">降级</el-tag>
                </template>
              </el-table-column>
              <el-table-column label="置信度" width="90" align="center">
                <template #default="{ row }">
                  <template v-if="row.is_skipped"><span class="text-muted">—</span></template>
                  <template v-else-if="row.confidence_score != null && row.confidence_score > 0">
                    <el-tag :type="row.confidence_score >= 0.85 ? 'success' : row.confidence_score >= 0.6 ? 'warning' : 'danger'" size="small">
                      {{ row.confidence_score }}
                    </el-tag>
                  </template>
                  <template v-else><span class="text-muted">—</span></template>
                </template>
              </el-table-column>
              <el-table-column label="评分依据" min-width="180">
                <template #default="{ row }">
                  <span v-if="row.is_skipped" class="text-muted">—</span>
                  <el-tooltip v-else :content="row.scoring_basis || '—'" placement="top" :disabled="!row.scoring_basis || row.scoring_basis.length < 30">
                    <span class="cell-text">{{ row.scoring_basis || '—' }}</span>
                  </el-tooltip>
                </template>
              </el-table-column>
              <el-table-column label="问题点" min-width="200">
                <template #default="{ row }">
                  <template v-if="row.is_skipped"><span class="text-muted">—</span></template>
                  <template v-else-if="row.issues && row.issues.length > 0">
                    <div v-for="issue in row.issues" :key="issue.issue_id" class="issue-cell">
                      <el-tag size="small" :type="issue.severity === '严重' ? 'danger' : issue.severity === '轻微' ? 'info' : 'warning'" style="margin-right: 4px;">
                        {{ issue.severity }}
                      </el-tag>
                      <span>{{ issue.description }}</span>
                      <div v-if="issue.photos && issue.photos.length > 0" class="issue-photos-pc">
                        <el-image
                          v-for="photo in issue.photos"
                          :key="photo.photo_id"
                          :src="`/api/v1/records/photos/${photo.photo_id}?token=${authToken}`"
                          :preview-src-list="issue.photos.map(p => `/api/v1/records/photos/${p.photo_id}?token=${authToken}`)"
                          fit="cover"
                          class="issue-photo-pc"
                        />
                      </div>
                    </div>
                  </template>
                  <template v-else><span class="text-muted">无</span></template>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="120" align="center">
                <template #default="{ row }">
                  <el-button v-if="!row.is_skipped" size="small" type="primary" link @click="openEditDialog(row, mod)">
                    编辑
                  </el-button>
                  <el-button v-if="authStore.isAdmin && !row.is_skipped" size="small" type="danger" link @click.stop="onRecallItem(mod, row)">
                    退回
                  </el-button>
                </template>
              </el-table-column>
            </el-table>
          </el-collapse-item>
        </el-collapse>
      </div>

      <!-- 无数据 -->
      <el-empty v-else-if="dialogState === 'empty'" description="暂无评分数据，请确认AI评分已完成" />

      <template #footer>
        <el-button @click="showScoring = false">关闭</el-button>
        <el-button v-if="dialogState === 'done'" type="success" @click="onExportExcel" :loading="exportingExcel">
          导出Excel
        </el-button>
      </template>
    </el-dialog>

    <!-- 编辑评分弹窗 -->
    <el-dialog v-model="showEditScoreDialog" title="修改评分" width="500px" class="styled-dialog">
      <el-form :model="editForm" label-width="90px">
        <el-form-item label="检查项">
          <span>{{ editForm.item_name }}</span>
        </el-form-item>
        <el-form-item :label="editScoreLabel">
          <el-input-number v-model="editForm.score" :min="editScoreMin" :max="editScoreMax" :step="0.5" :precision="1" />
        </el-form-item>
        <el-form-item label="评分依据">
          <el-input v-model="editForm.scoring_basis" type="textarea" :rows="3" />
        </el-form-item>
        <el-form-item label="修改原因">
          <el-select v-model="editForm.edit_reason" clearable placeholder="选择修改原因（可选）">
            <el-option label="AI评分过高" value="ai_score_too_high" />
            <el-option label="AI评分过低" value="ai_score_too_low" />
            <el-option label="问题已现场整改" value="fixed_on_site" />
            <el-option label="检查记录有误" value="inspection_error" />
            <el-option label="特殊情况" value="special_circumstance" />
            <el-option label="其他" value="other" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showEditScoreDialog = false">取消</el-button>
        <el-button type="primary" @click="onSaveEditScore" :loading="savingEditScore">保存</el-button>
      </template>
    </el-dialog>

    <!-- 一键执行完整流程弹窗 -->
    <el-dialog v-model="showPipeline" title="执行完整流程" width="600px" class="styled-dialog" :close-on-click-modal="false">
      <!-- 执行中 -->
      <div v-if="pipelineState === 'running'" class="pipeline-progress">
        <div class="pipeline-header">
          <el-icon class="is-loading" :size="32" color="var(--blue)"><Loading /></el-icon>
          <span class="pipeline-title">AI 正在执行中...</span>
        </div>
        <el-progress :percentage="pipelinePct" :stroke-width="20" :text-inside="true" style="margin: 24px 0" />
        <div class="pipeline-steps">
          <div class="pipeline-step" :class="{ active: pipelineStep === 'scoring', done: ['report', 'rectification', 'done'].includes(pipelineStep) }">
            <el-icon v-if="['report', 'rectification', 'done'].includes(pipelineStep)"><Select /></el-icon>
            <el-icon v-else-if="pipelineStep === 'scoring'" class="is-loading"><Loading /></el-icon>
            <span v-else><CircleCheck /></span>
            <span>AI评分</span>
          </div>
          <div class="pipeline-step-line"></div>
          <div class="pipeline-step" :class="{ active: pipelineStep === 'report', done: ['rectification', 'done'].includes(pipelineStep) }">
            <el-icon v-if="['rectification', 'done'].includes(pipelineStep)"><Select /></el-icon>
            <el-icon v-else-if="pipelineStep === 'report'" class="is-loading"><Loading /></el-icon>
            <span v-else><CircleCheck /></span>
            <span>生成报告</span>
          </div>
          <div class="pipeline-step-line"></div>
          <div class="pipeline-step" :class="{ active: pipelineStep === 'rectification', done: pipelineStep === 'done' }">
            <el-icon v-if="pipelineStep === 'done'"><Select /></el-icon>
            <el-icon v-else-if="pipelineStep === 'rectification'" class="is-loading"><Loading /></el-icon>
            <span v-else><CircleCheck /></span>
            <span>整改追踪</span>
          </div>
        </div>
        <p class="pipeline-tip">预计耗时 30-60 秒，请勿关闭页面</p>
      </div>

      <!-- 执行完成 -->
      <div v-else-if="pipelineState === 'completed'" class="pipeline-result">
        <div class="pipeline-success">
          <el-icon :size="48" color="var(--ok)"><SuccessFilled /></el-icon>
          <span class="pipeline-success-text">执行完成！</span>
        </div>
        <div class="pipeline-summary">
          <div class="summary-item">
            <span class="summary-label">项目总分</span>
            <span class="summary-value" :class="getScoreClass(pipelineData?.scoring?.total_score)">
              {{ pipelineData?.scoring?.total_score?.toFixed(2) || '-' }}
            </span>
          </div>
          <div class="summary-item">
            <span class="summary-label">报告ID</span>
            <span class="summary-value">{{ pipelineData?.report?.report_id || '-' }}</span>
          </div>
          <div class="summary-item">
            <span class="summary-label">待整改</span>
            <span class="summary-value">{{ pipelineData?.rectification?.pending_count || 0 }} 项</span>
          </div>
          <div class="summary-item">
            <span class="summary-label">已完成整改</span>
            <span class="summary-value">{{ pipelineData?.rectification?.completed_count || 0 }} 项</span>
          </div>
        </div>
        <p class="pipeline-duration">总耗时：{{ pipelineData?.duration_seconds?.toFixed(1) || 0 }} 秒</p>
      </div>

      <!-- 执行失败 -->
      <div v-else-if="pipelineState === 'failed'" class="pipeline-error">
        <el-icon :size="48" color="var(--err)"><CircleCloseFilled /></el-icon>
        <span class="pipeline-error-text">执行失败</span>
        <p class="pipeline-error-detail">{{ pipelineError }}</p>
      </div>

      <template #footer>
        <el-button v-if="pipelineState === 'completed'" type="primary" @click="onViewReport">查看报告</el-button>
        <el-button v-if="pipelineState === 'completed'" @click="onViewScoring">查看评分</el-button>
        <el-button v-if="pipelineState === 'failed'" type="primary" @click="onRetryPipeline">重试</el-button>
        <el-button @click="showPipeline = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Loading, Plus, RefreshLeft, User, View, Delete, CaretRight, Select, CircleCheck, SuccessFilled, CircleCloseFilled } from '@element-plus/icons-vue'
import { getTasks, getTaskDetail, createTask, createTaskBatch, createTaskAssignBatch, getAssignments, assignModule, getAllProjects, getUsers } from '../../api/pc'
import { getScoringResults, getScoringStatus, startScoring, editScore, rescoreModule, exportScoringExcel, exportBatchScoringExcel, getScoringSummary, getModuleDetail } from '../../api/scoring'
import { recallModule, recallItem } from '../../api/inspection'
import { runFullPipeline, getPipelineStatus } from '../../api/orchestrator'
import { getStandardList } from '../../api/standards'
import { useAuthStore } from '../../stores/auth'
import request from '../../utils/request'
import { getAuthToken } from '../../utils/authStorage'

const router = useRouter()
const authStore = useAuthStore()
const authToken = computed(() => getAuthToken())
const tasks = ref([])
const projects = ref([])
const inspectors = ref([])
const loading = ref(false)
const total = ref(0)
const page = ref(1)
const filters = ref({ project_id: authStore.activeProjectId || null, status: null })
const selectedTaskIds = ref([])
const selectedTaskIdSet = computed(() => new Set(selectedTaskIds.value))
const currentPageSelectableIds = computed(() => tasks.value.map(task => task.task_id))
const isCurrentPageAllSelected = computed(() => (
  currentPageSelectableIds.value.length > 0
  && currentPageSelectableIds.value.every(taskId => selectedTaskIdSet.value.has(taskId))
))
const isCurrentPagePartlySelected = computed(() => {
  const selectedCount = currentPageSelectableIds.value.filter(taskId => selectedTaskIdSet.value.has(taskId)).length
  return selectedCount > 0 && selectedCount < currentPageSelectableIds.value.length
})

const showBatchExport = ref(false)
const batchExportScope = ref('filtered')
const exportingBatch = ref(false)

const showCreate = ref(false)
const creating = ref(false)
const standardTypes = ref([])
const newTask = ref({ project_id: null, check_date: '', standard_type: 'diecheng' })

const showBatchCreate = ref(false)
const batchCreating = ref(false)
const batchTask = ref({ project_ids: [], check_date: '', standard_type: 'diecheng' })

const showBatchAssign = ref(false)
const batchAssigning = ref(false)
const batchAssignModules = ref([])

const showAssign = ref(false)
const currentTaskId = ref('')
const moduleList = ref([])
const savingAssign = ref(false)

const MODULE_NAMES = ['客户服务', '安全管理', 'EHS及风险管理', '环境管理', '机电运维', '设施维护', '综合管理', '财务管理']  // 蝶城默认（用于任务创建时选择标准前的占位）

// ===== 评分状态追踪 =====
const scoringStatusMap = ref({})   // { task_id: 'scoring' | 'completed' | null }
const scoringResultsCache = ref({}) // { task_id: scoringData } — 完整数据缓存
const moduleDetailCache = ref({})   // { task_id: { module_name: items[] } } — 模块详情缓存
const moduleLoadingMap = ref({})    // { task_id: { module_name: true/false } } — 模块加载状态
let statusPollingTimer = null

const fetchTasks = async () => {
  loading.value = true
  try {
    const res = await getTasks({ page: page.value, page_size: 20, ...filters.value })
    tasks.value = res.items || []
    total.value = res.total || 0
    // 对已完成的任务检查评分状态
    checkScoringForCompleted()
  } catch (e) {
    ElMessage.error('获取任务列表失败')
  } finally {
    loading.value = false
  }
}

// 检查已完成任务的评分状态
const checkScoringForCompleted = async () => {
  const completed = tasks.value.filter(t => t.status === 'completed' && (!t.total_score || t.total_score === 0))
  for (const t of completed) {
    try {
      const res = await getScoringStatus(t.task_id)
      if (res.is_complete) {
        scoringStatusMap.value[t.task_id] = 'completed'
        // 用摘要接口更新总分（轻量）
        try {
          const summary = await getScoringSummary(t.task_id)
          t.total_score = summary.total_score || 0
        } catch (e) { /* ignore */ }
      } else if (res.scored_modules > 0 || res.total_modules > 0) {
        scoringStatusMap.value[t.task_id] = 'scoring'
      }
    } catch (e) { /* not started */ }
  }
  // 如果有评分中的任务，启动轮询
  startStatusPolling()
}

// 轮询评分状态（更新表格中的状态）
// 动态轮询：快速反馈 → 逐渐放缓
let statusPollingCount = 0
const startStatusPolling = () => {
  if (statusPollingTimer) return
  const hasScoring = Object.values(scoringStatusMap.value).some(s => s === 'scoring')
  if (!hasScoring) return

  statusPollingCount = 0
  const doPoll = async () => {
    let anyScoring = false
    for (const [taskId, status] of Object.entries(scoringStatusMap.value)) {
      if (status !== 'scoring') continue
      try {
        const res = await getScoringStatus(taskId)
        if (res.is_complete) {
          scoringStatusMap.value[taskId] = 'completed'
          const task = tasks.value.find(t => t.task_id === taskId)
          if (task) {
            try {
              const summary = await getScoringSummary(taskId)
              task.total_score = summary.total_score || 0
            } catch (e) { /* ignore */ }
          }
        } else {
          anyScoring = true
        }
      } catch (e) { /* ignore */ }
    }
    if (!anyScoring) {
      clearTimeout(statusPollingTimer)
      statusPollingTimer = null
      return
    }
    // 动态间隔：前5次1秒，之后逐渐增加到5秒
    statusPollingCount++
    const interval = statusPollingCount <= 5 ? 1000 : Math.min(5000, 1000 + (statusPollingCount - 5) * 1000)
    statusPollingTimer = setTimeout(doPoll, interval)
  }
  statusPollingTimer = setTimeout(doPoll, 1000)
}

const fetchProjects = async () => {
  try {
    const res = await getAllProjects()
    projects.value = res.items || []
  } catch (e) { /* ignore */ }
}

const fetchInspectors = async () => {
  try {
    // 获取检查员、阵地督导、驻场经理（都可以被分配模块）
    const [inspRes, svRes, fsRes] = await Promise.all([
      getUsers({ page: 1, page_size: 100, role: 'inspector' }),
      getUsers({ page: 1, page_size: 100, role: 'site_supervisor' }),
      getUsers({ page: 1, page_size: 100, role: 'field_supervisor' })
    ])
    inspectors.value = [
      ...(inspRes.items || []),
      ...(svRes.items || []),
      ...(fsRes.items || [])
    ]
  } catch (e) { /* ignore */ }
}

const fetchStandardTypes = async () => {
  try {
    const res = await getStandardList()
    standardTypes.value = (res.items || []).map(s => ({
      value: s.standard_type,
      label: s.label,
      module_count: s.module_count,
    }))
    // 模块数映射（进度条分母），兜底内置标准
    stdModuleCounts.value = Object.fromEntries(standardTypes.value.map(s => [s.value, s.module_count || 8]))
  } catch (e) {
    standardTypes.value = [
      { value: 'diecheng', label: '蝶城版', module_count: 8 },
      { value: 'feidiecheng', label: '非蝶城版', module_count: 8 },
      { value: 'lizhi', label: '砺质版', module_count: 5 }
    ]
  }
}
const stdModuleCounts = ref({ 'diecheng': 8, 'feidiecheng': 8, 'lizhi': 5 })

// 检查标准显示名（自定义标准取导入时的名称）
const standardLabel = (std) => {
  const hit = standardTypes.value.find(s => s.value === std)
  return hit ? hit.label : std
}

const clearTaskSelection = () => { selectedTaskIds.value = [] }
const onSearch = () => { clearTaskSelection(); page.value = 1; fetchTasks() }
const resetFilters = () => { filters.value = { project_id: null, status: null }; onSearch() }

const isTaskSelected = (taskId) => selectedTaskIdSet.value.has(taskId)

const toggleTask = (taskId) => {
  const next = new Set(selectedTaskIds.value)
  if (next.has(taskId)) next.delete(taskId)
  else next.add(taskId)
  selectedTaskIds.value = Array.from(next)
}

const toggleCurrentPage = (event) => {
  const next = new Set(selectedTaskIds.value)
  currentPageSelectableIds.value.forEach(taskId => {
    if (event.target.checked) next.add(taskId)
    else next.delete(taskId)
  })
  selectedTaskIds.value = Array.from(next)
}

const openBatchExport = () => {
  batchExportScope.value = selectedTaskIds.value.length > 0 ? 'selected' : 'filtered'
  showBatchExport.value = true
}

const onBatchExport = async () => {
  if (batchExportScope.value === 'selected' && selectedTaskIds.value.length === 0) {
    ElMessage.warning('请至少选择一个已有AI评分的任务')
    return
  }
  exportingBatch.value = true
  try {
    const payload = batchExportScope.value === 'selected'
      ? { scope: 'selected', task_ids: selectedTaskIds.value }
      : {
          scope: 'filtered',
          project_id: filters.value.project_id || null,
          status: filters.value.status || null
        }
    const result = await exportBatchScoringExcel(payload)
    const url = window.URL.createObjectURL(result.blob)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = result.filename
    document.body.appendChild(anchor)
    anchor.click()
    document.body.removeChild(anchor)
    window.URL.revokeObjectURL(url)

    const skippedText = result.skippedCount > 0 ? `，跳过未评分任务${result.skippedCount}项` : ''
    ElMessage.success(`已导出${result.exportedCount}项${skippedText}`)
    if (batchExportScope.value === 'selected') clearTaskSelection()
    showBatchExport.value = false
  } catch (error) {
    ElMessage.error(error.message || '批量导出失败')
  } finally {
    exportingBatch.value = false
  }
}

const statusType = (s) => ({ pending: 'info', in_progress: 'warning', completed: 'success' }[s] || 'info')
const statusText = (s) => ({ pending: '待开始', in_progress: '进行中', completed: '已完成' }[s] || s)
// 各检查标准的模块总数（蝶城/非蝶城=8，砺质=5），用于进度条分母
const moduleTotal = (std) => stdModuleCounts.value[std] || 8

const openCreate = () => {
  newTask.value = { project_id: null, check_date: '', standard_type: 'diecheng' }
  showCreate.value = true
}

const openBatchCreate = () => {
  batchTask.value = { project_ids: [], check_date: '', standard_type: 'diecheng' }
  showBatchCreate.value = true
}

const openBatchAssign = async () => {
  if (!selectedTaskIds.value.length) {
    ElMessage.warning('请先勾选要分配的任务')
    return
  }
  try {
    // 模块清单取自第一个选中任务（按其检查标准）；跨页混选其他标准的任务由后端分项校验兜底
    const detail = await getTaskDetail(selectedTaskIds.value[0])
    batchAssignModules.value = (detail.modules || []).map(m => ({ name: m.module_name, inspector_id: null }))
    if (!batchAssignModules.value.length) {
      ElMessage.warning('未能获取模块清单，请稍后重试')
      return
    }
  } catch (e) {
    ElMessage.error('获取模块清单失败')
    return
  }
  showBatchAssign.value = true
}

const onBatchAssign = async () => {
  const assignments = batchAssignModules.value
    .filter(m => m.inspector_id)
    .map(m => ({ module_name: m.name, inspector_id: m.inspector_id }))
  if (!assignments.length) {
    ElMessage.warning('请至少为一个模块选择检查员')
    return
  }
  batchAssigning.value = true
  try {
    const result = await createTaskAssignBatch({ task_ids: selectedTaskIds.value, assignments })
    const parts = [`成功分配 ${result.assigned_count} 个任务`]
    if (result.skipped_count > 0) parts.push(`跳过 ${result.skipped_count} 个（已有分配记录）`)
    if (result.failed_count > 0) {
      const reasons = [...new Set(result.failed.map(f => f.reason))].join('；')
      parts.push(`失败 ${result.failed_count} 个（${reasons}）`)
    }
    if (result.assigned_count > 0) ElMessage.success(parts[0])
    if (result.skipped_count > 0 || result.failed_count > 0) {
      ElMessage.warning(parts.slice(result.assigned_count > 0 ? 1 : 0).join('；'))
    }
    showBatchAssign.value = false
    if (result.assigned_count > 0) fetchTasks()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '批量分配失败')
  } finally {
    batchAssigning.value = false
  }
}

const onBatchCreateTask = async () => {
  if (!batchTask.value.project_ids.length || !batchTask.value.check_date || !batchTask.value.standard_type) {
    ElMessage.warning('请选择项目、检查标准和日期')
    return
  }
  batchCreating.value = true
  try {
    const result = await createTaskBatch(batchTask.value)
    const parts = [`成功创建 ${result.created_count} 个任务`]
    if (result.skipped_count > 0) {
      const names = result.skipped.map(s => s.project_name).join('、')
      parts.push(`跳过 ${result.skipped_count} 个（${names} 当日同标准任务已存在）`)
    }
    if (result.failed_count > 0) parts.push(`失败 ${result.failed_count} 个`)
    if (result.created_count > 0) ElMessage.success(parts[0])
    if (result.skipped_count > 0 || result.failed_count > 0) {
      ElMessage.warning(parts.slice(result.created_count > 0 ? 1 : 0).join('；'))
    }
    showBatchCreate.value = false
    if (result.created_count > 0) fetchTasks()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '批量创建失败')
  } finally {
    batchCreating.value = false
  }
}

const onCreateTask = async () => {
  if (!newTask.value.project_id || !newTask.value.check_date || !newTask.value.standard_type) {
    ElMessage.warning('请选择项目、检查标准和日期')
    return
  }
  creating.value = true
  try {
    await createTask(newTask.value)
    ElMessage.success('任务创建成功')
    showCreate.value = false
    fetchTasks()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '创建失败')
  } finally {
    creating.value = false
  }
}

const openAssign = async (row) => {
  currentTaskId.value = row.task_id
  try {
    // 从任务详情取模块列表（按任务自身的检查标准：蝶城8模块 / 砺质5模块）
    const detail = await getTaskDetail(row.task_id)
    const taskModules = detail.modules || []
    // 合并已分配信息
    moduleList.value = taskModules.map(m => ({
      name: m.module_name,
      inspector_id: m.inspector_id || null,
      max_score: m.max_score,
      role: m.role,
    }))
  } catch (e) {
    moduleList.value = MODULE_NAMES.map(name => ({ name, inspector_id: null }))
  }
  showAssign.value = true
}

const saveAssignments = async () => {
  savingAssign.value = true
  try {
    for (const m of moduleList.value) {
      if (m.inspector_id) {
        await assignModule(currentTaskId.value, {
          module_name: m.name,
          inspector_id: m.inspector_id
        })
      }
    }
    ElMessage.success('模块分配保存成功')
    showAssign.value = false
    fetchTasks()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '分配失败')
  } finally {
    savingAssign.value = false
  }
}

const viewTask = (row) => {
  router.push(`/task/${row.task_id}`)
}

const onDelete = async (row) => {
  try {
    await ElMessageBox.confirm('确定删除该任务？', '确认', { type: 'warning' })
    await request.delete(`/tasks/${row.task_id}`)
    ElMessage.success('删除成功')
    fetchTasks()
  } catch (e) { /* cancel */ }
}

// ===== AI评分结果弹窗 =====
const showScoring = ref(false)
const dialogState = ref('empty')     // 'scoring' | 'done' | 'empty'
const scoringData = ref(null)
const expandedModules = ref([])
// 轮询相关
const scoringPct = ref(0)
const scoringDone = ref(0)
const scoringTotal = ref(0)
const scoringCurrent = ref('')
let dialogPollingTimer = null

// ===== 评分编辑 =====
const showEditScoreDialog = ref(false)

// ===== 一键执行完整流程 =====
const showPipeline = ref(false)          // 弹窗显示
const pipelineState = ref('idle')        // idle | running | completed | failed
const pipelineData = ref(null)           // 完整结果
const pipelineStep = ref('')             // 当前步骤
const pipelinePct = ref(0)               // 进度百分比
const pipelineError = ref('')
let pipelineTimer = null
const savingEditScore = ref(false)
const exportingExcel = ref(false)
const recallingModule = ref(false)
const editForm = ref({
  scoring_id: '',
  item_name: '',
  score: 5,
  max_score: 5,
  module_role: 'score',
  standard_type: 'diecheng',
  scoring_basis: '',
  edit_reason: ''
})

const editScoreMin = computed(() => (
  editForm.value.standard_type === 'lizhi' && editForm.value.module_role === 'deduction' ? -99.9 : 0
))
const editScoreMax = computed(() => {
  if (editForm.value.standard_type !== 'lizhi') return 5
  if (editForm.value.module_role === 'deduction') return 0
  return Number(editForm.value.max_score || 0)
})
const editScoreLabel = computed(() => {
  if (editForm.value.standard_type !== 'lizhi') return '分数 (0-5)'
  if (editForm.value.module_role === 'deduction') return '扣分 (≤0)'
  return `分数 (0-${editScoreMax.value})`
})

const openEditDialog = (row, mod) => {
  editForm.value = {
    scoring_id: row.scoring_id,
    item_name: row.item_name,
    score: Number(row.score),
    max_score: Number(row.max_score ?? mod?.max_score ?? 5),
    module_role: mod?.role || 'score',
    standard_type: scoringData.value?.standard_type || 'diecheng',
    scoring_basis: row.scoring_basis || '',
    edit_reason: ''
  }
  showEditScoreDialog.value = true
}

const onSaveEditScore = async () => {
  savingEditScore.value = true
  try {
    const res = await editScore(editForm.value.scoring_id, {
      score: editForm.value.score,
      scoring_basis: editForm.value.scoring_basis,
      edit_reason: editForm.value.edit_reason || undefined
    })
    ElMessage.success('评分已更新')
    showEditScoreDialog.value = false
    // 清除前端缓存，重新加载
    if (currentTaskId.value) {
      delete scoringResultsCache.value[currentTaskId.value]
      delete moduleDetailCache.value[currentTaskId.value]
      await loadScoringResults(currentTaskId.value)
      // 更新表格中的总分
      const task = tasks.value.find(t => t.task_id === currentTaskId.value)
      if (task && scoringData.value) {
        task.total_score = scoringData.value.total_score
      }
    }
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '修改失败')
  } finally {
    savingEditScore.value = false
  }
}

const onRescoreModule = async (moduleName) => {
  if (!currentTaskId.value) return
  try {
    await rescoreModule(currentTaskId.value, moduleName)
    ElMessage.success(`模块 ${moduleName} 重新评分已启动`)
    // 清除前端缓存
    delete scoringResultsCache.value[currentTaskId.value]
    delete moduleDetailCache.value[currentTaskId.value]
    // 切换到评分中状态
    dialogState.value = 'scoring'
    scoringTotal.value = 8
    scoringPct.value = 0
    startDialogPolling(currentTaskId.value)
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '启动重新评分失败')
  }
}

const onRecallModule = async (mod) => {
  if (!currentTaskId.value) return
  const recordId = mod.record_id
  if (!recordId) {
    ElMessage.warning('找不到该模块的检查记录')
    return
  }
  try {
    await ElMessageBox.confirm(
      `确定退回模块「${mod.module_name}」吗？退回后该模块的评分、整改记录将被清除，检查人员需要重新填写。`,
      '退回确认',
      { confirmButtonText: '确定退回', cancelButtonText: '取消', type: 'warning' }
    )
  } catch {
    return
  }
  try {
    recallingModule.value = true
    const res = await recallModule(recordId)
    ElMessage.success(res.message || '模块已退回')
    // 关闭对话框，刷新任务列表
    showScoring.value = false
    fetchTasks()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '退回失败')
  } finally {
    recallingModule.value = false
  }
}

const onRecallItem = async (mod, row) => {
  const recordId = mod.record_id
  if (!recordId) {
    ElMessage.warning('找不到该模块的检查记录')
    return
  }
  const itemName = row.item_name || row.item_id
  try {
    await ElMessageBox.confirm(
      `确定退回检查项「${itemName}」吗？退回后该项的评分和问题记录将被清除，检查人员需要重新填写。`,
      '退回确认',
      { confirmButtonText: '确定退回', cancelButtonText: '取消', type: 'warning' }
    )
  } catch {
    return
  }
  try {
    const res = await recallItem(recordId, row.item_id)
    ElMessage.success(res.message || '检查项已退回')
    // 刷新该模块详情
    if (moduleDetailCache.value[currentTaskId.value]) {
      delete moduleDetailCache.value[currentTaskId.value][mod.module_name]
    }
    onModuleExpand(expandedModules.value)
    // 也刷新摘要
    loadSummaryAndShow(currentTaskId.value)
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '退回失败')
  }
}

const onExportExcel = async () => {
  if (!currentTaskId.value) return
  exportingExcel.value = true
  try {
    const blob = await exportScoringExcel(currentTaskId.value)
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `AI评分结果_${currentTaskId.value}.xlsx`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    window.URL.revokeObjectURL(url)
    ElMessage.success('导出成功')
  } catch (e) {
    ElMessage.error('导出失败')
  } finally {
    exportingExcel.value = false
  }
}

// ===== 一键执行完整流程 =====
const pipelineTaskId = ref('')

const onRunPipeline = async (row) => {
  try {
    await ElMessageBox.confirm('AI流程已执行过，确认重新运行？', '提示', {
      confirmButtonText: '确认运行',
      cancelButtonText: '取消',
      type: 'warning',
    })
  } catch { return }

  pipelineTaskId.value = row.task_id
  pipelineState.value = 'running'
  pipelineStep.value = 'scoring'
  pipelinePct.value = 0
  pipelineError.value = ''
  pipelineData.value = null
  showPipeline.value = true

  try {
    const res = await runFullPipeline(row.task_id)
    if (res.success) {
      pipelineState.value = 'completed'
      pipelineStep.value = 'done'
      pipelinePct.value = 100
      pipelineData.value = res
      // 更新任务列表中的总分
      const task = tasks.value.find(t => t.task_id === row.task_id)
      if (task && res.scoring?.total_score) {
        task.total_score = res.scoring.total_score
      }
    } else {
      pipelineState.value = 'failed'
      pipelineError.value = res.error_detail || res.error || '执行失败'
    }
  } catch (e) {
    pipelineState.value = 'failed'
    pipelineError.value = e.response?.data?.detail || e.message || '执行失败'
  }
}

const onRetryPipeline = () => {
  const row = tasks.value.find(t => t.task_id === pipelineTaskId.value)
  if (row) {
    onRunPipeline(row)
  }
}

const onViewReport = () => {
  showPipeline.value = false
  router.push('/reports')
}

const onViewScoring = () => {
  showPipeline.value = false
  const row = tasks.value.find(t => t.task_id === pipelineTaskId.value)
  if (row) {
    viewScoring(row)
  }
}

const viewScoring = async (row) => {
  showScoring.value = true
  expandedModules.value = []
  scoringData.value = null
  dialogState.value = 'empty'
  currentTaskId.value = row.task_id

  const taskId = row.task_id

  // 1. 命中完整数据缓存 → 瞬间显示
  if (scoringResultsCache.value[taskId]) {
    scoringData.value = scoringResultsCache.value[taskId]
    if (scoringData.value.modules.length > 0) {
      expandedModules.value = [scoringData.value.modules[0].module_name]
    }
    dialogState.value = 'done'
    return
  }

  // 2. 已知评分完成（total_score > 0）→ 先加载摘要（瞬间），后台加载详情
  if (row.total_score && row.total_score > 0) {
    await loadSummaryAndShow(taskId)
    return
  }

  // 3. 已知正在评分 → 直接显示进度并轮询
  if (scoringStatusMap.value[taskId] === 'scoring') {
    dialogState.value = 'scoring'
    scoringTotal.value = 8
    scoringDone.value = 0
    scoringPct.value = 0
    startDialogPolling(taskId)
    return
  }

  // 4. 未知状态 → 并行检查状态和尝试加载摘要
  try {
    const [statusRes] = await Promise.all([
      getScoringStatus(taskId),
      loadSummaryAndShow(taskId).catch(() => null)
    ])

    if (scoringData.value) return

    if (statusRes.is_complete) {
      await loadSummaryAndShow(taskId)
    } else if (statusRes.scored_modules > 0 || statusRes.total_modules > 0) {
      dialogState.value = 'scoring'
      scoringTotal.value = statusRes.total_modules || 1
      scoringDone.value = statusRes.scored_modules || 0
      scoringCurrent.value = statusRes.current_module || ''
      scoringPct.value = Math.round((scoringDone.value / scoringTotal.value) * 100)
      startDialogPolling(taskId)
    } else {
      try {
        await startScoring(taskId)
        dialogState.value = 'scoring'
        scoringTotal.value = 8
        scoringDone.value = 0
        scoringPct.value = 0
        startDialogPolling(taskId)
      } catch (e) {
        ElMessage.warning(e.response?.data?.detail || '启动评分失败')
      }
    }
  } catch (e) {
    try {
      await startScoring(taskId)
      dialogState.value = 'scoring'
      scoringTotal.value = 8
      scoringDone.value = 0
      scoringPct.value = 0
      startDialogPolling(taskId)
    } catch (e2) {
      ElMessage.warning(e2.response?.data?.detail || '启动评分失败')
    }
  }
}

// ===== 加载摘要（~1KB，秒返回）→ 立即显示评分概览 =====
const loadSummaryAndShow = async (taskId) => {
  const res = await getScoringSummary(taskId)
  const data = {
    total_score: res.total_score || 0,
    project_name: res.project_name || '',
    standard_type: res.standard_type || 'diecheng',
    modules: (res.modules || []).map(m => ({
      module_name: m.module_name,
      module_pct_score: m.module_pct_score,
      weight_ratio: m.weight_ratio,
      max_score: m.max_score,
      role: m.role || 'score',
      items_count: m.items_count,
      record_id: m.record_id || null, // 用于退回功能
      items: null, // 标记为未加载，展开时按需拉取
    }))
  }
  scoringData.value = data
  dialogState.value = 'done'
}

// ===== 展开模块时按需加载详情 =====
const onModuleExpand = async (moduleNames) => {
  expandedModules.value = moduleNames
  if (!currentTaskId.value || !scoringData.value) return

  for (const name of moduleNames) {
    const mod = scoringData.value.modules.find(m => m.module_name === name)
    if (!mod || mod.items) continue // 已有数据则跳过

    // 检查模块级缓存
    if (moduleDetailCache.value[currentTaskId.value]?.[name]) {
      mod.items = moduleDetailCache.value[currentTaskId.value][name]
      continue
    }

    // 标记加载中
    if (!moduleLoadingMap.value[currentTaskId.value]) moduleLoadingMap.value[currentTaskId.value] = {}
    moduleLoadingMap.value[currentTaskId.value][name] = true

    try {
      const res = await getModuleDetail(currentTaskId.value, name)
      mod.items = res.items || []
      // 缓存
      if (!moduleDetailCache.value[currentTaskId.value]) moduleDetailCache.value[currentTaskId.value] = {}
      moduleDetailCache.value[currentTaskId.value][name] = mod.items
    } catch (e) {
      console.error('加载模块详情失败:', name, e)
      mod.items = []
    } finally {
      moduleLoadingMap.value[currentTaskId.value][name] = false
    }
  }
}

let dialogPollingCount = 0
const startDialogPolling = (taskId) => {
  stopDialogPolling()
  dialogPollingCount = 0
  const doPoll = async () => {
    try {
      const res = await getScoringStatus(taskId)
      scoringTotal.value = res.total_modules || 1
      scoringDone.value = res.scored_modules || 0
      scoringCurrent.value = res.current_module || ''
      scoringPct.value = Math.min(100, Math.round((scoringDone.value / scoringTotal.value) * 100))

      if (res.is_complete) {
        stopDialogPolling()
        await loadSummaryAndShow(taskId)
        const task = tasks.value.find(t => t.task_id === taskId)
        if (task && scoringData.value) {
          task.total_score = scoringData.value.total_score
        }
        scoringStatusMap.value[taskId] = 'completed'
        return
      }
    } catch (e) {
      console.error('评分状态轮询失败', e)
    }
    // 动态间隔：前5次1秒，之后逐渐增加到3秒
    dialogPollingCount++
    const interval = dialogPollingCount <= 5 ? 1000 : Math.min(3000, 1000 + (dialogPollingCount - 5) * 500)
    dialogPollingTimer = setTimeout(doPoll, interval)
  }
  dialogPollingTimer = setTimeout(doPoll, 1000)
}

const stopDialogPolling = () => {
  if (dialogPollingTimer) {
    clearTimeout(dialogPollingTimer)
    dialogPollingTimer = null
  }
}

const loadScoringResults = async (taskId) => {
  // 使用轻量摘要接口（~1KB，秒返回）
  await loadSummaryAndShow(taskId)
}

// 模块是否正在加载详情
const isModuleLoading = (moduleName) => {
  if (!currentTaskId.value) return false
  return !!moduleLoadingMap.value[currentTaskId.value]?.[moduleName]
}

// 折叠面板变化时触发模块详情加载
const onCollapseChange = (activeNames) => {
  onModuleExpand(activeNames)
}

const getScoreClass = (score) => {
  if (score >= 90) return 'score-excellent'
  if (score >= 80) return 'score-good'
  if (score >= 60) return 'score-normal'
  return 'score-poor'
}

const getItemScoreClass = (score) => {
  if (Number(score) >= 5) return 'item-score-full'
  if (Number(score) >= 3) return 'item-score-warn'
  return 'item-score-low'
}

const itemRowClass = ({ row }) => {
  if (row.is_skipped) return 'skipped-row'
  if (row.is_fallback) return 'fallback-row'
  return ''
}

const getProgressColor = (pct) => {
  if (pct >= 100) return 'var(--ok)'
  if (pct >= 50) return 'var(--blue)'
  return 'var(--warn)'
}

// ===== Template helpers for prototype classes =====
const statusClass = (s) => {
  if (s === 'pending') return 'st-pending'
  if (s === 'in_progress') return 'st-progress'
  if (s === 'completed') return 'st-done'
  return 'st-pending'
}

const scoreClass = (score) => {
  if (score >= 80) return 'sp-hi'
  if (score >= 60) return 'sp-mid'
  return 'sp-lo'
}

const totalPages = computed(() => Math.ceil(total.value / 20) || 1)

const pageNumbers = computed(() => {
  const pages = []
  const tp = totalPages.value
  const cur = page.value
  let start = Math.max(1, cur - 1)
  let end = Math.min(tp, start + 2)
  if (end - start < 2) start = Math.max(1, end - 2)
  for (let i = start; i <= end; i++) pages.push(i)
  return pages
})

const goPage = (p) => {
  if (p < 1 || p > totalPages.value) return
  page.value = p
  fetchTasks()
}

onMounted(async () => {
  await authStore.fetchUser()
  fetchTasks()
  fetchProjects()
  fetchInspectors()
  fetchStandardTypes()
})

onUnmounted(() => {
  if (statusPollingTimer) {
    clearInterval(statusPollingTimer)
    statusPollingTimer = null
  }
  stopDialogPolling()
  // 确保 loading 状态不会残留导致白色遮罩
  loading.value = false
  // 清理可能残留的 Element Plus 遮罩层
  document.querySelectorAll('.el-loading-mask, .el-overlay').forEach(el => el.remove())
})
</script>

<style scoped>
/* ==================== Page Container ==================== */
.tasks-page {
  max-width: 1400px;
  padding-bottom: 40px;
}

/* ==================== Page Header (prototype .phdr) ==================== */

/* ==================== Buttons (prototype .btn) ==================== */

/* ==================== Filters (prototype .filters) ==================== */
.filters {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.f-sel {
  padding: 7px 28px 7px 12px;
  border-radius: var(--r);
  font-size: 13px;
  font-weight: 500;
  color: var(--ink-600);
  border: 1px solid var(--ink-100);
  background: var(--bg-card);
  cursor: pointer;
  font-family: var(--sans);
  transition: all 0.12s;
  appearance: none;
  -webkit-appearance: none;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 16 16'%3E%3Cpath d='M4 6l4 4 4-4' stroke='%23a1a1aa' fill='none' stroke-width='1.8'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 8px center;
}

.f-sel:hover {
  border-color: var(--ink-200);
}

.f-reset {
  font-size: 13px;
  font-weight: 500;
  color: var(--ink-400);
  cursor: pointer;
  border: none;
  background: none;
  font-family: var(--sans);
  padding: 6px 10px;
  border-radius: var(--r-sm);
  transition: all 0.1s;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.f-reset:hover {
  color: var(--ink-800);
  background: var(--bg-muted);
}

.f-reset svg {
  width: 12px;
  height: 12px;
  stroke: currentColor;
  fill: none;
  stroke-width: 2;
}

.selection-count {
  margin-left: auto;
  color: var(--blue);
  font-size: 13px;
  font-weight: 600;
}

/* ==================== Card (prototype .card) ==================== */
.card {
  background: var(--bg-card);
  border: 1px solid var(--ink-100);
  border-radius: var(--r-lg);
  overflow: hidden;
  animation: cardIn 0.3s var(--ease) 0.05s both;
}

/* ==================== Table (prototype .tbl) ==================== */
.tbl {
  width: 100%;
  border-collapse: collapse;
}

.tbl th {
  font-size: 12px;
  font-weight: 700;
  color: var(--ink-400);
  letter-spacing: 0.3px;
  text-align: center;
  padding: 10px 10px;
  background: var(--bg-muted);
  border-bottom: 1px solid var(--ink-100);
}

.tbl th:first-child {
  text-align: left;
  padding-left: 20px;
}

.tbl th.select-col,
.tbl td.select-col {
  width: 46px;
  padding-left: 14px;
  padding-right: 6px;
  text-align: center;
  font-family: var(--sans);
}

.tbl td.task-id-cell {
  text-align: left;
  font-family: var(--mono);
  font-size: 12px;
  color: var(--ink-400);
}

.task-checkbox {
  width: 15px;
  height: 15px;
  cursor: pointer;
  accent-color: var(--blue);
}

.task-checkbox:disabled {
  cursor: not-allowed;
}

.tbl td {
  font-size: 14px;
  font-weight: 500;
  text-align: center;
  padding: 12px 10px;
  border-bottom: 1px solid var(--ink-100);
  color: var(--ink-600);
}

.tbl td:first-child {
  text-align: left;
  padding-left: 20px;
  font-family: var(--mono);
  font-size: 12px;
  color: var(--ink-400);
}

.tbl th.select-col,
.tbl td.select-col {
  padding-left: 14px;
  padding-right: 6px;
  text-align: center;
  font-family: var(--sans);
  color: var(--ink-600);
}

.batch-export-options {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 14px;
  margin-bottom: 20px;
}

.tbl tbody tr {
  transition: background 0.08s;
}

.tbl tbody tr:hover {
  background: var(--bg);
}

/* ==================== Progress bar (prototype .prog-*) ==================== */
.prog-wrap {
  display: flex;
  align-items: center;
  gap: 6px;
  justify-content: center;
}

.prog-bar {
  width: 80px;
  height: 6px;
  background: var(--ink-100);
  border-radius: 3px;
  overflow: hidden;
}

.prog-fill {
  height: 100%;
  border-radius: 3px;
  background: var(--teal-600);
  transition: width 0.4s var(--ease);
}

.prog-txt {
  font-family: var(--mono);
  font-size: 12px;
  font-weight: 600;
  color: var(--ink-400);
  white-space: nowrap;
}

/* ==================== Status pills (prototype .st) ==================== */
.st {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 600;
}

.st-pending {
  background: var(--bg-muted);
  color: var(--ink-400);
}

.st-progress {
  background: var(--warn-bg);
  color: var(--warn);
}

.st-done {
  background: var(--ok-bg);
  color: var(--ok);
}

/* ==================== Score pills (prototype .sp) ==================== */
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

.sp-hi {
  background: var(--ok-bg);
  color: var(--ok);
}

.sp-mid {
  background: var(--warn-bg);
  color: var(--warn);
}

.sp-lo {
  background: var(--err-bg);
  color: var(--err);
}

/* ==================== Tags (prototype .kt) ==================== */
.kt {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 3px;
  font-size: 12px;
  font-weight: 600;
}

.kt-blue {
  background: var(--blue-bg);
  color: var(--blue);
}

.kt-warn {
  background: var(--warn-bg);
  color: var(--warn);
}

.kt-lizhi {
  background: var(--bg-muted);
  color: var(--ink-700);
}

.kt-muted {
  background: var(--bg-muted);
  color: var(--ink-600);
}

.kt-err {
  background: var(--err-bg);
  color: var(--err);
}

/* ==================== Action buttons (prototype .act) ==================== */
.act {
  font-size: 12px;
  font-weight: 600;
  color: var(--blue);
  cursor: pointer;
  border: none;
  background: none;
  font-family: var(--sans);
  padding: 4px 8px;
  border-radius: var(--r-sm);
  transition: background 0.1s;
}

.act:hover {
  background: var(--blue-bg);
}

.act + .act {
  margin-left: 2px;
}

.act-warn {
  color: var(--warn);
}

.act-warn:hover {
  background: var(--warn-bg);
}

.act-ok {
  color: var(--ok);
}

.act-ok:hover {
  background: var(--ok-bg);
}

.act-err {
  color: var(--err);
}

.act-err:hover {
  background: var(--err-bg);
}

/* ==================== Pagination (prototype .pagi) ==================== */
.pagi {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 20px;
  border-top: 1px solid var(--ink-100);
}

.pagi-info {
  font-size: 12px;
  color: var(--ink-400);
}

.pagi-info b {
  color: var(--ink-800);
}

.pagi-btns {
  display: flex;
  gap: 3px;
}

.pg {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--r-sm);
  font-size: 13px;
  font-weight: 500;
  color: var(--ink-600);
  cursor: pointer;
  border: 1px solid var(--ink-100);
  background: var(--bg-card);
  transition: all 0.1s;
  font-family: var(--sans);
}

.pg:hover:not(:disabled) {
  background: var(--bg-muted);
}

.pg.on {
  background: var(--blue);
  color: #fff;
  border-color: var(--blue);
}

.pg:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.pg svg {
  width: 12px;
  height: 12px;
  stroke: currentColor;
  fill: none;
  stroke-width: 2;
}

/* ==================== Score link in table ==================== */
.score-link {
  cursor: pointer;
  transition: opacity 0.15s;
}

.score-link:hover {
  opacity: 0.7;
}

/* ==================== Scoring tag ==================== */
.scoring-tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
}

.scoring-tag.scoring {
  color: var(--warn);
}

.text-muted {
  color: var(--ink-400);
}

/* ==================== Scoring Progress ==================== */
.scoring-progress-area {
  text-align: center;
  padding: 48px 20px;
}

.scoring-progress-header {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  font-size: 17px;
  font-weight: 600;
  color: var(--ink-900);
  margin-bottom: 8px;
}

.scoring-pulse {
  display: none;
}

.scoring-detail {
  color: var(--blue);
  font-size: 14px;
  font-weight: 500;
  margin: 12px 0 4px;
}

.scoring-current {
  color: var(--ink-600);
  font-size: 14px;
}

.scoring-tip {
  color: var(--ink-400);
  font-size: 12px;
  margin-top: 12px;
}

/* ==================== Score Colors ==================== */
.score-excellent { color: var(--ok); font-weight: bold; }
.score-good { color: var(--blue); font-weight: bold; }
.score-normal { color: var(--warn); font-weight: bold; }
.score-poor { color: var(--err); font-weight: bold; }

.item-score-full { color: var(--ok); font-weight: bold; }
.item-score-warn { color: var(--warn); font-weight: bold; }
.item-score-low { color: var(--err); font-weight: bold; }

/* ==================== Scoring Dialog - Score Header ==================== */
.score-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: var(--bg-muted);
  border: 1px solid var(--ink-200);
  padding: 24px 28px;
  border-radius: 10px;
  margin-bottom: 20px;
}

.total-score {
  display: flex;
  align-items: baseline;
  gap: 8px;
}

.score-label {
  font-size: 14px;
  color: var(--ink-600);
}

.score-value {
  font-family: var(--mono);
  font-size: 36px;
  font-weight: 800;
  color: var(--blue);
}

.score-unit {
  font-size: 14px;
  color: var(--ink-400);
}

.score-meta {
  font-size: 12px;
  color: var(--ink-400);
}

/* ==================== Module Collapse ==================== */
.module-collapse {
  margin-top: 8px;
  border: none;
}

.module-collapse :deep(.el-collapse-item__header) {
  background: var(--bg-muted);
  border: 1px solid var(--ink-200);
  border-radius: 6px;
  padding: 0 16px;
  margin-bottom: 4px;
  font-size: 14px;
  height: 48px;
  line-height: 48px;
}

.module-collapse :deep(.el-collapse-item__header:hover) {
  background: var(--bg-muted);
}

.module-collapse :deep(.el-collapse-item__wrap) {
  border: none;
}

.module-collapse :deep(.el-collapse-item__content) {
  padding: 12px 0;
}

.module-title {
  display: flex;
  align-items: center;
  width: 100%;
}

.module-name {
  font-weight: 600;
  min-width: 120px;
  color: var(--ink-900);
}

.module-score {
  margin-left: 16px;
  font-weight: 600;
  font-size: 14px;
}

.module-items-count {
  margin-left: 12px;
  color: var(--ink-400);
  font-size: 12px;
}

.module-loading-hint {
  color: var(--blue);
  font-size: 12px;
  margin-left: 8px;
}

.module-loading-area {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 24px;
  color: var(--ink-400);
}

.cell-text {
  font-size: 12px;
  line-height: 1.5;
  color: var(--ink-600);
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.issue-cell {
  margin-bottom: 6px;
  font-size: 12px;
  line-height: 1.5;
  color: var(--ink-600);
}

.issue-photos-pc {
  display: flex;
  gap: 4px;
  margin-top: 4px;
  flex-wrap: wrap;
}

.issue-photo-pc {
  width: 40px;
  height: 40px;
  border-radius: 4px;
  cursor: pointer;
  border: 1px solid var(--ink-200);
}

.editable-score {
  cursor: pointer;
}

.editable-score:hover {
  opacity: 0.7;
}

:deep(.skipped-row) {
  opacity: 0.5;
  background-color: var(--bg-muted) !important;
}

:deep(.fallback-row) {
  background-color: var(--warn-bg) !important;
}

/* ==================== Pipeline Dialog ==================== */
.pipeline-progress {
  text-align: center;
  padding: 24px 20px;
}

.pipeline-header {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  margin-bottom: 8px;
}

.pipeline-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--ink-900);
}

.pipeline-steps {
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 32px 0 24px;
}

.pipeline-step {
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--ink-400);
  font-size: 14px;
}

.pipeline-step.active {
  color: var(--blue);
  font-weight: 600;
}

.pipeline-step.done {
  color: var(--ok);
}

.pipeline-step-line {
  width: 60px;
  height: 2px;
  background: var(--ink-200);
  margin: 0 12px;
}

.pipeline-tip {
  color: var(--ink-400);
  font-size: 13px;
  margin-top: 16px;
}

.pipeline-result {
  padding: 24px 20px;
  text-align: center;
}

.pipeline-success {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  margin-bottom: 24px;
}

.pipeline-success-text {
  font-size: 20px;
  font-weight: 600;
  color: var(--ok);
}

.pipeline-summary {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
  background: var(--bg-muted);
  border-radius: 8px;
  padding: 20px;
  margin-bottom: 16px;
}

.summary-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.summary-label {
  font-size: 12px;
  color: var(--ink-400);
}

.summary-value {
  font-size: 18px;
  font-weight: 600;
  color: var(--ink-900);
}

.pipeline-duration {
  font-size: 13px;
  color: var(--ink-400);
  margin: 0;
}

.pipeline-error {
  text-align: center;
  padding: 24px 20px;
}

.pipeline-error-text {
  display: block;
  font-size: 18px;
  font-weight: 600;
  color: var(--err);
  margin-top: 12px;
}

.pipeline-error-detail {
  color: var(--ink-600);
  font-size: 14px;
  margin-top: 8px;
}

/* ==================== Styled Dialogs ==================== */
:deep(.styled-dialog .el-dialog) {
  border-radius: 10px;
  overflow: hidden;
}

:deep(.styled-dialog .el-dialog__title) {
  font-weight: 600;
  color: var(--ink-900);
}

/* ==================== Scoring Dialog ==================== */
:deep(.scoring-dialog .el-dialog) {
  border-radius: 10px;
  overflow: hidden;
}

:deep(.scoring-dialog .el-dialog__title) {
  color: var(--ink-900);
  font-weight: 600;
}

/* Scoring detail inner table */
.module-collapse :deep(.el-table) {
  --el-table-border-color: var(--ink-200);
  --el-table-header-bg-color: var(--bg-muted);
}

.module-collapse :deep(.el-table th) {
  color: var(--ink-600);
  font-size: 12px;
}

.module-collapse :deep(.el-table td) {
  color: var(--ink-600);
}

/* ==================== Animations ==================== */
@keyframes cardIn {
  from { opacity: 0; transform: translateY(6px); }
  to { opacity: 1; transform: translateY(0); }
}

/* ==================== Responsive ==================== */
@media (max-width: 900px) {
}
</style>
