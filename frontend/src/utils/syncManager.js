/**
 * 同步管理器 — 离线检测、本地保存、自动同步
 *
 * 核心策略：每条数据同步成功后立即从 IndexedDB 删除，
 * 不依赖先标记再批量清理的方式。
 */
import { ref, onMounted, onUnmounted } from 'vue'
import { showToast } from 'vant'
import {
  savePendingOp,
  getPendingOps,
  getPendingCount,
  deleteOp,
  clearAllSyncedOps,
  generateTempId,
  arrayBufferToBlob,
  deletePendingOpsByItemId,
  getAllPendingRecordIds
} from './offlineDB'
import { batchSync } from '../api/sync'
import { updateItemStatus } from '../api/inspection'
import { compressPhoto } from './photoCompress'

// ==================== 共享锁 ====================
const _recordLocks = new Map()
function acquireLock(recordId) { if (_recordLocks.get(recordId)) return false; _recordLocks.set(recordId, true); return true }
function releaseLock(recordId) { _recordLocks.delete(recordId) }

// ==================== 同步完成通知 ====================
const SYNC_DONE_EVENT = 'offline-sync-done'
function notifySyncDone(recordId) {
  window.dispatchEvent(new CustomEvent(SYNC_DONE_EVENT, { detail: { recordId } }))
}

// ==================== 核心同步逻辑 ====================

async function syncPendingOps(recordId, { onQualifiedSynced, onIdReplaced } = {}) {
  const ops = await getPendingOps(recordId)
  if (ops.length === 0) return { synced: 0, conflicts: 0 }

  const qualifiedOps = ops.filter(op => op.op_type === 'qualified')
  const issueOps = ops.filter(op => op.op_type !== 'qualified')

  let totalSynced = 0
  let totalConflicts = 0

  // 1. 逐条同步合格操作，成功即删除
  for (const op of qualifiedOps) {
    try {
      await updateItemStatus(recordId, op.item_id, { status: 'checked' })
      await deleteOp(op.id)
      totalSynced++
      if (onQualifiedSynced) onQualifiedSynced(op.item_id)
    } catch (e) {
      // API 失败，保留在 IndexedDB，下次重试
      if (!e.response) break  // 网络错误，停止后续
    }
  }

  // 2. 逐条同步问题操作，每次只发一条（含照片），避免请求体过大
  for (const op of issueOps) {

    const formData = new FormData()
    formData.append('metadata', JSON.stringify({
      issues: [{
        temp_issue_id: op.temp_issue_id,
        item_id: op.item_id,
        item_name: op.item_name,
        description: op.description,
        severity: op.severity,
        item_status: op.item_status
      }]
    }))

    for (let pIdx = 0; pIdx < (op.photos || []).length; pIdx++) {
      const photo = op.photos[pIdx]
      formData.append(`photo_${op.temp_issue_id}_${pIdx}`, arrayBufferToBlob(photo), photo.filename)
    }

    try {
      const result = await batchSync(recordId, formData)
      const r = (result.results || [])[0]
      if (r) {
        if (r.status === 'created') {
          await deleteOp(op.id)
          totalSynced++
          if (onIdReplaced) onIdReplaced(op.temp_issue_id, r.issue_id, r.photo_ids || [])
        } else if (r.status === 'conflict') {
          await deleteOp(op.id)
          totalConflicts++
        }
      }
    } catch (e) {
      if (!e.response) break  // 网络错误，停止后续
    }
  }

  return { synced: totalSynced, conflicts: totalConflicts }
}

/**
 * 全局同步（供 App.vue 调用）
 */
export async function globalSyncAll() {
  if (!navigator.onLine) return

  try {
    await clearAllSyncedOps()
    const recordIds = await getAllPendingRecordIds()
    if (recordIds.length === 0) return

    for (const rid of recordIds) {
      if (!acquireLock(rid)) continue
      try {
        await syncPendingOps(rid)
        notifySyncDone(rid)
      } catch (e) { /* ignore */ }
      finally { releaseLock(rid) }
    }
  } catch (e) { /* ignore */ }
}

// ==================== Vue 3 Composable ====================

