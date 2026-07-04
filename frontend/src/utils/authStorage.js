const AUTH_KEYS = ['token', 'user', 'activeProjectId']

export function createAuthStorage(storage = {}) {
  return {
    localStorage: storage.localStorage || window.localStorage,
    sessionStorage: storage.sessionStorage || window.sessionStorage
  }
}

function getDefaultStorage() {
  return createAuthStorage()
}

function getActiveStorage(storage = getDefaultStorage()) {
  if (storage.localStorage.getItem('token')) return storage.localStorage
  if (storage.sessionStorage.getItem('token')) return storage.sessionStorage
  return storage.sessionStorage
}

export function clearAuthSession(storage = getDefaultStorage()) {
  AUTH_KEYS.forEach(key => {
    storage.localStorage.removeItem(key)
    storage.sessionStorage.removeItem(key)
  })
}

export function getAuthToken(storage = getDefaultStorage()) {
  return storage.localStorage.getItem('token') || storage.sessionStorage.getItem('token') || ''
}

export function getStoredUser(storage = getDefaultStorage()) {
  const serialized = storage.localStorage.getItem('user') || storage.sessionStorage.getItem('user')
  return JSON.parse(serialized || '{}')
}

export function getStoredActiveProjectId(storage = getDefaultStorage()) {
  const value = storage.localStorage.getItem('activeProjectId') || storage.sessionStorage.getItem('activeProjectId')
  return value ? parseInt(value, 10) : null
}

export function setActiveProject(projectId, storage = getDefaultStorage()) {
  getActiveStorage(storage).setItem('activeProjectId', String(projectId))
}

export function setStoredUser(user, storage = getDefaultStorage()) {
  getActiveStorage(storage).setItem('user', JSON.stringify(user))
}

export function saveAuthenticatedSession(response, persistent, storage = getDefaultStorage()) {
  clearAuthSession(storage)
  const target = persistent ? storage.localStorage : storage.sessionStorage
  target.setItem('token', response.access_token)
  target.setItem('user', JSON.stringify(response.user))
  if (response.user.projects && response.user.projects.length > 0) {
    target.setItem('activeProjectId', String(response.user.projects[0].id))
  }
}
