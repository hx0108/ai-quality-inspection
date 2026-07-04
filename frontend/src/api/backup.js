import request from '../utils/request'

export function getBackupStatus() {
  return request.get('/backup/status').catch(() => ({}))
}

export function listBackups(params) {
  return request.get('/backup/list', { params }).catch(() => ({ items: [] }))
}

export function createBackup(data) {
  return request.post('/backup/create', data)
}

export function restoreBackup(filename) {
  return request.post(`/backup/restore/${filename}`)
}

export function deleteBackup(filename) {
  return request.delete(`/backup/${filename}`)
}
