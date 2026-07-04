import { onBeforeUnmount } from 'vue'
import { onBeforeRouteLeave } from 'vue-router'

/**
 * 统一轮询定时器管理。
 *
 * 解决的核心问题：移动端用系统手势返回 / 物理返回键时，组件的 onUnmounted / nav-bar 的
 * @click-left 不一定触发，导致 setInterval/setTimeout 泄漏，反复进出页面会叠加多个轮询。
 * 本 composable 在「组件卸载」和「路由离开」两个时机都兜底清理，杜绝泄漏。
 *
 * 用法一 · 固定间隔（Report / TaskDetail）：
 *   const { start, stop } = usePolling(pollReportStatus, { interval: 1500 })
 *   start()   // 立即执行一次（immediate 默认 true）+ 每 1.5s 执行
 *   // 业务完成时调 stop()
 *
 * 用法二 · 动态间隔（Scoring 的 1s→4s 递增）：
 *   const { schedule, stop } = usePolling()
 *   const tick = async () => { await fetch(); if (需继续) schedule(tick, nextDelay) }
 *   schedule(tick, 1000)
 *
 * 两种用法都自动在卸载 / 路由离开时清理，无需手动 onUnmounted。
 */
export function usePolling(callback, options = {}) {
  let timerId = null

  const stop = () => {
    if (timerId !== null) {
      clearTimeout(timerId)
      clearInterval(timerId)
      timerId = null
    }
  }

  // 固定间隔模式：启动周期轮询
  const start = () => {
    if (timerId) return // 防重复启动
    const interval = options.interval || 2000
    if (options.immediate !== false) {
      Promise.resolve(callback()).catch(() => {})
    }
    timerId = setInterval(() => {
      Promise.resolve(callback()).catch(() => {})
    }, interval)
  }

  // 动态调度模式：延迟 ms 后执行 cb（cb 内可再次 schedule 实现动态间隔）
  const schedule = (cb, ms) => {
    stop() // 清掉上一个，保证同一时刻只有一个 timer
    timerId = setTimeout(() => {
      timerId = null
      Promise.resolve(cb()).catch(() => {})
    }, ms)
  }

  // 关键：卸载 + 路由离开都清理（修复手势返回泄漏）
  onBeforeUnmount(stop)
  onBeforeRouteLeave(stop)

  return { start, stop, schedule }
}
