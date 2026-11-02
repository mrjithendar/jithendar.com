# infra — AWS resources for jithendar.com (Terraform)

| Stack | Applied by | State (`s3://jithendardharmapuri/…`) | Creates |
|---|---|---|---|
| `infra/bootstrap` | a person, once, with IAM admin credentials | `jithendar-com/bootstrap.tfstate` | policy `jithendar-com-ci-boundary`, role `github-jithendar-com-terraform` |
| `infra` | CI (`.github/workflows/infra.yml`) on `master` | `jithendar-com/infra.tfstate` | ECR `jithendar-com`, `practice-executor`, `practice-sandbox` (scan on push, immutable tags except `latest`, last 30 images kept, untagged expire after 7 days); role `github-jithendar-com-ci` |

Separate from `tools/infrastructure` on purpose: that stack auto-applies the whole account's network and EKS
from a self-hosted runner. This one only touches this site's repositories and roles.

## Who can do what

- **`github-jithendar-com-ci`** (assumed by `ci-jithendar-com.yml` and `ci-practice-executor.yml`): push and pull
  images in the three repositories. Only jobs on `master` of this repository can assume it.
- **`github-jithendar-com-terraform`** (assumed by `infra.yml`): manage those repositories (not delete them), and
  create or change roles named `github-jithendar-com-*` only while they carry `jithendar-com-ci-boundary`, which
  caps them at ECR push/pull. It cannot change itself or the boundary, so a change merged to `infra/` cannot
  turn CI into an admin. Only jobs in the GitHub environment `aws-infra` can assume it.
- Repositories have `prevent_destroy`; the Terraform role has no `ecr:DeleteRepository` either.

## First-time setup (in order)

1. **Bootstrap** (Mac, admin credentials):
   ```sh
   terraform -chdir=infra/bootstrap init
   terraform -chdir=infra/bootstrap apply
   ```
2. **GitHub** (repository settings, or `gh`):
   - Environment `aws-infra` with *Deployment branches* limited to `master`
     (`gh api -X PUT repos/mrjithendar/jithendar.com/environments/aws-infra -F 'deployment_branch_policy[protected_branches]=false' -F 'deployment_branch_policy[custom_branch_policies]=true'`,
     then `gh api -X POST repos/mrjithendar/jithendar.com/environments/aws-infra/deployment-branch-policies -f name=master`).
   - Variables: `AWS_TERRAFORM_ROLE_ARN=arn:aws:iam::881026659929:role/github-jithendar-com-terraform` and
     `AWS_CI_ROLE_ARN=arn:aws:iam::881026659929:role/github-jithendar-com-ci`.
3. **Push `infra/` to `master`.** `infra.yml` plans and applies; the summary lists what it created.
4. **Re-run** the image workflows (`jithendar.com`, `practice-executor`) if they ran before step 3 finished.
5. **Remove the stored AWS keys:** `gh secret delete AWS_ACCESS_KEY_ID` and `gh secret delete AWS_SECRET_ACCESS_KEY`.
   They held the account **root** access key; deactivate and delete that key in IAM (Security credentials) once
   nothing else uses it.

If a repository already exists when the stack is first applied (for example `jithendar-com` was recreated by
hand), adopt it instead of failing: `terraform -chdir=infra import 'aws_ecr_repository.this["jithendar-com"]' jithendar-com`
(from the Mac with admin credentials), then push.

## Changing things

Edit `infra/*.tf`, open a pull request (CI checks format and validates; it has no AWS access), merge. To preview
from the Mac without changing anything: `terraform -chdir=infra plan -lock=false`.
Pulls on mk4 use the `ecr-pull` Secret from the `ecr-refresh` CronJob in the tools repository; if its IAM principal
is limited to named repositories, add `practice-executor` and `practice-sandbox` there.
