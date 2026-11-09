output "public_ip" {
  description = "Public IPv4 of the K3s server."
  value       = hcloud_primary_ip.server.ip_address
}

output "ssh_command" {
  description = "SSH into the server."
  value       = "ssh root@${hcloud_primary_ip.server.ip_address}"
}

output "kubernetes_api" {
  description = "Kubernetes API endpoint."
  value       = "https://${hcloud_primary_ip.server.ip_address}:6443"
}

output "argocd_url" {
  description = "Argo CD UI, once Argo CD is exposed on the NodePort (admin IPs only)."
  value       = "https://${hcloud_primary_ip.server.ip_address}:${var.argocd_node_port}"
}

output "kubeconfig_command" {
  description = "Fetch the kubeconfig (wait ~2 minutes after apply for K3s to be ready)."
  value       = "scripts/get-kubeconfig.sh ${hcloud_primary_ip.server.ip_address}"
}
