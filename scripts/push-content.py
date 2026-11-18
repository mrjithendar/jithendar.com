#!/usr/bin/env python3
"""Push this site's images and articles to the CMS that serves it, through its API. Nothing is built or restarted.

  JITHENDAR_API_KEY=jk_… scripts/push-content.py [options] [content/blog/a-post.mdx …]

1. Images: every file under public/images/ that the site does not have yet, or has with other bytes, is sent with
   PUT /api/v1/images/<path>. The site keeps the SHA-256 of each file it was sent (GET /api/v1/images), so files that
   have not changed are not sent again. The site stores a PNG as lossless WebP; articles keep the .png path.
2. Articles: each file named on the command line (content/{blog,news,projects}/<slug>.mdx) is sent with
   PUT /api/v1/posts/by-path/<collection>/<slug>.mdx. A new slug becomes a DRAFT, whatever the file's status says. A
   post that is still a draft or in review is updated from the file. A published, scheduled or archived post is left
   alone: edit those in Admin → Posts. Nothing is ever published from here.

Images go first, because the site refuses an article whose image it does not have. An article that names a related
post which is sent in the same run is tried again after the others. Articles that name each other (A relates to B and
B to A) are each created without those related posts first, then sent whole, so they end up linked both ways.

The key (Admin → API keys, created by an admin) needs the scopes images:write and posts:draft. A posts:draft key cannot
publish, schedule or delete, so a leaked CI secret cannot change an article readers see; with images:write it can
replace an image on a live page.

Options:
  --site URL         the site (default: https://<host in site.json>)
  --images-dir DIR   default public/images
  --no-images        send articles only
  --all-posts        send every article file under content/, not only the ones named
  --create-only      create new drafts but never change an existing post
  --dry-run          say what would be sent; send nothing (the image comparison still asks the site)
  --summary FILE     also write the report there as Markdown (default: $GITHUB_STEP_SUMMARY when set)

Exit status: 0 everything sent or already there, 1 at least one file was refused, 2 it could not start (no key, no
site, the site has no such API). Python 3.9 or later, standard library only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COLLECTIONS = ("blog", "news", "projects")
IMAGE_TYPES = {".png", ".jpg", ".jpeg", ".webp", ".avif", ".gif", ".svg"}
RELATED_MISSING = re.compile(r'^related: ".*" does not exist')
TIMEOUT = 60
MAX_TRIES = 6


class Stop(Exception):
    """The run cannot go on (exit status 2)."""


class Api:
    def __init__(self, site: str, key: str, sleep=time.sleep):
        self.site = site.rstrip("/")
        self.key = key
        self.sleep = sleep

    def call(self, method: str, path: str, body: bytes | None = None, content_type: str | None = None) -> tuple[int, dict]:
        """One request, repeated while the site says "slow down" (429) or is briefly unavailable. Returns (status, JSON)."""
        headers = {"Authorization": f"Bearer {self.key}", "Accept": "application/json", "User-Agent": "push-content"}
        if content_type:
            headers["Content-Type"] = content_type
        last = "no answer"
        for attempt in range(1, MAX_TRIES + 1):
            request = urllib.request.Request(self.site + path, data=body, method=method, headers=headers)
            try:
                with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
                    return response.status, _json(response.read())
            except urllib.error.HTTPError as error:
                payload = _json(error.read())
                if error.code == 429 and attempt < MAX_TRIES:
                    # 120 requests a minute per key: wait as long as the site asks, then carry on.
                    self.sleep(min(float(error.headers.get("Retry-After") or 60), 90))
                    continue
                if error.code in (502, 503, 504) and attempt < MAX_TRIES:
                    last = f"HTTP {error.code}"
                    self.sleep(min(2**attempt, 30))
                    continue
                return error.code, payload
            except (urllib.error.URLError, TimeoutError, ConnectionError) as error:
                last = str(getattr(error, "reason", error))
                if attempt < MAX_TRIES:
                    self.sleep(min(2**attempt, 30))
        raise Stop(f"{self.site} did not answer {method} {path}: {last}")


def _json(raw: bytes) -> dict:
    try:
        value = json.loads(raw.decode("utf-8")) if raw else {}
    except (ValueError, UnicodeDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def reason_of(status: int, payload: dict) -> str:
    error = payload.get("error") if isinstance(payload.get("error"), dict) else {}
    parts = [str(error.get("message") or f"HTTP {status}")] + [str(i) for i in (error.get("issues") or [])]
    return " · ".join(parts) if status != 404 else f"HTTP 404 ({parts[0]})"


# --- Images ------------------------------------------------------------------------------------


def local_images(directory: Path) -> tuple[dict[str, Path], list[str]]:
    """{"/images/a/b.png": file} for every image file, and the files that are not images (reported, never sent)."""
    found: dict[str, Path] = {}
    other: list[str] = []
    if not directory.is_dir():
        return found, other
    for file in sorted(directory.rglob("*")):
        relative = file.relative_to(directory)
        if not file.is_file() or any(part.startswith(".") for part in relative.parts):
            continue
        if file.suffix.lower() in IMAGE_TYPES:
            found["/images/" + relative.as_posix()] = file
        else:
            other.append(relative.as_posix())
    return found, other


def stored_images(api: Api) -> dict[str, str]:
    """{path: SHA-256 of the file the site was sent} for every image the site has."""
    stored: dict[str, str] = {}
    offset = 0
    while True:
        status, payload = api.call("GET", f"/api/v1/images?limit=1000&offset={offset}")
        if status == 404:
            raise Stop(f"{api.site} has no /api/v1/images: it runs a moks-cms release from before site images were stored in R2")
        if status != 200:
            raise Stop(f"{api.site} refused to list its images: {reason_of(status, payload)}")
        page = payload.get("data") or []
        for row in page:
            stored[row["path"]] = row["sha256"]
        if len(page) < 1000:
            return stored
        offset += 1000


def push_images(api: Api, directory: Path, dry_run: bool) -> dict:
    files, other = local_images(directory)
    stored = stored_images(api)
    report = {"created": [], "replaced": [], "unchanged": 0, "failed": [], "not_images": other, "only_on_site": sorted(set(stored) - set(files))}
    for path, file in files.items():
        data = file.read_bytes()
        if stored.get(path) == hashlib.sha256(data).hexdigest():
            report["unchanged"] += 1
            continue
        kind = "replaced" if path in stored else "created"
        if dry_run:
            report[kind].append(path)
            continue
        status, payload = api.call("PUT", "/api/v1" + urllib.parse.quote(path), data, "application/octet-stream")
        if status == 200:
            result = payload.get("data") or {}
            if result.get("unchanged"):
                report["unchanged"] += 1
            else:
                report["created" if result.get("created") else "replaced"].append(path)
        else:
            report["failed"].append((path, reason_of(status, payload)))
    return report


# --- Articles ----------------------------------------------------------------------------------


def post_target(file: Path) -> tuple[str, str] | None:
    """(collection, slug) of content/<collection>/<slug>.mdx, or None for anything else (pages, authors, other files)."""
    parts = file.parts
    if len(parts) >= 3 and parts[-3] == "content" and parts[-2] in COLLECTIONS and file.suffix == ".mdx":
        return parts[-2], file.stem
    return None


def push_posts(api: Api, files: list[Path], create_only: bool, dry_run: bool) -> dict:
    report = {"results": [], "failed": [], "not_articles": []}
    pending: list[tuple[Path, str, str]] = []
    for file in files:
        target = post_target(file)
        if target is None:
            report["not_articles"].append(str(file))
        elif not file.is_file():
            report["failed"].append((str(file), "the file does not exist"))
        else:
            pending.append((file, *target))
    if dry_run:
        report["results"] = [(f"/{collection}/{slug}", "would send", "") for _, collection, slug in pending]
        return report

    query = "?mode=create" if create_only else ""

    def send(collection: str, slug: str, body: bytes, mode: str) -> tuple[int, dict]:
        status, payload = api.call("PUT", f"/api/v1/posts/by-path/{collection}/{slug}.mdx{mode}", body, "text/markdown; charset=utf-8")
        if status == 404 and not payload:
            raise Stop(f"{api.site} has no /api/v1/posts/by-path: it runs a moks-cms release from before articles could be sent as files")
        return status, payload

    def answered(collection: str, slug: str, payload: dict, note: str = "") -> None:
        result = payload.get("data") or {}
        report["results"].append((result.get("url") or f"/{collection}/{slug}", result.get("action", "?"), note or result.get("reason") or result.get("admin") or ""))

    # Round after round while an article's related post is created later in the run.
    waiting: list[tuple[Path, str, str, int, dict]] = []
    while pending:
        progress = False
        waiting = []
        for file, collection, slug in pending:
            status, payload = send(collection, slug, file.read_bytes(), query)
            if status == 200:
                answered(collection, slug, payload)
                progress = True
            elif status == 400 and related_missing(payload):
                waiting.append((file, collection, slug, status, payload))
            else:
                report["failed"].append((str(file), reason_of(status, payload)))
        pending = [(file, collection, slug) for file, collection, slug, _, _ in waiting]
        if not progress:
            break

    # The rest name each other (A relates to B, B to A), so none can go first. Create each without the related posts
    # that are still waiting, then send the whole file again: the post is now a draft this run made, so it is updated.
    waiting_refs = {f"{collection}/{slug}" for _, collection, slug in pending}
    linked: list[tuple[Path, str, str]] = []
    for file, collection, slug, status, payload in waiting:
        text = file.read_text(encoding="utf-8")
        without = drop_related(text, waiting_refs - {f"{collection}/{slug}"})
        if without == text:
            report["failed"].append((str(file), reason_of(status, payload)))
            continue
        status, payload = send(collection, slug, without.encode("utf-8"), query)
        if status == 200 and (payload.get("data") or {}).get("action") == "created":
            linked.append((file, collection, slug))
        elif status == 200:
            answered(collection, slug, payload)
        else:
            report["failed"].append((str(file), reason_of(status, payload)))
    for file, collection, slug in linked:
        status, payload = send(collection, slug, file.read_bytes(), "")
        if status == 200:
            answered(collection, slug, {"data": {**(payload.get("data") or {}), "action": "created"}}, "created first without the related posts that name it back, then sent whole")
        else:
            report["failed"].append((str(file), "created as a draft without its related posts, then refused: " + reason_of(status, payload)))
    return report


def related_missing(payload: dict) -> bool:
    error = payload.get("error")
    issues = error.get("issues") or [] if isinstance(error, dict) else []
    return any(RELATED_MISSING.match(str(i)) for i in issues)


def drop_related(text: str, refs: set[str]) -> str:
    """The article with these refs taken out of `related:` in its front matter (a [a, b] list or one "- a" per line)."""
    match = re.match(r"---\r?\n(.*?\r?\n)---", text, re.S)
    if not match or not refs:
        return text
    lines = match[1].splitlines(keepends=True)
    out: list[str] = []
    i = 0
    while i < len(lines):
        head = re.match(r"related:[ \t]*(.*?)\s*$", lines[i])
        if not head:
            out.append(lines[i])
            i += 1
            continue
        i += 1
        flow = head[1].startswith("[")
        if flow:
            items = [s.strip().strip("'\"") for s in head[1].strip("[]").split(",") if s.strip()]
        else:
            items = []
            while i < len(lines) and re.match(r"\s+-\s", lines[i]):
                items.append(lines[i].split("-", 1)[1].strip().strip("'\""))
                i += 1
        kept = [item for item in items if item not in refs]
        if kept and flow:
            out.append(f"related: [{', '.join(kept)}]\n")
        elif kept:
            out.append("related:\n" + "".join(f"  - {item}\n" for item in kept))
    return text[: match.start(1)] + "".join(out) + text[match.end(1) :]


# --- Report ------------------------------------------------------------------------------------


def render(site: str, images: dict | None, posts: dict | None, dry_run: bool) -> tuple[str, bool]:
    lines = [f"### Content pushed to {site}" + (" (dry run: nothing was sent)" if dry_run else ""), ""]
    failed = False
    if images is not None:
        would = "would be " if dry_run else ""
        lines.append(f"**Images:** {len(images['created'])} {would}new, {len(images['replaced'])} {would}replaced, {images['unchanged']} unchanged, {len(images['failed'])} refused.")
        for label, key in (("New", "created"), ("Replaced", "replaced")):
            if images[key]:
                shown = images[key][:20]
                lines.append(f"- {label}: " + ", ".join(f"`{p}`" for p in shown) + (f" and {len(images[key]) - len(shown)} more" if len(images[key]) > len(shown) else ""))
        for path, why in images["failed"]:
            lines.append(f"- Refused `{path}`: {why}")
        if images["not_images"]:
            lines.append(f"- Not sent (not an image type): {', '.join(f'`{p}`' for p in images['not_images'][:10])}")
        if images["only_on_site"]:
            lines.append(f"- {len(images['only_on_site'])} image(s) are on the site but no longer in this repository; they are left there.")
        failed = failed or bool(images["failed"])
        lines.append("")
    if posts is not None:
        lines.append(f"**Articles:** {len(posts['results'])} answered, {len(posts['failed'])} refused.")
        if posts["results"]:
            lines += ["", "| Article | Result | Note |", "|---|---|---|"]
            lines += [f"| `{url}` | {action} | {note} |" for url, action, note in posts["results"]]
        for file, why in posts["failed"]:
            lines.append(f"- Refused `{file}`: {why}")
        if posts["not_articles"]:
            lines.append(f"- Not sent (only content/{{{','.join(COLLECTIONS)}}}/*.mdx are articles; pages and authors are edited in the admin): {', '.join(f'`{p}`' for p in posts['not_articles'])}")
        failed = failed or bool(posts["failed"])
        lines.append("")
    return "\n".join(lines), failed


def default_site() -> str:
    try:
        host = json.loads((ROOT / "site.json").read_text(encoding="utf-8"))["host"]
    except (OSError, ValueError, KeyError) as error:
        raise Stop(f"--site was not given and site.json has no host: {error}") from error
    return f"https://{host}"


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Push this site's images and articles to the CMS through its API.", epilog="See the top of this file for the rules.")
    parser.add_argument("--site")
    parser.add_argument("--images-dir", default=str(ROOT / "public" / "images"))
    parser.add_argument("--no-images", action="store_true")
    parser.add_argument("--all-posts", action="store_true")
    parser.add_argument("--create-only", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--summary", default=os.environ.get("GITHUB_STEP_SUMMARY"))
    parser.add_argument("posts", nargs="*", type=Path)
    args = parser.parse_args(argv)
    try:
        site = (args.site or default_site()).rstrip("/")
        url = urllib.parse.urlsplit(site)
        if url.scheme != "https" and not (url.scheme == "http" and url.hostname in ("127.0.0.1", "localhost")):
            raise Stop(f"{site}: the key is only ever sent over https")
        key = os.environ.get("JITHENDAR_API_KEY", "").strip()
        if not key:
            raise Stop("JITHENDAR_API_KEY is not set (Admin → API keys: scopes images:write and posts:draft)")
        api = Api(site, key)
        files = list(args.posts)
        if args.all_posts:
            files += [f for c in COLLECTIONS for f in sorted((ROOT / "content" / c).glob("*.mdx"))]
        images = None if args.no_images else push_images(api, Path(args.images_dir), args.dry_run)
        posts = push_posts(api, files, args.create_only, args.dry_run) if files else None
    except Stop as stop:
        print(f"push-content: {stop}", file=sys.stderr)
        return 2
    text, failed = render(site, images, posts, args.dry_run)
    print(text)
    if args.summary:
        with open(args.summary, "a", encoding="utf-8") as out:
            out.write(text + "\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
