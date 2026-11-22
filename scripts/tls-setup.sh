#!/usr/bin/env bash
# HTTPS for the whole cluster: self-signed certificate for the public IP, set as Traefik's default certificate.
# Usage: scripts/tls-setup.sh [public-ip]   (default: `terraform output public_ip`; KUBECONFIG as usual)
# The certificate covers supportops.local, <ip-with-dashes>.sslip.io (public DNS name for the IP) and the IP itself.
set -euo pipefail

cd "$(dirname "$0")/.."
IP="${1:-$(terraform -chdir=infrastructure/terraform output -raw public_ip)}"
[[ "${IP}" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]] || { echo "ERROR: not an IPv4 address: ${IP}" >&2; exit 1; }
SSLIP="${IP//./-}.sslip.io"

TLS_SANS="DNS:${SSLIP},IP:${IP}" scripts/tls-selfsigned.sh supportops.local supportops-tls
kubectl apply -f deploy/tls/tlsstore.yaml

echo "HTTPS ready (self-signed, browsers will warn):"
echo "  https://${SSLIP}/    https://${IP}/"
