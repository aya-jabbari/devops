#!/usr/bin/env bash
# Decrypt the encrypted Secret and apply it to the cluster (nothing written to disk).
# Needs the Age private key: SOPS_AGE_KEY_FILE (default ~/.config/sops/age/keys.txt).
# Usage: scripts/secrets-apply.sh
set -euo pipefail

cd "$(dirname "$0")/.."
export SOPS_AGE_KEY_FILE="${SOPS_AGE_KEY_FILE:-$HOME/.config/sops/age/keys.txt}"
NAMESPACE="${NAMESPACE:-supportops}"

kubectl get namespace "${NAMESPACE}" >/dev/null 2>&1 || kubectl create namespace "${NAMESPACE}"
sops --decrypt deploy/secrets/supportops-secrets.enc.yaml | kubectl apply -f -
echo "Secret supportops-secrets applied in namespace ${NAMESPACE}."
