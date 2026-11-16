#!/usr/bin/env bash
# One-time creation of the jithendar.com Secrets in namespace jithendar (run by an admin, never by CI).
#   KUBE_CONTEXT=mk4 scripts/create-secrets.sh
#   (kube context: KUBE_CONTEXT=<name>, else the current context with a confirmation prompt; scripts/lib/kube-context.sh)
# Generates every password/key randomly. Prompts only for Cloudflare Turnstile keys and optional SMTP.
# Refuses to overwrite an existing Secret (SETTINGS_ENCRYPTION_KEY decrypts stored credentials).
# DATABASE_URL is not here: Terraform in the miniKube repo writes postgres-db-credentials, which
# kubernetes/30-jithendar-com.yaml reads. The site runs without Redis (no REDIS_URL).
set -euo pipefail
# shellcheck source=/dev/null
source "$(dirname -- "${BASH_SOURCE[0]}")/lib/kube-context.sh"

NS="jithendar"
k() { kubectl -n "$NS" "$@"; }
rand() { openssl rand -base64 48 | tr -d '/+=\n' | cut -c1-"${1:-40}"; }

if k get secret jithendar-com-env >/dev/null 2>&1; then
  echo "Secret jithendar-com-env already exists. Nothing changed. (Delete it deliberately first if you really mean to recreate it.)" >&2
  exit 1
fi

read -r -p "Cloudflare Turnstile site key: " TURNSTILE_SITE_KEY
read -r -s -p "Cloudflare Turnstile secret key: " TURNSTILE_SECRET_KEY; echo
[[ -n "$TURNSTILE_SITE_KEY" && -n "$TURNSTILE_SECRET_KEY" ]] || { echo "Turnstile keys are required (Cloudflare dashboard → Turnstile → add site jithendar.com)." >&2; exit 1; }
read -r -p "SMTP URL (optional, e.g. smtps://user:pass@smtp.example.com:465; Enter to skip): " SMTP_URL
MAIL_FROM=""
[[ -n "$SMTP_URL" ]] && read -r -p "Mail From (e.g. Jithendar.com <no-reply@jithendar.com>): " MAIL_FROM

BOOTSTRAP="$(rand 48)"

args=(
  --from-literal=BETTER_AUTH_SECRET="$(rand 64)"
  --from-literal=SETTINGS_ENCRYPTION_KEY="$(rand 64)"
  --from-literal=ADMIN_BOOTSTRAP_TOKEN="$BOOTSTRAP"
  --from-literal=METRICS_TOKEN="$(rand 40)"
  --from-literal=TURNSTILE_SITE_KEY="$TURNSTILE_SITE_KEY"
  --from-literal=TURNSTILE_SECRET_KEY="$TURNSTILE_SECRET_KEY"
)
[[ -n "$SMTP_URL" ]] && args+=(--from-literal=SMTP_URL="$SMTP_URL" --from-literal=MAIL_FROM="$MAIL_FROM")
k create secret generic jithendar-com-env "${args[@]}"

cat <<MSG

Secret created in namespace $NS: jithendar-com-env.
DATABASE_URL is not here: the site reads it from postgres-db-credentials (shared CloudNativePG cluster,
Terraform in miniKube). The site runs without Redis.

One-time admin setup token (shown once; also stored in jithendar-com-env/ADMIN_BOOTSTRAP_TOKEN):

  $BOOTSTRAP

After deploying, open https://jithendar.com/setup and use it to create the first admin.
Back up SETTINGS_ENCRYPTION_KEY with your database backups: without it, stored S3/backup
credentials cannot be decrypted.
MSG
