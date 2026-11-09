# Skill: branch, commit, PR

```bash
git checkout main && git pull origin main
git checkout -b feat/<topic>            # fix/, docs/, chore/ also valid
# ... work ...
git add <specific files>                # avoid `git add .`; never add .env, tfstate, kubeconfig, keys
git commit -m "feat(infra): short imperative summary"
git push -u origin feat/<topic>
gh pr create --base main                # template: .github/pull_request_template.md
```

## Before pushing

- `python -m pytest -q tests` if backend code changed
- `helm lint deploy/helm/supportops` if the chart changed
- `terraform fmt -check && terraform validate` if Terraform changed
- `git diff --staged` : check for secrets, tokens, IPs, state files

## Review

- One other member reviews within 24 h (matrix in spec §7 gives the reviewer per topic).
- After 24 h, merge is allowed if CI is green.
- A failing test or a detected secret blocks the PR; fix it, do not bypass CI.

## Conflicts

`git fetch origin && git rebase origin/main` (or merge main), resolve, `git add`, `git rebase --continue`. Do not force-push shared branches.
