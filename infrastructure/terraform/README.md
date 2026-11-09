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
export AWS_ACCESS_KEY_ID="..."                    # uniquement dans l'environnement du terminal
export AWS_SECRET_ACCESS_KEY="..."

terraform init
terraform plan
terraform apply                                   # ~2 minutes ; coûte de l'argent dès la création

cd ../..
SSH_USER=ubuntu scripts/get-kubeconfig.sh <public_ip>   # la commande exacte est la sortie kubeconfig_command
export KUBECONFIG=$PWD/kubeconfig && kubectl get nodes
```

Les images Ubuntu d'AWS n'autorisent pas la connexion `root` : l'utilisateur SSH est `ubuntu` (`SSH_USER=ubuntu`).
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

`t3.medium` (2 vCPU, 4 Go) est facturé à l'heure (quelques centimes), plus le disque gp3 de 30 Go et l'adresse IPv4 publique,
facturée à l'heure elle aussi. Une session de quelques heures coûte peu, une instance laissée allumée coûte quelques dizaines
d'euros par mois. `t3.micro` (1 Go) est trop petit pour K3s et la pile complète. Relever les prix réels dans la console avant
le premier `apply` et les consigner dans le rapport de coûts final.

## État de vérification

`terraform fmt -check` et `terraform validate` passent. **`plan` et `apply` n'ont jamais été exécutés** : `instance_type`,
`k3s_version` et l'AMI (recherche Canonical) sont à confirmer au premier `plan`. Région par défaut : `eu-west-3` (Paris).

## Contrôle de CI

Le job `terraform` de `.github/workflows/ci.yml` lance `fmt -check` et `validate` (sans identifiants, `init -backend=false`).
