#!/usr/bin/env bash
# Create a self-signed TLS certificate and store it as a kubernetes.io/tls Secret.
# The key never touches the repo: it is generated in a temp dir and removed.
# Usage: scripts/tls-selfsigned.sh [host] [secret-name]
#   defaults: supportops.local  supportops-tls   (NAMESPACE env, default supportops)
# Env:   TLS_SANS  extra subjectAltName entries, e.g. "IP:56.228.0.126,DNS:56-228-0-126.sslip.io"
set -euo pipefail

HOST="${1:-supportops.local}"
SECRET="${2:-supportops-tls}"
NAMESPACE="${NAMESPACE:-supportops}"
SANS="DNS:${HOST}${TLS_SANS:+,${TLS_SANS}}"

tmp="$(mktemp -d)"
trap 'rm -rf "${tmp}"' EXIT

openssl req -x509 -newkey rsa:2048 -nodes -days 365 \
  -keyout "${tmp}/tls.key" -out "${tmp}/tls.crt" \
  -subj "/CN=${HOST}" -addext "subjectAltName=${SANS}" 2>/dev/null

kubectl get namespace "${NAMESPACE}" >/dev/null 2>&1 || kubectl create namespace "${NAMESPACE}"
kubectl -n "${NAMESPACE}" create secret tls "${SECRET}" \
  --cert="${tmp}/tls.crt" --key="${tmp}/tls.key" \
  --dry-run=client -o yaml | kubectl apply -f -
echo "TLS Secret ${SECRET} (CN=${HOST}, SAN ${SANS}) applied in namespace ${NAMESPACE}."
