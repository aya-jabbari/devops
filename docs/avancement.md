# Avancement : pôle Aya (Cloud, données et résilience)

Mis à jour le 9 novembre 2026 (fin de la semaine 3). Référence : cahier des charges v2.1 (§5, §6, §7).

Légende : ✅ fait et vérifié · 🟡 écrit mais pas complètement vérifié ou pas encore fusionné · ⬜ pas commencé

## Principe de travail

Rien ne dépend d'une autre personne. Tant qu'il n'y a pas de compte cloud, tout avance sur un cluster local
**k3d** (K3s dans Docker), conformément à l'alternative du §5.2. Les secrets sont appliqués avec
`scripts/secrets-apply.sh` (plan B du §5.2) tant que Doha n'a pas branché le déchiffrement dans Argo CD.

Les branches du pôle sont réunies dans `feat/aya-pole-integration` (PostgreSQL PVC, sauvegarde, SOPS, Terraform,
contrat d'interface, contexte agents, Redis PVC, TLS). Les branches individuelles restent disponibles pour des PR
séparées et relues.

## Semaine 2 : Terraform, cloud-init, K3s, kubeconfig

| Livrable (§5) | État | Où | Vérification |
|---|---|---|---|
| Contrat d'interface commun (§5.1) | 🟡 | `docs/interfaces.md`, `docs/interfaces-contract` | Poussé. Relecture de Doha et Maryam en attente. Le Service Redis est nommé `redis` comme le contrat, et le chart le respecte. |
| Terraform : réseau, pare-feu minimal, IP fixe, VM Ubuntu, clé SSH | 🟡 | `infrastructure/terraform/` | `terraform fmt` et `validate` OK (rejoués). `plan` et `apply` jamais exécutés : pas de compte cloud. |
| cloud-init : installation de K3s sans intervention | 🟡 | `infrastructure/terraform/cloud-init.yaml` | Jamais exécuté sur une vraie VM |
| Export du kubeconfig | 🟡 | `scripts/get-kubeconfig.sh` | Jamais exécuté sur une vraie VM |
| Règle de pare-feu et sortie Terraform pour Argo CD | ✅ | `network.tf`, `outputs.tf` | Relu, validé |
| README Terraform : usage, coûts, `terraform destroy` | ✅ | `infrastructure/terraform/README.md` | Remplace `docs/passation-terraform-cloud.md` (obsolète, supprimé) |
| Job CI de validation Terraform (§5.3, avec Maryam) | 🟡 | `.github/workflows/ci.yml` (job `terraform`) | YAML valide ; pas encore exécuté par GitHub Actions |
| Cluster local k3d | ✅ | n/a | Pile complète en marche (voir plus bas) |

## Semaine 3 : SOPS + Age, PVC, Traefik et TLS

| Livrable (§5) | État | Où | Vérification |
|---|---|---|---|
| SOPS + Age : règles, Secret chiffré, scripts, contrôle anti-clair | ✅ | `.sops.yaml`, `deploy/secrets/`, `scripts/secrets-*.sh` | Déchiffrement OK avec la bonne clé, refus avec une mauvaise, aucun secret en clair |
| Secret chiffré appliqué sur k3d | ✅ | `scripts/secrets-apply.sh` | Appliqué ; PostgreSQL et les pods le lisent (base initialisée avec ces identifiants, connexion OK) |
| Rotation de clé | ✅ | `docs/secrets-sops-age.md` | **Rejouée** le 9 novembre sur une copie : la nouvelle clé déchiffre, l'ancienne est refusée après retrait |
| PVC PostgreSQL, paramètre `persistence.enabled` | ✅ | `templates/postgres.yaml` | Les données survivent à la suppression du pod |
| PVC Redis, AOF, StorageClass explicite | ✅ | `templates/redis.yaml`, `values.yaml` (`redis.persistence`) | Clé écrite, pod supprimé, clé relue ; PVC `redis-data` 1 Gi liée |
| Mailpit dans le chart | ✅ | `templates/mailpit.yaml` | Déployé sur k3d |
| Traefik et TLS (certificat auto-signé) | ✅ | `scripts/tls-selfsigned.sh`, `deploy/tls/demo-ingress.yaml`, `docs/tls-traefik.md` | HTTPS servi par Traefik avec `CN=supportops.local` ; refusé sans `-k` (attendu). Sur k3d via port-forward. |
| Sauvegarde PostgreSQL | ✅ | `scripts/backup-db.sh` | Dump créé, dump vide refusé, pas de fichier partiel |
| Restauration sur base vierge | ✅ | `scripts/restore-db.sh` | Rejouée : 5 utilisateurs et 4 tickets retrouvés |
| Rapport du test de restauration | ✅ | `docs/restauration-rapport.md` | Date, comptes de lignes, durée (4 s) |
| Scénario d'acte 5 scripté | ✅ | `scripts/demo-acte5.sh` | Exécuté de bout en bout : pod supprimé (recréé en 7 s), données détruites, restauration, preuve de non-perte |
| Alerte Prometheus sur l'espace disque des PVC (§5.3, avec Maryam) | 🟡 | `monitoring/alert_rules.yml` | Écrite, YAML valide ; non testée dans Prometheus (`promtool` absent, pas de stack) |
| `values-prod` pour l'infrastructure réelle (§5.3, avec Doha) | 🟡 | `deploy/environments/prod.yaml` | `helm lint` OK ; tailles à confirmer sur la vraie VM |
| Contexte pour les agents IA | ✅ | `CLAUDE.md`, `.agents/` | Fusionné dans la branche d'intégration |

## Problème ouvert à transmettre à Doha (hors périmètre Aya)

La sonde de disponibilité du **worker** (`templates/worker.yaml`) échoue sur k3d : `No nodes replied within time constraint`,
le pod reste `0/1` alors que Celery est connecté à Redis et prêt. Le même `celery inspect ping -d celery@<pod>` lancé à la
main avec `kubectl exec` répond `pong`. Un essai avec `--timeout 8` et `timeoutSeconds: 20` n'a **pas** corrigé le problème
et a été annulé. Cause non identifiée : à investiguer par Doha (sonde alternative, par exemple `inspect ping` sans `-d`, ou
test de connexion à Redis). Les pods Redis, PostgreSQL, Mailpit et scheduler sont sains.

## Ce qui reste à faire

### Dépend d'un compte cloud (décision à prendre avant la semaine 4)

Une demande de jeton d'API Hetzner a été envoyée à une coéquipière (projet Hetzner dédié, droits lecture/écriture, jeton
transmis en privé, jamais dans Git). Tant qu'il n'est pas reçu :

