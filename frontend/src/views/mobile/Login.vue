<template>
  <div class="login-page">
    <!-- 品牌头（原型 MLogin 结构） -->
    <div class="hero">
      <div class="hero-brand">
        <div class="brand-mark">
          <van-icon name="passed" />
        </div>
        <div>
          <div class="brand-name">AI 品质检查</div>
          <div class="brand-sub">QUALITY INSPECTION</div>
        </div>
      </div>
      <h1 class="hero-line">现场检查，AI 评分</h1>
      <p class="hero-sub">拍照留证 · 离线可用 · 自动生成报告与整改闭环</p>
    </div>

    <!-- 表单区 -->
    <div class="form-wrap">
      <div class="mode-tabs" role="tablist">
        <button
          type="button"
          :class="['mode-tab', mode === 'login' && 'on']"
          @click="mode = 'login'"
        >
          登录
        </button>
        <button
          type="button"
          :class="['mode-tab', mode === 'register' && 'on']"
          @click="switchToRegister"
        >
          注册
        </button>
      </div>

      <van-form v-if="mode === 'login'" @submit="onLogin" class="the-form">
        <div class="field-wrapper">
          <van-icon name="manager-o" class="field-icon" />
          <van-field
            v-model="loginForm.account"
            placeholder="手机号 / 账号"
            :rules="[{ required: true, message: '请填写账号' }]"
          />
        </div>

        <div class="field-wrapper">
          <van-icon name="lock" class="field-icon" />
          <van-field
            v-model="loginForm.password"
            :type="showLoginPwd ? 'text' : 'password'"
            placeholder="密码"
            :rules="[{ required: true, message: '请填写密码' }]"
            :right-icon="showLoginPwd ? 'eye-o' : 'closed-eye'"
            @click-right-icon="showLoginPwd = !showLoginPwd"
          />
        </div>

        <div class="form-extra">
          <van-checkbox v-model="keepSignedIn" shape="square" icon-size="14px">
            <span class="checkbox-text">保持登录</span>
          </van-checkbox>
          <button type="button" class="forgot-link" @click="showForgotTip">忘记密码</button>
        </div>

        <van-button block native-type="submit" :loading="loading" class="submit-btn">
          登录
        </van-button>
      </van-form>

      <van-form v-else @submit="onRegister" class="the-form">
        <div class="field-wrapper">
          <van-icon name="phone-o" class="field-icon" />
          <van-field
            v-model="registerForm.phone"
            type="tel"
            placeholder="手机号"
            maxlength="11"
            :rules="[
              { required: true, message: '请填写手机号' },
              { pattern: /^1[3-9]\d{9}$/, message: '手机号格式不正确' }
            ]"
          />
        </div>

        <div class="field-wrapper">
          <van-icon name="user-o" class="field-icon" />
          <van-field
            v-model="registerForm.real_name"
            placeholder="真实姓名"
            :rules="[{ required: true, message: '请填写姓名' }]"
          />
        </div>

        <div class="field-wrapper selectable" @click="openProjectPicker">
          <van-icon name="location-o" class="field-icon" />
          <div class="selected-projects">
            <template v-if="selectedProjects.length">
              <span v-for="(project, index) in selectedProjects" :key="project.id" class="project-tag">
                {{ project.name }}
                <em v-if="index === 0">默认</em>
              </span>
            </template>
            <span v-else class="project-placeholder">所属项目（可多选）</span>
          </div>
          <van-icon name="arrow-down" class="field-arrow" />
        </div>

        <div class="reg-note">
          <van-icon name="info-o" />
          <span>注册需选择所属项目，由管理员审核后启用</span>
        </div>

        <div class="field-wrapper">
          <van-icon name="lock" class="field-icon" />
          <van-field
            v-model="registerForm.password"
            :type="showRegPwd ? 'text' : 'password'"
            placeholder="密码（字母+数字，不少于8位）"
            :rules="[
              { required: true, message: '请填写密码' },
              { validator: (val) => val.length >= 8 && /[a-zA-Z]/.test(val) && /\d/.test(val), message: '密码需包含字母和数字，不少于8位' }
            ]"
            :right-icon="showRegPwd ? 'eye-o' : 'closed-eye'"
            @click-right-icon="showRegPwd = !showRegPwd"
          />
        </div>

        <div class="field-wrapper">
          <van-icon name="lock" class="field-icon" />
          <van-field
            v-model="registerForm.confirmPassword"
            :type="showRegConfirmPwd ? 'text' : 'password'"
            placeholder="确认密码"
            :rules="[
              { required: true, message: '请确认密码' },
              { validator: (val) => val === registerForm.password, message: '两次密码不一致' }
            ]"
            :right-icon="showRegConfirmPwd ? 'eye-o' : 'closed-eye'"
            @click-right-icon="showRegConfirmPwd = !showRegConfirmPwd"
          />
        </div>

        <van-button block native-type="submit" :loading="loading" class="submit-btn">
          提交注册
        </van-button>
      </van-form>

      <div class="agreement-row">
        <van-checkbox v-model="agreementAccepted" shape="square" icon-size="14px" />
        <span>
          我已阅读并同意
          <button type="button" @click="openLegalDocument('service')">《服务协议》</button>
          与
          <button type="button" @click="openLegalDocument('privacy')">《隐私政策》</button>
        </span>
      </div>
    </div>

    <footer class="footer">
      <span>登录即代表同意相关条款 · © 2026 智能品质检查系统</span>
      <a href="https://beian.miit.gov.cn/" target="_blank" rel="noopener noreferrer">粤ICP备2026046557号</a>
    </footer>

    <van-popup v-model:show="showProjectPicker" position="bottom" round class="project-popup">
      <div class="project-picker">
        <div class="project-picker-header">
          <h3>选择所属项目</h3>
          <p>可多选，第一个选择的项目将作为默认项目</p>
        </div>
        <van-checkbox-group v-model="draftProjectIds" class="project-options">
          <van-checkbox
            v-for="project in projects"
            :key="project.id"
            :name="project.id"
            shape="square"
            class="project-option"
          >
            {{ project.name }}
          </van-checkbox>
        </van-checkbox-group>
        <div class="project-picker-summary">已选择 {{ draftProjectIds.length }} 个项目</div>
        <div class="project-picker-actions">
          <van-button class="project-cancel" @click="showProjectPicker = false">取消</van-button>
          <van-button class="project-confirm" @click="confirmProjects">确认选择</van-button>
        </div>
      </div>
    </van-popup>

    <van-popup v-model:show="showLegalDocument" position="bottom" round class="legal-popup">
      <article class="legal-document">
        <header class="legal-header">
          <div>
            <h3>{{ legalTitle }}</h3>
            <p>生效日期：2026年5月24日</p>
          </div>
          <button type="button" aria-label="关闭" @click="showLegalDocument = false">
            <van-icon name="cross" />
          </button>
        </header>

        <template v-if="legalType === 'service'">
          <section>
            <h4>一、服务内容</h4>
            <p>品质检查系统提供账号与项目关联、现场检查记录、问题照片上传、智能评分分析、检查报告生成及整改跟踪等服务，用于物业品质管理与工作协同。</p>
          </section>
          <section>
            <h4>二、账号注册与使用</h4>
            <p>您应提交真实、准确的信息，并仅选择您获授权参与的所属项目。账号仅限本人使用，您应妥善保管登录凭证并对账号下的操作承担责任。</p>
          </section>
          <section>
            <h4>三、检查资料与行为规范</h4>
            <p>您应确保录入的检查记录、问题描述、整改信息及上传照片真实、合法，并已取得必要授权。不得上传违法、不实、侵犯他人权益或与业务无关的内容，不得干扰系统正常运行。</p>
          </section>
          <section>
            <h4>四、智能分析说明</h4>
            <p>系统可能使用智能能力辅助形成评分建议、问题分析与报告内容。相关输出用于辅助管理和复核，不替代有权限人员作出的最终业务判断。</p>
          </section>
          <section>
            <h4>五、服务调整与责任范围</h4>
            <p>为维护安全和优化服务，系统可进行功能升级或必要维护。因网络故障、不可抗力、用户违规操作等非运营方可控原因造成的影响，将在法律允许范围内处理。</p>
          </section>
          <section>
            <h4>六、协议变更与联系</h4>
            <p>协议更新后将在系统中提示或公示。您继续使用服务即表示接受更新内容；如有异议，可停止使用并联系运营方处理。</p>
          </section>
        </template>

        <template v-else>
          <section>
            <h4>一、处理者信息</h4>
            <p>本系统个人信息处理者为李英群。我们依据合法、正当、必要和诚信原则处理您的个人信息。</p>
          </section>
          <section>
            <h4>二、收集的信息</h4>
            <p>为提供服务，我们可能处理您的手机号、姓名、所属项目、登录凭证的加密校验信息、登录及安全日志，以及您在业务过程中提交的检查任务、问题描述、照片、整改记录、评分与报告信息。</p>
          </section>
          <section>
            <h4>三、处理目的</h4>
            <p>上述信息用于注册登录、项目权限管理、检查与整改闭环、评分分析与报告生成、运行安全审计、故障排查和用户支持。密码不会以明文形式保存。</p>
          </section>
          <section>
            <h4>四、共享与委托处理</h4>
            <p>我们不会出售您的个人信息。为实现系统托管、存储或智能分析等必要功能，可能向服务提供方委托处理与功能所需的最小范围信息；法律法规要求提供的除外。</p>
          </section>
          <section>
            <h4>五、保存与安全</h4>
            <p>我们在实现业务目的和满足法定义务所必要的期限内保存信息，并采取访问控制、身份鉴权、日志审计等措施降低未经授权访问、泄露或篡改风险。</p>
          </section>
          <section>
            <h4>六、您的权利</h4>
            <p>您可联系我们申请查询、更正、删除个人信息，撤回同意或申请注销账号。撤回同意不影响撤回前已开展的处理；必要信息缺失可能导致部分服务无法继续提供。</p>
          </section>
          <section>
            <h4>七、未成年人及政策更新</h4>
            <p>本系统面向物业品质管理工作人员，不面向未成年人提供服务。政策发生重要变化时，我们将通过系统提示或公示方式告知您。</p>
          </section>
        </template>

        <div class="legal-contact">
          <strong>运营方 / 个人信息处理者：李英群</strong>
          <span>对外联系电话：<a href="tel:18578426218">18578426218</a></span>
        </div>
      </article>
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
const keepSignedIn = ref(false)
const agreementAccepted = ref(false)
const showLegalDocument = ref(false)
const legalType = ref('service')
const projects = ref([])
const showProjectPicker = ref(false)
const selectedProjectIds = ref([])
const draftProjectIds = ref([])

