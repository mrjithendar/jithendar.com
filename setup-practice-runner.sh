# 1. On the mk4 host (needs minikube there): install gVisor
scripts/install-gvisor-mk4.sh            # dry run: should list 5 nodes, "would install..."
scripts/install-gvisor-mk4.sh --apply    # restarts containerd one node at a time

# 2. From the Mac: code runner + its secret
kubectl --context mk4 apply -k k8s/practice-executor
scripts/create-practice-executor-secrets.sh mk4   # prints PRACTICE_EXECUTOR_TOKEN, keep it

# 3. Prove the sandbox is isolated (every line must be PASS)
scripts/verify-practice-sandbox.sh

# 4. Let CI deploy the images, then run it
scripts/setup-practice-ci-deployer.sh
gh variable set PRACTICE_EXECUTOR_DEPLOY --body true
gh workflow run ci-practice-executor.yml --ref master


# 5. Connect the site
kubectl --context mk4 -n jithendar patch secret jithendar-com-env --type merge \
  -p '{"stringData":{"PRACTICE_EXECUTOR_URL":"http://practice-executor.practice-exec","PRACTICE_EXECUTOR_TOKEN":"<token from step 2>"}}'
./deploy.sh        # applies the site's network rule to the code runner and restarts the site
