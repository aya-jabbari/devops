#!/usr/bin/env bash
# Give Argo CD the Age private key so KSOPS can decrypt deploy/secrets/*.enc.yaml in the cluster.
# Platform secret: created once per cluster (after Argo CD is installed), NEVER stored in Git.
# Usage: scripts/argocd-age-key.sh            (KUBECONFIG pointing at the cluster)
# Env:   SOPS_AGE_KEY_FILE (default ~/.config/sops/age/keys.txt), ARGOCD_NAMESPACE (default argocd)
set -euo pipefail

KEY_FILE="${SOPS_AGE_KEY_FILE:-$HOME/.config/sops/age/keys.txt}"
NS="${ARGOCD_NAMESPACE:-argocd}"

[ -s "${KEY_FILE}" ] || { echo "ERROR: Age key not found: ${KEY_FILE}" >&2; exit 1; }
grep -q '^AGE-SECRET-KEY-' "${KEY_FILE}" || { echo "ERROR: ${KEY_FILE} holds no Age private key." >&2; exit 1; }
kubectl get namespace "${NS}" >/dev/null 2>&1 || { echo "ERROR: namespace ${NS} not found: install Argo CD first." >&2; exit 1; }

# Rendered in memory and piped: the key is never written to disk outside its usual place.
kubectl -n "${NS}" create secret generic sops-age --from-file=keys.txt="${KEY_FILE}" \
  --dry-run=client -o yaml | kubectl apply -f -
echo "Secret sops-age ready in namespace ${NS} (mounted by argocd-repo-server for KSOPS)."
