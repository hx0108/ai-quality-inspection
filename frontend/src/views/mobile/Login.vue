<template>
  <div class="login-page">
    <!-- 多层背景 -->
    <div class="bg-base"></div>
    <div class="bg-nebula"></div>
    <div class="bg-stars"></div>
    <div class="bg-aurora"></div>

    <!-- 宇宙传送门（左侧偏上） -->
    <div class="portal-wrapper">
      <div class="portal-ring ring-1"></div>
      <div class="portal-ring ring-2"></div>
      <div class="portal-ring ring-3"></div>
      <div class="portal-ring ring-4"></div>
      <div class="portal-ring ring-5"></div>
      <div class="portal-core"></div>
      <div class="portal-pulse pulse-1"></div>
      <div class="portal-pulse pulse-2"></div>
      <!-- 粒子 -->
      <div class="particle p1"></div>
      <div class="particle p2"></div>
      <div class="particle p3"></div>
      <div class="particle p4"></div>
      <div class="particle p5"></div>
      <div class="particle p6"></div>
      <div class="particle p7"></div>
      <div class="particle p8"></div>
      <div class="particle p9"></div>
      <div class="particle p10"></div>
      <!-- 光束 -->
      <div class="light-beam beam-1"></div>
      <div class="light-beam beam-2"></div>
      <div class="light-beam beam-3"></div>
    </div>

    <!-- 漂浮粒子 -->
    <div class="floating-dots">
      <div class="dot d1"></div>
      <div class="dot d2"></div>
      <div class="dot d3"></div>
      <div class="dot d4"></div>
      <div class="dot d5"></div>
      <div class="dot d6"></div>
      <div class="dot d7"></div>
      <div class="dot d8"></div>
    </div>

    <!-- 底部模糊球 -->
    <div class="orb orb-left"></div>
    <div class="orb orb-right"></div>

    <!-- 左上 logo -->
    <div class="top-logo">
      <div class="logo-mark">
        <svg viewBox="0 0 60 60" width="44" height="44">
          <defs>
            <linearGradient id="lg1" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" style="stop-color:#818cf8"/>
              <stop offset="100%" style="stop-color:#c084fc"/>
            </linearGradient>
            <linearGradient id="lg2" x1="100%" y1="0%" x2="0%" y2="100%">
              <stop offset="0%" style="stop-color:#6366f1"/>
              <stop offset="100%" style="stop-color:#a78bfa"/>
            </linearGradient>
            <filter id="lglow">
              <feGaussianBlur stdDeviation="2" result="b"/>
              <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
            </filter>
          </defs>
          <!-- 外层六边形 - 顺时针旋转 -->
          <polygon points="30,4 52,16 52,44 30,56 8,44 8,16"
                   fill="none" stroke="url(#lg1)" stroke-width="1.2"
                   stroke-linejoin="round" filter="url(#lglow)">
            <animateTransform attributeName="transform" type="rotate"
              from="0 30 30" to="360 30 30" dur="20s" repeatCount="indefinite"/>
          </polygon>
          <!-- 内层六边形 - 逆时针旋转 -->
          <polygon points="30,13 43,21 43,39 30,47 17,39 17,21"
                   fill="rgba(139,92,246,0.04)" stroke="url(#lg2)" stroke-width="0.8"
                   stroke-linejoin="round">
            <animateTransform attributeName="transform" type="rotate"
              from="360 30 30" to="0 30 30" dur="14s" repeatCount="indefinite"/>
          </polygon>
          <!-- 中心呼吸光晕 -->
          <circle cx="30" cy="30" r="8" fill="rgba(139,92,246,0.06)">
            <animate attributeName="r" values="6;10;6" dur="3s" repeatCount="indefinite"/>
            <animate attributeName="opacity" values="0.6;1;0.6" dur="3s" repeatCount="indefinite"/>
          </circle>
          <!-- 勾选标记 -->
          <path d="M23,30 L27.5,34.5 L37,25" fill="none" stroke="url(#lg1)" stroke-width="2.2"
                stroke-linecap="round" stroke-linejoin="round" filter="url(#lglow)"/>
          <!-- 轨道粒子1 -->
          <circle r="2" fill="#c4b5fd" opacity="0.9">
            <animateMotion dur="8s" repeatCount="indefinite"
              path="M30,30 m-18,0 a18,18 0 1,0 36,0 a18,18 0 1,0 -36,0"/>
          </circle>
          <!-- 轨道粒子2 -->
          <circle r="1.5" fill="#818cf8" opacity="0.7">
            <animateMotion dur="12s" repeatCount="indefinite"
              path="M30,30 m-22,0 a22,22 0 1,0 44,0 a22,22 0 1,0 -44,0"/>
          </circle>
          <!-- 轨道粒子3 -->
          <circle r="1" fill="#e9d5ff" opacity="0.5">
            <animateMotion dur="6s" repeatCount="indefinite"
              path="M30,30 m-12,0 a12,12 0 1,1 24,0 a12,12 0 1,1 -24,0"/>
          </circle>
        </svg>
      </div>
      <div class="logo-text-group">
        <span class="logo-title">品质检查</span>
        <span class="logo-subtitle">QUALITY INSPECT</span>
      </div>
    </div>

    <!-- 登录卡片 -->
    <div class="login-card">
      <!-- 顶部发光线 -->
      <div class="card-glow-line"></div>
      <!-- 角落装饰 -->
      <div class="corner-deco corner-tl"></div>
      <div class="corner-deco corner-tr"></div>
      <div class="corner-deco corner-bl"></div>
      <div class="corner-deco corner-br"></div>

      <!-- 卡片标题 -->
      <div class="card-header">
        <div class="title-icon">
          <svg viewBox="0 0 32 32" width="32" height="32">
            <defs>
              <linearGradient id="tg" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" style="stop-color:#818cf8"/>
                <stop offset="100%" style="stop-color:#a78bfa"/>
              </linearGradient>
            </defs>
            <path d="M16 3 L28 10 L28 18 C28 25 23 30 16 31 C9 30 4 25 4 18 L4 10 Z"
                  fill="url(#tg)" opacity="0.15" stroke="url(#tg)" stroke-width="1"/>
            <path d="M12 16 L15 19 L21 13" fill="none" stroke="#c4b5fd" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </div>
        <div class="card-title">欢迎使用智能品质检查系统</div>
      </div>

      <!-- Tab 切换（下划线风格） -->
      <div class="tab-bar">
        <div :class="['tab-item', mode === 'login' && 'tab-active']" @click="mode = 'login'">
          账号登录
          <div v-if="mode === 'login'" class="tab-underline"></div>
        </div>
        <div :class="['tab-item', mode === 'register' && 'tab-active']" @click="switchToRegister">
          账号注册
          <div v-if="mode === 'register'" class="tab-underline"></div>
        </div>
      </div>

      <!-- 登录表单 -->
      <van-form v-if="mode === 'login'" @submit="onLogin" class="login-form">
        <div class="field-wrapper">
          <div class="field-icon-bg">
            <van-icon name="manager-o" class="field-icon" />
          </div>
          <van-field
            v-model="loginForm.account"
            placeholder="请输入账号"
            :rules="[{ required: true, message: '请填写账号' }]"
          />
        </div>
        <div class="field-wrapper">
          <div class="field-icon-bg">
            <van-icon name="lock" class="field-icon" />
          </div>
          <van-field
            v-model="loginForm.password"
            :type="showLoginPwd ? 'text' : 'password'"
            placeholder="请输入密码"
            :rules="[{ required: true, message: '请填写密码' }]"
            :right-icon="showLoginPwd ? 'eye-o' : 'closed-eye'"
            @click-right-icon="showLoginPwd = !showLoginPwd"
          />
        </div>

        <div class="form-extra">
          <van-checkbox v-model="rememberMe" shape="square" icon-size="14px">
            <span class="checkbox-text">记住密码</span>
          </van-checkbox>
          <span class="forgot-link" @click="showForgotTip">忘记密码?</span>
        </div>

        <van-button block type="primary" native-type="submit" :loading="loading" class="submit-btn">
          <span class="btn-text">登 录</span>
          <div class="btn-shimmer"></div>
        </van-button>

      </van-form>

      <!-- 注册表单 -->
      <van-form v-else @submit="onRegister" class="login-form">
        <div class="field-wrapper">
          <div class="field-icon-bg">
            <van-icon name="phone-o" class="field-icon" />
          </div>
          <van-field
            v-model="registerForm.phone"
            type="tel"
            placeholder="请输入11位手机号"
            maxlength="11"
            :rules="[
              { required: true, message: '请填写手机号' },
              { pattern: /^1[3-9]\d{9}$/, message: '手机号格式不正确' }
            ]"
          />
        </div>
        <div class="field-wrapper">
          <div class="field-icon-bg">
            <van-icon name="user-o" class="field-icon" />
          </div>
          <van-field
            v-model="registerForm.real_name"
            placeholder="请输入真实姓名"
            :rules="[{ required: true, message: '请填写姓名' }]"
          />
        </div>
        <div class="field-wrapper" @click="openProjectPicker">
          <div class="field-icon-bg">
            <van-icon name="location-o" class="field-icon" />
          </div>
          <van-field
            v-model="selectedProjectName"
            placeholder="请选择所属项目"
            readonly
            :rules="[{ required: true, message: '请选择所属项目' }]"
          />
          <van-icon name="arrow-down" class="field-arrow" />
        </div>
        <div class="field-wrapper">
          <div class="field-icon-bg">
            <van-icon name="lock" class="field-icon" />
          </div>
          <van-field
            v-model="registerForm.password"
            :type="showRegPwd ? 'text' : 'password'"
            placeholder="请设置密码（字母+数字，不少于8位）"
            :rules="[
              { required: true, message: '请填写密码' },
              { validator: (val) => val.length >= 8 && /[a-zA-Z]/.test(val) && /\d/.test(val), message: '密码需包含字母和数字，不少于8位' }
            ]"
            :right-icon="showRegPwd ? 'eye-o' : 'closed-eye'"
            @click-right-icon="showRegPwd = !showRegPwd"
          />
        </div>
        <div class="field-wrapper">
          <div class="field-icon-bg">
            <van-icon name="lock" class="field-icon" />
          </div>
          <van-field
            v-model="registerForm.confirmPassword"
            :type="showRegConfirmPwd ? 'text' : 'password'"
            placeholder="请再次输入密码"
            :rules="[
              { required: true, message: '请确认密码' },
              { validator: (val) => val === registerForm.password, message: '两次密码不一致' }
            ]"
            :right-icon="showRegConfirmPwd ? 'eye-o' : 'closed-eye'"
            @click-right-icon="showRegConfirmPwd = !showRegConfirmPwd"
          />
        </div>

        <van-button block type="primary" native-type="submit" :loading="loading" class="submit-btn">
          <span class="btn-text">注 册</span>
          <div class="btn-shimmer"></div>
        </van-button>

      </van-form>
    </div>

    <!-- 底部通知栏 -->
    <div class="bottom-notice">
      <div class="notice-dot"></div>
      <span class="notice-date">{{ currentDate }}</span>
      <span class="notice-divider">|</span>
      <span class="notice-text">品质检查系统 · 智能质量管理平台</span>
    </div>

    <!-- 底部版权 -->
    <div class="footer">
      <p>© 2026 品质检查系统 · Quality Inspection Platform</p>
    </div>

    <!-- 项目选择弹出层 -->
    <van-popup v-model:show="showProjectPicker" position="bottom" round>
      <van-picker
        title="选择所属项目"
        :columns="projectColumns"
        @confirm="onProjectConfirm"
        @cancel="showProjectPicker = false"
      />
    </van-popup>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { showToast, showSuccessToast, showDialog, closeToast } from 'vant'
