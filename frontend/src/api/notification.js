import request from '../utils/request'

/**
 * 通知 API
 */

// 获取通知列表
export function getNotifications(params) {
  return request.get('/notifications', { params })
}

// 获取未读数量
export function getUnreadCount() {
  return request.get('/notifications/unread-count')
}

// 标记已读
export function markAsRead(notificationId) {
  return request.post(`/notifications/${notificationId}/read`)
}

// 全部已读
export function markAllAsRead() {
  return request.post('/notifications/read-all')
}

// 删除通知
export function deleteNotification(notificationId) {
  return request.delete(`/notifications/${notificationId}`)
}
