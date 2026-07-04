<template>
  <van-action-sheet v-model:show="show" title="个人信息">
    <div class="user-sheet">
      <van-cell title="用户名" :value="user.username" />
      <van-cell title="姓名" :value="user.real_name" />
      <van-cell title="手机号" :value="user.phone || '未设置'" />
      <van-cell title="角色" :value="getRoleText(user.role)" />
      <van-cell title="所属项目" :value="projectName" />
      <van-cell title="注册时间" :value="formatDate(user.created_at)" />
      <div class="user-sheet-actions">
        <van-button block type="primary" plain icon="lock" @click="showPwdDialog = true">修改密码</van-button>
        <van-button block type="danger" @click="onLogout" style="margin-top: 10px">退出登录</van-button>
      </div>
    </div>

    <!-- 修改密码弹窗 -->
    <van-dialog
      v-model:show="showPwdDialog"
      title="修改密码"
      show-cancel-button
      :before-close="onPwdBeforeClose"
    >
      <div style="padding: 16px">
        <van-field
          v-model="newPwd"
          type="password"
          label="新密码"
          placeholder="至少8位，包含字母和数字"
          maxlength="32"
        />
        <van-field
          v-model="confirmPwd"
          type="password"
          label="确认密码"
          placeholder="再次输入新密码"
          maxlength="32"
        />
      </div>
    </van-dialog>
  </van-action-sheet>
</template>

<script setup>
import { ref, computed } from 'vue'
import { showToast, showSuccessToast } from 'vant'
import { useAuthStore } from '../stores/auth'
import { changePassword } from '../api/auth'

const props = defineProps({
  show: Boolean
})
const emit = defineEmits(['update:show'])

const show = computed({
  get: () => props.show,
  set: (v) => emit('update:show', v)
})

const authStore = useAuthStore()
const user = computed(() => authStore.user || {})

const projectName = computed(() => {
  return authStore.activeProjectName || '未分配'
})

const getRoleText = (role) => {
  const map = { admin: '管理员', inspector: '检查员', site_supervisor: '阵地督导', field_supervisor: '驻场经理', project_staff: '项目人员' }
  return map[role] || role
}

const formatDate = (iso) => {
  if (!iso) return '—'
  return iso.slice(0, 10)
}

const onLogout = () => { authStore.logout() }

// 修改密码
const showPwdDialog = ref(false)
const newPwd = ref('')
const confirmPwd = ref('')

const onPwdBeforeClose = async (action) => {
  if (action === 'confirm') {
    if (!newPwd.value || newPwd.value.length < 8) {
      showToast('密码长度不能少于8位')
      return false
    }
    if (!/[a-zA-Z]/.test(newPwd.value) || !/\d/.test(newPwd.value)) {
      showToast('密码需包含字母和数字')
      return false
    }
    if (newPwd.value !== confirmPwd.value) {
      showToast('两次输入的密码不一致')
      return false
    }
    try {
      await changePassword({ new_password: newPwd.value })
      showSuccessToast('密码修改成功')
      newPwd.value = ''
      confirmPwd.value = ''
      return true
    } catch (e) {
      showToast(e.response?.data?.detail || '修改失败')
      return false
    }
  }
  newPwd.value = ''
  confirmPwd.value = ''
  return true
}
</script>

<style scoped>
.user-sheet {
  padding: 0 4px 20px;
}

.user-sheet-actions {
  padding: 16px;
}
</style>
