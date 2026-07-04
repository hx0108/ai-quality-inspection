<template>
  <div class="login-page">
    <header class="topbar">
      <div class="brand">
        <div class="brand-mark">
          <van-icon name="passed" />
        </div>
        <div>
          <div class="brand-name">智能品质检查</div>
          <div class="brand-subtitle">Quality Inspection Platform</div>
        </div>
      </div>
      <div class="topbar-meta">{{ currentDate }}</div>
    </header>

    <main class="login-shell">
      <section class="brand-panel" aria-label="平台信息">
        <div class="panel-kicker">物业品质管理</div>
        <h1>让现场检查、问题闭环与质量复盘保持一致标准</h1>
        <p>
          面向项目现场、区域管理与品质负责人，沉淀检查过程数据，统一项目口径，形成可追踪的质量管理闭环。
        </p>

        <div class="panel-visual" aria-hidden="true">
          <div class="building">
            <span v-for="n in 36" :key="n"></span>
          </div>
          <div class="inspection-card">
            <div class="card-line strong"></div>
            <div class="card-line"></div>
            <div class="card-line short"></div>
            <div class="check-row">
              <van-icon name="success" />
              <span>现场记录已归档</span>
            </div>
          </div>
        </div>

        <div class="panel-stats">
          <div>
            <strong>8</strong>
            <span>检查模块</span>
          </div>
          <div>
            <strong>100%</strong>
            <span>过程留痕</span>
          </div>
          <div>
            <strong>闭环</strong>
            <span>整改追踪</span>
          </div>
        </div>
      </section>

      <section class="auth-card">
        <div class="auth-heading">
          <span class="auth-eyebrow">Account Access</span>
          <h2>{{ mode === 'login' ? '登录智能品质检查系统' : '注册项目检查账号' }}</h2>
          <p>{{ mode === 'login' ? '请输入账号信息进入工作台' : '请填写真实信息，便于绑定项目与检查记录' }}</p>
        </div>

        <div class="tab-bar" role="tablist">
          <button
            type="button"
            :class="['tab-item', mode === 'login' && 'tab-active']"
            @click="mode = 'login'"
          >
            账号登录
          </button>
          <button
            type="button"
            :class="['tab-item', mode === 'register' && 'tab-active']"
            @click="switchToRegister"
          >
            账号注册
          </button>
        </div>

        <van-form v-if="mode === 'login'" @submit="onLogin" class="login-form">
          <label class="field-label">账号</label>
          <div class="field-wrapper">
            <van-icon name="manager-o" class="field-icon" />
            <van-field
              v-model="loginForm.account"
              placeholder="请输入账号"
              :rules="[{ required: true, message: '请填写账号' }]"
            />
          </div>

          <label class="field-label">密码</label>
          <div class="field-wrapper">
            <van-icon name="lock" class="field-icon" />
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
            <van-checkbox v-model="keepSignedIn" shape="square" icon-size="14px">
              <span class="checkbox-text">保持登录状态</span>
            </van-checkbox>
            <button type="button" class="forgot-link" @click="showForgotTip">忘记密码？</button>
          </div>

          <van-button block native-type="submit" :loading="loading" class="submit-btn">
            登录
          </van-button>
        </van-form>

        <van-form v-else @submit="onRegister" class="login-form">
          <label class="field-label">手机号</label>
          <div class="field-wrapper">
            <van-icon name="phone-o" class="field-icon" />
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

          <label class="field-label">姓名</label>
          <div class="field-wrapper">
            <van-icon name="user-o" class="field-icon" />
            <van-field
              v-model="registerForm.real_name"
              placeholder="请输入真实姓名"
              :rules="[{ required: true, message: '请填写姓名' }]"
            />
          </div>

          <label class="field-label">所属项目</label>
          <div class="field-wrapper selectable" @click="openProjectPicker">
            <van-icon name="location-o" class="field-icon" />
            <div class="selected-projects">
              <template v-if="selectedProjects.length">
                <span v-for="(project, index) in selectedProjects" :key="project.id" class="project-tag">
                  {{ project.name }}
                  <em v-if="index === 0">默认</em>
                </span>
              </template>
              <span v-else class="project-placeholder">请选择所属项目（可多选）</span>
            </div>
            <van-icon name="arrow-down" class="field-arrow" />
          </div>

          <label class="field-label">密码</label>
          <div class="field-wrapper">
            <van-icon name="lock" class="field-icon" />
            <van-field
              v-model="registerForm.password"
              :type="showRegPwd ? 'text' : 'password'"
              placeholder="字母+数字，不少于8位"
              :rules="[
                { required: true, message: '请填写密码' },
                { validator: (val) => val.length >= 8 && /[a-zA-Z]/.test(val) && /\d/.test(val), message: '密码需包含字母和数字，不少于8位' }
              ]"
              :right-icon="showRegPwd ? 'eye-o' : 'closed-eye'"
              @click-right-icon="showRegPwd = !showRegPwd"
            />
          </div>

          <label class="field-label">确认密码</label>
          <div class="field-wrapper">
            <van-icon name="lock" class="field-icon" />
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

          <van-button block native-type="submit" :loading="loading" class="submit-btn">
            注册并进入
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
      </section>
    </main>

    <footer class="footer">
      <span>© 2026 智能品质检查系统</span>
      <span>企业质量管理平台</span>
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

