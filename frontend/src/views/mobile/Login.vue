<template>
  <div class="login-page">
    <div class="login-shell">
    <!-- 品牌头（青绿渐变，原型 MLogin 结构） -->
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
      <div class="hero-eyebrow">
        <span class="eyebrow-dot" />AI 驱动的物业品质数字化平台
      </div>
      <h1 class="hero-line">现场检查，<br /><span class="grad-text">AI 评分与闭环管理</span></h1>
      <p class="hero-sub">拍照留证 · 离线可用 · 报告与整改自动生成</p>
      <div class="hero-chip">
        <span class="hc-num">96%</span>
        <span class="hc-txt">本月整改闭环率<small>较上月 +8pp</small></span>
      </div>
      <ul class="hero-feats">
        <li>
          <span class="feat-ico"><van-icon name="photograph" /></span>
          <div><b>拍照留证</b><span>时间地点水印，责任可溯</span></div>
        </li>
        <li>
          <span class="feat-ico"><van-icon name="description" /></span>
          <div><b>离线可用</b><span>弱网地库照常执行检查</span></div>
        </li>
        <li>
          <span class="feat-ico"><van-icon name="replay" /></span>
          <div><b>闭环管理</b><span>评分、报告、整改一体</span></div>
        </li>
      </ul>
    </div>

    <!-- 表单区 -->
    <div class="form-wrap">
      <div class="pane-head">
        <h3>欢迎回来</h3>
        <p>登录以继续品质检查工作台</p>
      </div>
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
    </div><!-- /login-shell -->

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

/* 特性清单仅桌面展示（移动端保持已批准原型） */
.hero-feats { display: none; }

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

