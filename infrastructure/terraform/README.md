# Terraform : serveur K3s sur AWS

Crée un VPC, un sous-réseau public, un groupe de sécurité minimal, une IP élastique, une clé SSH et une instance EC2
Ubuntu 24.04 ; **cloud-init** y installe K3s sans intervention. Cette version remplace la première version Hetzner
(historique Git) : le compte disponible dans l'équipe est un compte AWS. Le cahier des charges n'impose pas de fournisseur.

## Prérequis

- Terraform 1.7+ et une clé SSH (`~/.ssh/id_ed25519.pub`).
- Un **utilisateur IAM** dédié (pas le compte racine), avec accès programmatique et les politiques `AmazonEC2FullAccess` et
  `AmazonVPCFullAccess`. Sa clé d'accès (Access key ID et Secret access key) ne va **jamais** dans un fichier ni dans Git.
- Un **budget AWS** (par exemple 10 $ par mois avec alerte e-mail) créé avant le premier `apply`.

## Utilisation

```bash
cd infrastructure/terraform
cp terraform.tfvars.example terraform.tfvars      # ignoré par Git ; renseigner admin_cidrs (votre IP : curl -4 ifconfig.me)
export AWS_PROFILE=supportops                     # profil créé par `aws configure --profile supportops` (~/.aws, hors dépôt)

terraform init
terraform plan
terraform apply                                   # ~2 minutes ; coûte de l'argent dès la création

cd ../..
SSH_USER=ubuntu scripts/get-kubeconfig.sh <public_ip>   # la commande exacte est la sortie kubeconfig_command
export KUBECONFIG=$PWD/kubeconfig && kubectl get nodes
```

Les images Ubuntu d'AWS n'autorisent pas la connexion `root` : l'utilisateur SSH est `ubuntu` (valeur par défaut du script).

Sorties : `public_ip`, `ssh_command`, `kubernetes_api`, `argocd_url`, `kubeconfig_command`.

## Pare-feu (groupe de sécurité)

Ouvert à tous : 80 et 443 (Traefik). Limité à `admin_cidrs` : 22 (SSH), 6443 (API Kubernetes) et le NodePort Argo CD
(30443 par défaut). `0.0.0.0/0` est refusé par une validation Terraform. Sortie libre (installation de paquets, images).

## Détruire (obligatoire après chaque session ou démo)

```bash
cd infrastructure/terraform
terraform destroy
```

Vérifier ensuite dans la console AWS (région utilisée) qu'il ne reste ni instance, ni **IP élastique**, ni volume EBS, ni VPC :
une IP élastique ou un volume orphelin continue d'être facturé. Le disque racine est supprimé avec l'instance
(`delete_on_termination`). Détruire invalide aussi le kubeconfig : en régénérer un au prochain `apply`.

## Coût indicatif

`m7i-flex.large` (2 vCPU, 8 Go) est facturé à l'heure (une dizaine de centimes, couverts par les crédits du Free plan), plus le disque gp3 de 30 Go et l'adresse IPv4 publique,
facturée à l'heure elle aussi. Une session de quelques heures coûte peu, une instance laissée allumée coûte quelques dizaines
d'euros par mois. `t3.micro` (1 Go) est trop petit pour K3s et la pile complète. Relever les prix réels dans la console avant
le premier `apply` et les consigner dans le rapport de coûts final.

## État de vérification

`terraform fmt -check` et `terraform validate` passent. **`plan` exécuté le 22 novembre 2026** sur le compte de l'équipe :
16 ressources à créer, AMI Ubuntu 24.04 trouvée. **`apply` exécuté le même jour** : K3s v1.30.5 `Ready` environ 1 minute après
la création de l'instance, kubeconfig récupéré par `scripts/get-kubeconfig.sh`, Traefik répond sur le port 80. `destroy` exécuté ensuite : 16 ressources supprimées, rien de facturable restant
(voir `docs/rapport-couts.md`).

Région : `eu-north-1` (Stockholm). Le compte est sur le **Free plan** AWS, qui le verrouille sur une seule région ; les autres
régions renvoient un refus explicite (politique d'organisation AWS). Les crédits du Free plan couvrent EC2.
Type d'instance : `m7i-flex.large`. Le Free plan refuse au lancement tout type non éligible (`t3.medium` : « not eligible for
Free Tier ») ; `run-instances --dry-run` ne détecte pas ce refus. Lister les types acceptés :
`aws ec2 describe-instance-types --filters Name=free-tier-eligible,Values=true`.

## Contrôle de CI

Le job `terraform` de `.github/workflows/ci.yml` lance `fmt -check` et `validate` (sans identifiants, `init -backend=false`).
