# Official Ubuntu 24.04 image published by Canonical.
data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"]

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-amd64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

resource "aws_key_pair" "admin" {
  key_name   = "${var.project_name}-admin"
  public_key = file(pathexpand(var.ssh_public_key_path))
}

resource "aws_instance" "k3s" {
  ami                         = data.aws_ami.ubuntu.id
  instance_type               = var.instance_type
  subnet_id                   = aws_subnet.public.id
  vpc_security_group_ids      = [aws_security_group.server.id]
  key_name                    = aws_key_pair.admin.key_name
  associate_public_ip_address = false

  root_block_device {
    volume_type           = "gp3"
    volume_size           = var.root_volume_gb
    encrypted             = true
    delete_on_termination = true # terraform destroy must leave nothing billable behind
  }

  metadata_options {
    http_tokens = "required" # IMDSv2 only
  }

  user_data = templatefile("${path.module}/cloud-init.yaml", {
    public_ip   = aws_eip.server.public_ip
    k3s_version = var.k3s_version
  })

  # cloud-init only runs on first boot: a changed script must replace the server.
  user_data_replace_on_change = true

  tags = { Name = "${var.project_name}-k3s" }
}

resource "aws_eip_association" "server" {
  instance_id   = aws_instance.k3s.id
  allocation_id = aws_eip.server.id
}
