# Tier 1 Auth Test Checklist (Execution Plan)

1. Login success returns access/refresh tokens and role payload.
2. Failed login increments `failed_login_count` and sets `first_failed_login_at` window.
3. Account locks after 10 failed attempts inside 5 minutes.
4. Locked user receives `403 FORBIDDEN` until lock window expires.
5. Successful login resets lock counters.
6. Refresh token endpoint issues new token pair for active user.