export function useOfflineSync(recordId) {
  const isOnline = ref(navigator.onLine)
  const pendingCount = ref(0)
  const syncing = ref(false)
  const syncProgress = ref('')
  const conflictCount = ref(0)

  const onOnline = () => { isOnline.value = true; trySyncNow() }
  const onOffline = () => { isOnline.value = false }
  const onVisibilityChange = () => { if (document.visibilityState === 'visible' && navigator.onLine) { isOnline.value = true; trySyncNow() } }
  const onGlobalSyncDone = (e) => { if (e.detail.recordId === recordId) refreshPendingCount() }

  const refreshPendingCount = async () => {
    try { pendingCount.value = await getPendingCount(recordId) } catch (e) { /* ignore */ }
  }

  // ===== 离线保存问题 =====
  const saveOfflineIssue = async ({ item_id, item_name, description, severity, photos, item_status }) => {
    const tempId = generateTempId()
    const photoData = []
    for (const photo of photos || []) {
      if (photo.file) {
        try {
          // 先压缩再存储，减少 IndexedDB 占用和后续同步体积
          const compressed = await compressPhoto(photo.file)
          const data = await compressed.arrayBuffer()
          photoData.push({ data, filename: photo.file.name || `photo_${Date.now()}.jpg`, type: compressed.type || 'image/jpeg' })
        } catch (e) { /* skip */ }
      }
    }
    await savePendingOp({ record_id: recordId, temp_issue_id: tempId, item_id, item_name, description, severity, photos: photoData, item_status: item_status || 'checked' })
    await refreshPendingCount()
    return tempId
  }

  // ===== 离线保存合格状态 =====
  const saveOfflineQualified = async ({ item_id, item_name }) => {
    const tempId = generateTempId()
    await savePendingOp({ record_id: recordId, temp_issue_id: tempId, item_id, item_name, op_type: 'qualified', description: '', severity: '', photos: [], item_status: 'checked' })
    await refreshPendingCount()
    return tempId
  }

  // ===== 删除离线合格记录 =====
  const deleteOfflineQualified = async (itemId) => {
    const count = await deletePendingOpsByItemId(recordId, itemId, 'qualified')
    await refreshPendingCount()
    return count
  }

  // ===== 同步 =====
  let onIdReplaced = null
  let onQualifiedSyncedCb = null

  const trySyncNow = async () => {
    if (syncing.value) return
    if (!navigator.onLine) return
    if (!acquireLock(recordId)) return

    syncing.value = true
    syncProgress.value = ''

    try {
      const ops = await getPendingOps(recordId)
      if (ops.length > 0) {
        syncProgress.value = `正在同步 ${ops.length} 条...`
        const result = await syncPendingOps(recordId, {
          onQualifiedSynced: onQualifiedSyncedCb,
          onIdReplaced
        })
        conflictCount.value = result.conflicts
        if (result.synced > 0) {
          showToast(`同步成功：${result.synced} 条`)
        } else if (result.conflicts > 0) {
          showToast(`${result.conflicts} 条数据冲突，服务器已有记录`)
        }
      }
      // 同步结束，重新计数
      await refreshPendingCount()
    } catch (e) {
      showToast('同步失败，请重试')
      await refreshPendingCount()
    } finally {
      releaseLock(recordId)
      syncing.value = false
      syncProgress.value = ''
    }
  }

  const setIdReplacedCallback = (cb) => { onIdReplaced = cb }
  const setQualifiedSyncedCallback = (cb) => { onQualifiedSyncedCb = cb }

  onMounted(async () => {
    window.addEventListener('online', onOnline)
    window.addEventListener('offline', onOffline)
    document.addEventListener('visibilitychange', onVisibilityChange)
    window.addEventListener(SYNC_DONE_EVENT, onGlobalSyncDone)
    await refreshPendingCount()
    if (navigator.onLine && pendingCount.value > 0) trySyncNow()
  })

  onUnmounted(() => {
    window.removeEventListener('online', onOnline)
    window.removeEventListener('offline', onOffline)
    document.removeEventListener('visibilitychange', onVisibilityChange)
    window.removeEventListener(SYNC_DONE_EVENT, onGlobalSyncDone)
  })

  return {
    isOnline, pendingCount, syncing, syncProgress, conflictCount,
    trySyncNow, saveOfflineIssue, saveOfflineQualified,
    deleteOfflineQualified, refreshPendingCount,
    setIdReplacedCallback, setQualifiedSyncedCallback
  }
}