| # | Tâche | Critère de réussite |
|---|---|---|
| 1 | `terraform plan`, `apply`, `kubectl get nodes` prêt, puis `destroy` | « Provisioning reproductible » |
| 2 | Rejouer `restore-db.sh` et `demo-acte5.sh` sur la VM | Acte 5 sur l'infrastructure réelle |
| 3 | Rapport de coûts réels | « Maîtrise des coûts » |
| 4 | Acte 1 de la démonstration (plan Terraform, K3s, secrets déchiffrés) | Acte 1 |

Pistes gratuites si le compte n'arrive pas : Azure for Students, crédits étudiants GitHub. Seul le fichier fournisseur
Terraform changerait.

### Avec les coéquipières

| # | Tâche | Avec |
|---|---|---|
| 5 | Pousser les branches et ouvrir les PR, relecture par une autre personne sous 24 h | Doha, Maryam |
| 6 | Ajouter les clés publiques Age de Doha et Maryam dans `.sops.yaml` puis `sops updatekeys` | Doha, Maryam |
| 7 | Brancher le déchiffrement SOPS dans Argo CD (ksops ou helm-secrets) | Doha |
| 8 | Réutiliser `supportops-tls` dans l'Ingress de l'application (voir `docs/tls-traefik.md`) | Doha |
| 9 | Valider la règle d'alerte PVC dans la stack Prometheus | Maryam |

### Semaine 5

- Répétition des actes 1 et 5, rapport de coûts final.
- Être capable de reproduire et présenter le pôle de Doha (suppléante) et d'expliquer un incident de bout en bout.

## Écarts assumés par rapport au cahier des charges

- PostgreSQL 17 et Redis 8 au lieu de 16 et 7 : déjà utilisés dans Compose et le chart (voir `docs/interfaces.md` §7).
- Fournisseur cloud : Hetzner dans le code Terraform, faute d'indication du cahier des charges. À remplacer si un autre compte est obtenu.
- Certificat TLS auto-signé : pas de nom de domaine. Cert-manager + Let's Encrypt si un domaine est obtenu.

## Risques connus

- Aucun code Terraform n'a été exécuté contre un vrai fournisseur : `server_type` et `k3s_version` sont à vérifier au premier `plan`.
- La restauration a été testée sur un petit jeu de données (4 tickets) ; `comments` et `incidents` étaient vides : voir `docs/restauration-rapport.md`.
- Premier démarrage de PostgreSQL : un pod supprimé pendant l'initialisation laisse un volume à moitié initialisé (rencontré en test). À ne pas faire pendant la démonstration.
- La clé privée Age n'existe que sur le poste d'Aya : en faire une sauvegarde hors du dépôt. Les clés publiques de Doha et Maryam ne sont pas encore dans `.sops.yaml`.
- Les sauvegardes restent dans `backups/` sur le poste (ignoré par Git) : prévoir une copie hors machine.
- La table `notifications` n'est créée que par le démarrage de l'API (`main.py` importe `models_notification`), pas par `app.seed`. Le chart n'a pas encore de pod API : la table a été créée à la main sur k3d. À corriger côté application ou par le chart de l'API.