const currentDate = computed(() => {
  const d = new Date()
  return `${d.getFullYear()}年${d.getMonth() + 1}月${d.getDate()}日`
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
.login-page {
  min-height: 100vh;
  position: relative;
  display: flex;
  flex-direction: column;
  overflow-x: hidden;
  background:
    linear-gradient(90deg, rgba(15, 40, 56, 0.04) 1px, transparent 1px),
    linear-gradient(180deg, rgba(15, 40, 56, 0.04) 1px, transparent 1px),
    linear-gradient(135deg, #eef3f6 0%, #f8faf9 48%, #e7eef0 100%);
  background-size: 56px 56px, 56px 56px, auto;
  color: #1f2933;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
}

.login-page::before {
  content: "";
  position: absolute;
  inset: 0;
  background:
    linear-gradient(118deg, rgba(12, 55, 74, 0.16) 0%, rgba(12, 55, 74, 0.08) 34%, transparent 34.2%),
    linear-gradient(142deg, transparent 62%, rgba(33, 92, 101, 0.1) 62.2%, rgba(33, 92, 101, 0.02) 100%);
  pointer-events: none;
}

.topbar {
  position: relative;
  z-index: 2;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 28px 44px 0;
}

.brand {
  display: flex;
  align-items: center;
  gap: 12px;
}

.brand-mark {
  width: 42px;
  height: 42px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  color: #ffffff;
  font-size: 22px;
  background: #143947;
  box-shadow: 0 10px 24px rgba(20, 57, 71, 0.2);
}

.brand-name {
  font-size: 18px;
  line-height: 1.2;
  font-weight: 700;
  color: #12313d;
}

.brand-subtitle {
  margin-top: 3px;
  font-size: 11px;
  color: #6a7a82;
  text-transform: uppercase;
}

.topbar-meta {
  font-size: 13px;
  color: #667982;
}

.login-shell {
  position: relative;
  z-index: 1;
  width: min(1080px, calc(100% - 48px));
  margin: auto;
  display: grid;
  grid-template-columns: minmax(0, 1.08fr) 420px;
  min-height: 620px;
  border: 1px solid rgba(18, 49, 61, 0.1);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.76);
  box-shadow: 0 24px 80px rgba(15, 40, 56, 0.16);
  overflow: hidden;
}

.brand-panel {
  position: relative;
  display: flex;
  flex-direction: column;
  padding: 56px;
  background:
    linear-gradient(135deg, rgba(16, 49, 62, 0.98) 0%, rgba(20, 66, 78, 0.96) 58%, rgba(32, 93, 93, 0.94) 100%);
  color: #ffffff;
  overflow: hidden;
}

.brand-panel::after {
  content: "";
  position: absolute;
  inset: 0;
  background:
    linear-gradient(90deg, rgba(255, 255, 255, 0.045) 1px, transparent 1px),
    linear-gradient(180deg, rgba(255, 255, 255, 0.04) 1px, transparent 1px);
  background-size: 72px 72px;
  opacity: 0.7;
}

.panel-kicker,
.brand-panel h1,
.brand-panel p,
.panel-visual,
.panel-stats {
  position: relative;
  z-index: 1;
}

.panel-kicker {
  width: fit-content;
  padding: 7px 12px;
  border: 1px solid rgba(255, 255, 255, 0.22);
  border-radius: 999px;
  font-size: 13px;
  color: #dce7e7;
}

.brand-panel h1 {
  max-width: 560px;
  margin: 28px 0 18px;
  font-size: 36px;
  line-height: 1.24;
  font-weight: 700;
}

.brand-panel p {
  max-width: 520px;
  margin: 0;
  font-size: 15px;
  line-height: 1.9;
  color: #cfdbdc;
}

.panel-visual {
  flex: 1;
  min-height: 230px;
  margin-top: 34px;
}

.building {
  position: absolute;
  left: 4px;
  bottom: 8px;
  width: 230px;
  height: 210px;
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 12px;
  padding: 28px 24px;
  border: 1px solid rgba(255, 255, 255, 0.14);
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.08);
}

.building span {
  min-width: 0;
  height: 18px;
  border-radius: 2px;
  background: rgba(255, 255, 255, 0.2);
}

.building span:nth-child(3n) {
  background: rgba(159, 197, 187, 0.58);
}

.inspection-card {
  position: absolute;
  right: 10px;
  bottom: 44px;
  width: 280px;
  padding: 22px;
  border-radius: 8px;
  background: #f7fbfa;
  box-shadow: 0 18px 48px rgba(0, 0, 0, 0.28);
}

.card-line {
  height: 10px;
  margin-bottom: 12px;
  border-radius: 999px;
  background: #c8d7d6;
}

.card-line.strong {
  width: 62%;
  height: 14px;
  background: #173f4b;
}

.card-line.short {
  width: 46%;
}

.check-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 20px;
  color: #245f55;
  font-size: 13px;
  font-weight: 600;
}

