# Auth Legal Consent and Session Persistence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add service/privacy disclosures and ICP information to authentication, while making the login persistence choice behave accurately without storing passwords.

**Architecture:** Keep legal content within the existing public login view as readable popup documents, with a shared consent gate for authentication actions. Introduce an authentication storage utility that selects local or session storage and route all token consumers through it, so login persistence behavior stays consistent throughout the SPA.

**Tech Stack:** Vue 3, Pinia, Vant, JavaScript ES modules, Node test runner, Vite.

---

### Task 1: Authentication Storage Behavior

**Files:**
- Create: `frontend/tests/authStorage.test.mjs`
- Create: `frontend/src/utils/authStorage.js`
- Modify: `frontend/src/stores/auth.js`
- Modify: `frontend/src/utils/request.js`
- Modify: `frontend/src/router/index.js`
- Modify: token-consuming views and API utilities returned by `rg "localStorage.getItem\\('token'\\)" frontend/src`

- [ ] **Step 1: Write failing storage behavior tests**

Test that a persistent session writes `token`, `user`, and `activeProjectId` to local storage, a non-persistent session writes them to session storage, reads work from either storage, and clear removes both.

- [ ] **Step 2: Verify RED**

Run: `node --test tests/authStorage.test.mjs`

Expected: fail because `src/utils/authStorage.js` does not exist.

- [ ] **Step 3: Implement and integrate storage utility**

Create helper functions for reading, setting and clearing authentication state; use them in Pinia auth state/actions, routing guards, request interceptors, and all direct token accessors.

- [ ] **Step 4: Verify GREEN**

Run: `node --test tests/authStorage.test.mjs`

Expected: all storage tests pass.

### Task 2: Agreement, Privacy, and ICP View

**Files:**
- Modify: `frontend/src/views/mobile/Login.vue`

- [ ] **Step 1: Add legal consent and document popups**

Render one consent checkbox below authentication forms; links open the complete system-specific service agreement and privacy policy; block login and registration submissions until checked.

- [ ] **Step 2: Add registration-page identity and filing details**

Show operator contact information in policy text and expose the supplied ICP filing number in the footer linked to the MIIT filing site.

- [ ] **Step 3: Wire accurate session control**

Rename “记住密码” to “保持登录状态” and pass its value into the auth store; do not store or refill password values.

### Task 3: Verification and Publication

**Files:**
- Use existing frontend publication workflow.

- [ ] **Step 1: Build and validate**

Run: `node --test tests/authStorage.test.mjs` and `node .\node_modules\vite\bin\vite.js build`.

- [ ] **Step 2: Deploy frontend build**

Publish the updated frontend to `qualisense.top`.

- [ ] **Step 3: Verify production resources**

Read the public login route and lazy login chunk to confirm the agreement links, ICP number, and session-storage marker are being served.
