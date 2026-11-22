#!/usr/bin/env bash
# Demo act 5: self-healing, voluntary data loss, restore with proof of no loss.
# Usage: scripts/demo-acte5.sh        (local k3d or real cluster, namespace supportops)
# Needs: kubectl, scripts/backup-db.sh, scripts/restore-db.sh, scripts/demo-data.py. Takes a backup FIRST.
# Env:   SKIP_DEMO_DATA=1 to skip adding comments and an incident before the backup.
set -euo pipefail

cd "$(dirname "$0")/.."
NAMESPACE="${NAMESPACE:-supportops}"
RELEASE="${RELEASE:-supportops}"
PG="deploy/${RELEASE}-postgres"
TABLES="users tickets comments incidents ticket_events notifications"
export NAMESPACE RELEASE

psql_q() {
  kubectl -n "${NAMESPACE}" exec "${PG}" -- sh -c \
    "psql -U \"\$POSTGRES_USER\" -d \"\$POSTGRES_DB\" -At -c \"$1\""
}
count() { psql_q "SELECT count(*) FROM $1"; }
# One line with every table count, e.g. "users=5 tickets=5 comments=6 ...": compared as a whole.
counts() { local t out=""; for t in ${TABLES}; do out+="${t}=$(count "${t}") "; done; echo "${out% }"; }

step() { printf '\n=== %s ===\n' "$1"; }

step "1/6 Demo data: comments and a monitoring incident, through the real API"
if [ "${SKIP_DEMO_DATA:-0}" = "1" ]; then
  echo "Skipped (SKIP_DEMO_DATA=1)."
else
  kubectl -n "${NAMESPACE}" exec -i deploy/api -c api -- python - < scripts/demo-data.py
fi
# Notifications are written by the Celery worker: wait until the counts stop moving.
prev=""; for _ in $(seq 1 12); do
  cur="$(counts)"; [ "${cur}" = "${prev}" ] && break; prev="${cur}"; sleep 5
done
if [ "$(count comments)" = "0" ] || [ "$(count incidents)" = "0" ]; then
  echo "ERROR: comments or incidents are empty: the proof would not cover them." >&2; exit 1
fi

step "2/6 State before and backup"
# Retry if the worker writes between the snapshot and the dump, so "before" is exactly what the dump holds.
for attempt in 1 2 3; do
  before="$(counts)"
  backup_out="$(scripts/backup-db.sh backups)"
  dump="$(echo "${backup_out}" | sed -n 's/^OK: \([^ ]*\) .*/\1/p')"
  [ -s "${dump}" ] || { echo "ERROR: no dump produced." >&2; exit 1; }
  [ "$(counts)" = "${before}" ] && break
  echo "Data changed during the backup (attempt ${attempt}), taking it again."; rm -f "${dump}"; sleep 5
done
echo "Before: ${before}"
echo "${backup_out}"

step "3/6 Self-healing: delete the Redis pod (volume keeps its data)"
old="$(kubectl -n "${NAMESPACE}" get pod -l app.kubernetes.io/component=redis -o name | head -1)"
kubectl -n "${NAMESPACE}" delete "${old}" --wait=false
start=$(date +%s)
kubectl -n "${NAMESPACE}" rollout status "deploy/${RELEASE}-redis" --timeout=120s
echo "Pod recreated by Kubernetes in $(( $(date +%s) - start ))s."

step "4/6 Voluntary data loss"
psql_q "TRUNCATE tickets CASCADE" >/dev/null
echo "After deletion: $(counts)"

step "5/6 Restore on a blank database"
start=$(date +%s)
scripts/restore-db.sh "${dump}" --yes
dur=$(( $(date +%s) - start ))
after="$(counts)"
echo "Restore took ${dur}s."

step "6/6 Proof"
echo "Before: ${before}"
echo "After:  ${after}"
if [ "${before}" = "${after}" ]; then
  echo "PROOF: no data lost on any table (${TABLES// /, })."
else
  echo "FAIL: counts differ." >&2; exit 1
fi
