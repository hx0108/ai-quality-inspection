# Registration Multi-Project Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Allow project staff to select multiple affiliated projects during account registration while preserving the existing default-project behavior.

**Architecture:** Extend the existing `/auth/register` contract with ordered project ID/name arrays and write all selected items into the existing `user_projects` association table. Keep `users.project_id` as the first selected project for compatibility, and change the Vue registration form from a single picker to an explicit multi-select popup.

**Tech Stack:** FastAPI, Pydantic, SQLAlchemy, pytest, Vue 3, Vant, Vite.

---

### Task 1: Register API Contract and Persistence

**Files:**
- Modify: `backend/api/auth.py`
- Test: `backend/tests/test_auth_security.py`

- [ ] **Step 1: Write the failing API test**

Add a test that creates a second `Project`, posts `project_ids` and `project_names` in order, then asserts the response preserves that order, the first project remains `project_id`, and two `UserProject` rows exist.

- [ ] **Step 2: Run test to verify it fails**

Run: `$env:PYTHONPATH='.'; pytest tests/test_auth_security.py::TestRegisterValidation::test_register_multiple_projects -q`

Expected: `FAIL` because `/auth/register` currently persists only `project_name`.

- [ ] **Step 3: Implement ordered multi-project registration**

Add optional `project_ids` and `project_names` fields to `RegisterRequest`; resolve and validate ordered projects, use the first as the compatible default, insert all `UserProject` rows, and return every selected project in `user.projects`.

- [ ] **Step 4: Run authentication tests**

Run: `$env:PYTHONPATH='.'; pytest tests/test_auth_security.py -q`

Expected: all authentication tests pass, including existing single-project registration.

### Task 2: Registration Page Multi-Select

**Files:**
- Modify: `frontend/src/views/mobile/Login.vue`

- [ ] **Step 1: Replace the single-project picker interaction**

Maintain an ordered `selectedProjectIds` array, present project checkboxes in the existing popup, render selected project tags in the form, and mark the first selected tag as default.

- [ ] **Step 2: Submit compatible multi-project request data**

Submit `project_ids`, `project_names`, and first-item `project_id`/`project_name`; after success, verify the returned project IDs contain the user's ordered selection.

- [ ] **Step 3: Build frontend**

Run: `node .\node_modules\vite\bin\vite.js build`

Expected: production build succeeds.

### Task 3: Release Verification

**Files:**
- Use existing scripts: `deploy_backend.py`, `deploy_frontend.py`

- [ ] **Step 1: Deploy the backend and frontend**

Publish backend registration behavior and current frontend build using the repository's production scripts.

- [ ] **Step 2: Verify production**

Confirm `https://qualisense.top/login` serves the new frontend chunk and that the registration contract is present in the deployed backend without creating a production test account.
