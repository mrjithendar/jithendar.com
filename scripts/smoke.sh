#!/usr/bin/env bash
# Post-deploy smoke test. Usage: scripts/smoke.sh [origin] [expected-version]
# Exits non-zero if any check failed.
#
# SMOKE_VIA=http://127.0.0.1:PORT sends the app checks there instead (with Host: <origin host>), e.g. through
# `kubectl port-forward deployment/jithendar-com PORT:3000`, and skips the checks only the edge can answer
# (http -> https, www -> apex, argocd route). The deploy workflow uses this: Cloudflare answers 403 to GitHub-hosted
# runners, so the public URL cannot be tested from there.
set -euo pipefail

ORIGIN="${1:-https://jithendar.com}"
EXPECTED_VERSION="${2:-}"
HOST="${ORIGIN#https://}"
VIA="${SMOKE_VIA:-}"
failures=0

check() {
  local name="$1" expected="$2" actual="$3"
  if [[ "$actual" == "$expected" ]]; then
    echo "ok   $name"
  else
    echo "FAIL $name: expected '$expected', got '$actual'" >&2
    failures=$((failures + 1))
  fi
}

skip() { echo "skip $1 (SMOKE_VIA: edge not tested)"; }

# fetch URL [curl args…]: curl the public URL, or its path on SMOKE_VIA with the public Host header.
fetch() {
  local url="$1"; shift
  if [[ -n "$VIA" ]]; then
    curl -sS --max-time 15 -H "Host: $HOST" "$@" "$VIA${url#"$ORIGIN"}"
  else
    curl -sS --max-time 15 "$@" "$url"
  fi
}
status() { fetch "$1" -o /dev/null -w '%{http_code}'; }
location() { curl -sS -o /dev/null -w '%{redirect_url}' --max-time 15 "$1"; }

health="$(fetch "$ORIGIN/api/health")"
check "health status" '"ok"' "$(sed -nE 's/.*"status":("[^"]*").*/\1/p' <<<"$health")"
if [[ -n "$EXPECTED_VERSION" ]]; then
  # Right after `rollout status` returns, old pods are still draining (preStop sleep) and the Istio gateway may route a
  # few requests to them. Wait up to 90 s until 5 consecutive answers report the new version.
  version="" streak=0
  for _ in $(seq 1 45); do
    version="$(fetch "$ORIGIN/api/health" | sed -nE 's/.*"version":("[^"]*").*/\1/p' || true)"
    if [[ "$version" == "\"$EXPECTED_VERSION\"" ]]; then
      streak=$((streak + 1))
      [[ $streak -ge 5 ]] && break
    else
      streak=0
    fi
    sleep 2
  done
  check "health version" "\"$EXPECTED_VERSION\"" "$version"
fi

check "homepage" 200 "$(status "$ORIGIN/")"
check "about page" 200 "$(status "$ORIGIN/about")"
check "rss feed" 200 "$(status "$ORIGIN/feed.xml")"
check "sitemap.xml" 200 "$(status "$ORIGIN/sitemap.xml")"
check "news-sitemap.xml" 200 "$(status "$ORIGIN/news-sitemap.xml")"
check "robots.txt lists sitemap" 1 "$(fetch "$ORIGIN/robots.txt" | grep -c "^Sitemap: $ORIGIN/sitemap.xml$" || true)"
check "unknown page" 404 "$(status "$ORIGIN/this-page-does-not-exist")"
check "hijacked URL gone" 410 "$(status "$ORIGIN/category/cracks/")"
if [[ -n "$VIA" ]]; then
  skip "http -> https"; skip "www -> apex"; skip "argocd route untouched"
else
  check "http -> https" "$ORIGIN/" "$(location "http://$HOST/")"
  check "www -> apex" "$ORIGIN/blog" "$(location "https://www.$HOST/blog")"
  check "argocd route untouched" 200 "$(status "$ORIGIN/argocd/")"
fi

if ((failures > 0)); then
  echo "$failures smoke check(s) failed" >&2
  exit 1
fi
echo "all smoke checks passed"
