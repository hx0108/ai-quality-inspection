/**
 * IndexedDB 封装层 — 离线问题点/照片本地存储
 *
 * 数据库：inspection_offline
 * 存储：pending_operations
 *
 * 每条记录结构：
 * {
 *   id: Number (自增),
 *   record_id: String,
 *   temp_issue_id: String,  // "TMP-{timestamp}-{random6}"
 *   item_id: String,
 *   item_name: String,
 *   op_type: String|null,   // "qualified" | null(问题项)
 *   description: String,
 *   severity: String,
 *   photos: [{ data: ArrayBuffer, filename: String, type: String }],
 *   item_status: String,    // "checked"
 *   created_at: Number,     // Date.now()
 *   status: String          // "pending" | "syncing" | "synced" | "conflict"
 * }
 */

const DB_NAME = 'inspection_offline'
const DB_VERSION = 1
const STORE_NAME = 'pending_operations'

let dbInstance = null

function openDB() {
  if (dbInstance) return Promise.resolve(dbInstance)

  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION)

    request.onupgradeneeded = (event) => {
      const db = event.target.result
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        const store = db.createObjectStore(STORE_NAME, { keyPath: 'id', autoIncrement: true })
        store.createIndex('record_id', 'record_id', { unique: false })
        store.createIndex('status', 'status', { unique: false })
        store.createIndex('temp_issue_id', 'temp_issue_id', { unique: true })
      }
    }

    request.onsuccess = (event) => {
      dbInstance = event.target.result
      resolve(dbInstance)
    }

    request.onerror = (event) => {
      console.error('[OfflineDB] 打开数据库失败:', event.target.error)
      reject(event.target.error)
    }
  })
}

function getStore(mode = 'readonly') {
  return openDB().then(db => {
    const tx = db.transaction(STORE_NAME, mode)
    return tx.objectStore(STORE_NAME)
  })
}

/**
 * 生成临时问题ID
 * 格式: TMP-{timestamp}-{random6}
 */
export function generateTempId() {
  const ts = Date.now()
  const rand = Math.random().toString(36).slice(2, 8)
  return `TMP-${ts}-${rand}`
}

/**
 * 将照片 File/Blob 转为 ArrayBuffer（iOS Safari 安全存储）
 */
async function photoToArrayBuffer(file) {
  return {
    data: await file.arrayBuffer(),
    filename: file.name || `photo_${Date.now()}.jpg`,
    type: file.type || 'image/jpeg'
  }
}

/**
 * 保存一条待同步操作
 */
export async function savePendingOp(op) {
  // 转换照片为 ArrayBuffer
  const photos = []
  for (const photo of op.photos || []) {
    if (photo instanceof Blob || photo instanceof File) {
      photos.push(await photoToArrayBuffer(photo))
    } else if (photo.data instanceof ArrayBuffer) {
      photos.push(photo)
    }
  }

  const record = {
    record_id: op.record_id,
    temp_issue_id: op.temp_issue_id || generateTempId(),
    item_id: op.item_id,
    item_name: op.item_name || '',
    op_type: op.op_type || null,
    description: op.description || '',
    severity: op.severity || '一般',
    photos,
    item_status: op.item_status || 'checked',
    created_at: Date.now(),
    status: 'pending'
  }

  const store = await getStore('readwrite')
  return new Promise((resolve, reject) => {
    const request = store.add(record)
    request.onsuccess = () => resolve({ id: request.result, ...record })
    request.onerror = () => reject(request.error)
  })
}

/**
 * 获取某记录的所有待同步操作
 */
export async function getPendingOps(recordId) {
  const store = await getStore('readonly')
  return new Promise((resolve, reject) => {
    const index = store.index('record_id')
    const request = index.getAll(recordId)
    request.onsuccess = () => {
      const results = request.result || []
      // 返回 pending / failed / syncing 的记录
      // syncing 状态可能是上次同步中途断开，需要重新同步
      resolve(results.filter(r => r.status === 'pending' || r.status === 'failed' || r.status === 'syncing'))
    }
    request.onerror = () => reject(request.error)
  })
}

/**
 * 获取某记录的待同步数量
 */
export async function getPendingCount(recordId) {
  const ops = await getPendingOps(recordId)
  return ops.length
}

/**
 * 更新操作状态
 */
