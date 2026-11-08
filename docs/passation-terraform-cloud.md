# Passation : chantier Terraform et cloud

Pour : Maryam (reprend le chantier). De : Aya. Référence : cahier des charges, §3.2 et §5.1.

## État actuel (à lire d'abord)

- **Rien n'est encore écrit** : `infrastructure/terraform/` ne contient que `.gitkeep`, aucune branche ne contient de Terraform.
- Le cahier des charges dit « un fournisseur cloud ». AWS était le choix envisagé, à **confirmer en équipe** avant de commencer.
- Rôles prévus : Aya coordonne, Maryam est le binôme, Doha vérifie le plan et la reproduction. Le chantier ne doit pas être fait par une seule personne.

## Objectif

Créer, **par du code** et sans clic dans la console, l'environnement qui héberge l'application : un serveur k3s (et un worker si le budget le permet) sur lequel on déploie le chart Helm. C'est ce qui débloque Argo CD, Argo Rollouts, Prometheus/Grafana, k6 et la démo finale.

## Ce qu'il y a à faire

### 1. Terraform (`infrastructure/terraform/`)

Ressources à décrire :

| Élément | Détail |
|---|---|
| Réseau | VPC, sous-réseau public, passerelle Internet, table de routage |
| Règles réseau (security group) | SSH (22) et API Kubernetes (6443) **limités à nos IP**, HTTP/HTTPS (80/443) ouverts, trafic interne libre entre les nœuds |
| Clé SSH | Paire de clés (la clé publique seule va dans Terraform) |
| VM serveur k3s | Petite instance, à dimensionner : k3s + PostgreSQL + Redis + Argo CD + Prometheus/Grafana demandent de la mémoire (viser 4 Go minimum, à valider par mesure) |
| VM worker | Optionnelle, seulement si le budget le permet |
| Disque | Volume suffisant pour PostgreSQL et les métriques |
| Sorties (`outputs`) | IP publique, commande SSH, adresse de l'API |

Fichiers conseillés : `versions.tf`, `variables.tf`, `network.tf`, `compute.tf`, `outputs.tf`, `terraform.tfvars.example` (sans valeurs réelles).

### 2. Installation de k3s

Par **cloud-init** (`user_data` de la VM) ou par un script versionné dans `scripts/` :
- installer k3s sur le serveur,
- récupérer le jeton pour joindre le worker, si il y en a un,
- récupérer le `kubeconfig` et remplacer l'adresse locale par l'IP publique.

### 3. Vérifications attendues

- `terraform validate` et `terraform plan` sans erreur (Doha les rejoue de son côté).
- `terraform apply`, puis `kubectl get nodes` montre les nœuds `Ready`.
- Le chart `deploy/helm/supportops` s'installe sur ce cluster (Redis, worker, scheduler).
- `terraform destroy` supprime tout, sans ressource oubliée.

## Règles de sécurité et de coût

- **Aucun secret dans Git** : pas de clés AWS, pas de `terraform.tfstate`, pas de `.tfvars` réel. Vérifier le `.gitignore` (`*.tfstate*`, `*.tfvars`, `.terraform/`).
- Utiliser un utilisateur IAM dédié aux droits limités, jamais le compte racine.
- Le state Terraform contient des données sensibles : le garder hors du dépôt (local, ou un bucket privé si l'équipe le décide).
- Coûts : instances petites, une seule région, et **tout détruire après chaque démo**. Documenter la procédure dans `docs/`. Mettre une alerte de budget sur le compte.

## Lien avec le reste du projet

- Le chart Helm (Redis, worker, scheduler) lit un Secret nommé `supportops-secrets`, avec les clés `DATABASE_URL`, `SECRET_KEY` et `ALERTMANAGER_WEBHOOK_SECRET`. Il doit exister dans le cluster avant l'installation (chantier Argo CD et secrets, SOPS + age).
- Le chart ne contient pas encore l'API, le frontend ni PostgreSQL (chantier de Doha).
- Les images viennent de GHCR (chantier CI).

## Questions à trancher en équipe

1. Quel fournisseur et quel compte ? (AWS était envisagé.)
2. Quelle région, et quel budget maximum ?
3. Un seul nœud, ou un serveur et un worker ?
4. Où stocker le state Terraform ?
5. Qui possède les identifiants du compte, et comment les partage-t-on sans les mettre dans Git ?
