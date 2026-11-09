# Skill: SOPS + Age secrets (planned, week 3)

Goal: `deploy/secrets/supportops-secrets.enc.yaml` is encrypted in Git; only the Age private key can decrypt it. Zero plaintext secret in Git (Gitleaks green).

## One-time setup

```bash
mkdir -p ~/.config/sops/age
age-keygen -o ~/.config/sops/age/keys.txt        # PRIVATE key: never commit, never paste in chat
grep "public key" ~/.config/sops/age/keys.txt     # age1... = public key, safe to commit
```

Create `.sops.yaml` at the repo root:

```yaml
creation_rules:
  - path_regex: deploy/secrets/.*\.enc\.yaml$
    encrypted_regex: '^(data|stringData)$'
    age: <age1... public key(s), one per team member>
```

## Encrypt

Write the plain Secret manifest **outside the repo** (or in an ignored path), then:

```bash
sops --encrypt plain-secret.yaml > deploy/secrets/supportops-secrets.enc.yaml
shred -u plain-secret.yaml        # or rm; never leave plaintext in the work tree
```

Required keys: `DATABASE_URL`, `SECRET_KEY`, `ALERTMANAGER_WEBHOOK_SECRET`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`.

## Decrypt into the cluster

```bash
export SOPS_AGE_KEY_FILE=~/.config/sops/age/keys.txt
sops --decrypt deploy/secrets/supportops-secrets.enc.yaml | kubectl -n supportops apply -f -
kubectl -n supportops get secret supportops-secrets
```

Production path (with Argo CD): give Argo CD the Age key as a cluster Secret and use a SOPS-aware plugin (e.g. ksops/helm-secrets); decided with Doha.

## Key rotation (must be documented in docs/)

1. Generate a new Age key; add its public key to `.sops.yaml`.
2. `sops updatekeys deploy/secrets/*.enc.yaml`
3. Remove the old public key, run `updatekeys` again, re-encrypt if the old key was compromised and rotate the underlying secret values.
4. Update the key stored in the cluster.

## Never

Commit `keys.txt`, any `age.key`, or a decrypted file. `.gitignore` covers `age.key` and `*.key`.
