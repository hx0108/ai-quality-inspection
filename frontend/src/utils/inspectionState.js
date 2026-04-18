/**
 * 检查状态共享层
 * 两种检查模式（列表/巡检卡片）共享同一份内存数据
 * 切换模式时不重新加载，保持检查状态完全同步
 */
import { ref, shallowRef } from 'vue'

// 每个 recordId 对应一份状态
const _store = new Map()

/**
 * 获取指定记录的共享检查状态
 * 同一个 recordId 始终返回同一个响应式对象
 */
export function getInspectionState(recordId) {
  if (!_store.has(recordId)) {
    _store.set(recordId, {
      items: ref([]),
      moduleName: ref(''),
      taskId: ref(''),
      isCompleted: ref(false),
      loaded: ref(false),
      recordId,
      // AI 检查引导共享数据
      guideTips: ref([]),
      guideFocusItems: ref([]),
    })
  }
  return _store.get(recordId)
}

/**
 * 记录离开检查页面时清除缓存（完成检查或返回时调用）
 */
export function clearInspectionState(recordId) {
  _store.delete(recordId)
}
