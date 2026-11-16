#!/usr/bin/env bash
# Check this site's files with the CMS that will serve them: start the moks-cms image the Deployment runs (the web
# container's image in kubernetes/30-jithendar-com.yaml) with this repository's content/, public/images/, site.json
# and config/ mounted where the content image puts them, and an embedded database (PGlite, so no Secrets), then
# request the main pages and every published article. moks-cms validates the content when it loads it (schema,
# related links, images): an invalid article makes these pages answer 500, so it is caught here, before the content
# image is pushed and the pods would serve it.
#
#   scripts/check-content.sh [<moks-cms image>]     (default: the image in kubernetes/30-jithendar-com.yaml)
#
# Needs Docker and a login to registry.jithendar.com. CI runs it in check.yml (pull requests) and content.yml.
set -euo pipefail
root="$(cd "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
IMAGE="${1:-$(sed -n 's/^ *image: \(registry\.jithendar\.com\/jithendar\/moks-cms:[^ ]*\)$/\1/p' "$root/kubernetes/30-jithendar-com.yaml" | head -1)}"
[[ -n "$IMAGE" ]] || { echo "No moks-cms image in kubernetes/30-jithendar-com.yaml" >&2; exit 1; }
name="content-check-${GITHUB_RUN_ID:-local}-$$"
site="$(mktemp -d)"
cp "$root/site.json" "$site/" && cp -R "$root/config" "$site/"
chmod -R a+rX "$site"

echo "Checking the content with $IMAGE"
docker run -d --rm --name "$name" -e APP_ENV=development -e PGLITE_DIR=/tmp/pglite \
  -v "$root/content:/app/content:ro" -v "$root/public/images:/app/public/images:ro" -v "$site:/app/site:ro" \
  -p 127.0.0.1::3000 "$IMAGE" >/dev/null
cleanup() {
  local status=$?
  # On failure, the CMS's own error lines say which article is wrong.
  [[ $status -eq 0 ]] || docker logs "$name" 2>&1 | grep -E '"level":"(error|warn)"' | tail -20 || true
  docker rm -f "$name" >/dev/null 2>&1 || true
  rm -rf "$site"
}
trap cleanup EXIT
port="$(docker port "$name" 3000/tcp | head -1 | sed 's/.*://')"
for _ in $(seq 1 90); do curl -fsS "http://127.0.0.1:$port/api/health" >/dev/null 2>&1 && break; sleep 1; done
curl -fsS "http://127.0.0.1:$port/api/health" >/dev/null || { echo "The CMS did not start" >&2; exit 1; }

# The main pages, then every published article (status: published in its frontmatter; the URL is its slug or file name).
mapfile -t pages < <(printf '%s\n' / /blog /news /projects /about /hire-me /python-practice /sitemap.xml /robots.txt
  python3 - "$root/content" <<'PY'
import pathlib, re, sys
for f in sorted(pathlib.Path(sys.argv[1]).glob("*/*.mdx")):
    if f.parent.name not in ("blog", "news", "projects"):
        continue
    m = re.match(r"---\n(.*?)\n---", f.read_text(), re.S)
    fm = m.group(1) if m else ""
    if re.search(r"^status:\s*[\"']?published", fm, re.M):
        slug = re.search(r"^slug:\s*[\"']?([a-z0-9-]+)", fm, re.M)
        print(f"/{f.parent.name}/{slug.group(1) if slug else f.stem}")
PY
)
failed=0
for p in "${pages[@]}"; do
  code="$(curl -sS -m 120 -o /dev/null -w '%{http_code}' "http://127.0.0.1:$port$p" || echo 000)"
  echo "$code $p"
  [[ "$code" == 200 ]] || failed=1
done
[[ $failed -eq 0 ]] || { echo "::error::Some pages did not answer 200 with this content (log lines above)"; exit 1; }
echo "Content OK: ${#pages[@]} pages answered 200"
