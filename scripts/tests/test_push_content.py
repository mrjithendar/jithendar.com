"""Tests for scripts/push-content.py against a stand-in for the CMS API on 127.0.0.1. No network, no cluster.

  python3 -m unittest discover -s scripts/tests -p 'test_*.py'

The stand-in follows the rules of moks-cms (docs/SITE_IMAGES.md, docs/EDITOR.md): the image list with the SHA-256 of
each pushed file, PUT /api/v1/images/<path>, and PUT /api/v1/posts/by-path/<collection>/<slug>.mdx with its actions.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

SCRIPT = Path(__file__).resolve().parents[1] / "push-content.py"
KEY = "jk_test-key-for-the-stand-in-only"


class Site:
    """What the stand-in holds, and what it was asked."""

    def __init__(self) -> None:
        self.images: dict[str, str] = {}
        self.posts: dict[str, dict] = {}
        self.requests: list[tuple[str, str]] = []
        self.throttle = 0  # answer this many requests with 429 first
        self.has_api = True

    def count(self, method: str, prefix: str) -> int:
        return sum(1 for m, p in self.requests if m == method and p.startswith(prefix))


def handler_for(site: Site):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args) -> None:  # keep the test output quiet
            pass

        def answer(self, status: int, payload: dict | None = None, headers: dict | None = None) -> None:
            body = json.dumps(payload).encode() if payload is not None else b"<html>Not found</html>"
            self.send_response(status)
            self.send_header("Content-Type", "application/json" if payload is not None else "text/html")
            self.send_header("Content-Length", str(len(body)))
            for name, value in (headers or {}).items():
                self.send_header(name, value)
            self.end_headers()
            self.wfile.write(body)

        def handle_any(self) -> None:
            url = urlsplit(self.path)
            query = parse_qs(url.query)
            body = self.rfile.read(int(self.headers.get("Content-Length") or 0))
            site.requests.append((self.command, url.path))
            if not site.has_api:
                return self.answer(404)
            if self.headers.get("Authorization") != f"Bearer {KEY}":
                return self.answer(401, {"error": {"message": "Invalid, expired or revoked API key."}})
            if site.throttle > 0:
                site.throttle -= 1
                return self.answer(429, {"error": {"message": "Rate limit exceeded (120 requests per minute per key)."}}, {"Retry-After": "0"})

            if self.command == "GET" and url.path == "/api/v1/images":
                rows = [{"path": p, "sha256": s} for p, s in sorted(site.images.items())]
                offset = int(query.get("offset", ["0"])[0])
                return self.answer(200, {"data": rows[offset : offset + int(query.get("limit", ["1000"])[0])]})

            if self.command == "PUT" and url.path.startswith("/api/v1/images/"):
                path = url.path[len("/api/v1") :]
                if b"<script" in body:
                    return self.answer(400, {"error": {"message": f"{path}: SVG files with a <script> element are not accepted.", "issues": []}})
                sha = hashlib.sha256(body).hexdigest()
                created, unchanged = path not in site.images, site.images.get(path) == sha
                site.images[path] = sha
                return self.answer(200, {"data": {"path": path, "created": created, "unchanged": unchanged}})

            match = re.fullmatch(r"/api/v1/posts/by-path/(blog|news|projects)/([a-z0-9-]+)\.mdx", url.path)
            if self.command == "PUT" and match:
                ref = f"{match[1]}/{match[2]}"
                text = body.decode()
                missing = [r for r in re.findall(r"^related: \[(.*?)\]", text, re.M) for r in r.split(", ") if r and r not in site.posts]
                if missing:
                    return self.answer(400, {"error": {"message": "The post is not valid.", "issues": [f'related: "{missing[0]}" does not exist (check the spelling, or remove it under Related posts)']}})
                current = site.posts.get(ref)
                result = {"url": f"/{ref}", "admin": f"/admin/posts/{ref}"}
                if current is None:
                    site.posts[ref] = {"status": "draft", "body": text}
                    return self.answer(200, {"data": {**result, "action": "created", "status": "draft"}})
                if query.get("mode") == ["create"]:
                    return self.answer(200, {"data": {**result, "action": "exists", "status": current["status"], "reason": f"/{ref} is already a post ({current['status']}); not changed"}})
                if current["status"] != "draft":
                    return self.answer(200, {"data": {**result, "action": "skipped", "status": current["status"], "reason": f"/{ref} is {current['status']}; edit it in Admin → Posts"}})
                if current["body"] == text:
                    return self.answer(200, {"data": {**result, "action": "unchanged", "status": "draft"}})
                current["body"] = text
                return self.answer(200, {"data": {**result, "action": "updated", "status": "draft"}})

            return self.answer(404)

        do_GET = do_PUT = handle_any

    return Handler


class PushContent(unittest.TestCase):
    def setUp(self) -> None:
        self.site = Site()
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), handler_for(self.site))
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}"
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.images = self.root / "public" / "images"
        self.write_image("aws-vpc/01-what-is-a-vpc.png", b"\x89PNG one")
        self.write_image("aws-vpc/01-what-is-a-vpc.svg", b"<svg>one</svg>")
        self.write_image("cover.jpg", b"\xff\xd8\xff cover")
        self.write_image(".gitkeep", b"")
        self.write_image("aws-vpc/notes.txt", b"not an image")

    def write_image(self, name: str, data: bytes) -> None:
        file = self.images / name
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_bytes(data)

    def write_post(self, collection: str, slug: str, body: str = "Body.", related: str = "") -> str:
        file = self.root / "content" / collection / f"{slug}.mdx"
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(f"---\ntitle: A post\nslug: {slug}\n{f'related: [{related}]' + chr(10) if related else ''}---\n{body}\n", encoding="utf-8")
        return str(file)

    def run_script(self, *args: str, key: str | None = KEY, site: str | None = None) -> subprocess.CompletedProcess:
        env = {k: v for k, v in os.environ.items() if k not in ("JITHENDAR_API_KEY", "GITHUB_STEP_SUMMARY") and not k.lower().endswith("_proxy")}
        if key is not None:
            env["JITHENDAR_API_KEY"] = key
        return subprocess.run([sys.executable, str(SCRIPT), "--site", site or self.url, "--images-dir", str(self.images), *args], capture_output=True, text=True, env=env, timeout=120)

    # --- images ---

    def test_sends_every_image_once_and_only_changed_ones_afterwards(self) -> None:
        first = self.run_script()
        self.assertEqual(first.returncode, 0, first.stderr + first.stdout)
        self.assertIn("**Images:** 3 new, 0 replaced, 0 unchanged, 0 refused.", first.stdout)
        self.assertIn("Not sent (not an image type): `aws-vpc/notes.txt`", first.stdout)
        self.assertEqual(sorted(self.site.images), ["/images/aws-vpc/01-what-is-a-vpc.png", "/images/aws-vpc/01-what-is-a-vpc.svg", "/images/cover.jpg"])
        self.assertEqual(self.site.images["/images/cover.jpg"], hashlib.sha256(b"\xff\xd8\xff cover").hexdigest())

        sent = self.site.count("PUT", "/api/v1/images/")
        second = self.run_script()
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertIn("**Images:** 0 new, 0 replaced, 3 unchanged, 0 refused.", second.stdout)
        self.assertEqual(self.site.count("PUT", "/api/v1/images/"), sent, "unchanged files are not sent again")

        self.write_image("cover.jpg", b"\xff\xd8\xff another cover")
        self.write_image("new/diagram.svg", b"<svg>two</svg>")
        third = self.run_script()
        self.assertIn("**Images:** 1 new, 1 replaced, 2 unchanged, 0 refused.", third.stdout)
        self.assertIn("- New: `/images/new/diagram.svg`", third.stdout)
        self.assertIn("- Replaced: `/images/cover.jpg`", third.stdout)
        self.assertEqual(self.site.count("PUT", "/api/v1/images/"), sent + 2)

    def test_reports_a_refused_image_and_still_sends_the_others(self) -> None:
        self.write_image("bad.svg", b"<svg><script>alert(1)</script></svg>")
        result = self.run_script()
        self.assertEqual(result.returncode, 1)
        self.assertIn("**Images:** 3 new, 0 replaced, 0 unchanged, 1 refused.", result.stdout)
        self.assertIn("Refused `/images/bad.svg`: /images/bad.svg: SVG files with a <script> element are not accepted.", result.stdout)
        self.assertEqual(len(self.site.images), 3)

    def test_waits_and_carries_on_when_the_site_says_slow_down(self) -> None:
        self.site.throttle = 2
        result = self.run_script()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(self.site.images), 3)

    def test_says_which_images_are_no_longer_in_the_repository(self) -> None:
        self.site.images["/images/old/removed.png"] = "0" * 64
        result = self.run_script()
        self.assertEqual(result.returncode, 0)
        self.assertIn("1 image(s) are on the site but no longer in this repository; they are left there.", result.stdout)
        self.assertIn("/images/old/removed.png", self.site.images)

    def test_dry_run_sends_nothing(self) -> None:
        post = self.write_post("blog", "first-post")
        result = self.run_script("--dry-run", post)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("(dry run: nothing was sent)", result.stdout)
        self.assertIn("**Images:** 3 would be new, 0 would be replaced, 0 unchanged, 0 refused.", result.stdout)
        self.assertIn("| `/blog/first-post` | would send |", result.stdout)
        self.assertEqual(self.site.count("PUT", "/"), 0)

    # --- articles ---

    def test_creates_a_draft_then_updates_it_and_leaves_a_published_post_alone(self) -> None:
        post = self.write_post("blog", "first-post")
        first = self.run_script("--no-images", post)
        self.assertEqual(first.returncode, 0, first.stderr + first.stdout)
        self.assertIn("| `/blog/first-post` | created | /admin/posts/blog/first-post |", first.stdout)
        self.assertEqual(self.site.count("GET", "/api/v1/images"), 0, "--no-images does not ask for the image list")
        self.assertIn("| `/blog/first-post` | unchanged |", self.run_script("--no-images", post).stdout)

        self.write_post("blog", "first-post", "Second version.")
        self.assertIn("| `/blog/first-post` | updated |", self.run_script("--no-images", post).stdout)
        self.assertIn("Second version.", self.site.posts["blog/first-post"]["body"])

        self.site.posts["blog/first-post"]["status"] = "published"
        self.write_post("blog", "first-post", "Edited after publishing.")
        skipped = self.run_script("--no-images", post)
        self.assertEqual(skipped.returncode, 0, "a published post that is left alone is not a failure")
        self.assertIn("| `/blog/first-post` | skipped | /blog/first-post is published; edit it in Admin → Posts |", skipped.stdout)
        self.assertNotIn("Edited after publishing.", self.site.posts["blog/first-post"]["body"])

    def test_create_only_never_changes_an_existing_post(self) -> None:
        post = self.write_post("blog", "first-post")
        self.run_script("--no-images", post)
        self.write_post("blog", "first-post", "Edited.")
        again = self.run_script("--no-images", "--create-only", post)
        self.assertIn("| `/blog/first-post` | exists |", again.stdout)
        self.assertNotIn("Edited.", self.site.posts["blog/first-post"]["body"])

    def test_sends_an_article_again_when_its_related_post_arrives_later_in_the_run(self) -> None:
        first = self.write_post("blog", "a-first", related="blog/b-second")
        second = self.write_post("blog", "b-second")
        result = self.run_script("--no-images", first, second)
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertEqual(sorted(self.site.posts), ["blog/a-first", "blog/b-second"])
        self.assertIn("**Articles:** 2 answered, 0 refused.", result.stdout)

        lonely = self.write_post("blog", "c-third", related="blog/never-written")
        refused = self.run_script("--no-images", lonely)
        self.assertEqual(refused.returncode, 1)
        self.assertIn('related: "blog/never-written" does not exist', refused.stdout)
        self.assertNotIn("blog/c-third", self.site.posts)

    def test_creates_articles_that_name_each_other_and_links_them_both_ways(self) -> None:
        for mode in ((), ("--create-only",)):
            with self.subTest(mode=mode):
                self.site.posts.clear()
                a = self.write_post("blog", "crew-a", related="blog/crew-b, blog/kept")
                b = self.write_post("blog", "crew-b", related="blog/crew-a")
                kept = self.write_post("blog", "kept")
                result = self.run_script("--no-images", *mode, a, b, kept)
                self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
                self.assertIn("**Articles:** 3 answered, 0 refused.", result.stdout)
                self.assertIn("related: [blog/crew-b, blog/kept]", self.site.posts["blog/crew-a"]["body"])
                self.assertIn("related: [blog/crew-a]", self.site.posts["blog/crew-b"]["body"])
                self.assertIn("created first without the related posts", result.stdout)

    def test_a_cycle_with_a_post_that_is_not_in_the_run_is_still_refused(self) -> None:
        a = self.write_post("blog", "loop-a", related="blog/loop-b, blog/never-written")
        b = self.write_post("blog", "loop-b", related="blog/loop-a")
        result = self.run_script("--no-images", a, b)
        self.assertEqual(result.returncode, 1)
        self.assertIn('related: "blog/never-written" does not exist', result.stdout)
        self.assertNotIn("blog/loop-a", self.site.posts)

    def test_sends_images_before_articles_and_only_article_files(self) -> None:
        post = self.write_post("news", "a-story")
        page = self.root / "content" / "pages" / "about.mdx"
        page.parent.mkdir(parents=True)
        page.write_text("---\ntitle: About\n---\n", encoding="utf-8")
        result = self.run_script(post, str(page))
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertIn("Not sent (only content/{blog,news,projects}/*.mdx are articles", result.stdout)
        puts = [p for m, p in self.site.requests if m == "PUT"]
        self.assertEqual(puts[-1], "/api/v1/posts/by-path/news/a-story.mdx")
        self.assertTrue(all(p.startswith("/api/v1/images/") for p in puts[:-1]) and len(puts) == 4)

    def test_writes_the_report_for_the_workflow_summary(self) -> None:
        summary = self.root / "summary.md"
        self.run_script("--summary", str(summary))
        self.assertIn(f"### Content pushed to {self.url}", summary.read_text(encoding="utf-8"))

    # --- it cannot start ---

    def test_stops_without_a_key_a_safe_address_or_the_api(self) -> None:
        no_key = self.run_script(key=None)
        self.assertEqual(no_key.returncode, 2)
        self.assertIn("JITHENDAR_API_KEY is not set", no_key.stderr)

        plain = self.run_script(site="http://example.com")
        self.assertEqual(plain.returncode, 2)
        self.assertIn("the key is only ever sent over https", plain.stderr)

        wrong = self.run_script(key="jk_wrong")
        self.assertEqual(wrong.returncode, 2)
        self.assertIn("refused to list its images: Invalid, expired or revoked API key.", wrong.stderr)

        self.site.has_api = False
        old = self.run_script()
        self.assertEqual(old.returncode, 2)
        self.assertIn("has no /api/v1/images", old.stderr)
        self.assertEqual(self.site.count("PUT", "/"), 0)
        post = self.write_post("blog", "first-post")
        old_posts = self.run_script("--no-images", post)
        self.assertEqual(old_posts.returncode, 2)
        self.assertIn("has no /api/v1/posts/by-path", old_posts.stderr)


if __name__ == "__main__":
    unittest.main()