import { useAuthStore } from '../../stores/auth'
import { register } from '../../api/auth'
import { getProjects } from '../../api/tasks'

const router = useRouter()
const authStore = useAuthStore()

const mode = ref('login')
const loading = ref(false)
const showLoginPwd = ref(false)
const showRegPwd = ref(false)
const showRegConfirmPwd = ref(false)
const rememberMe = ref(false)
const projects = ref([])
const showProjectPicker = ref(false)

// 动态加载项目列表
onMounted(async () => {
  try {
    const res = await getProjects()
    projects.value = res.items || res || []
  } catch (e) {
    console.error('加载项目列表失败', e)
  }
})

const currentDate = computed(() => {
  const d = new Date()
  return `${d.getFullYear()}年${d.getMonth() + 1}月${d.getDate()}日`
})

const selectedProjectName = computed(() => {
  const p = projects.value.find(p => p.id === registerForm.project_id)
  return p ? p.name : ''
})

const projectColumns = computed(() =>
  projects.value.map(p => ({ text: p.name, value: p.id }))
)

const onProjectConfirm = ({ selectedOptions }) => {
  const selected = selectedOptions[0]
  registerForm.project_id = selected.value
  registerForm.project_name = selected.text
  showProjectPicker.value = false
}

const openProjectPicker = () => {
  showProjectPicker.value = true
}

