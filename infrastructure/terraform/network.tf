locals {
  tags = {
    Project   = var.project_name
    ManagedBy = "terraform"
  }
}

data "aws_availability_zones" "available" {
  state = "available"
}

resource "aws_vpc" "main" {
  cidr_block           = "10.20.0.0/16"
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = { Name = "${var.project_name}-vpc" }
}

resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id

  tags = { Name = "${var.project_name}-igw" }
}

resource "aws_subnet" "public" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.20.1.0/24"
  availability_zone       = data.aws_availability_zones.available.names[0]
  map_public_ip_on_launch = false # the Elastic IP below is the only public address

  tags = { Name = "${var.project_name}-public" }
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }

  tags = { Name = "${var.project_name}-public" }
}

resource "aws_route_table_association" "public" {
  subnet_id      = aws_subnet.public.id
  route_table_id = aws_route_table.public.id
}

# Stable public IPv4, created first so cloud-init can put it in the K3s certificate.
resource "aws_eip" "server" {
  domain = "vpc"

  tags = { Name = "${var.project_name}-ip" }

  depends_on = [aws_internet_gateway.main]
}

# Minimal security group: only what the demo needs.
resource "aws_security_group" "server" {
  name        = "${var.project_name}-sg"
  description = "SupportOps K3s node"
  vpc_id      = aws_vpc.main.id

  tags = { Name = "${var.project_name}-sg" }
}

resource "aws_vpc_security_group_ingress_rule" "ssh" {
  for_each          = toset(var.admin_cidrs)
  security_group_id = aws_security_group.server.id
  description       = "SSH (admin)"
  ip_protocol       = "tcp"
  from_port         = 22
  to_port           = 22
  cidr_ipv4         = each.value
}

resource "aws_vpc_security_group_ingress_rule" "kube_api" {
  for_each          = toset(var.admin_cidrs)
  security_group_id = aws_security_group.server.id
  description       = "Kubernetes API (admin)"
  ip_protocol       = "tcp"
  from_port         = 6443
  to_port           = 6443
  cidr_ipv4         = each.value
}

resource "aws_vpc_security_group_ingress_rule" "argocd" {
  for_each          = toset(var.admin_cidrs)
  security_group_id = aws_security_group.server.id
  description       = "Argo CD UI (admin)"
  ip_protocol       = "tcp"
  from_port         = var.argocd_node_port
  to_port           = var.argocd_node_port
  cidr_ipv4         = each.value
}

resource "aws_vpc_security_group_ingress_rule" "http" {
  security_group_id = aws_security_group.server.id
  description       = "HTTP"
  ip_protocol       = "tcp"
  from_port         = 80
  to_port           = 80
  cidr_ipv4         = "0.0.0.0/0"
}

resource "aws_vpc_security_group_ingress_rule" "https" {
  security_group_id = aws_security_group.server.id
  description       = "HTTPS"
  ip_protocol       = "tcp"
  from_port         = 443
  to_port           = 443
  cidr_ipv4         = "0.0.0.0/0"
}

resource "aws_vpc_security_group_egress_rule" "all" {
  security_group_id = aws_security_group.server.id
  description       = "All outbound (package installs, images, K3s download)"
  ip_protocol       = "-1"
  cidr_ipv4         = "0.0.0.0/0"
}
