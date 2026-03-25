#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:15173}"

echo "[API] login via frontend proxy"
LOGIN_JSON=$(curl -sS -X POST "${BASE_URL}/api/v1/auth/login" -H "Content-Type: application/json" -d '{"username":"sysadmin","password":"Admin#123456"}')
echo "$LOGIN_JSON" | python3 -c 'import sys,json; j=json.load(sys.stdin); assert j["success"] is True; print("ok")'
TOKEN=$(echo "$LOGIN_JSON" | python3 -c 'import sys,json; print(json.load(sys.stdin)["data"]["access_token"])')

echo "[API] register new applicant"
REGISTER_EMAIL="audit_user_$(date +%s)@example.com"
REGISTER_JSON=$(curl -sS -X POST "${BASE_URL}/api/v1/auth/register" -H "Content-Type: application/json" -d '{"email":"'"${REGISTER_EMAIL}"'","password":"StrongPass1!","confirm_password":"StrongPass1!"}')
echo "$REGISTER_JSON" | python3 -c 'import sys,json; j=json.load(sys.stdin); assert j["success"] is True; assert j["data"]["user"]["role"]=="APPLICANT"; print("ok")'
APPLICANT_TOKEN=$(echo "$REGISTER_JSON" | python3 -c 'import sys,json; print(json.load(sys.stdin)["data"]["access_token"])')

echo "[API] auth lockout after repeated failures"
LOCK_EMAIL="lock_user_$(date +%s)@example.com"
curl -sS -X POST "${BASE_URL}/api/v1/auth/register" -H "Content-Type: application/json" -d '{"email":"'"${LOCK_EMAIL}"'","password":"StrongPass1!","confirm_password":"StrongPass1!"}' >/dev/null
for i in $(seq 1 10); do
  curl -sS -X POST "${BASE_URL}/api/v1/auth/login" -H "Content-Type: application/json" -d '{"username":"'"${LOCK_EMAIL}"'","password":"WrongPass1!"}' >/dev/null
done
LOCK_STATUS=$(curl -sS -o /tmp/lock_resp.json -w "%{http_code}" -X POST "${BASE_URL}/api/v1/auth/login" -H "Content-Type: application/json" -d '{"username":"'"${LOCK_EMAIL}"'","password":"StrongPass1!"}')
test "$LOCK_STATUS" = "403"
python3 - <<'PY'
import json
j=json.load(open('/tmp/lock_resp.json'))
assert j['success'] is False
assert j['error']['code']=='FORBIDDEN'
print('ok')
PY

echo "[API] frontend dashboard route"
curl -sS "${BASE_URL}/dashboard" | grep -q "<title>Activity Registration Platform</title>"
echo "ok"

echo "[API] reserved similarity endpoint disabled"
SIM_CODE=$(curl -sS -o /tmp/sim_resp.json -w "%{http_code}" "${BASE_URL}/api/v1/reserved/similarity-check")
test "$SIM_CODE" = "501"
python3 - <<'PY'
import json
j=json.load(open('/tmp/sim_resp.json'))
assert j['success'] is False
assert j['error']['code']=='NOT_IMPLEMENTED'
print('ok')
PY

echo "[API] materials list"
curl -sS "${BASE_URL}/api/v1/registrations/1/materials" -H "Authorization: Bearer ${TOKEN}" | python3 -c 'import sys,json; j=json.load(sys.stdin); assert j["success"] is True; print("ok")'

echo "[API] IDOR protection on registration read"
USER1_EMAIL="idor_user1_$(date +%s)@example.com"
USER2_EMAIL="idor_user2_$(date +%s)@example.com"
U1=$(curl -sS -X POST "${BASE_URL}/api/v1/auth/register" -H "Content-Type: application/json" -d '{"email":"'"${USER1_EMAIL}"'","password":"StrongPass1!","confirm_password":"StrongPass1!"}')
U2=$(curl -sS -X POST "${BASE_URL}/api/v1/auth/register" -H "Content-Type: application/json" -d '{"email":"'"${USER2_EMAIL}"'","password":"StrongPass1!","confirm_password":"StrongPass1!"}')
U1_TOKEN=$(echo "$U1" | python3 -c 'import sys,json; print(json.load(sys.stdin)["data"]["access_token"])')
U2_TOKEN=$(echo "$U2" | python3 -c 'import sys,json; print(json.load(sys.stdin)["data"]["access_token"])')
U1_REG=$(curl -sS -X POST "${BASE_URL}/api/v1/registrations" -H "Authorization: Bearer ${U1_TOKEN}" -H "Content-Type: application/json" -d '{"activity_id":1,"form_payload":{"full_name":"IDOR User1","contact":"10001"}}')
U1_REG_ID=$(echo "$U1_REG" | python3 -c 'import sys,json; print(json.load(sys.stdin)["data"]["id"])')
IDOR_STATUS=$(curl -sS -o /tmp/idor_resp.json -w "%{http_code}" "${BASE_URL}/api/v1/registrations/${U1_REG_ID}" -H "Authorization: Bearer ${U2_TOKEN}")
test "$IDOR_STATUS" = "400"
python3 - <<'PY'
import json
j=json.load(open('/tmp/idor_resp.json'))
assert j['success'] is False
assert j['error']['code']=='VALIDATION_ERROR'
print('ok')
PY

