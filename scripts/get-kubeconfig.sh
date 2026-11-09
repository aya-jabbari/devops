#!/usr/bin/env bash
# Fetch the K3s kubeconfig from the server and point it at the public IP.
# Usage: scripts/get-kubeconfig.sh <server-public-ip> [output-file]
set -euo pipefail

IP="${1:?usage: $0 <server-public-ip> [output-file]}"
OUT="${2:-kubeconfig}"   # "kubeconfig*" is ignored by Git

echo "Waiting for K3s on ${IP} ..."
for _ in $(seq 1 60); do
  if ssh -o StrictHostKeyChecking=accept-new -o ConnectTimeout=5 "root@${IP}" 'test -f /var/lib/k3s-ready' 2>/dev/null; then
    break
  fi
  sleep 5
done

ssh "root@${IP}" 'cat /etc/rancher/k3s/k3s.yaml' | sed "s/127.0.0.1/${IP}/" > "${OUT}"
chmod 600 "${OUT}"

echo "Written to ${OUT}. Use it with:"
echo "  export KUBECONFIG=\$PWD/${OUT} && kubectl get nodes"
