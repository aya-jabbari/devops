variable "project_name" {
  description = "Prefix for resource names and tags."
  type        = string
  default     = "supportops"
}

variable "aws_region" {
  description = "AWS region (single region, to keep costs and latency simple)."
  type        = string
  default     = "eu-west-3"
}

variable "instance_type" {
  description = "EC2 size. K3s + PostgreSQL + Redis + Argo CD + Prometheus/Grafana need about 4 GB of RAM at least (t3.medium). t3.micro (1 GB) is too small."
  type        = string
  default     = "t3.medium"
}

variable "root_volume_gb" {
  description = "Root disk size in GB (K3s, images, PostgreSQL and Redis volumes live here via local-path)."
  type        = number
  default     = 30
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