const loginForm = reactive({
  account: '',
  password: ''
})

const registerForm = reactive({
  phone: '',
  real_name: '',
  project_id: null,
  project_name: null,
  password: '',
  confirmPassword: ''
})

const switchToRegister = () => {
  registerForm.phone = ''
  registerForm.real_name = ''
  registerForm.project_id = null
  registerForm.project_name = null
  registerForm.password = ''
  registerForm.confirmPassword = ''
  mode.value = 'register'
}

const showForgotTip = () => {
  showDialog({
    title: '忘记密码',
    message: '请联系系统管理员重置密码',
    confirmButtonText: '我知道了'
  })
}

const onLogin = async () => {
  loading.value = true
  try {
    const res = await authStore.login(loginForm.account, loginForm.password)
    showSuccessToast('登录成功')
    // 延迟跳转，等待Toast动画完成，防止弹窗DOM残留
    await new Promise(r => setTimeout(r, 300))
    if (res.user.must_change_pwd) {
      router.push('/change-password')
    } else {
      const isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent) || window.innerWidth < 768
      router.push(isMobile ? '/tasks' : '/pc/tasks')
    }
  } catch (error) {
    showToast('登录失败：' + (error.response?.data?.detail || '请检查账号密码'))
  } finally {
    loading.value = false
  }
}

