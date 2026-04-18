/**
 * 白色遮罩层防护工具
 *
 * 根因分析：
 *  1. Vant showToast/showSuccessToast 内部使用 van-fade CSS 动画
 *  2. 动画在移动端可能卡在中间状态(opacity介于0~1之间)
 *  3. van-popup 默认 background: #fff(白色)
 *  4. 两者叠加 → 白色半透明遮罩残留 + pointer-events:none 残留
 *
 * 防护策略：
 *  - CSS层：禁用toast动画 + 强制深色背景 + 中和unclickable
 *  - JS层：强制清理函数 + 延迟自动清理
 */
import { closeToast } from 'vant'

let _timer = null

/**
 * 强制清理所有 Vant 遮罩层残留
 */
export function forceOverlayCleanup() {
  try { closeToast() } catch (e) { /* ignore */ }
  document.body.classList.remove('van-toast--unclickable')
}

/**
 * 延迟清理（等 Toast 自然消失后再清理残留）
 */
export function scheduleCleanup(delay = 2500) {
  clearTimeout(_timer)
  _timer = setTimeout(forceOverlayCleanup, delay)
}
