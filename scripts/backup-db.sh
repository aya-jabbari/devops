#!/usr/bin/env bash
# Back up the SupportOps PostgreSQL database (pg_dump custom format).
# Usage: scripts/backup-db.sh [output-dir]      (default: ./backups)
# Env:   NAMESPACE (supportops)  RELEASE (supportops)  KUBECONFIG as usual
set -euo pipefail

NAMESPACE="${NAMESPACE:-supportops}"
RELEASE="${RELEASE:-supportops}"
OUT_DIR="${1:-backups}"
TARGET="deploy/${RELEASE}-postgres"

mkdir -p "${OUT_DIR}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUT="${OUT_DIR}/supportops-${STAMP}.dump"

trap 'rm -f "${OUT}.tmp"' EXIT   # never leave a partial dump behind

echo "Backing up from ${TARGET} (namespace ${NAMESPACE}) ..."
# Credentials are read inside the pod, so they never appear on this machine.
kubectl -n "${NAMESPACE}" exec "${TARGET}" -- \
  sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' > "${OUT}.tmp"

if [ ! -s "${OUT}.tmp" ]; then
  rm -f "${OUT}.tmp"
  echo "ERROR: dump is empty, nothing written." >&2
  exit 1
fi

mv "${OUT}.tmp" "${OUT}"
chmod 600 "${OUT}"
echo "OK: ${OUT} ($(wc -c < "${OUT}") bytes)"
