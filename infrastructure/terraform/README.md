# Terraform : serveur K3s sur Hetzner Cloud

Crée un réseau, un pare-feu minimal, une IP fixe, une clé SSH et une VM Ubuntu 24.04 ; **cloud-init** y installe K3s
sans intervention. Fournisseur : Hetzner (le cahier des charges ne l'impose pas : seul `versions.tf` et les ressources
`hcloud_*` changeraient pour un autre cloud).

## Prérequis

Terraform 1.7+, une clé SSH (`~/.ssh/id_ed25519.pub`), un **jeton d'API Hetzner en lecture/écriture** (projet Hetzner
Cloud, Security > API Tokens). Le jeton ne va **jamais** dans un fichier ni dans Git.

## Utilisation

```bash
cd infrastructure/terraform
cp terraform.tfvars.example terraform.tfvars      # ignoré par Git ; renseigner admin_cidrs (votre IP : curl -4 ifconfig.me)
export TF_VAR_hcloud_token="..."                  # uniquement dans l'environnement

terraform init
terraform plan
terraform apply                                   # ~2 minutes ; coûte de l'argent dès la création

cd ../.. && scripts/get-kubeconfig.sh <public_ip> # la commande exacte est donnée par la sortie kubeconfig_command
export KUBECONFIG=$PWD/kubeconfig && kubectl get nodes
```

Sorties : `public_ip`, `ssh_command`, `kubernetes_api`, `argocd_url`, `kubeconfig_command`.

## Pare-feu

Ouvert à tous : 80 et 443 (Traefik). Limité à `admin_cidrs` : 22 (SSH), 6443 (API Kubernetes) et le NodePort Argo CD
(30443 par défaut). `0.0.0.0/0` est refusé par une validation Terraform.

## Détruire (obligatoire après chaque session ou démo)

```bash
cd infrastructure/terraform
terraform destroy
```

Vérifier ensuite dans la console Hetzner (projet) qu'il ne reste ni serveur, ni IP primaire, ni volume : une IP primaire
ou un volume orphelin continue d'être facturé. Détruire aussi invalide le kubeconfig : en régénérer un au prochain `apply`.

## Coût indicatif

Le type `cx22` (2 vCPU, 4 Go) est facturé à l'heure, de l'ordre de quelques euros par mois s'il tourne en continu. Une session
de démonstration de quelques heures coûte quelques centimes. Les prix réels sont à relever dans la console avant le premier
`apply` et à consigner dans le rapport de coûts final.

## État de vérification

`terraform fmt -check` et `terraform validate` passent. **`plan` et `apply` n'ont jamais été exécutés** (pas de compte cloud
au 9 novembre 2026) : `server_type` et `k3s_version` sont à confirmer au premier `plan`.

## Contrôle de CI

Le job `terraform` de `.github/workflows/ci.yml` lance `fmt -check` et `validate` (sans jeton, `init -backend=false`).
