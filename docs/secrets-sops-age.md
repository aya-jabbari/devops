# Secrets : SOPS + Age

Objectif (cahier des charges §4) : **aucun secret en clair dans Git**. Les secrets Kubernetes sont versionnés
chiffrés avec SOPS et des clés Age asymétriques. Seule une clé privée Age permet de les déchiffrer.

## Principe

| Élément | Où | Versionné ? |
|---|---|---|
| Clé publique Age (`age1...`) | `.sops.yaml` | Oui |
| Clé privée Age | `~/.config/sops/age/keys.txt` de chaque membre | **Jamais** |
| Secret chiffré | `deploy/secrets/supportops-secrets.enc.yaml` | Oui (chiffré) |
| Modèle sans valeur réelle | `deploy/secrets/supportops-secrets.example.yaml` | Oui |

Seules les valeurs sous `data` et `stringData` sont chiffrées ; les noms de clés restent lisibles, ce qui garde les diffs utiles.

Clés du Secret `supportops-secrets` (voir `docs/interfaces.md`) : `DATABASE_URL`, `SECRET_KEY`,
`ALERTMANAGER_WEBHOOK_SECRET`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`.

## Mise en place d'un membre

```bash
mkdir -p ~/.config/sops/age
age-keygen -o ~/.config/sops/age/keys.txt
chmod 600 ~/.config/sops/age/keys.txt
grep "public key" ~/.config/sops/age/keys.txt     # envoyer cette ligne (publique) à Aya
```

Sauvegarder `keys.txt` hors du dépôt (gestionnaire de mots de passe). Sans lui, les secrets sont indéchiffrables.
Pour donner accès à un nouveau membre : ajouter sa clé publique sous `age:` dans `.sops.yaml`, puis

```bash
sops updatekeys deploy/secrets/supportops-secrets.enc.yaml
```

## Créer ou renouveler les secrets

```bash
scripts/secrets-generate.sh            # refuse d'écraser un fichier existant
scripts/secrets-generate.sh --force    # renouvellement volontaire
```

Le script génère des valeurs aléatoires et les passe **par un tube** directement à `sops` : le texte en clair
n'est jamais écrit sur le disque.

## Appliquer dans le cluster

```bash
scripts/secrets-apply.sh               # déchiffre en mémoire puis kubectl apply
kubectl -n supportops get secret supportops-secrets
```

Attention : si le Secret change `POSTGRES_PASSWORD` alors que le volume PostgreSQL existe déjà, la base garde
l'ancien mot de passe et l'application n'arrive plus à se connecter. En développement, recréer le volume
(`kubectl -n supportops scale deploy/supportops-postgres --replicas=0`, `kubectl -n supportops delete pvc postgres-data`,
puis `helm upgrade`). En production, changer aussi le mot de passe dans PostgreSQL (`ALTER USER`), ou restaurer
depuis une sauvegarde (`scripts/restore-db.sh`).

## Vérification en CI

```bash
scripts/check-secrets-encrypted.sh
```

Échoue si un fichier de `deploy/secrets/` n'est pas réellement chiffré, ou n'est ni `*.enc.yaml` ni `*.example.yaml`.
Gitleaks complète ce contrôle sur tout le dépôt.

## Rotation de clé

À faire quand un membre quitte l'équipe, ou si une clé privée est exposée.

1. Le membre concerné génère une nouvelle clé (`age-keygen`) et envoie sa clé publique.
2. Ajouter la nouvelle clé publique dans `.sops.yaml` (garder l'ancienne le temps de la transition).
3. `sops updatekeys deploy/secrets/supportops-secrets.enc.yaml`, vérifier le déchiffrement avec la nouvelle clé.
4. Retirer l'ancienne clé publique de `.sops.yaml`, puis `sops updatekeys` à nouveau.
5. **Si l'ancienne clé a pu fuiter**, changer aussi les valeurs des secrets (`scripts/secrets-generate.sh --force`),
   car l'historique Git contient encore les anciennes versions chiffrées pour cette clé.
6. Réappliquer : `scripts/secrets-apply.sh`, puis redémarrer les pods qui lisent le Secret
   (`kubectl -n supportops rollout restart deploy`).
7. Mettre à jour la clé privée stockée dans le cluster (voir « Argo CD » ci-dessous).

**Rejouée le 9 novembre 2026** sur une copie temporaire du fichier chiffré (aucune vraie clé touchée) : après les étapes
2 et 3, l'ancienne et la nouvelle clé déchiffrent toutes deux ; après l'étape 4, l'ancienne clé est **refusée** et la
nouvelle déchiffre toujours.

## Argo CD (à finaliser avec Doha)

Argo CD doit pouvoir déchiffrer. Piste : stocker la clé privée Age dans un Secret du cluster, lu par un plugin
SOPS (ksops ou helm-secrets). Cette clé est un **secret de plateforme** : elle est créée à la main une seule fois
(jamais dans Git) et fait partie de la procédure de rotation ci-dessus.
