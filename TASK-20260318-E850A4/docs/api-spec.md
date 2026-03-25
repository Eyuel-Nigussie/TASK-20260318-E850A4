# API Specification - Implemented Endpoints

This specification documents the endpoints currently implemented by the backend.

Base URL (frontend proxy): `http://localhost:15173/api/v1`

Direct backend URL: `http://localhost:18000/api/v1`

## 1) Envelope and Errors

Success:

```json
{
  "success": true,
  "data": {},
  "meta": {
    "request_id": "req_xxx"
  }
}
```

Error:

```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Input validation failed",
    "details": {},
    "request_id": "req_xxx"
  }
}
```

Common status/code mapping:

- `400`: `VALIDATION_ERROR`
- `401`: `AUTHENTICATION_FAILED`
- `403`: `FORBIDDEN`
- `404`: `NOT_FOUND`
- `409`: conflict codes such as `INVALID_STATE_TRANSITION`, `ROW_VERSION_CONFLICT`, etc.
- `413`: `PAYLOAD_TOO_LARGE`
- `500`: `INTERNAL_ERROR`

Note: `429 RATE_LIMITED` is not currently emitted by backend handlers.

## 2) Authentication

### POST `/auth/login`

Request:

```json
{
  "username": "sysadmin",
  "password": "Admin#123456"
}
```

Response data fields:

- `access_token`
- `refresh_token`
- `token_type` (`bearer`)
- `expires_in`
- `user` (`id`, `username`, `role`)

### POST `/auth/refresh`

Request:

```json
{
  "refresh_token": "jwt_refresh_token"
}
```

Returns same payload shape as login.

### POST `/auth/register`

Request:

```json
{
  "email": "new.user@example.com",
  "password": "StrongPass1!",
  "confirm_password": "StrongPass1!"
}
```

Behavior:

- Validates email format.
- Requires password and confirm_password to match.
- Enforces unique username/email.
- New user role defaults to `APPLICANT`.
- Returns token payload equivalent to login.

### POST `/auth/logout`

Returns:

```json
{
  "logged_out": true
}
```

## 3) Registrations (Applicant)

### POST `/registrations`

Request:

```json
{
  "activity_id": 1,
  "form_payload": {
    "full_name": "Alex Applicant",
    "contact": "13800001234"
  }
}
```

### GET `/registrations/me`

Query params:

- `page` (default 1)
- `page_size` (default 20, max 100)
- `activity_id` (optional)
- `status` (optional)

### GET `/registrations/{registration_id}`

Ownership enforced for applicant.

### POST `/registrations/{registration_id}/submit`

Allowed from `DRAFT` only.

### POST `/registrations/{registration_id}/supplement`

Request:

```json
{
  "reason": "Correction reason text"
}
```

Rules:

- One-time only (`supplement_used`)
- Requires both windows to still be open:
  - `now <= submitted_at + 72h`
  - `now <= activity.supplement_deadline`

## 4) Uploads and Materials

### POST `/registrations/{registration_id}/materials/{checklist_id}/upload-init`

Request:

```json
{
  "filename": "certificate.pdf",
  "mime_type": "application/pdf",
  "size_bytes": 1048576
}
```

Response data:

- `upload_session_id`
- `max_chunk_size`
- `expires_at`

### PUT `/uploads/{upload_session_id}/chunk/{chunk_index}`

Headers:

- `Content-Range` (required)

Multipart field:

- `upload_file`

### POST `/uploads/{upload_session_id}/finalize`

Headers:

- `Idempotency-Key` (required)

Request:

```json
{
  "registration_id": 1,
  "checklist_id": 1,
  "status_label": "SUBMITTED",
  "correction_reason": null
}
```

Response data:

- `material_item_id`
- `new_version_no`
- `sha256`
- `size_bytes`
- `total_material_size_bytes`

### GET `/registrations/{registration_id}/materials`

Returns current material items and version counts.

### GET `/registrations/{registration_id}/materials/{material_item_id}/history`

Returns version history with file metadata.

## 5) Reviewer Workflow

### GET `/reviews/queue`

Query params:

- `page`, `page_size`
- `activity_id` (optional)
- `status` (optional)
- `keyword` (optional)