onMounted(async () => {
  try {
    const res = await getProjects()
    projects.value = res.items || res || []
  } catch (e) {
    console.error('加载项目列表失败', e)
  }
})

const selectedProjects = computed(() =>
  selectedProjectIds.value
    .map(id => projects.value.find(project => project.id === id))
    .filter(Boolean)
)

const legalTitle = computed(() => legalType.value === 'service' ? '服务协议' : '隐私政策')

const openLegalDocument = (type) => {
  legalType.value = type
  showLegalDocument.value = true
}

const validateAgreement = () => {
  if (!agreementAccepted.value) {
    showToast('请先阅读并同意《服务协议》与《隐私政策》')
    return false
  }
  return true
}

const openProjectPicker = () => {
  draftProjectIds.value = [...selectedProjectIds.value]
  showProjectPicker.value = true
}

const confirmProjects = () => {
  if (!draftProjectIds.value.length) {
    showToast('请至少选择一个所属项目')
    return
  }
  selectedProjectIds.value = [...draftProjectIds.value]
  registerForm.project_id = selectedProjectIds.value[0]
  registerForm.project_name = selectedProjects.value[0]?.name || null
  showProjectPicker.value = false
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
  selectedProjectIds.value = []
  draftProjectIds.value = []
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
  if (!validateAgreement()) return

  loading.value = true
  try {
    const res = await authStore.login(loginForm.account, loginForm.password, keepSignedIn.value)
    showSuccessToast('登录成功')
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
  if (!validateAgreement()) return

  if (!selectedProjects.value.length) {
    showToast('请至少选择一个所属项目')
    return
  }

  loading.value = true
  try {
    const selectedIds = selectedProjects.value.map(project => project.id)
    const selectedNames = selectedProjects.value.map(project => project.name)
    const submitData = {
      phone: registerForm.phone,
      real_name: registerForm.real_name,
      project_id: selectedIds[0],
      project_name: selectedNames[0],
      project_ids: selectedIds,
      project_names: selectedNames,
      password: registerForm.password
    }

    console.log('[注册] 提交数据:', JSON.stringify(submitData))

    const res = await register(submitData)

    if (res.user) {
      const returnedIds = (res.user.projects || []).map(project => project.id)
      const projectBindingMatches = returnedIds.length === selectedIds.length &&
        selectedIds.every((id, index) => returnedIds[index] === id) &&
        res.user.project_id === selectedIds[0]
      if (!projectBindingMatches) {
        console.error('[注册] 项目归属不一致', { selectedIds, returnedIds, defaultProjectId: res.user.project_id })
        showToast('项目归属异常，请联系管理员')
        loading.value = false
        return
      }
      console.log('[注册] 项目归属验证通过:', returnedIds)
    }

    authStore.applyAuthenticatedSession(res, false)
    showSuccessToast('注册成功')
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
/* ===== 品牌头（青绿渐变，原型 MLogin） ===== */
.login-page {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--bg);
  font-family: var(--sans);
  color: var(--ink-800);
}

.hero {
  background: linear-gradient(150deg, #14a094 0%, #0c7168 78%);
  padding: 30px 22px 34px;
  color: #fff;
}

.hero-brand {
  display: flex;
  align-items: center;
  gap: 9px;
}

.brand-mark {
  width: 38px;
  height: 38px;
  border-radius: 11px;
  background: rgba(255, 255, 255, 0.16);
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.22);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  flex-shrink: 0;
}

.brand-name {
  font-size: 17px;
  font-weight: 800;
  letter-spacing: 0.2px;
}

.brand-sub {
  margin-top: 2px;
  font-size: 10.5px;
  opacity: 0.75;
  letter-spacing: 0.6px;
}

.hero-line {
  margin: 24px 0 0;
  font-size: 22px;
  font-weight: 800;
  letter-spacing: -0.3px;
}

.hero-sub {
  margin: 6px 0 0;
  font-size: 12.5px;
  opacity: 0.78;
  line-height: 1.6;
}

/* ===== 表单区 ===== */
.form-wrap {
  width: 100%;
  max-width: 448px;
  margin: 0 auto;
  padding: 20px 20px 8px;
  flex: 1;
}

.mode-tabs {
  display: flex;
  gap: 22px;
  padding: 0 2px 12px;
}

.mode-tab {
  border: none;
  background: none;
  padding: 0 2px 8px;
  font-family: var(--sans);
  font-size: 16px;
  font-weight: 500;
  color: var(--ink-400);
  cursor: pointer;
  border-bottom: 2.5px solid transparent;
  transition: color 0.15s;
}

.mode-tab.on {
  font-weight: 800;
  color: var(--ink-900);
  border-bottom-color: var(--blue);
}

.the-form {
  display: grid;
  gap: 11px;
}

.field-wrapper {
  display: flex;
  align-items: center;
  min-height: 44px;
  border: 1px solid var(--ink-200);
  border-radius: var(--r);
  background: var(--bg-card);
  transition: border-color 0.15s, box-shadow 0.15s;
}

.field-wrapper:focus-within {
  border-color: var(--blue);
  box-shadow: var(--focus-ring);
}

.field-wrapper.selectable {
  cursor: pointer;
}

.field-icon {
  width: 42px;
  color: var(--ink-400);
  font-size: 17px;
  text-align: center;
  flex-shrink: 0;
}

.field-wrapper:focus-within .field-icon {
  color: var(--blue);
}

.field-wrapper :deep(.van-cell) {
  flex: 1;
  min-width: 0;
  padding: 0 12px 0 0;
  background: transparent;
}

.field-wrapper :deep(.van-cell::after) {
  display: none;
}

.field-wrapper :deep(.van-field__control) {
  color: var(--ink-900);
  font-size: 14.5px;
}

.field-wrapper :deep(.van-field__control::placeholder) {
  color: var(--ink-400);
}

.field-wrapper :deep(.van-field__right-icon) {
  color: var(--ink-400);
}

.field-wrapper :deep(.van-field__error-message) {
  color: var(--err-strong);
  padding-top: 4px;
  font-size: 12px;
}

.selected-projects {
  display: flex;
  flex: 1;
  flex-wrap: wrap;
  gap: 6px;
  min-width: 0;
  padding: 9px 4px 9px 0;
}

.project-placeholder {
  align-self: center;
  color: var(--ink-400);
  font-size: 14px;
}

.project-tag {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  max-width: 100%;
  padding: 4px 8px;
  border-radius: 6px;
  background: var(--blue-bg);
  color: var(--brand-ink);
  font-size: 12px;
}

.project-tag em {
  padding: 1px 4px;
  border-radius: 4px;
  background: var(--blue);
  color: #fff;
  font-size: 10px;
  font-style: normal;
}

.field-arrow {
  margin-right: 14px;
  color: var(--ink-400);
  font-size: 14px;
}

.reg-note {
  display: flex;
  gap: 7px;
  align-items: flex-start;
  padding: 9px 12px;
  border-radius: var(--r);
  background: var(--bg-muted);
  color: var(--ink-500);
  font-size: 12px;
  line-height: 1.6;
}

.reg-note .van-icon {
  margin-top: 2px;
  flex-shrink: 0;
}

.form-extra {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin: 2px 2px 4px;
}

.form-extra :deep(.van-checkbox__label) {
  margin-left: 6px;
}

.form-extra :deep(.van-checkbox__icon--checked .van-icon),
.agreement-row :deep(.van-checkbox__icon--checked .van-icon),
.project-option :deep(.van-checkbox__icon--checked .van-icon) {
  background: var(--blue);
  border-color: var(--blue);
}

.checkbox-text {
  font-size: 13px;
  color: var(--ink-500);
}

.forgot-link {
  padding: 0;
  border: 0;
  background: transparent;
  color: var(--blue);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}

.submit-btn {
  height: 44px !important;
  border: none !important;
  border-radius: var(--r) !important;
  background: var(--blue) !important;
  color: #ffffff !important;
  font-size: 15px !important;
  font-weight: 700 !important;
}

.submit-btn:active {
  transform: translateY(1px);
}

.agreement-row {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  margin-top: 16px;
  color: var(--ink-500);
  font-size: 12px;
  line-height: 1.65;
}

.agreement-row button {
  padding: 0;
  border: 0;
  background: transparent;
  color: var(--blue);
  font-size: inherit;
  cursor: pointer;
}

.footer {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 8px 20px 16px;
  color: var(--ink-400);
  font-size: 11px;
}

.footer a {
  color: var(--ink-400);
  text-decoration: none;
}

/* ===== 项目选择弹窗 ===== */
.project-popup {
  background: var(--bg-card);
}

.project-picker {
  padding: 22px 20px max(22px, env(safe-area-inset-bottom));
}

.project-picker-header h3 {
  margin: 0;
  color: var(--ink-900);
  font-size: 17px;
  font-weight: 700;
}

.project-picker-header p {
  margin: 8px 0 18px;
  color: var(--ink-500);
  font-size: 13px;
}

.project-options {
  max-height: 280px;
  overflow-y: auto;
  border-top: 1px solid var(--ink-100);
}

.project-option {
  min-height: 48px;
  padding: 0 2px;
  border-bottom: 1px solid var(--ink-100);
  color: var(--ink-800);
  font-size: 14px;
}

.project-picker-summary {
  margin: 16px 0;
  color: var(--ink-500);
  font-size: 13px;
}

.project-picker-actions {
  display: grid;
  grid-template-columns: 108px 1fr;
  gap: 12px;
}

.project-cancel,
.project-confirm {
  height: 44px !important;
  border-radius: var(--r) !important;
  font-size: 14px !important;
  font-weight: 600 !important;
}

.project-cancel {
  border-color: var(--ink-200) !important;
  color: var(--ink-600) !important;
}

.project-confirm {
  border-color: var(--blue) !important;
  background: var(--blue) !important;
  color: #ffffff !important;
}

/* ===== 协议弹窗 ===== */
.legal-popup {
  background: var(--bg-card);
}

.legal-document {
  max-width: 760px;
  max-height: min(82vh, 720px);
  margin: 0 auto;
  padding: 24px 26px max(28px, env(safe-area-inset-bottom));
  overflow-y: auto;
  color: var(--ink-800);
}

.legal-header {
  position: sticky;
  top: -24px;
  z-index: 1;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin: -24px -26px 18px;
  padding: 24px 26px 16px;
  border-bottom: 1px solid var(--ink-100);
  background: var(--bg-card);
}

.legal-header h3 {
  margin: 0;
  color: var(--ink-900);
  font-size: 19px;
}

.legal-header p {
  margin: 7px 0 0;
  color: var(--ink-400);
  font-size: 12px;
}

.legal-header button {
  width: 34px;
  height: 34px;
  border: 0;
  border-radius: var(--r-sm);
  background: var(--bg-muted);
  color: var(--ink-500);
  cursor: pointer;
}

.legal-document section {
  margin-bottom: 18px;
}

.legal-document h4 {
  margin: 0 0 7px;
  color: var(--ink-900);
  font-size: 14px;
}

.legal-document section p {
  margin: 0;
  color: var(--ink-600);
  font-size: 13px;
  line-height: 1.75;
}

.legal-contact {
  display: flex;
  flex-direction: column;
  gap: 5px;
  margin-top: 24px;
  padding: 15px 16px;
  border-radius: var(--r);
  background: var(--bg-muted);
  color: var(--ink-700);
  font-size: 13px;
}

.legal-contact a {
  color: var(--blue);
  text-decoration: none;
}

@media (min-width: 700px) {
  .hero {
    padding: 40px 32px 44px;
  }

  .form-wrap {
    padding-top: 28px;
  }
}
</style>
