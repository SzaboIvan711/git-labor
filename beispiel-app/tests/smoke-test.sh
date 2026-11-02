#!/usr/bin/env bash
#
# Smoke test for the Taskboard application.
#
# Usage:
#   ./smoke-test.sh https://taskboard-xxxx.onrender.com
#
# Exercises the critical path end to end against a *running* instance:
#   1. /health   liveness (retried with backoff, because a Render free
#                instance is spun down after 15 min and needs up to a minute
#                to wake up on the first request)
#   2. /ready    readiness
#   3. POST      create a task
#   4. GET       read it back
#   5. DELETE    remove it again
#
# Exits non-zero on the first failing check so a CI job fails loudly, and
# prints "SMOKE TEST PASSED" only when every check succeeded.
#
# Dependencies: bash, curl, grep. No jq: JSON is matched with grep and parsed
# with bash parameter expansion.

set -euo pipefail

# --- arguments ---------------------------------------------------------------

if [ "$#" -ne 1 ]; then
  echo "usage: $0 <base-url>" >&2
  echo "example: $0 https://taskboard-xxxx.onrender.com" >&2
  exit 2
fi

# Strip a trailing slash so we can concatenate paths without doubling it.
BASE_URL="${1%/}"

# Retry budget for /health. A cold Render free instance can take ~30-60 s
# (occasionally up to a minute) to come back. Linear backoff: 5, 10, 15, ...
# Override via environment when needed, e.g. HEALTH_RETRIES=20 ./smoke-test.sh
HEALTH_RETRIES="${HEALTH_RETRIES:-12}"
BACKOFF_SECONDS="${BACKOFF_SECONDS:-5}"

# Shared curl options. We deliberately do NOT use --fail: curl must return the
# body and status even on 4xx/5xx so we can assert on them ourselves.
CURL_OPTS=(--silent --show-error --connect-timeout 10 --max-time 60)

echo "Target: ${BASE_URL}"

# --- helpers -----------------------------------------------------------------

# fail MESSAGE -> print message and abort with a non-zero exit code.
fail() {
  echo "FAIL: $1" >&2
  exit 1
}

# Global scratch variables filled by split_response().
STATUS=""
BODY=""

# Split a curl response of the form "<body>\n<http_status>" (produced with
# -w '\n%{http_code}') into BODY and STATUS using bash parameter expansion.
split_response() {
  local raw="$1"
  STATUS="${raw##*$'\n'}"   # everything after the last newline = status code
  BODY="${raw%$'\n'*}"      # everything before the last newline = body
}

# --- 1/5 liveness with cold-start backoff ------------------------------------

echo "== 1/5 waiting for /health (tolerates a cold start) =="

attempt=1
healthy=0
while [ "$attempt" -le "$HEALTH_RETRIES" ]; do
  # Guard the request: a not-yet-awake instance may refuse the connection,
  # which makes curl exit non-zero and would trip 'set -e' without this 'if'.
  if raw="$(curl "${CURL_OPTS[@]}" -w $'\n%{http_code}' "${BASE_URL}/health" 2>/dev/null)"; then
    split_response "$raw"
    if [ "$STATUS" = "200" ] && printf '%s' "$BODY" | grep -q '"status":"ok"'; then
      echo "  /health OK (attempt ${attempt}): ${BODY}"
      healthy=1
      break
    fi
  fi
  wait_for=$(( BACKOFF_SECONDS * attempt ))
  echo "  not ready yet (attempt ${attempt}/${HEALTH_RETRIES}); waiting ${wait_for}s..."
  sleep "$wait_for"
  attempt=$(( attempt + 1 ))
done

[ "$healthy" -eq 1 ] || fail "/health did not become healthy after ${HEALTH_RETRIES} attempts"

# --- 2/5 readiness -----------------------------------------------------------

echo "== 2/5 checking /ready =="
raw="$(curl "${CURL_OPTS[@]}" -w $'\n%{http_code}' "${BASE_URL}/ready")" || fail "/ready request failed"
split_response "$raw"
[ "$STATUS" = "200" ] || fail "/ready returned HTTP ${STATUS} (expected 200); body: ${BODY}"
printf '%s' "$BODY" | grep -q '"status":"ready"' || fail "/ready body missing status ready: ${BODY}"
echo "  /ready OK: ${BODY}"

# --- 3/5 create --------------------------------------------------------------

echo "== 3/5 creating a task via POST /api/tasks =="
title="smoke-test-${RANDOM}-$$"
raw="$(curl "${CURL_OPTS[@]}" \
  -H 'Content-Type: application/json' \
  -d "{\"title\":\"${title}\"}" \
  -w $'\n%{http_code}' \
  "${BASE_URL}/api/tasks")" || fail "POST /api/tasks request failed"
split_response "$raw"
[ "$STATUS" = "201" ] || fail "POST /api/tasks returned HTTP ${STATUS} (expected 201); body: ${BODY}"
printf '%s' "$BODY" | grep -q "\"title\":\"${title}\"" || fail "created task is missing its title: ${BODY}"

# Parse the numeric id out of the JSON using only grep.
id="$(printf '%s' "$BODY" | grep -oE '"id"[[:space:]]*:[[:space:]]*[0-9]+' | grep -m1 -oE '[0-9]+')"
[ -n "$id" ] || fail "could not parse a task id from: ${BODY}"
echo "  created task id=${id}"

# --- 4/5 read back -----------------------------------------------------------

echo "== 4/5 reading it back via GET /api/tasks/${id} =="
raw="$(curl "${CURL_OPTS[@]}" -w $'\n%{http_code}' "${BASE_URL}/api/tasks/${id}")" || fail "GET /api/tasks/${id} request failed"
split_response "$raw"
[ "$STATUS" = "200" ] || fail "GET /api/tasks/${id} returned HTTP ${STATUS} (expected 200); body: ${BODY}"
printf '%s' "$BODY" | grep -q "\"title\":\"${title}\"" || fail "read-back task is missing its title: ${BODY}"
echo "  read-back OK: ${BODY}"

# --- 5/5 delete --------------------------------------------------------------

echo "== 5/5 deleting it via DELETE /api/tasks/${id} =="
status="$(curl "${CURL_OPTS[@]}" -o /dev/null -w '%{http_code}' -X DELETE "${BASE_URL}/api/tasks/${id}")" || fail "DELETE /api/tasks/${id} request failed"
[ "$status" = "204" ] || fail "DELETE /api/tasks/${id} returned HTTP ${status} (expected 204)"
echo "  deleted task id=${id}"

echo
echo "SMOKE TEST PASSED"
