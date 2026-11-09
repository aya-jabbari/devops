terraform {
  required_version = ">= 1.7"

  required_providers {
    hcloud = {
      source  = "hetznercloud/hcloud"
      version = "~> 1.48"
    }
  }
}

# The API token is read from the environment, never from a file in Git:
#   export TF_VAR_hcloud_token="..."
provider "hcloud" {
  token = var.hcloud_token
}
