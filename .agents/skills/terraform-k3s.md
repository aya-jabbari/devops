# Skill: Terraform and K3s (cloud)

Code: `infrastructure/terraform/`. Provider: Hetzner (`hcloud`), one server.

## Validate without credentials (safe, also what CI runs)

```bash
cd infrastructure/terraform
terraform fmt -check
terraform init -backend=false
terraform validate
```

## Apply (needs a Hetzner account; costs money, ask the user first)

```bash
cp terraform.tfvars.example terraform.tfvars     # ignored by Git; set admin_cidrs to your IP (curl -4 ifconfig.me)
export TF_VAR_hcloud_token="..."                 # never write the token in a file
terraform init && terraform plan
terraform apply
../../scripts/get-kubeconfig.sh <public_ip>      # writes ./kubeconfig (ignored by Git)
KUBECONFIG=$PWD/kubeconfig kubectl get nodes     # expect Ready
```

## Always destroy after a session

```bash
terraform destroy
```

Then check the provider console: no server, primary IP, firewall or key left. Record the real cost for the cost report.

## Rules

- `admin_cidrs` must never contain `0.0.0.0/0` (enforced by a validation).
- State is local and must stay out of Git (`*.tfstate*` ignored). It contains sensitive data.
- `.terraform.lock.hcl` **is** committed.
- Check `server_type` availability/naming and the pinned `k3s_version` before the first apply (`hcloud server-type list`).
- Changing provider (e.g. Azure for Students): only `versions.tf`, `network.tf`, `compute.tf` change; `outputs.tf` names and `cloud-init.yaml` stay.
