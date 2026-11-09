output "public_ip" {
  description = "Public IPv4 of the K3s server."
  value       = aws_eip.server.public_ip
}

output "ssh_command" {
  description = "SSH into the server (Ubuntu AMIs allow the ubuntu user, not root)."
  value       = "ssh ubuntu@${aws_eip.server.public_ip}"
}

output "kubernetes_api" {
  description = "Kubernetes API endpoint."
  value       = "https://${aws_eip.server.public_ip}:6443"
}

output "argocd_url" {
  description = "Argo CD UI, once Argo CD is exposed on the NodePort (admin IPs only)."
  value       = "https://${aws_eip.server.public_ip}:${var.argocd_node_port}"
}

output "kubeconfig_command" {
  description = "Fetch the kubeconfig (wait ~2 minutes after apply for K3s to be ready)."
  value       = "SSH_USER=ubuntu scripts/get-kubeconfig.sh ${aws_eip.server.public_ip}"
}
