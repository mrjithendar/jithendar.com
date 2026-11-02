# Image repositories for jithendar.com. Tags are immutable (commit SHAs) except `latest`, which CI moves:
# the site runs jithendar-com:latest with imagePullPolicy Always, and the executor manifests start from
# practice-executor:latest until CI pins digests. Sandbox images are only ever referenced by digest.
locals {
  repositories = {
    "jithendar-com"     = { mutable_tags = ["latest"] }
    "practice-executor" = { mutable_tags = ["latest"] }
    "practice-sandbox"  = { mutable_tags = ["latest"] }
  }
}

resource "aws_ecr_repository" "this" {
  for_each = local.repositories

  name                 = each.key
  image_tag_mutability = length(each.value.mutable_tags) > 0 ? "IMMUTABLE_WITH_EXCLUSION" : "IMMUTABLE"
  force_delete         = false

  dynamic "image_tag_mutability_exclusion_filter" {
    for_each = each.value.mutable_tags
    content {
      filter      = image_tag_mutability_exclusion_filter.value
      filter_type = "WILDCARD"
    }
  }

  encryption_configuration {
    encryption_type = "AES256"
  }

  image_scanning_configuration {
    scan_on_push = true
  }

  # Deleting a repository deletes the images the cluster runs. Remove this only to delete one on purpose.
  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_ecr_lifecycle_policy" "this" {
  for_each   = aws_ecr_repository.this
  repository = each.value.name
  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Expire untagged images after 7 days"
        selection    = { tagStatus = "untagged", countType = "sinceImagePushed", countUnit = "days", countNumber = 7 }
        action       = { type = "expire" }
      },
      {
        rulePriority = 2
        description  = "Keep the last ${var.image_count_to_keep} images"
        selection    = { tagStatus = "any", countType = "imageCountMoreThan", countNumber = var.image_count_to_keep }
        action       = { type = "expire" }
      },
    ]
  })
}
