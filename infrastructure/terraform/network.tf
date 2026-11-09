locals {
  labels = {
    project    = var.project_name
    managed_by = "terraform"
  }
}

# Stable public IPv4, created first so cloud-init can put it in the K3s certificate.
resource "hcloud_primary_ip" "server" {
  name        = "${var.project_name}-ip"
  type        = "ipv4"
  location    = var.location
  auto_delete = false
  labels      = local.labels
}

# Minimal firewall: only what the demo needs.
resource "hcloud_firewall" "server" {
  name   = "${var.project_name}-fw"
  labels = local.labels

  # SSH, admin only
  rule {
    direction   = "in"
    protocol    = "tcp"
    port        = "22"
    source_ips  = var.admin_cidrs
    description = "SSH (admin)"
  }

  # Kubernetes API, admin only
  rule {
    direction   = "in"
    protocol    = "tcp"
    port        = "6443"
    source_ips  = var.admin_cidrs
    description = "Kubernetes API (admin)"
  }

  # Argo CD UI, admin only (needed by Doha's GitOps work)
  rule {
    direction   = "in"
    protocol    = "tcp"
    port        = tostring(var.argocd_node_port)
    source_ips  = var.admin_cidrs
    description = "Argo CD UI (admin)"
  }

  # Public web traffic through Traefik
  rule {
    direction   = "in"
    protocol    = "tcp"
    port        = "80"
    source_ips  = ["0.0.0.0/0", "::/0"]
    description = "HTTP"
  }

  rule {
    direction   = "in"
    protocol    = "tcp"
    port        = "443"
    source_ips  = ["0.0.0.0/0", "::/0"]
    description = "HTTPS"
  }
}
