terraform -chdir=infra/bootstrap init
terraform -chdir=infra/bootstrap plan      # should say: 3 to add, 0 to change, 0 to destroy
terraform -chdir=infra/bootstrap apply


R=mrjithendar/jithendar.com

# Environment "aws-infra", usable only from master
gh api -X PUT repos/$R/environments/aws-infra \
  -F 'deployment_branch_policy[protected_branches]=false' \
  -F 'deployment_branch_policy[custom_branch_policies]=true'
gh api -X POST repos/$R/environments/aws-infra/deployment-branch-policies -f name=master

# Role ARNs the workflows use
gh variable set AWS_TERRAFORM_ROLE_ARN -R $R --body arn:aws:iam::881026659929:role/github-jithendar-com-terraform
gh variable set AWS_CI_ROLE_ARN        -R $R --body arn:aws:iam::881026659929:role/github-jithendar-com-ci


# gh secret delete AWS_ACCESS_KEY_ID -R $R
# gh secret delete AWS_SECRET_ACCESS_KEY -R $R
