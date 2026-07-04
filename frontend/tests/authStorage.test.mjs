import test from 'node:test'
import assert from 'node:assert/strict'

import {
  clearAuthSession,
  createAuthStorage,
  getAuthToken,
  getStoredUser,
  saveAuthenticatedSession,
  setActiveProject
} from '../src/utils/authStorage.js'

function createMemoryStorage() {
  const values = new Map()
  return {
    getItem(key) {
      return values.has(key) ? values.get(key) : null
    },
    setItem(key, value) {
      values.set(key, String(value))
    },
    removeItem(key) {
      values.delete(key)
    }
  }
}

function createTestStorage() {
  return createAuthStorage({
    localStorage: createMemoryStorage(),
    sessionStorage: createMemoryStorage()
  })
}

const response = {
  access_token: 'token-value',
  user: { id: 7, real_name: '李经理', projects: [{ id: 9, name: '项目A' }] }
}

test('persistent login saves authentication in local storage', () => {
  const storage = createTestStorage()

  saveAuthenticatedSession(response, true, storage)

  assert.equal(getAuthToken(storage), 'token-value')
  assert.deepEqual(getStoredUser(storage), response.user)
  assert.equal(storage.localStorage.getItem('activeProjectId'), '9')
  assert.equal(storage.sessionStorage.getItem('token'), null)
})

test('session-only login does not persist authentication in local storage', () => {
  const storage = createTestStorage()

  saveAuthenticatedSession(response, false, storage)

  assert.equal(getAuthToken(storage), 'token-value')
  assert.deepEqual(getStoredUser(storage), response.user)
  assert.equal(storage.localStorage.getItem('token'), null)
  assert.equal(storage.sessionStorage.getItem('activeProjectId'), '9')
})

test('active project follows the storage holding the current token', () => {
  const storage = createTestStorage()

  saveAuthenticatedSession(response, false, storage)
  setActiveProject(12, storage)

  assert.equal(storage.sessionStorage.getItem('activeProjectId'), '12')
  assert.equal(storage.localStorage.getItem('activeProjectId'), null)
})

test('clearing authentication removes both persistent and session values', () => {
  const storage = createTestStorage()

  saveAuthenticatedSession(response, true, storage)
  storage.sessionStorage.setItem('token', 'stale-token')
  clearAuthSession(storage)

  assert.equal(storage.localStorage.getItem('token'), null)
  assert.equal(storage.sessionStorage.getItem('token'), null)
  assert.equal(getAuthToken(storage), '')
})
