#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

echo "[1/3] Ensuring stack is up"
BACKEND_PORT=${BACKEND_PORT:-18000} FRONTEND_PORT=${FRONTEND_PORT:-15173} POSTGRES_PORT=${POSTGRES_PORT:-15432} docker compose up --build -d

echo "[2/3] Running unit tests in backend container"
docker compose exec -T backend sh -lc "mkdir -p /workspace"
docker compose cp unit_tests backend:/workspace/unit_tests >/dev/null
docker compose exec -T backend python -m pytest -q /workspace/unit_tests

echo "[3/3] Running API tests"
BASE_URL="http://localhost:${FRONTEND_PORT:-15173}" ./API_tests/test_api.sh

echo "All tests passed"
