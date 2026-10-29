#!/usr/bin/env bash
# One-time (until GitHub OIDC replaces it): an IAM user that can only push images to the jithendar-com ECR
# repository, with its access key stored as GitHub repository secrets for .github/workflows/ci-jithendar-com.yml.
#
#   scripts/setup-ci-ecr-user.sh            # create user + policy + key, store the secrets
#   ROTATE=1 scripts/setup-ci-ecr-user.sh   # replace the key (old keys are deleted after the new one is stored)
#
# The secret key goes straight from AWS into `gh secret set` (stdin); it is never printed or written to disk.
# Needs: aws CLI signed in as an IAM admin, gh CLI signed in with admin on the repository.
set -euo pipefail

REPO="${GITHUB_REPO:-mrjithendar/jithendar.com}"
USER_NAME="${IAM_USER:-github-jithendar-com-ecr}"
REGION="${AWS_REGION:-us-east-1}"
ECR_REPO="${ECR_REPOSITORY:-jithendar-com}"

ACCOUNT="$(aws sts get-caller-identity --query Account --output text)"
echo "→ AWS account $ACCOUNT, IAM user $USER_NAME, repository $REPO"

if aws iam get-user --user-name "$USER_NAME" >/dev/null 2>&1; then
  echo "→ User exists"
else
  echo "→ Creating user"
  aws iam create-user --user-name "$USER_NAME" --tags Key=purpose,Value="GitHub Actions $REPO ECR push" >/dev/null
fi

aws iam put-user-policy --user-name "$USER_NAME" --policy-name ecr-push --policy-document "$(cat <<JSON
{
  "Version": "2012-10-17",
  "Statement": [
    { "Effect": "Allow", "Action": "ecr:GetAuthorizationToken", "Resource": "*" },
    {
      "Effect": "Allow",
      "Action": [
        "ecr:BatchCheckLayerAvailability", "ecr:BatchGetImage", "ecr:GetDownloadUrlForLayer",
        "ecr:InitiateLayerUpload", "ecr:UploadLayerPart", "ecr:CompleteLayerUpload", "ecr:PutImage",
        "ecr:DescribeImages", "ecr:DescribeRepositories"
      ],
      "Resource": "arn:aws:ecr:${REGION}:${ACCOUNT}:repository/${ECR_REPO}"
    }
  ]
}
JSON
)"
echo "→ Policy ecr-push attached (push/pull on $ECR_REPO only)"

OLD_KEYS="$(aws iam list-access-keys --user-name "$USER_NAME" --query 'AccessKeyMetadata[].AccessKeyId' --output text)"
if [[ -n "$OLD_KEYS" && "${ROTATE:-0}" != "1" ]]; then
  echo "The user already has an access key ($OLD_KEYS). Rerun with ROTATE=1 to replace it." >&2
  exit 1
fi

echo "→ Creating a new access key and storing it as repository secrets"
read -r KEY_ID KEY_SECRET < <(aws iam create-access-key --user-name "$USER_NAME" --query 'AccessKey.[AccessKeyId,SecretAccessKey]' --output text)
printf '%s' "$KEY_ID" | gh secret set AWS_ACCESS_KEY_ID --repo "$REPO"
printf '%s' "$KEY_SECRET" | gh secret set AWS_SECRET_ACCESS_KEY --repo "$REPO"
unset KEY_SECRET

for old in $OLD_KEYS; do
  echo "→ Deleting old key $old"
  aws iam delete-access-key --user-name "$USER_NAME" --access-key-id "$old"
done

echo "Done: key $KEY_ID stored in $REPO (secrets AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)."
echo "Rotate it every 90 days with ROTATE=1, and delete the user once OIDC is in place."
