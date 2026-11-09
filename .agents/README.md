# .agents

Context for AI coding agents (and humans) working on SupportOps. Start with [../CLAUDE.md](../CLAUDE.md).

| Folder | Content |
|---|---|
| [context/](context/project.md) | Team, plan, current status, decisions |
| [architecture/](architecture/architecture.md) | How the system fits together |
| [skills/](skills/) | Step-by-step procedures for recurring tasks |

## Skills

| Skill | Use it for |
|---|---|
| [k3d-local-cluster](skills/k3d-local-cluster.md) | Local cluster used while there is no cloud account |
| [terraform-k3s](skills/terraform-k3s.md) | Provision the cloud server and K3s |
| [sops-age-secrets](skills/sops-age-secrets.md) | Encrypt and decrypt Kubernetes secrets |
| [helm-chart-work](skills/helm-chart-work.md) | Change and validate the Helm chart |
| [postgres-backup-restore](skills/postgres-backup-restore.md) | Backup and restore PostgreSQL |
| [pr-workflow](skills/pr-workflow.md) | Branch, commit, PR, review |

Keep these files short and true. If something is planned but not built, say "planned". Update them when reality changes.