/* ===== 桌面端（≥900px）：明亮清新 · 高级感双栏登录 ===== */
@media (min-width: 900px) {
  .login-page {
    box-sizing: border-box;
    min-height: 100vh;
    display: grid;
    place-items: center;
    padding: 44px 48px;
    position: relative;
    isolation: isolate;
    background:
      radial-gradient(1100px 700px at 80% -14%, rgba(20, 160, 148, 0.15), transparent 62%),
      radial-gradient(900px 620px at -12% 114%, rgba(94, 212, 198, 0.18), transparent 60%),
      linear-gradient(180deg, #f7fbfa 0%, #eef5f3 100%);
  }

  /* 氛围层1：清新点阵（边缘渐隐） */
  .login-page::before {
    content: "";
    position: absolute;
    inset: 0;
    z-index: -1;
    background-image: radial-gradient(rgba(15, 90, 82, 0.16) 1px, transparent 1.5px);
    background-size: 24px 24px;
    -webkit-mask-image: radial-gradient(75% 75% at 50% 42%, #000 25%, transparent 100%);
    mask-image: radial-gradient(75% 75% at 50% 42%, #000 25%, transparent 100%);
  }

  /* 氛围层2：噪点纹理（高级质感） */
  .login-page::after {
    content: "";
    position: absolute;
    inset: 0;
    z-index: -1;
    opacity: 0.55;
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='180' height='180'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.82' numOctaves='2' stitchTiles='stitch'/%3E%3CfeColorMatrix type='saturate' values='0'/%3E%3C/filter%3E%3Crect width='180' height='180' filter='url(%23n)' opacity='0.05'/%3E%3C/svg%3E");
  }

  /* ===== 玻璃白卡 ===== */
  .login-shell {
    position: relative;
    display: grid;
    grid-template-columns: 1.06fr 440px;
    width: min(1160px, 100%);
    min-height: 660px;
    background: rgba(255, 255, 255, 0.66);
    border: 1px solid rgba(255, 255, 255, 0.85);
    border-radius: 28px;
    box-shadow:
      0 2px 6px rgba(16, 40, 36, 0.04),
      0 40px 100px -24px rgba(16, 40, 36, 0.30);
    backdrop-filter: blur(24px) saturate(1.35);
    -webkit-backdrop-filter: blur(24px) saturate(1.35);
    overflow: hidden;
  }

  /* ===== 品牌面板 ===== */
  .hero {
    position: relative;
    padding: 48px 46px 42px;
    display: flex;
    flex-direction: column;
    background:
      radial-gradient(560px 420px at 108% 8%, rgba(20, 160, 148, 0.10), transparent 60%),
      linear-gradient(168deg, #eaf7f3 0%, #f8fcfb 55%, #ecf6f3 100%);
    border-right: 1px solid rgba(31, 62, 58, 0.06);
    overflow: hidden;
  }

  .hero::before {
    content: "";
    position: absolute;
    right: -110px;
    top: -130px;
    width: 340px;
    height: 340px;
    border-radius: 50%;
    border: 1.5px solid rgba(15, 138, 128, 0.15);
  }

  .hero::after {
    content: "";
    position: absolute;
    right: 48px;
    top: 72px;
    width: 128px;
    height: 128px;
    border-radius: 50%;
    border: 1.5px dashed rgba(15, 138, 128, 0.26);
  }

  .hero-brand {
    position: relative;
    display: flex;
    align-items: center;
    gap: 13px;
  }

  .brand-mark {
    width: 48px;
    height: 48px;
    border-radius: 14px;
    background: linear-gradient(135deg, #14a094, #0c7168);
    color: #fff;
    font-size: 24px;
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow:
      0 10px 24px rgba(15, 138, 128, 0.32),
      inset 0 1px 0 rgba(255, 255, 255, 0.35);
  }

  .brand-name {
    font-size: 18px;
    font-weight: 800;
    color: var(--ink-900);
    letter-spacing: 0.3px;
  }

  .brand-sub {
    margin-top: 2px;
    font-size: 10.5px;
    color: var(--ink-400);
    letter-spacing: 1.8px;
  }

  .hero-eyebrow {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    align-self: flex-start;
    margin-top: 56px;
    padding: 7px 14px;
    border-radius: 999px;
    background: rgba(255, 255, 255, 0.75);
    border: 1px solid var(--brand-border);
    font-size: 12.5px;
    font-weight: 600;
    color: var(--brand-ink);
    letter-spacing: 0.4px;
    box-shadow: 0 2px 8px rgba(15, 138, 128, 0.08);
  }

  .eyebrow-dot {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: var(--brand);
    box-shadow: 0 0 0 3px rgba(15, 138, 128, 0.15);
  }

  .hero-line {
    position: relative;
    margin: 22px 0 0;
    font-size: 42px;
    font-weight: 800;
    color: var(--ink-900);
    letter-spacing: -1px;
    line-height: 1.24;
  }

  .grad-text {
    background: linear-gradient(120deg, #14a094 20%, #0c7168 80%);
    -webkit-background-clip: text;
    background-clip: text;
    color: transparent;
  }

  .hero-sub {
    position: relative;
    margin: 14px 0 0;
    font-size: 15.5px;
    color: var(--ink-600);
    line-height: 1.75;
  }

  /* 悬浮数据小卡（产品价值暗示） */
  .hero-chip {
    position: absolute;
    right: 26px;
    top: 44%;
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 13px 18px;
    background: rgba(255, 255, 255, 0.9);
    border: 1px solid rgba(31, 62, 58, 0.07);
    border-radius: 16px;
    box-shadow: 0 16px 40px -8px rgba(16, 40, 36, 0.22);
    animation: chipFloat 5s ease-in-out infinite;
  }

  @keyframes chipFloat {
    0%, 100% { transform: translateY(0); }
    50% { transform: translateY(-7px); }
  }

  @media (prefers-reduced-motion: reduce) {
    .hero-chip { animation: none; }
  }

  .hc-num {
    font-size: 24px;
    font-weight: 800;
    color: var(--brand);
    font-variant-numeric: tabular-nums;
    letter-spacing: -0.5px;
  }

  .hc-txt {
    display: flex;
    flex-direction: column;
    font-size: 12.5px;
    font-weight: 600;
    color: var(--ink-800);
    line-height: 1.35;
  }

  .hc-txt small {
    font-size: 11px;
    font-weight: 500;
    color: var(--ok-strong);
  }

  /* 特性清单（放大） */
  .hero-feats {
    position: relative;
    list-style: none;
    margin: 30px 0 0;
    padding: 24px 0 0;
    border-top: 1px solid rgba(31, 62, 58, 0.09);
    display: grid;
    gap: 19px;
  }

  .hero-feats li {
    display: flex;
    align-items: flex-start;
    gap: 14px;
  }

  .feat-ico {
    flex-shrink: 0;
    width: 40px;
    height: 40px;
    border-radius: 12px;
    background: linear-gradient(145deg, #ffffff, #f0f8f6);
    border: 1px solid var(--brand-border);
    color: var(--brand-ink);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 18px;
    box-shadow: 0 4px 12px rgba(15, 138, 128, 0.12);
  }

  .hero-feats b {
    display: block;
    font-size: 15px;
    font-weight: 700;
    color: var(--ink-900);
  }

  .hero-feats div > span {
    display: block;
    margin-top: 3px;
    font-size: 13px;
    color: var(--ink-500);
  }

  /* ===== 表单区 ===== */
  .form-wrap {
    padding: 52px 46px 26px;
    background: rgba(255, 255, 255, 0.7);
    backdrop-filter: blur(8px);
  }

  .pane-head { margin-bottom: 22px; }

  .pane-head h3 {
    font-size: 24px;
    font-weight: 800;
    color: var(--ink-900);
    letter-spacing: -0.4px;
  }

  .pane-head p {
    margin-top: 5px;
    font-size: 14px;
    color: var(--ink-500);
  }

  .mode-tabs {
    display: flex;
    gap: 24px;
    padding: 0 2px 12px;
  }

  .mode-tab {
    border: none;
    background: none;
    padding: 0 2px 9px;
    font-size: 17px;
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

  .the-form { display: grid; gap: 13px; }

  .field-wrapper { height: 46px; border-radius: 10px; }

  .field-wrapper :deep(.van-field__control) { font-size: 15px; }

  .submit-btn { height: 48px !important; font-size: 16px !important; }

  /* 页脚 */
  .footer {
    position: relative;
    background: transparent;
    border: none;
    padding: 0;
    margin-top: 20px;
  }
}


</style>
