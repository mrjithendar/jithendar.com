output "ci_role_arn" {
  description = "Set as repository variable AWS_CI_ROLE_ARN (the image workflows assume it)."
  value       = aws_iam_role.ci.arn
}

output "repository_urls" {
  value = { for k, r in aws_ecr_repository.this : k => r.repository_url }
}