.panel-stats {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
  margin-top: 28px;
}

.panel-stats div {
  padding-top: 16px;
  border-top: 1px solid rgba(255, 255, 255, 0.18);
}

.panel-stats strong {
  display: block;
  font-size: 24px;
  line-height: 1.2;
}

.panel-stats span {
  display: block;
  margin-top: 4px;
  font-size: 12px;
  color: #c9d7d7;
}

.auth-card {
  padding: 52px 44px 42px;
  background: rgba(255, 255, 255, 0.96);
}

.auth-heading {
  margin-bottom: 26px;
}

.auth-eyebrow {
  display: block;
  margin-bottom: 10px;
  font-size: 12px;
  color: #6f838b;
  text-transform: uppercase;
}

.auth-heading h2 {
  margin: 0;
  font-size: 25px;
  line-height: 1.3;
  color: #12313d;
}

.auth-heading p {
  margin: 10px 0 0;
  font-size: 14px;
  color: #6d7b82;
}

.tab-bar {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 6px;
  padding: 4px;
  margin-bottom: 24px;
  border-radius: 8px;
  background: #edf3f4;
}

.tab-item {
  height: 40px;
  border: 0;
  border-radius: 6px;
  background: transparent;
  color: #68787f;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
}

.tab-item.tab-active {
  color: #12313d;
  background: #ffffff;
  box-shadow: 0 5px 14px rgba(15, 40, 56, 0.08);
}

