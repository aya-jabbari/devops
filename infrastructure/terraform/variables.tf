variable "hcloud_token" {
  description = "Hetzner Cloud API token (read/write). Pass it with TF_VAR_hcloud_token, never in a file."
  type        = string
  sensitive   = true
}

variable "project_name" {
  description = "Prefix for resource names and labels."
  type        = string
  default     = "supportops"
}

variable "location" {
  description = "Hetzner location (single region, to keep costs and latency simple)."
  type        = string
  default     = "fsn1"
}

variable "server_type" {
  description = "Server size. K3s + PostgreSQL + Redis + Argo CD + Prometheus/Grafana need about 4 GB of RAM at least. Check availability with: hcloud server-type list"
  type        = string
  default     = "cx22"
}

variable "image" {
  description = "Operating system image."
  type        = string
  default     = "ubuntu-24.04"
}

variable "ssh_public_key_path" {
  description = "Path to the PUBLIC SSH key installed on the server."
  type        = string
  default     = "~/.ssh/id_ed25519.pub"
}

variable "admin_cidrs" {
  description = "CIDRs allowed to reach SSH (22), the Kubernetes API (6443) and the Argo CD port. Use your public IP, e.g. [\"203.0.113.10/32\"]. Never 0.0.0.0/0."
  type        = list(string)

  validation {
    condition     = length(var.admin_cidrs) > 0 && !contains(var.admin_cidrs, "0.0.0.0/0")
    error_message = "admin_cidrs must list at least one CIDR and must not contain 0.0.0.0/0."
  }
}

variable "k3s_version" {
  description = "Pinned K3s release, for reproducible installs. Check the latest stable at https://github.com/k3s-io/k3s/releases"
  type        = string
  default     = "v1.30.5+k3s1"
}

variable "argocd_node_port" {
  description = "NodePort used to reach the Argo CD UI (restricted to admin_cidrs). Doha sets the Argo CD Service to this port."
  type        = number
  default     = 30443
}
