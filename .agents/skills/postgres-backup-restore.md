# Skill: PostgreSQL backup and restore (planned, week 4)

Deliverables: `scripts/backup-db.sh`, `scripts/restore-db.sh`. A PVC survives pod deletion but is **not** a backup.

## Target behavior

**backup-db.sh**
- Runs `pg_dump` (custom format, `-Fc`) inside the `postgres` pod via `kubectl exec`.
- Writes `backups/supportops-<UTC timestamp>.dump` locally (`backups/` must be git-ignored).
- Fails loudly (`set -euo pipefail`) and refuses to write an empty file.

**restore-db.sh**
- Takes a dump file as argument; asks for explicit confirmation (it overwrites data).
- Recreates the target database empty, then `pg_restore` into it.
- Prints row counts per main table (users, tickets, ticket audit log, incidents) so the result can be compared with the source.

## Test procedure (spec §7: "restauration sur base vierge")

1. Seed data (`python -m app.seed`) and create a few tickets.
2. Note row counts. Run `backup-db.sh`.
3. Delete data on purpose (drop the DB or truncate tables) - this is the Act 5 demo.
4. Run `restore-db.sh <dump>` on the empty database.
5. Compare row counts; log in with `admin` and open an old ticket.
6. Record the result (date, counts, duration) in `docs/`. Doha also runs the restore herself (cross-contribution).

## Persistence test

Delete the `postgres` pod (`kubectl -n supportops delete pod -l app.kubernetes.io/component=postgres`); the PVC must keep the data after the pod is recreated.

## Safety

Never run restore against a database you have not just backed up. Never commit dump files (they contain user data and password hashes).