.login-form {
  width: 100%;
}

.field-label {
  display: block;
  margin: 14px 0 8px;
  font-size: 13px;
  font-weight: 600;
  color: #2d3d44;
}

.field-wrapper {
  display: flex;
  align-items: center;
  min-height: 48px;
  border: 1px solid #d8e1e4;
  border-radius: 8px;
  background: #ffffff;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.field-wrapper:focus-within {
  border-color: #24675d;
  box-shadow: 0 0 0 3px rgba(36, 103, 93, 0.12);
}

.field-wrapper.selectable {
  cursor: pointer;
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
  color: #9aa8ae;
  font-size: 14px;
}

.project-tag {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  max-width: 100%;
  padding: 5px 8px;
  border-radius: 6px;
  background: #eaf3f1;
  color: #234c4c;
  font-size: 12px;
}

.project-tag em {
  padding: 1px 4px;
  border-radius: 4px;
  background: #24675d;
  color: #ffffff;
  font-size: 10px;
  font-style: normal;
}

.field-icon {
  width: 46px;
  color: #789099;
  font-size: 18px;
  text-align: center;
  flex-shrink: 0;
}

.field-wrapper:focus-within .field-icon {
  color: #24675d;
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
  color: #1f2933;
  font-size: 14px;
}

.field-wrapper :deep(.van-field__control::placeholder) {
  color: #9aa8ae;
}

.field-wrapper :deep(.van-field__right-icon) {
  color: #789099;
}

.field-wrapper :deep(.van-field__error-message) {
  color: #b42318;
  padding-top: 4px;
  font-size: 12px;
}

.field-arrow {
  margin-right: 14px;
  color: #789099;
  font-size: 14px;
}

.form-extra {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin: 18px 0 22px;
}

.form-extra :deep(.van-checkbox__label) {
  margin-left: 6px;
}

.form-extra :deep(.van-checkbox__icon--checked .van-icon) {
  background: #24675d;
  border-color: #24675d;
}

.checkbox-text {
  font-size: 13px;
  color: #61747d;
}

.forgot-link {
  padding: 0;
  border: 0;
  background: transparent;
  color: #24675d;
  font-size: 13px;
  cursor: pointer;
}

.submit-btn {
  height: 46px !important;
  border: none !important;
  border-radius: 8px !important;
  background: #143947 !important;
  color: #ffffff !important;
  font-size: 15px !important;
  font-weight: 700 !important;
  box-shadow: 0 12px 24px rgba(20, 57, 71, 0.22);
}

.submit-btn:active {
  transform: translateY(1px);
  box-shadow: 0 8px 18px rgba(20, 57, 71, 0.2);
}

.agreement-row {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  margin-top: 18px;
  color: #657880;
  font-size: 12px;
  line-height: 1.65;
}

.agreement-row :deep(.van-checkbox__icon--checked .van-icon) {
  background: #24675d;
  border-color: #24675d;
}

.agreement-row button {
  padding: 0;
  border: 0;
  background: transparent;
  color: #24675d;
  font-size: inherit;
  cursor: pointer;
}

.project-popup {
  background: #ffffff;
}

.project-picker {
  padding: 22px 20px max(22px, env(safe-area-inset-bottom));
}

.project-picker-header h3 {
  margin: 0;
  color: #12313d;
  font-size: 18px;
  font-weight: 700;
}

.project-picker-header p {
  margin: 8px 0 18px;
  color: #6d7b82;
  font-size: 13px;
}

.project-options {
  max-height: 280px;
  overflow-y: auto;
  border-top: 1px solid #edf1f2;
}

.project-option {
  min-height: 48px;
  padding: 0 2px;
  border-bottom: 1px solid #edf1f2;
  color: #24343c;
  font-size: 14px;
}

