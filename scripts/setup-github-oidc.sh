#!/usr/bin/env bash
# One-time: let GitHub Actions (master branch of this repository only) push images to ECR without stored AWS keys.
#
#   scripts/setup-github-oidc.sh
#
# Creates (or updates) in the current AWS account:
#   - the GitHub OIDC identity provider token.actions.githubusercontent.com (if missing)
#   - IAM role github-jithendar-com-ecr, assumable only by mrjithendar/jithendar.com on refs/heads/master
#   - an inline policy: push/pull on the jithendar-com ECR repository, nothing else
# and sets the repository variable AWS_ROLE_ARN that .github/workflows/ci-jithendar-com.yml uses.
# Safe to rerun. Needs: aws CLI signed in as an IAM admin, gh CLI signed in with admin on the repository.
set -euo pipefail

REPO="${GITHUB_REPO:-mrjithendar/jithendar.com}"
BRANCH="${GITHUB_BRANCH:-master}"
ROLE="${ROLE_NAME:-github-jithendar-com-ecr}"
REGION="${AWS_REGION:-us-east-1}"
ECR_REPO="${ECR_REPOSITORY:-jithendar-com}"
ISSUER="token.actions.githubusercontent.com"

ACCOUNT="$(aws sts get-caller-identity --query Account --output text)"
PROVIDER_ARN="arn:aws:iam::${ACCOUNT}:oidc-provider/${ISSUER}"
echo "→ AWS account $ACCOUNT, repository $REPO ($BRANCH)"

if aws iam get-open-id-connect-provider --open-id-connect-provider-arn "$PROVIDER_ARN" >/dev/null 2>&1; then
  echo "→ OIDC provider exists"
else
  echo "→ Creating OIDC provider $ISSUER"
  # AWS validates GitHub's certificate itself; the thumbprint is required by the API but not used for this issuer.
  aws iam create-open-id-connect-provider --url "https://$ISSUER" --client-id-list sts.amazonaws.com \
    --thumbprint-list 6938fd4d98bab03faadb97b34396831e3780aea1 >/dev/null
fi

TRUST="$(cat <<JSON
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": { "Federated": "$PROVIDER_ARN" },
    "Action": "sts:AssumeRoleWithWebIdentity",
    "Condition": {
      "StringEquals": {
        "$ISSUER:aud": "sts.amazonaws.com",
        "$ISSUER:sub": "repo:$REPO:ref:refs/heads/$BRANCH"
      }
    }
  }]
}
JSON
)"

POLICY="$(cat <<JSON
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

if aws iam get-role --role-name "$ROLE" >/dev/null 2>&1; then
  echo "→ Updating trust policy of role $ROLE"
  aws iam update-assume-role-policy --role-name "$ROLE" --policy-document "$TRUST"
else
  echo "→ Creating role $ROLE"
  aws iam create-role --role-name "$ROLE" --assume-role-policy-document "$TRUST" \
    --description "GitHub Actions $REPO ($BRANCH): push to ECR $ECR_REPO" --max-session-duration 3600 >/dev/null
fi
aws iam put-role-policy --role-name "$ROLE" --policy-name ecr-push --policy-document "$POLICY"
ROLE_ARN="$(aws iam get-role --role-name "$ROLE" --query Role.Arn --output text)"

echo "→ Setting repository variable AWS_ROLE_ARN"
gh variable set AWS_ROLE_ARN --repo "$REPO" --body "$ROLE_ARN"

echo "Done: $ROLE_ARN"
echo "The next push to $BRANCH builds on GitHub-hosted runners. Then remove this repository's runners from the server: bash runner/setup.sh remove"
