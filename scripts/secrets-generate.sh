#!/usr/bin/env bash
# Generate fresh random secrets and write them ENCRYPTED to deploy/secrets/supportops-secrets.enc.yaml.
# The plaintext never touches the disk: it goes through a pipe straight into sops.
# Usage: scripts/secrets-generate.sh [--force]
set -euo pipefail

cd "$(dirname "$0")/.."
OUT="deploy/secrets/supportops-secrets.enc.yaml"

if [ -e "${OUT}" ] && [ "${1:-}" != "--force" ]; then
  echo "ERROR: ${OUT} exists. Rotating overwrites every secret; use --force if you mean it." >&2
  exit 1
fi

DB_USER="supportops"
DB_NAME="supportops"
DB_PASS="$(openssl rand -hex 16)"

sops --encrypt --input-type yaml --output-type yaml --filename-override "${OUT}" /dev/stdin > "${OUT}.tmp" <<EOF
apiVersion: v1
kind: Secret
metadata:
  name: supportops-secrets
  namespace: supportops
type: Opaque
stringData:
  DATABASE_URL: postgresql+psycopg://${DB_USER}:${DB_PASS}@postgres:5432/${DB_NAME}
  SECRET_KEY: $(openssl rand -hex 32)
  ALERTMANAGER_WEBHOOK_SECRET: $(openssl rand -hex 16)
  POSTGRES_USER: ${DB_USER}
  POSTGRES_PASSWORD: ${DB_PASS}
  POSTGRES_DB: ${DB_NAME}
EOF

mv "${OUT}.tmp" "${OUT}"
echo "Written (encrypted): ${OUT}"