.project-option :deep(.van-checkbox__icon--checked .van-icon) {
  background: #24675d;
  border-color: #24675d;
}

.project-picker-summary {
  margin: 16px 0;
  color: #5f7178;
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
  border-radius: 8px !important;
  font-size: 14px !important;
  font-weight: 600 !important;
}

.project-cancel {
  border-color: #d8e1e4 !important;
  color: #51656d !important;
}

.project-confirm {
  border-color: #143947 !important;
  background: #143947 !important;
  color: #ffffff !important;
}

.legal-popup {
  background: #ffffff;
}

.legal-document {
  max-width: 760px;
  max-height: min(82vh, 720px);
  margin: 0 auto;
  padding: 24px 26px max(28px, env(safe-area-inset-bottom));
  overflow-y: auto;
  color: #24343c;
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
  border-bottom: 1px solid #edf1f2;
  background: #ffffff;
}

.legal-header h3 {
  margin: 0;
  color: #12313d;
  font-size: 20px;
}

.legal-header p {
  margin: 7px 0 0;
  color: #73848c;
  font-size: 12px;
}

.legal-header button {
  width: 34px;
  height: 34px;
  border: 0;
  border-radius: 6px;
  background: #f1f5f5;
  color: #566a72;
  cursor: pointer;
}

.legal-document section {
  margin-bottom: 18px;
}

.legal-document h4 {
  margin: 0 0 7px;
  color: #153844;
  font-size: 14px;
}

.legal-document section p {
  margin: 0;
  color: #53666f;
  font-size: 13px;
  line-height: 1.75;
}

.legal-contact {
  display: flex;
  flex-direction: column;
  gap: 5px;
  margin-top: 24px;
  padding: 15px 16px;
  border-radius: 6px;
  background: #f2f6f6;
  color: #3f545c;
  font-size: 13px;
}

.legal-contact a {
  color: #24675d;
  text-decoration: none;
}

.footer {
  position: relative;
  z-index: 1;
  display: flex;
  justify-content: center;
  gap: 14px;
  padding: 0 20px 24px;
  color: #75868d;
  font-size: 12px;
}

.footer a {
  color: #5d727a;
  text-decoration: none;
}

.footer a:hover {
  color: #24675d;
}

@media (max-width: 900px) {
  .topbar {
    padding: 20px 20px 0;
  }

  .topbar-meta {
    display: none;
  }

  .login-shell {
    width: calc(100% - 32px);
    grid-template-columns: 1fr;
    min-height: 0;
    margin: 28px auto;
  }

  .brand-panel {
    min-height: 230px;
    padding: 30px 28px;
  }

  .brand-panel h1 {
    margin-top: 18px;
    font-size: 26px;
  }

  .brand-panel p {
    font-size: 14px;
    line-height: 1.7;
  }

  .panel-visual {
    display: none;
  }

  .panel-stats {
    margin-top: 24px;
  }

  .auth-card {
    padding: 32px 24px 28px;
  }

  .footer {
    flex-direction: column;
    align-items: center;
    gap: 4px;
  }

  .legal-document {
    padding-right: 20px;
    padding-left: 20px;
  }

  .legal-header {
    margin-right: -20px;
    margin-left: -20px;
    padding-right: 20px;
    padding-left: 20px;
  }
}

@media (max-width: 420px) {
  .login-page {
    background-size: 40px 40px, 40px 40px, auto;
  }

  .brand-subtitle,
  .panel-kicker,
  .auth-eyebrow,
  .brand-panel p,
  .panel-stats {
    display: none;
  }

  .login-shell {
    width: calc(100% - 20px);
    margin-top: 20px;
  }

  .brand-panel {
    min-height: 0;
    padding: 24px 20px;
  }

  .brand-panel h1 {
    margin: 0;
    font-size: 23px;
  }

  .auth-heading h2 {
    font-size: 22px;
  }
}
</style>
