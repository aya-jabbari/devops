#!/usr/bin/env bash
# Restore a dump into an EMPTY database. The current database is DROPPED and recreated.
# Usage: scripts/restore-db.sh <dump-file> [--yes]
# Env:   NAMESPACE (supportops)  RELEASE (supportops)  KUBECONFIG as usual
set -euo pipefail

DUMP="${1:?usage: $0 <dump-file> [--yes]}"
ASSUME_YES="${2:-}"
NAMESPACE="${NAMESPACE:-supportops}"
RELEASE="${RELEASE:-supportops}"
TARGET="deploy/${RELEASE}-postgres"

[ -s "${DUMP}" ] || { echo "ERROR: ${DUMP} missing or empty." >&2; exit 1; }

if [ "${ASSUME_YES}" != "--yes" ]; then
  echo "This DROPS the database in ${TARGET} (namespace ${NAMESPACE}) and restores ${DUMP}."
  read -r -p "Type 'restore' to continue: " ANSWER
  [ "${ANSWER}" = "restore" ] || { echo "Aborted."; exit 1; }
fi

PSQL=(kubectl -n "${NAMESPACE}" exec -i "${TARGET}" -- sh -c)

echo "Recreating an empty database ..."
"${PSQL[@]}" 'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d postgres \
  -c "DROP DATABASE IF EXISTS \"$POSTGRES_DB\" WITH (FORCE)" \
  -c "CREATE DATABASE \"$POSTGRES_DB\" OWNER \"$POSTGRES_USER\""'

echo "Restoring ${DUMP} ..."
"${PSQL[@]}" 'pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --no-owner --exit-on-error' < "${DUMP}"

echo "Row counts after restore:"
"${PSQL[@]}" 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -At -F " : " -c "
  SELECT table_name,
         (xpath(\$\$/row/c/text()\$\$, query_to_xml(format(\$\$SELECT count(*) AS c FROM %I.%I\$\$, table_schema, table_name), false, true, \$\$\$\$)))[1]::text
  FROM information_schema.tables
  WHERE table_schema = \$\$public\$\$ AND table_type = \$\$BASE TABLE\$\$
  ORDER BY 1"'

echo "Restore finished."