const onRegister = async () => {
  // ★ 注册前验证项目选择
  if (!registerForm.project_name) {
    // 如果 project_name 丢失，从 projects 列表按 project_id 反查（防御性编程）
    if (registerForm.project_id) {
      const found = projects.value.find(p => p.id === registerForm.project_id)
      if (found) {
        registerForm.project_name = found.name
        console.warn('[注册] project_name 丢失，已从项目列表反查恢复:', found.name)
      }
    }
  }
  if (!registerForm.project_name) {
    showToast('请先选择所属项目')
    return
  }

  loading.value = true
  try {
    // 清除旧的登录态，不影响当前表单数据
    localStorage.removeItem('token')
    localStorage.removeItem('user')

    const submitData = {
      phone: registerForm.phone,
      real_name: registerForm.real_name,
      project_id: registerForm.project_id,
      project_name: registerForm.project_name,
      password: registerForm.password
    }

    console.log('[注册] 提交数据:', JSON.stringify(submitData))

    const res = await register(submitData)

    // ★ 验证后端返回的项目归属是否与用户选择一致
    if (res.user) {
      const returnedProjectName = res.user.project_name
      const selectedProjectName = registerForm.project_name
      if (returnedProjectName && returnedProjectName !== selectedProjectName) {
        console.error(`[注册] ★ 项目归属不一致！用户选择=${selectedProjectName}, 后端返回=${returnedProjectName}`)
        showToast(`项目归属异常：${returnedProjectName}，请联系管理员`)
        loading.value = false
        return
      }
      console.log(`[注册] 项目归属验证通过: ${returnedProjectName} (id=${res.user.project_id})`)
    }

    authStore.token = res.access_token
    authStore.user = res.user
    localStorage.setItem('token', res.access_token)
    localStorage.setItem('user', JSON.stringify(res.user))
    showSuccessToast('注册成功')
    // 延迟跳转，等待Toast动画完成，防止弹窗DOM残留
    await new Promise(r => setTimeout(r, 300))
    router.push('/tasks')
  } catch (error) {
    showToast('注册失败：' + (error.response?.data?.detail || '请检查输入信息'))
  } finally {
    loading.value = false
  }
}

onUnmounted(() => {
  closeToast()
})
</script>

<style scoped>
/* ========== 页面基础 ========== */
.login-page {
  min-height: 100vh;
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 20px 20px 90px;
  overflow: hidden;
  background: #050510;
}

