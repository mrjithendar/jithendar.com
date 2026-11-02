# Bootstrap for infra/: applied ONCE by a person with IAM admin rights, never by CI.
#
#   terraform -chdir=infra/bootstrap init && terraform -chdir=infra/bootstrap apply
#
# Creates:
#   - policy jithendar-com-ci-boundary: the most any role created by infra/ may ever do (ECR push/pull on this
#     site's repositories). Every role infra/ creates must carry it, so CI cannot grant itself more.
#   - role github-jithendar-com-terraform: what .github/workflows/infra.yml assumes through GitHub OIDC. Only jobs
#     in the GitHub environment "aws-infra" of this repository can assume it; it can manage the ECR repositories,
#     roles that carry the boundary, and its own state file — nothing else.
# It lives in its own state so that the CI role can never edit its own permissions.
terraform {
  required_version = ">= 1.10, < 2.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.20"
    }
  }
  backend "s3" {
    bucket       = "jithendardharmapuri"
    key          = "jithendar-com/bootstrap.tfstate"
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
      stack      = "jithendar.com/infra/bootstrap"
    }
  }
}

variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "github_subject_prefix" {
  type    = string
  default = "repo:mrjithendar@20453233/jithendar.com@1437838676"
}

variable "github_environment" {
  description = "GitHub environment the Terraform job runs in; restrict it to the master branch in the repository settings."
  type        = string
  default     = "aws-infra"
}

variable "state_bucket" {
  type    = string
  default = "jithendardharmapuri"
}

# Repository name patterns infra/ may manage.
variable "ecr_repositories" {
  type    = list(string)
  default = ["jithendar-com", "practice-*"]
}

data "aws_caller_identity" "current" {}

# Already exists in the account (shared with moks-github-ci); not managed here.
data "aws_iam_openid_connect_provider" "github" {
  url = "https://token.actions.githubusercontent.com"
}

locals {
  account_id    = data.aws_caller_identity.current.account_id
  ecr_repo_arns = [for r in var.ecr_repositories : "arn:aws:ecr:${var.aws_region}:${local.account_id}:repository/${r}"]
  boundary_arn  = "arn:aws:iam::${local.account_id}:policy/jithendar-com-ci-boundary"
  ci_role_arns  = ["arn:aws:iam::${local.account_id}:role/github-jithendar-com-*"]
  state_prefix  = "jithendar-com/infra.tfstate"
}

resource "aws_iam_policy" "ci_boundary" {
  name        = "jithendar-com-ci-boundary"
  description = "Permissions boundary for roles created by jithendar.com/infra: ECR push/pull on the site's repositories only"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      { Effect = "Allow", Action = "ecr:GetAuthorizationToken", Resource = "*" },
      {
        Effect = "Allow"
        Action = [
          "ecr:BatchCheckLayerAvailability", "ecr:BatchGetImage", "ecr:GetDownloadUrlForLayer",
          "ecr:InitiateLayerUpload", "ecr:UploadLayerPart", "ecr:CompleteLayerUpload", "ecr:PutImage",
          "ecr:DescribeImages", "ecr:DescribeRepositories",
        ]
        Resource = local.ecr_repo_arns
      },
    ]
  })
}

resource "aws_iam_role" "terraform" {
  name                 = "github-jithendar-com-terraform"
  description          = "GitHub Actions (mrjithendar/jithendar.com, environment ${var.github_environment}): apply infra/"
  max_session_duration = 3600
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Federated = data.aws_iam_openid_connect_provider.github.arn }
      Action    = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringEquals = {
          "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
          "token.actions.githubusercontent.com:sub" = "${var.github_subject_prefix}:environment:${var.github_environment}"
        }
      }
    }]
  })
}

resource "aws_iam_role_policy" "terraform" {
  name = "manage-jithendar-com-infra"
  role = aws_iam_role.terraform.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      # Remote state (S3-native lock file next to it).
      {
        Sid       = "StateList"
        Effect    = "Allow"
        Action    = "s3:ListBucket"
        Resource  = "arn:aws:s3:::${var.state_bucket}"
        Condition = { StringLike = { "s3:prefix" = ["${local.state_prefix}*"] } }
      },
      {
        Sid      = "StateObjects"
        Effect   = "Allow"
        Action   = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"]
        Resource = ["arn:aws:s3:::${var.state_bucket}/${local.state_prefix}", "arn:aws:s3:::${var.state_bucket}/${local.state_prefix}.tflock"]
      },
      # ECR repositories of this site. No DeleteRepository: removing one is a manual decision.
      {
        Sid    = "Repositories"
        Effect = "Allow"
        Action = [
          "ecr:CreateRepository", "ecr:DescribeRepositories", "ecr:ListTagsForResource", "ecr:TagResource",
          "ecr:UntagResource", "ecr:PutImageTagMutability", "ecr:PutImageScanningConfiguration",
          "ecr:GetLifecyclePolicy", "ecr:PutLifecyclePolicy", "ecr:DeleteLifecyclePolicy",
          "ecr:GetRepositoryPolicy",
        ]
        Resource = local.ecr_repo_arns
      },
      # Reading roles and the OIDC provider (plan/refresh).
      {
        Sid    = "ReadIam"
        Effect = "Allow"
        Action = [
          "iam:GetRole", "iam:GetRolePolicy", "iam:ListRolePolicies", "iam:ListAttachedRolePolicies",
          "iam:ListInstanceProfilesForRole",
        ]
        Resource = local.ci_role_arns
      },
      { Sid = "ReadOidc", Effect = "Allow", Action = "iam:GetOpenIDConnectProvider", Resource = data.aws_iam_openid_connect_provider.github.arn },
      # Creating and changing roles only while they carry the boundary, so CI cannot grant more than ECR push/pull.
      {
        Sid    = "ManageBoundedRoles"
        Effect = "Allow"
        Action = [
          "iam:CreateRole", "iam:PutRolePolicy", "iam:DeleteRolePolicy", "iam:PutRolePermissionsBoundary",
          "iam:AttachRolePolicy", "iam:DetachRolePolicy",
        ]
        Resource  = local.ci_role_arns
        Condition = { StringEquals = { "iam:PermissionsBoundary" = local.boundary_arn } }
      },
      {
        Sid    = "ChangeRoleMetadata"
        Effect = "Allow"
        Action = [
          "iam:UpdateRole", "iam:UpdateRoleDescription", "iam:UpdateAssumeRolePolicy", "iam:TagRole",
          "iam:UntagRole", "iam:DeleteRole",
        ]
        Resource = local.ci_role_arns
      },
      # Never: the Terraform role itself, the boundary policy, or lifting a boundary.
      {
        Sid      = "ProtectBootstrap"
        Effect   = "Deny"
        Action   = "iam:*"
        Resource = [local.boundary_arn, "arn:aws:iam::${local.account_id}:role/github-jithendar-com-terraform"]
      },
      {
        Sid      = "KeepBoundaries"
        Effect   = "Deny"
        Action   = "iam:DeleteRolePermissionsBoundary"
        Resource = "*"
      },
    ]
  })
}

output "terraform_role_arn" {
  description = "Set as repository variable AWS_TERRAFORM_ROLE_ARN."
  value       = aws_iam_role.terraform.arn
}

output "ci_boundary_arn" {
  value = aws_iam_policy.ci_boundary.arn
}
