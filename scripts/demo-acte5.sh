#!/usr/bin/env bash
# Demo act 5: self-healing, voluntary data loss, restore with proof of no loss.
# Usage: scripts/demo-acte5.sh        (local k3d or real cluster, namespace supportops)
# Needs: kubectl, scripts/backup-db.sh and scripts/restore-db.sh. Takes a backup FIRST.
set -euo pipefail

cd "$(dirname "$0")/.."
NAMESPACE="${NAMESPACE:-supportops}"
RELEASE="${RELEASE:-supportops}"
PG="deploy/${RELEASE}-postgres"
export NAMESPACE RELEASE

psql_q() {
  kubectl -n "${NAMESPACE}" exec "${PG}" -- sh -c \
    "psql -U \"\$POSTGRES_USER\" -d \"\$POSTGRES_DB\" -At -c \"$1\""
}
count() { psql_q "SELECT count(*) FROM $1"; }

step() { printf '\n=== %s ===\n' "$1"; }

step "1/5 State before"
users_before="$(count users)"; tickets_before="$(count tickets)"
echo "users=${users_before} tickets=${tickets_before}"

step "2/5 Backup"
backup_out="$(scripts/backup-db.sh backups)"
echo "${backup_out}"
dump="$(echo "${backup_out}" | sed -n 's/^OK: \([^ ]*\) .*/\1/p')"
[ -s "${dump}" ] || { echo "ERROR: no dump produced." >&2; exit 1; }

step "3/5 Self-healing: delete the Redis pod (volume keeps its data)"
old="$(kubectl -n "${NAMESPACE}" get pod -l app.kubernetes.io/component=redis -o name | head -1)"
kubectl -n "${NAMESPACE}" delete "${old}" --wait=false
start=$(date +%s)
kubectl -n "${NAMESPACE}" rollout status "deploy/${RELEASE}-redis" --timeout=120s
echo "Pod recreated by Kubernetes in $(( $(date +%s) - start ))s."

step "4/5 Voluntary data loss"
psql_q "TRUNCATE tickets CASCADE" >/dev/null
echo "After deletion: tickets=$(count tickets)"

step "5/5 Restore"
start=$(date +%s)
scripts/restore-db.sh "${dump}" --yes
dur=$(( $(date +%s) - start ))
users_after="$(count users)"; tickets_after="$(count tickets)"
echo "Restore took ${dur}s. users=${users_after} tickets=${tickets_after}"

if [ "${users_before}" = "${users_after}" ] && [ "${tickets_before}" = "${tickets_after}" ]; then
  echo "PROOF: no data lost (users ${users_before}=${users_after}, tickets ${tickets_before}=${tickets_after})."
else
  echo "FAIL: counts differ." >&2; exit 1
fi