/* 多层背景 */
.bg-base {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(ellipse 80% 50% at 25% 15%, rgba(124, 58, 237, 0.2) 0%, transparent 50%),
    radial-gradient(ellipse 50% 40% at 75% 85%, rgba(79, 70, 229, 0.12) 0%, transparent 50%),
    linear-gradient(180deg, #0f0b2a 0%, #080620 50%, #050510 100%);
  z-index: 0;
}

.bg-nebula {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(ellipse 40% 30% at 60% 20%, rgba(168, 85, 247, 0.08) 0%, transparent 60%),
    radial-gradient(ellipse 35% 25% at 30% 70%, rgba(99, 102, 241, 0.06) 0%, transparent 60%),
    radial-gradient(ellipse 50% 35% at 80% 50%, rgba(139, 92, 246, 0.05) 0%, transparent 55%);
  animation: nebula-drift 20s ease-in-out infinite alternate;
  z-index: 0;
}

.bg-stars {
  position: absolute;
  inset: 0;
  background-image:
    radial-gradient(1px 1px at 10% 15%, rgba(255,255,255,0.4), transparent),
    radial-gradient(1px 1px at 25% 75%, rgba(255,255,255,0.3), transparent),
    radial-gradient(1px 1px at 45% 8%, rgba(255,255,255,0.35), transparent),
    radial-gradient(1.5px 1.5px at 65% 35%, rgba(196,181,253,0.5), transparent),
    radial-gradient(1px 1px at 80% 70%, rgba(255,255,255,0.25), transparent),
    radial-gradient(1px 1px at 92% 20%, rgba(255,255,255,0.3), transparent),
    radial-gradient(1px 1px at 5% 55%, rgba(255,255,255,0.2), transparent),
    radial-gradient(1.5px 1.5px at 35% 40%, rgba(167,139,250,0.45), transparent),
    radial-gradient(1px 1px at 55% 85%, rgba(255,255,255,0.3), transparent),
    radial-gradient(1px 1px at 72% 55%, rgba(255,255,255,0.25), transparent),
    radial-gradient(1px 1px at 18% 92%, rgba(255,255,255,0.2), transparent),
    radial-gradient(1.5px 1.5px at 88% 90%, rgba(129,140,248,0.4), transparent);
  z-index: 0;
}

.bg-aurora {
  position: absolute;
  top: -50%;
  left: -50%;
  width: 200%;
  height: 200%;
  background: conic-gradient(from 0deg at 50% 50%,
    transparent 0deg,
    rgba(124, 58, 237, 0.03) 60deg,
    transparent 120deg,
    rgba(99, 102, 241, 0.02) 200deg,
    transparent 280deg,
    rgba(139, 92, 246, 0.03) 340deg,
    transparent 360deg
  );
  animation: aurora-rotate 30s linear infinite;
  z-index: 0;
}

@keyframes nebula-drift {
  0% { transform: translate(0, 0) scale(1); }
  100% { transform: translate(10px, -10px) scale(1.05); }
}

@keyframes aurora-rotate {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* ========== 宇宙传送门 ========== */
.portal-wrapper {
  position: absolute;
  top: -60px;
  left: -100px;
  width: 360px;
  height: 360px;
  z-index: 0;
  pointer-events: none;
}

.portal-ring {
  position: absolute;
  border-radius: 50%;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
}

.ring-1 {
  width: 360px;
  height: 360px;
  border: 1px solid rgba(139, 92, 246, 0.1);
  background: radial-gradient(circle, rgba(139, 92, 246, 0.05) 0%, transparent 70%);
  box-shadow: 0 0 60px rgba(139, 92, 246, 0.06), inset 0 0 60px rgba(139, 92, 246, 0.03);
  animation: ring-rotate 25s linear infinite;
}

.ring-2 {
  width: 280px;
  height: 280px;
  border: 1px solid rgba(99, 102, 241, 0.18);
  background: radial-gradient(circle, rgba(99, 102, 241, 0.1) 0%, transparent 70%);
  box-shadow: 0 0 40px rgba(99, 102, 241, 0.08);
  animation: ring-rotate 18s linear infinite reverse;
}

.ring-3 {
  width: 200px;
  height: 200px;
  border: 1.5px solid rgba(168, 85, 247, 0.28);
  background: radial-gradient(circle, rgba(168, 85, 247, 0.12) 0%, transparent 60%);
  box-shadow: 0 0 30px rgba(168, 85, 247, 0.1), inset 0 0 30px rgba(168, 85, 247, 0.05);
  animation: ring-rotate 14s linear infinite;
}

.ring-4 {
  width: 130px;
  height: 130px;
  border: 1px solid rgba(196, 181, 253, 0.35);
  background: radial-gradient(circle, rgba(196, 181, 253, 0.15) 0%, transparent 60%);
  box-shadow: 0 0 20px rgba(139, 92, 246, 0.15);
  animation: ring-pulse 4s ease-in-out infinite;
}

.ring-5 {
  width: 80px;
  height: 80px;
  border: 1px solid rgba(232, 219, 254, 0.2);
  background: radial-gradient(circle, rgba(232, 219, 254, 0.1) 0%, transparent 60%);
  animation: ring-rotate 8s linear infinite reverse;
}

.portal-core {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 50px;
  height: 50px;
  border-radius: 50%;
  background: radial-gradient(circle,
    rgba(232, 219, 254, 0.7) 0%,
    rgba(168, 85, 247, 0.5) 30%,
    rgba(124, 58, 237, 0.3) 60%,
    transparent 80%
  );
  box-shadow: 0 0 40px rgba(168, 85, 247, 0.4), 0 0 80px rgba(124, 58, 237, 0.2);
  animation: core-breathe 3s ease-in-out infinite;
}

.portal-pulse {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  border-radius: 50%;
  border: 1px solid rgba(168, 85, 247, 0.4);
  box-shadow: 0 0 15px rgba(168, 85, 247, 0.2);
}

.pulse-1 {
  width: 50px;
  height: 50px;
  animation: portal-expand 3s ease-out infinite;
}

.pulse-2 {
  width: 50px;
  height: 50px;
  animation: portal-expand 3s ease-out infinite 1.5s;
}

/* 粒子 */
.particle {
  position: absolute;
  width: 3px;
  height: 3px;
  border-radius: 50%;
  background: rgba(196, 181, 253, 0.8);
  top: 50%;
  left: 50%;
  box-shadow: 0 0 6px rgba(168, 85, 247, 0.4);
}

.p1 { animation: orbit1 8s linear infinite; }
.p2 { animation: orbit2 10s linear infinite; width: 2px; height: 2px; background: rgba(129, 140, 248, 0.9); }
.p3 { animation: orbit3 7s linear infinite; width: 4px; height: 4px; background: rgba(232, 219, 254, 0.7); }
.p4 { animation: orbit4 12s linear infinite; width: 2px; height: 2px; background: rgba(196, 181, 253, 0.7); }
.p5 { animation: orbit5 9s linear infinite; width: 3px; height: 3px; background: rgba(129, 140, 248, 0.8); }
.p6 { animation: orbit6 11s linear infinite; width: 2px; height: 2px; background: rgba(99, 102, 241, 0.8); }
.p7 { animation: orbit7 6s linear infinite; width: 2px; height: 2px; background: rgba(232, 219, 254, 0.6); }
.p8 { animation: orbit8 14s linear infinite; width: 3px; height: 3px; background: rgba(139, 92, 246, 0.7); }
.p9 { animation: orbit9 16s linear infinite; width: 2px; height: 2px; background: rgba(196, 181, 253, 0.6); }
.p10 { animation: orbit10 13s linear infinite; width: 2px; height: 2px; background: rgba(129, 140, 248, 0.7); }

/* 光束 */
.light-beam {
  position: absolute;
  top: 50%;
  left: 50%;
  width: 280px;
  height: 2px;
  transform-origin: left center;
}

.beam-1 {
  transform: rotate(-25deg);
  background: linear-gradient(90deg, rgba(139, 92, 246, 0.5), rgba(236, 72, 153, 0.25), transparent);
  filter: blur(0.5px);
  animation: beam-fade 4s ease-in-out infinite;
}

.beam-2 {
  transform: rotate(200deg);
  background: linear-gradient(90deg, rgba(99, 102, 241, 0.4), rgba(168, 85, 247, 0.2), transparent);
  filter: blur(0.5px);
  animation: beam-fade 4s ease-in-out infinite 2s;
  width: 200px;
}

.beam-3 {
  transform: rotate(110deg);
  background: linear-gradient(90deg, rgba(168, 85, 247, 0.3), rgba(236, 72, 153, 0.15), transparent);
  filter: blur(0.5px);
  animation: beam-fade 5s ease-in-out infinite 1s;
  width: 160px;
  height: 1px;
}

/* ========== 漂浮粒子 ========== */
.floating-dots {
  position: absolute;
  inset: 0;
  z-index: 0;
  pointer-events: none;
}

.dot {
  position: absolute;
  border-radius: 50%;
  opacity: 0;
  animation: float-up 8s ease-in-out infinite;
}

.d1 { left: 10%; width: 3px; height: 3px; background: rgba(167,139,250,0.6); animation-delay: 0s; }
.d2 { left: 25%; width: 2px; height: 2px; background: rgba(129,140,248,0.5); animation-delay: 1s; }
.d3 { left: 45%; width: 4px; height: 4px; background: rgba(196,181,253,0.4); animation-delay: 2s; }
.d4 { left: 65%; width: 2px; height: 2px; background: rgba(139,92,246,0.5); animation-delay: 3s; }
.d5 { left: 80%; width: 3px; height: 3px; background: rgba(99,102,241,0.4); animation-delay: 4s; }
.d6 { left: 35%; width: 2px; height: 2px; background: rgba(232,219,254,0.3); animation-delay: 5s; }
.d7 { left: 55%; width: 2px; height: 2px; background: rgba(167,139,250,0.5); animation-delay: 6s; }
.d8 { left: 90%; width: 3px; height: 3px; background: rgba(129,140,248,0.4); animation-delay: 7s; }

@keyframes float-up {
  0% { bottom: -5%; opacity: 0; transform: translateX(0); }
  10% { opacity: 0.6; }
  90% { opacity: 0.6; }
  100% { bottom: 105%; opacity: 0; transform: translateX(20px); }
}

/* 模糊球 */
.orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(80px);
  z-index: 0;
  pointer-events: none;
}

.orb-left {
  bottom: 15%;
  left: -60px;
  width: 220px;
  height: 220px;
  background: rgba(124, 58, 237, 0.1);
}

.orb-right {
  bottom: 5%;
  right: -50px;
  width: 180px;
  height: 180px;
  background: rgba(168, 85, 247, 0.08);
}

/* ========== 动画 ========== */
@keyframes ring-rotate {
  from { transform: translate(-50%, -50%) rotate(0deg); }
  to { transform: translate(-50%, -50%) rotate(360deg); }
}

@keyframes ring-pulse {
  0%, 100% { transform: translate(-50%, -50%) scale(1); opacity: 0.7; }
  50% { transform: translate(-50%, -50%) scale(1.1); opacity: 1; }
}

@keyframes core-breathe {
  0%, 100% { transform: translate(-50%, -50%) scale(1); opacity: 0.9; }
  50% { transform: translate(-50%, -50%) scale(1.2); opacity: 1; }
}

@keyframes portal-expand {
  0% { width: 50px; height: 50px; opacity: 0.6; transform: translate(-50%, -50%); }
  100% { width: 200px; height: 200px; opacity: 0; transform: translate(-50%, -50%); }
}

@keyframes beam-fade {
  0%, 100% { opacity: 0.4; }
  50% { opacity: 1; }
}

@keyframes orbit1 { from { transform: rotate(0deg) translateX(110px) rotate(0deg); } to { transform: rotate(360deg) translateX(110px) rotate(-360deg); } }
@keyframes orbit2 { from { transform: rotate(45deg) translateX(135px) rotate(-45deg); } to { transform: rotate(405deg) translateX(135px) rotate(-405deg); } }
@keyframes orbit3 { from { transform: rotate(90deg) translateX(80px) rotate(-90deg); } to { transform: rotate(450deg) translateX(80px) rotate(-450deg); } }
@keyframes orbit4 { from { transform: rotate(135deg) translateX(155px) rotate(-135deg); } to { transform: rotate(495deg) translateX(155px) rotate(-495deg); } }
@keyframes orbit5 { from { transform: rotate(180deg) translateX(95px) rotate(-180deg); } to { transform: rotate(540deg) translateX(95px) rotate(-540deg); } }
@keyframes orbit6 { from { transform: rotate(225deg) translateX(145px) rotate(-225deg); } to { transform: rotate(585deg) translateX(145px) rotate(-585deg); } }
@keyframes orbit7 { from { transform: rotate(270deg) translateX(65px) rotate(-270deg); } to { transform: rotate(630deg) translateX(65px) rotate(-630deg); } }
@keyframes orbit8 { from { transform: rotate(30deg) translateX(160px) rotate(-30deg); } to { transform: rotate(390deg) translateX(160px) rotate(-390deg); } }
@keyframes orbit9 { from { transform: rotate(160deg) translateX(125px) rotate(-160deg); } to { transform: rotate(520deg) translateX(125px) rotate(-520deg); } }
@keyframes orbit10 { from { transform: rotate(300deg) translateX(100px) rotate(-300deg); } to { transform: rotate(660deg) translateX(100px) rotate(-660deg); } }

/* ========== 左上 Logo ========== */
.top-logo {
  position: absolute;
  top: 18px;
  left: 18px;
  display: flex;
  align-items: center;
  gap: 10px;
  z-index: 2;
}

.logo-mark {
  width: 44px;
  height: 44px;
  position: relative;
  filter: drop-shadow(0 0 10px rgba(139,92,246,0.5));
  animation: mark-breathe 4s ease-in-out infinite;
}

@keyframes mark-breathe {
  0%, 100% { filter: drop-shadow(0 0 10px rgba(139,92,246,0.4)); }
  50% { filter: drop-shadow(0 0 18px rgba(139,92,246,0.7)); }
}

.logo-text-group {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.logo-title {
  font-size: 16px;
  color: #ffffff;
  font-weight: 700;
  letter-spacing: 3px;
  line-height: 1.2;
  text-shadow: 0 0 12px rgba(139,92,246,0.3);
}

.logo-subtitle {
  font-size: 8px;
  color: rgba(196,181,253,0.55);
  font-weight: 500;
  letter-spacing: 2.5px;
  text-transform: uppercase;
}

/* ========== 登录卡片 ========== */
.login-card {
  width: 100%;
  max-width: 380px;
  background: rgba(15, 15, 35, 0.85);
  backdrop-filter: blur(24px);
  -webkit-backdrop-filter: blur(24px);
  border: 1px solid rgba(139, 92, 246, 0.15);
  border-radius: 16px;
  padding: 30px 28px;
  z-index: 1;
  position: relative;
  overflow: hidden;
  box-shadow:
    0 8px 32px rgba(0, 0, 0, 0.4),
    0 0 60px rgba(124, 58, 237, 0.06),
    inset 0 1px 0 rgba(255, 255, 255, 0.05);
}

/* 顶部发光线 */
.card-glow-line {
  position: absolute;
  top: 0;
  left: 15%;
  right: 15%;
  height: 2px;
  background: linear-gradient(90deg, transparent, rgba(139, 92, 246, 0.6), rgba(99, 102, 241, 0.8), rgba(139, 92, 246, 0.6), transparent);
  filter: blur(1px);
  box-shadow: 0 0 12px rgba(139, 92, 246, 0.3);
}

/* 角落装饰 */
.corner-deco {
  position: absolute;
  width: 20px;
  height: 20px;
  border-color: rgba(139, 92, 246, 0.2);
  border-style: solid;
}

.corner-tl { top: 8px; left: 8px; border-width: 1px 0 0 1px; border-radius: 4px 0 0 0; }
.corner-tr { top: 8px; right: 8px; border-width: 1px 1px 0 0; border-radius: 0 4px 0 0; }
.corner-bl { bottom: 8px; left: 8px; border-width: 0 0 1px 1px; border-radius: 0 0 0 4px; }
.corner-br { bottom: 8px; right: 8px; border-width: 0 1px 1px 0; border-radius: 0 0 4px 0; }

/* 卡片头部 */
.card-header {
  display: flex;
  flex-direction: column;
  align-items: center;
  margin-bottom: 22px;
}

.title-icon {
  margin-bottom: 12px;
  animation: emblem-float 4s ease-in-out infinite;
  filter: drop-shadow(0 0 8px rgba(167,139,250,0.3));
}

@keyframes emblem-float {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-4px); }
}

