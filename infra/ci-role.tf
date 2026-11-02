# Role the image-building workflows (ci-jithendar-com.yml, ci-practice-executor.yml) assume through GitHub OIDC,
# replacing stored AWS access keys. Only jobs on master of this repository can assume it, and it can only push to
# and pull from the repositories above. It carries the permissions boundary from infra/bootstrap, which is the
# only kind of role the Terraform role (and therefore this stack's CI) may create or change.
data "aws_caller_identity" "current" {}

data "aws_iam_openid_connect_provider" "github" {
  url = "https://token.actions.githubusercontent.com"
}

locals {
  account_id    = data.aws_caller_identity.current.account_id
  ci_boundary   = "arn:aws:iam::${local.account_id}:policy/jithendar-com-ci-boundary"
  ecr_repo_arns = [for r in aws_ecr_repository.this : r.arn]
}

resource "aws_iam_role" "ci" {
  name                 = "github-jithendar-com-ci"
  description          = "GitHub Actions (mrjithendar/jithendar.com, master): push images to ECR"
  max_session_duration = 3600
  permissions_boundary = local.ci_boundary
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Federated = data.aws_iam_openid_connect_provider.github.arn }
      Action    = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringEquals = {
          "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
          "token.actions.githubusercontent.com:sub" = "${var.github_subject_prefix}:ref:refs/heads/master"
        }
      }
    }]
  })
}

resource "aws_iam_role_policy" "ci_ecr_push" {
  name = "ecr-push"
  role = aws_iam_role.ci.id
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
