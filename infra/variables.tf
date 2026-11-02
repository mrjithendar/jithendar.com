variable "aws_region" {
  type    = string
  default = "us-east-1"
}

# GitHub OIDC subject prefix of mrjithendar/jithendar.com. The repository uses immutable subjects
# (gh api repos/mrjithendar/jithendar.com/actions/oidc/customization/sub), so ids are part of the claim.
variable "github_subject_prefix" {
  type    = string
  default = "repo:mrjithendar@20453233/jithendar.com@1437838676"
}

variable "image_count_to_keep" {
  description = "Images kept per repository; older ones (and untagged ones after 7 days) are expired."
  type        = number
  default     = 5
}