export async function updateOpStatus(id, status) {
  const store = await getStore('readwrite')
  return new Promise((resolve, reject) => {
    const getRequest = store.get(id)
    getRequest.onsuccess = () => {
      const record = getRequest.result
      if (!record) return resolve(false)
      record.status = status
      const putRequest = store.put(record)
      putRequest.onsuccess = () => resolve(true)
      putRequest.onerror = () => reject(putRequest.error)
    }
    getRequest.onerror = () => reject(getRequest.error)
  })
}

/**
 * 批量更新状态
 */
export async function updateOpsStatus(ids, status) {
  for (const id of ids) {
    await updateOpStatus(id, status)
  }
}

/**
 * 删除单条操作记录
 */
export async function deleteOp(id) {
  const store = await getStore('readwrite')
  return new Promise((resolve, reject) => {
    const request = store.delete(id)
    request.onsuccess = () => resolve(true)
    request.onerror = () => reject(request.error)
  })
}

/**
 * 清理已同步的记录
 */
export async function clearSyncedOps(recordId) {
  const store = await getStore('readwrite')
  return new Promise((resolve, reject) => {
    const index = store.index('record_id')
    const request = index.openCursor(recordId)
    const toDelete = []

    request.onsuccess = (event) => {
      const cursor = event.target.result
      if (cursor) {
        if (cursor.value.status === 'synced') {
          toDelete.push(cursor.value.id)
        }
        cursor.continue()
      } else {
        // 删除所有 synced 记录
        let pending = toDelete.length
        if (pending === 0) return resolve(0)
        for (const id of toDelete) {
          const delReq = store.delete(id)
          delReq.onsuccess = () => {
            pending--
            if (pending === 0) resolve(toDelete.length)
          }
          delReq.onerror = () => reject(delReq.error)
        }
      }
    }
    request.onerror = () => reject(request.error)
  })
}

/**
 * 删除某检查项的待同步操作（用于取消离线合格标记）
 * @param {string} recordId
 * @param {string} itemId
 * @param {string|null} opType - 'qualified' | 'issue' | null (null=所有类型)
 * @returns {number} 删除的记录数
 */
export async function deletePendingOpsByItemId(recordId, itemId, opType = null) {
  const store = await getStore('readwrite')
  return new Promise((resolve, reject) => {
    const index = store.index('record_id')
    const request = index.openCursor(recordId)
    const toDelete = []

    request.onsuccess = (event) => {
      const cursor = event.target.result
      if (cursor) {
        const val = cursor.value
        if (val.item_id === itemId && (val.status === 'pending' || val.status === 'failed')) {
          if (!opType || val.op_type === opType) {
            toDelete.push(val.id)
          }
        }
        cursor.continue()
      } else {
        if (toDelete.length === 0) return resolve(0)
        let done = 0
        for (const id of toDelete) {
          const delReq = store.delete(id)
          delReq.onsuccess = () => {
            done++
            if (done === toDelete.length) resolve(done)
          }
          delReq.onerror = () => reject(delReq.error)
        }
      }
    }
    request.onerror = () => reject(request.error)
  })
}

/**
 * ArrayBuffer 转回 Blob（用于同步上传）
 */
export function arrayBufferToBlob(photoData) {
  return new Blob([photoData.data], { type: photoData.type })
}

/**
 * 获取所有有待同步操作的 record_id 列表（全局，不限单个记录）
 */
export async function getAllPendingRecordIds() {
  const store = await getStore('readonly')
  return new Promise((resolve, reject) => {
    const request = store.index('status').openCursor()
    const recordIds = new Set()
    request.onsuccess = (event) => {
      const cursor = event.target.result
      if (cursor) {
        const s = cursor.value.status
        if (s === 'pending' || s === 'failed' || s === 'syncing') {
          recordIds.add(cursor.value.record_id)
        }
        cursor.continue()
      } else {
        resolve([...recordIds])
      }
    }
    request.onerror = () => reject(request.error)
  })
}

/**
 * 清理所有已同步的记录（全局，不限单个 recordId）
 */
export async function clearAllSyncedOps() {
  const store = await getStore('readwrite')
  return new Promise((resolve, reject) => {
    const request = store.index('status').openCursor('synced')
    const toDelete = []
    request.onsuccess = (event) => {
      const cursor = event.target.result
      if (cursor) {
        toDelete.push(cursor.value.id)
        cursor.continue()
      } else {
        if (toDelete.length === 0) return resolve(0)
        let pending = toDelete.length
        for (const id of toDelete) {
          const delReq = store.delete(id)
          delReq.onsuccess = () => { pending--; if (pending === 0) resolve(toDelete.length) }
          delReq.onerror = () => reject(delReq.error)
        }
      }
    }
    request.onerror = () => reject(request.error)
  })
}
