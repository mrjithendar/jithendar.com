# Python practice code runner on mk4. Comments are on their own lines: pasted into zsh, a trailing "# ..." is
# passed to the command as arguments (unless `setopt interactivecomments`).

# 1. gVisor on every node. Must run ON THE mk4 HOST (where minikube runs), not on the Mac.
#    Dry run first (one "→ mk4..." block per node), then --apply (each node ends with "active" and a runsc version).
scp scripts/install-gvisor-mk4.sh <user>@<mk4-host>:/tmp/
ssh <user>@<mk4-host> bash /tmp/install-gvisor-mk4.sh
ssh <user>@<mk4-host> bash /tmp/install-gvisor-mk4.sh --apply

# 2. Back on the Mac. Every line must be PASS; stop here if not.
kubectl -n jithendar delete pod -l practice.jithendar.com/verify=true
scripts/verify-practice-sandbox.sh

# 3. Site: new executor URL + network rule + CI account rights, then restart (this was ./deploy.sh until
#    2026-11-14; the workflow applies kubernetes/ and restarts the site, and waits for the result)
gh workflow run deploy-kubernetes.yml --ref master
sleep 10 # give GitHub time to create the run before looking it up
gh run watch "$(gh run list --workflow deploy-kubernetes.yml --limit 1 --json databaseId --jq '.[0].databaseId')" --exit-status

# 4. Put the executor on the tag pinned in moks-cms.json ("practiceExecutor"; repository variable
#    PRACTICE_EXECUTOR_DEPLOY must be "true"). moks-cms builds the images; this repository rolls them out.
gh workflow run release.yml --ref master -f app=false -f content=false -f services=true
