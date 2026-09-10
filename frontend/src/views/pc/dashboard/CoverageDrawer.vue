<template>
  <el-drawer v-model="drawerVisible" title="本月检查项目明细" size="60%" :destroy-on-close="true" @close="$emit('update:visible', false)">
    <div class="drawer-filter">
      <el-select v-model="statusFilter" placeholder="状态筛选" clearable style="width: 140px">
        <el-option label="全部" value="" />
        <el-option label="已检查" value="checked" />
        <el-option label="未检查" value="unchecked" />
      </el-select>
      <div class="drawer-top-bar" style="margin-left: 10px">
        已检查：<strong style="color:var(--ok-strong)">{{ checkedCount }}</strong> / 总项目：<strong>{{ totalProjects }}</strong> / 覆盖率：<strong>{{ coverageRate }}%</strong>
      </div>
      <el-button style="margin-left:auto" @click="$emit('export')">
        <el-icon style="margin-right:4px"><Download /></el-icon>导出
      </el-button>
    </div>
    <el-table :data="filteredList" stripe size="small" class="drawer-table">
      <el-table-column prop="project_name" label="项目名称" />
      <el-table-column prop="check_date" label="最近检查日期" width="140" align="center">
        <template #default="{ row }">
          <span v-if="row.status === 'checked'">{{ row.check_date || '-' }}</span>
          <span v-else class="text-muted">-</span>
        </template>
      </el-table-column>
      <el-table-column prop="status" label="检查状态" width="100" align="center">
        <template #default="{ row }">
          <el-tag :type="row.status === 'checked' ? 'success' : 'info'" size="small">{{ row.status === 'checked' ? '已检查' : '未检查' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="70" align="center">
        <template #default="{ row }">
          <el-button v-if="row.status === 'checked' && row.project_id" type="primary" link size="small" @click="$emit('go-to-project', row.project_id)">查看</el-button>
        </template>
      </el-table-column>
    </el-table>
  </el-drawer>
</template>

<script setup>
import { computed, ref } from 'vue'
import { Download } from '@element-plus/icons-vue'

const props = defineProps({
  visible: Boolean,
  checkedProjects: { type: Array, default: () => [] },
  uncheckedProjects: { type: Array, default: () => [] },
  checkedCount: { type: Number, default: 0 },
  totalProjects: { type: Number, default: 0 },
  coverageRate: { type: [Number, String], default: 0 }
})

const emit = defineEmits(['update:visible', 'export', 'go-to-project'])

const drawerVisible = computed({
  get: () => props.visible,
  set: (val) => emit('update:visible', val)
})

const statusFilter = ref('')

const filteredList = computed(() => {
  const checked = props.checkedProjects.map(p => ({
    project_id: p.project_id,
    project_name: p.project_name,
    check_date: p.check_date || p.latest_report_date,
    status: 'checked'
  }))
  const unchecked = props.uncheckedProjects.map(p => ({
    project_id: p.id,
    project_name: p.name,
    check_date: null,
    status: 'unchecked'
  }))
  const all = [...checked, ...unchecked]
  if (!statusFilter.value) return all
  return all.filter(item => item.status === statusFilter.value)
})
</script>
