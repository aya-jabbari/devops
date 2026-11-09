#!/usr/bin/env bash
# Fail if any file in deploy/secrets/ holds a plaintext secret.
# Allowed: *.enc.yaml that are really SOPS-encrypted, and *.example.yaml (placeholders).
set -euo pipefail

cd "$(dirname "$0")/.."
status=0

for f in deploy/secrets/*.yaml; do
  [ -e "$f" ] || continue
  case "$f" in
    *.example.yaml) continue ;;
    *.enc.yaml)
      if ! grep -q '^sops:' "$f" || ! grep -q 'ENC\[AES256_GCM' "$f"; then
        echo "NOT ENCRYPTED: $f" >&2; status=1
      fi
      ;;
    *) echo "UNEXPECTED FILE (must be *.enc.yaml or *.example.yaml): $f" >&2; status=1 ;;
  esac
done

[ "$status" -eq 0 ] && echo "deploy/secrets: OK"
exit "$status"