### POST `/reviews/{registration_id}/transition`

Headers:

- `Idempotency-Key` (optional)
- `If-Match` (optional row version)

Request:

```json
{
  "action": "APPROVE",
  "to_state": "APPROVED",
  "comment": "Reviewed"
}
```

### POST `/reviews/batch-transition`

Query:

- `atomic=true|false` (default false)

Headers:

- `Idempotency-Key` (optional)

Request:

```json
{
  "action": "REJECT",
  "to_state": "REJECTED",
  "comment": "Batch review",
  "items": [
    {"registration_id": 1, "row_version": 1}
  ]
}
```

Limits:

- `items` length max 50

### GET `/reviews/{registration_id}/logs`

Returns workflow transition history.

## 6) Finance

### POST `/finance/accounts`

Request:

```json
{
  "activity_id": 1,
  "account_code": "MAIN",
  "name": "Main Account"
}
```

### GET `/finance/accounts`

Query params:

- `activity_id` (optional)
- `page`, `page_size`

### POST `/finance/transactions`

Headers:

- `Idempotency-Key` (required)

Request:

```json
{
  "activity_id": 1,
  "funding_account_id": 1,
  "tx_type": "EXPENSE",
  "category": "Venue",
  "amount": 1000,
  "occurred_at": "2026-03-24T09:30:00Z",
  "note": "Main hall rental",
  "invoice_upload_session_id": null
}
```

Invoice attachment linkage:

- `invoice_upload_session_id` must reference a `FINALIZED` upload session.
- Backend resolves invoice blob via deterministic linkage (`upload_sessions.finalized_file_blob_id`).

Budget warning behavior:

- If projected confirmed expense ratio `> 1.10`, transaction is created as `PENDING_CONFIRMATION` and response includes `budget_warning` with `requires_secondary_confirmation=true`.

### POST `/finance/transactions/{transaction_id}/confirm-overrun`

Request:

```json
{
  "confirm": true
}
```

### GET `/finance/transactions`

Query params:

- `activity_id` (required)
- `tx_type`, `category` (optional)
- `from`, `to` datetime filters (optional)
- `page`, `page_size`

### GET `/finance/statistics`

Query params:

- `activity_id` (required)
- `group_by` = `category|day|week|month`
- `from`, `to` (optional)

## 7) Quality

### POST `/quality/compute/{activity_id}`

Allowed roles:

- `REVIEWER`, `FINANCIAL_ADMIN`, `SYSTEM_ADMIN`

### GET `/quality/results`

Query params:

- `activity_id` (required)
- `page`, `page_size`

### GET `/quality/latest/{activity_id}`

Returns most recent metrics row.

## 8) System / Admin

### GET `/audit/logs`

Admin-only.

Query params:

- `page`, `page_size`

### GET `/users/{user_id}/profile`

Access policy:

- `SYSTEM_ADMIN`: unmasked values
- non-admin roles: self-only access (`user_id == requester_id`) and masked sensitive fields

### PUT `/users/{user_id}/profile`

Admin-only.

Request:

```json
{
  "id_number": "A123456789",
  "contact": "13800001234"
}
```

### POST `/system/backup/run`

Admin-only. Creates local backup artifacts.

Scheduler note:

- Backend runs a daily scheduled backup task.
- Scheduled backup failures are audit-logged (`error_code=SCHEDULER_ERROR`) and logged.

### GET `/system/backup/history`

Admin-only, paginated.

### POST `/system/backup/restore`

Admin-only.

Request:

```json
{
  "backup_id": "bkp_20260324_010000_xxxxxx",
  "confirm": true,
  "pre_restore_backup": true
}
```

### Export endpoints (admin-only)

- `POST /exports/reconciliation`
- `POST /exports/audit`
- `POST /exports/compliance`
- `POST /exports/whitelist-policy`

## 9) Reserved Endpoint

### GET `/reserved/similarity-check`

Policy-disabled interface.

- HTTP status: `501`
- Error code: `NOT_IMPLEMENTED`
- Message: `Feature disabled by policy`

## 10) Not Implemented Endpoints (Removed from this spec)

The following are not currently implemented and are intentionally not part of this implementation spec:

- `/activities` management endpoints
- `/security/access-events`
