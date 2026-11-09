#!/usr/bin/env bash
# Create a self-signed TLS certificate and store it as a kubernetes.io/tls Secret.
# The key never touches the repo: it is generated in a temp dir and removed.
# Usage: scripts/tls-selfsigned.sh [host] [secret-name]
#   defaults: supportops.local  supportops-tls   (NAMESPACE env, default supportops)
set -euo pipefail

HOST="${1:-supportops.local}"
SECRET="${2:-supportops-tls}"
NAMESPACE="${NAMESPACE:-supportops}"

tmp="$(mktemp -d)"
trap 'rm -rf "${tmp}"' EXIT

openssl req -x509 -newkey rsa:2048 -nodes -days 365 \
  -keyout "${tmp}/tls.key" -out "${tmp}/tls.crt" \
  -subj "/CN=${HOST}" -addext "subjectAltName=DNS:${HOST}" 2>/dev/null

kubectl get namespace "${NAMESPACE}" >/dev/null 2>&1 || kubectl create namespace "${NAMESPACE}"
kubectl -n "${NAMESPACE}" create secret tls "${SECRET}" \
  --cert="${tmp}/tls.crt" --key="${tmp}/tls.key" \
  --dry-run=client -o yaml | kubectl apply -f -
echo "TLS Secret ${SECRET} (CN=${HOST}) applied in namespace ${NAMESPACE}."
