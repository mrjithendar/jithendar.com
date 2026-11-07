#!/usr/bin/env bash
# Create or replace Secret jithendar/harbor-pull, the site's pull secret for registry.jithendar.com (run by an admin,
# never by CI). Safe to re-run: use it again to rotate the robot.
#   scripts/create-harbor-pull-secret.sh [kube-context]
# Prompts for a Harbor robot with pull access to project jithendar (default robot$k8s-pull; see
# tools/deploy/minikube/harbor/README.md, "Kubernetes robot"). The secret goes to kubectl on stdin, never argv.
set -euo pipefail

CONTEXT="${1:-mk4}"
REGISTRY="registry.jithendar.com"

read -r -p "Harbor robot user [robot\$k8s-pull]: " ROBOT_USER
ROBOT_USER="${ROBOT_USER:-robot\$k8s-pull}"
read -r -s -p "Secret for $ROBOT_USER: " ROBOT_SECRET; echo
[[ -n "$ROBOT_SECRET" ]] || { echo "The robot secret is required." >&2; exit 1; }

# Check the robot before storing it: a bad pull secret only shows up when a pod restarts. Harbor's token service
# answers 200 even for wrong credentials, with an empty action list, so check that the token grants pull.
granted="$(printf 'user = "%s:%s"\n' "$ROBOT_USER" "$ROBOT_SECRET" |
  curl -fsS --config - "https://$REGISTRY/service/token?service=harbor-registry&scope=repository:jithendar/jithendar-com:pull" |
  python3 -c 'import base64, json, sys
claims = json.load(sys.stdin)["token"].split(".")[1]
access = json.loads(base64.urlsafe_b64decode(claims + "=" * (-len(claims) % 4))).get("access") or []
print(" ".join(a for entry in access for a in entry.get("actions", [])))')"
[[ " $granted " == *" pull "* ]] || {
  echo "$ROBOT_USER cannot pull from project jithendar (wrong secret, or the robot lacks access). Nothing changed." >&2
  exit 1
}

ROBOT_USER="$ROBOT_USER" ROBOT_SECRET="$ROBOT_SECRET" REGISTRY="$REGISTRY" python3 - <<'EOF' |
import base64, json, os
auth = base64.b64encode(f"{os.environ['ROBOT_USER']}:{os.environ['ROBOT_SECRET']}".encode()).decode()
config = json.dumps({"auths": {os.environ["REGISTRY"]: {"auth": auth}}})
print(json.dumps({"apiVersion": "v1", "kind": "Secret", "type": "kubernetes.io/dockerconfigjson",
                  "metadata": {"name": "harbor-pull", "namespace": "jithendar"},
                  "data": {".dockerconfigjson": base64.b64encode(config.encode()).decode()}}))
EOF
  kubectl --context "$CONTEXT" apply -f -

echo "Secret jithendar/harbor-pull is ready. Next: ./deploy.sh"
