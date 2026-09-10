<template>
  <div class="change-pwd-page">
    <div class="deco-circle deco-1"></div>
    <div class="deco-circle deco-2"></div>

    <div class="form-card">
      <div class="form-icon">
        <van-icon name="lock" size="40" color="var(--blue)" />
      </div>
      <h2>修改密码</h2>
      <p class="form-desc">首次登录请修改初始密码</p>
      <div class="pwd-tip">密码要求：字母+数字，不少于8位</div>

      <van-form @submit="onSubmit" class="pwd-form">
        <van-cell-group inset>
          <van-field
            v-model="form.newPassword"
            :type="showPwd ? 'text' : 'password'"
            name="newPassword"
            label="新密码"
            placeholder="请输入新密码（字母+数字，不少于8位）"
            :rules="[
              { required: true, message: '请输入新密码' },
              { validator: (val) => val.length >= 8 && /[a-zA-Z]/.test(val) && /\d/.test(val), message: '密码需包含字母和数字，不少于8位' }
            ]"
            :right-icon="showPwd ? 'eye-o' : 'closed-eye'"
            @click-right-icon="showPwd = !showPwd"
          />
          <van-field
            v-model="form.confirmPassword"
            :type="showConfirmPwd ? 'text' : 'password'"
            name="confirmPassword"
            label="确认密码"
            placeholder="请再次输入新密码"
            :rules="[
              { required: true, message: '请确认密码' },
              { validator: (val) => val === form.newPassword, message: '两次密码不一致' }
            ]"
            :right-icon="showConfirmPwd ? 'eye-o' : 'closed-eye'"
            @click-right-icon="showConfirmPwd = !showConfirmPwd"
          />
        </van-cell-group>

        <div class="form-buttons">
          <van-button round block type="primary" native-type="submit" :loading="loading">
            确认修改
          </van-button>
        </div>
      </van-form>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { showToast, showSuccessToast, closeToast } from 'vant'
import request from '../../utils/request'

const router = useRouter()
const loading = ref(false)
const showPwd = ref(false)
const showConfirmPwd = ref(false)

const form = reactive({
  newPassword: '',
  confirmPassword: ''
})

const onSubmit = async () => {
  loading.value = true
  try {
    await request.post('/auth/change-password', {
      new_password: form.newPassword
    })
    // 更新本地用户信息
    const user = JSON.parse(localStorage.getItem('user') || '{}')
    user.must_change_pwd = false
    localStorage.setItem('user', JSON.stringify(user))

    showSuccessToast('密码修改成功')
    // 延迟跳转，等待Toast动画完成，防止弹窗DOM残留
    await new Promise(r => setTimeout(r, 300))
    const isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent) || window.innerWidth < 768
    router.push(isMobile ? '/tasks' : '/pc/tasks')
  } catch (error) {
    showToast('修改失败：' + (error.response?.data?.detail || '请重试'))
  } finally {
    loading.value = false
  }
}

onUnmounted(() => {
  closeToast()
})
</script>

<style scoped>
.change-pwd-page {
  min-height: 100vh;
  background: #f5f7fa;
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 20px;
  position: relative;
  overflow: hidden;
}

.deco-circle {
  display: none;
}

.form-card {
  background: #ffffff;
  border-radius: 16px;
  padding: 32px 16px;
  width: 100%;
  max-width: 400px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
  position: relative;
  z-index: 1;
}

.form-icon {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  background: rgba(37, 99, 235, 0.1);
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 16px;
}

.form-card h2 {
  text-align: center;
  font-size: 20px;
  color: #1a1d26;
  margin-bottom: 4px;
}

.form-desc {
  text-align: center;
  color: #9ba3af;
  font-size: 13px;
  margin-bottom: 8px;
}

.pwd-tip {
  text-align: center;
  color: var(--blue);
  font-size: 12px;
  margin-bottom: 24px;
  font-weight: 500;
}

.form-buttons {
  margin-top: 24px;
  padding: 0 16px;
}

.form-buttons .van-button--primary {
  background: var(--blue);
  border: none;
  height: 44px;
  font-size: 16px;
}
</style>
