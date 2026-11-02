terraform {
  required_version = ">= 1.10, < 2.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.20"
    }
  }

  # Same bucket as tools/infrastructure, separate key. use_lockfile: S3-native locking (no DynamoDB table).
  backend "s3" {
    bucket       = "jithendardharmapuri"
    key          = "jithendar-com/infra.tfstate"
    region       = "us-east-1"
    encrypt      = true
    use_lockfile = true
  }
}

provider "aws" {
  region = var.aws_region
  default_tags {
    tags = {
      project    = "jithendar.com"
      managed-by = "terraform"
      stack      = "jithendar.com/infra"
    }
  }
}