echo "[API] upload finalize idempotency replay"
U1_MAT_INIT=$(curl -sS -X POST "${BASE_URL}/api/v1/registrations/${U1_REG_ID}/materials/1/upload-init" -H "Authorization: Bearer ${U1_TOKEN}" -H "Content-Type: application/json" -d '{"filename":"proof.pdf","mime_type":"application/pdf","size_bytes":18}')
U1_SID=$(echo "$U1_MAT_INIT" | python3 -c 'import sys,json; print(json.load(sys.stdin)["data"]["upload_session_id"])')
printf '%s' '%PDF-1.4 samplepdf' > /tmp/idor-proof.pdf
curl -sS -X PUT "${BASE_URL}/api/v1/uploads/${U1_SID}/chunk/0" -H "Authorization: Bearer ${U1_TOKEN}" -H "Content-Range: bytes 0-17/18" -F "upload_file=@/tmp/idor-proof.pdf;type=application/pdf" >/tmp/chunk_resp.json
KEY="idem-upload-${U1_REG_ID}-1"
FIN1=$(curl -sS -X POST "${BASE_URL}/api/v1/uploads/${U1_SID}/finalize" -H "Authorization: Bearer ${U1_TOKEN}" -H "Idempotency-Key: ${KEY}" -H "Content-Type: application/json" -d '{"registration_id":'"${U1_REG_ID}"',"checklist_id":1,"status_label":"SUBMITTED","correction_reason":null}')
FIN2=$(curl -sS -X POST "${BASE_URL}/api/v1/uploads/${U1_SID}/finalize" -H "Authorization: Bearer ${U1_TOKEN}" -H "Idempotency-Key: ${KEY}" -H "Content-Type: application/json" -d '{"registration_id":'"${U1_REG_ID}"',"checklist_id":1,"status_label":"SUBMITTED","correction_reason":null}')
export FIN1 FIN2
python3 - <<'PY'
import json, os
f1=json.loads(os.environ['FIN1'])
f2=json.loads(os.environ['FIN2'])
assert f1['success'] and f2['success']
assert f1['data']['material_item_id']==f2['data']['material_item_id']
assert f1['data']['new_version_no']==f2['data']['new_version_no']
print('ok')
PY

echo "[API] review queue"
curl -sS "${BASE_URL}/api/v1/reviews/queue?page=1&page_size=10" -H "Authorization: Bearer ${TOKEN}" | python3 -c 'import sys,json; j=json.load(sys.stdin); assert j["success"] is True; print("ok")'

echo "[API] finance accounts"
curl -sS "${BASE_URL}/api/v1/finance/accounts?activity_id=1&page=1&page_size=10" -H "Authorization: Bearer ${TOKEN}" | python3 -c 'import sys,json; j=json.load(sys.stdin); assert j["success"] is True; print("ok")'

echo "[API] quality latest"
curl -sS "${BASE_URL}/api/v1/quality/latest/1" -H "Authorization: Bearer ${TOKEN}" | python3 -c 'import sys,json; j=json.load(sys.stdin); assert j["success"] is True; print("ok")'

echo "[API] backup run + audit log"
BACKUP_JSON=$(curl -sS -X POST "${BASE_URL}/api/v1/system/backup/run" -H "Authorization: Bearer ${TOKEN}")
echo "$BACKUP_JSON" | python3 -c 'import sys,json; j=json.load(sys.stdin); assert j["success"] is True; print("ok")'

echo "[API] supplement outside 72h rejected"
curl -sS -X POST "${BASE_URL}/api/v1/registrations/1/supplement" -H "Authorization: Bearer ${TOKEN}" -H "Content-Type: application/json" -d '{"reason":"late supplement"}' | python3 -c 'import sys,json; j=json.load(sys.stdin); assert j["success"] is False; print("ok")'

echo "[API] invalid transition rejected"
curl -sS -X POST "${BASE_URL}/api/v1/reviews/1/transition" -H "Authorization: Bearer ${TOKEN}" -H "Content-Type: application/json" -d '{"action":"APPROVE","to_state":"APPROVED","comment":"should fail when terminal/invalid path"}' | python3 -c 'import sys,json; j=json.load(sys.stdin); assert j["success"] is False or j.get("error"); print("ok")'

echo "[API] finance idempotency replay"
export TX1=$(curl -sS -X POST "${BASE_URL}/api/v1/finance/transactions" -H "Authorization: Bearer ${TOKEN}" -H "Idempotency-Key: fin-api-idem-1" -H "Content-Type: application/json" -d '{"activity_id":1,"funding_account_id":1,"tx_type":"INCOME","category":"Test","amount":12.34,"occurred_at":"2026-03-24T10:00:00Z","note":"idem","invoice_upload_session_id":null}')
export TX2=$(curl -sS -X POST "${BASE_URL}/api/v1/finance/transactions" -H "Authorization: Bearer ${TOKEN}" -H "Idempotency-Key: fin-api-idem-1" -H "Content-Type: application/json" -d '{"activity_id":1,"funding_account_id":1,"tx_type":"INCOME","category":"Test","amount":12.34,"occurred_at":"2026-03-24T10:00:00Z","note":"idem","invoice_upload_session_id":null}')
python3 - <<'PY'
import json, os
tx1=json.loads(os.environ['TX1'])
tx2=json.loads(os.environ['TX2'])
assert tx1['success'] and tx2['success']
assert tx1['data']['transaction_id']==tx2['data']['transaction_id']
print('ok')
PY

echo "[API] all checks passed"