.card-title {
  font-size: 20px;
  font-weight: 700;
  background: linear-gradient(135deg, #e0e7ff 0%, #c4b5fd 50%, #a78bfa 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  letter-spacing: 1px;
}

/* ========== Tab 下划线风格 ========== */
.tab-bar {
  display: flex;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  margin-bottom: 24px;
}

.tab-item {
  flex: 1;
  text-align: center;
  padding: 10px 0;
  font-size: 14px;
  color: #666666;
  cursor: pointer;
  position: relative;
  transition: color 0.3s;
}

.tab-item.tab-active {
  color: #ffffff;
}

.tab-underline {
  position: absolute;
  bottom: -1px;
  left: 15%;
  right: 15%;
  height: 2px;
  background: linear-gradient(90deg, #7c3aed, #6366f1, #818cf8);
  border-radius: 1px;
  box-shadow: 0 0 8px rgba(124, 58, 237, 0.4);
}

/* ========== 表单字段 ========== */
.login-form {
  width: 100%;
}

.field-wrapper {
  display: flex;
  align-items: center;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 8px;
  margin-bottom: 14px;
  transition: all 0.3s ease;
  overflow: hidden;
}

.field-wrapper:focus-within {
  border-color: rgba(139, 92, 246, 0.4);
  background: rgba(139, 92, 246, 0.04);
  box-shadow: 0 0 20px rgba(139, 92, 246, 0.08), inset 0 0 20px rgba(139, 92, 246, 0.02);
}

.field-icon-bg {
  width: 38px;
  height: 38px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(139, 92, 246, 0.08);
  border-right: 1px solid rgba(255, 255, 255, 0.06);
  flex-shrink: 0;
  margin: 1px 0 1px 1px;
  border-radius: 6px 0 0 6px;
}

.field-wrapper:focus-within .field-icon-bg {
  background: rgba(139, 92, 246, 0.15);
}

.field-icon {
  color: rgba(167, 139, 250, 0.6);
  font-size: 16px;
}

.field-wrapper:focus-within .field-icon {
  color: rgba(167, 139, 250, 0.9);
}

.field-wrapper :deep(.van-cell) {
  background: transparent;
  padding: 10px 12px 10px 10px;
}

.field-wrapper :deep(.van-cell::after) {
  display: none;
}

.field-wrapper :deep(.van-field__label) {
  display: none;
}

.field-wrapper :deep(.van-field__control) {
  color: #ffffff;
  font-size: 14px;
}

.field-wrapper :deep(.van-field__control::placeholder) {
  color: #666666;
}

.field-wrapper :deep(.van-field__right-icon) {
  color: #666666;
}

.field-arrow {
  color: #666666;
  font-size: 12px;
  margin-right: 12px;
}

.field-wrapper :deep(.van-field--error) {
  background: transparent;
}

.field-wrapper :deep(.van-field__error-message) {
  color: rgba(248, 113, 113, 0.8);
  font-size: 12px;
  padding-top: 2px;
}

/* ========== 记住密码 & 忘记密码 ========== */
.form-extra {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 18px;
  padding: 0 2px;
}

.form-extra :deep(.van-checkbox__label) {
  margin-left: 4px;
}

.checkbox-text {
  font-size: 12px;
  color: #aaaaaa;
}

.form-extra :deep(.van-checkbox__icon) {
  background: transparent;
  border-color: rgba(255, 255, 255, 0.2);
}

.form-extra :deep(.van-checkbox__icon--checked .van-icon) {
  background: linear-gradient(135deg, #7c3aed, #4f46e5);
  border-color: transparent;
}

.forgot-link {
  font-size: 12px;
  color: #888888;
  cursor: pointer;
  transition: color 0.2s;
}

.forgot-link:active {
  color: #c4b5fd;
}

/* ========== 提交按钮 ========== */
.submit-btn {
  background: linear-gradient(135deg, #7c3aed 0%, #6366f1 40%, #4f46e5 70%, #2563eb 100%) !important;
  border: none !important;
  border-radius: 8px !important;
  height: 44px !important;
  font-size: 15px !important;
  font-weight: 600 !important;
  letter-spacing: 4px;
  box-shadow:
    0 6px 20px rgba(124, 58, 237, 0.35),
    0 0 40px rgba(99, 102, 241, 0.1);
  transition: all 0.3s ease;
  position: relative;
  overflow: hidden;
}

.btn-text {
  position: relative;
  z-index: 1;
}

.btn-shimmer {
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.2), transparent);
  animation: shimmer 3s ease-in-out infinite;
}

@keyframes shimmer {
  0% { left: -100%; }
  50% { left: 100%; }
  100% { left: 100%; }
}

.submit-btn:active {
  box-shadow: 0 3px 12px rgba(124, 58, 237, 0.5), 0 0 50px rgba(99, 102, 241, 0.15);
  transform: scale(0.98);
}

/* ========== 底部通知栏 ========== */
.bottom-notice {
  position: absolute;
  bottom: 44px;
  left: 16px;
  right: 16px;
  display: flex;
  align-items: center;
  gap: 8px;
  background: rgba(15, 15, 35, 0.8);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(139, 92, 246, 0.1);
  border-radius: 8px;
  padding: 10px 14px;
  z-index: 1;
}

.notice-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #22c55e;
  box-shadow: 0 0 6px rgba(34, 197, 94, 0.5);
  animation: dot-blink 2s ease-in-out infinite;
  flex-shrink: 0;
}

@keyframes dot-blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

.notice-date {
  font-size: 12px;
  color: #aaaaaa;
  flex-shrink: 0;
}

.notice-divider {
  color: rgba(255, 255, 255, 0.15);
  font-size: 12px;
}

.notice-text {
  font-size: 12px;
  color: #aaaaaa;
}

/* ========== 底部版权 ========== */
.footer {
  position: absolute;
  bottom: 16px;
  text-align: center;
  z-index: 1;
  width: 100%;
}

.footer p {
  font-size: 11px;
  color: #555555;
  letter-spacing: 0.5px;
}
</style>
