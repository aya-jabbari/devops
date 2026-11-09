resource "hcloud_ssh_key" "admin" {
  name       = "${var.project_name}-admin"
  public_key = file(pathexpand(var.ssh_public_key_path))
  labels     = local.labels
}

resource "hcloud_server" "k3s" {
  name         = "${var.project_name}-k3s"
  server_type  = var.server_type
  image        = var.image
  location     = var.location
  ssh_keys     = [hcloud_ssh_key.admin.id]
  firewall_ids = [hcloud_firewall.server.id]
  labels       = local.labels

  public_net {
    ipv4_enabled = true
    ipv4         = hcloud_primary_ip.server.id
    ipv6_enabled = false
  }

  user_data = templatefile("${path.module}/cloud-init.yaml", {
    public_ip   = hcloud_primary_ip.server.ip_address
    k3s_version = var.k3s_version
  })
}
