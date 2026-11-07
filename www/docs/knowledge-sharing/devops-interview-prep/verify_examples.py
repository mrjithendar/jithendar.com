#!/usr/bin/env python3
"""Check the DevOps interview prep article's Python examples and run them.

Usage (from www/):
  python3 docs/knowledge-sharing/devops-interview-prep/verify_examples.py --python /path/to/venv/bin/python

The venv needs pytest and the MCP Python SDK 2.x (pip install pytest "mcp>=2,<3").
Examples are copied to a temp dir first, so nothing is written into the repo.
"""
import argparse
import json
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
WWW = HERE.parents[2]
ARTICLE = WWW / "content/blog/devops-interview-preparation-guide.mdx"
# Python code blocks in article order -> the example file each must equal.
BLOCK_SOURCES = ["log_summary.py", "retry.py", "test_retry.py", "health_check.py", "ops_mcp_server.py"]
SAMPLE_LOG = """\
10.0.0.1 - - [07/Nov/2026:10:00:01 +0000] "GET /api/cart?id=1 HTTP/1.1" 200 512 "-" "curl/8.0" 0.120
10.0.0.2 - - [07/Nov/2026:10:00:02 +0000] "POST /api/checkout HTTP/1.1" 502 0 "-" "Mozilla/5.0" 2.310
10.0.0.3 - - [07/Nov/2026:10:00:03 +0000] "POST /api/checkout HTTP/1.1" 200 88 "-" "Mozilla/5.0" 0.410
garbage line
10.0.0.4 - - [07/Nov/2026:10:00:04 +0000] "GET /healthz HTTP/1.1" 200 2 "-" "kube-probe/1.34" 0.002
"""
MCP_PROBE = """
import asyncio, json
from ops_mcp_server import mcp
async def main():
    tools = await mcp.list_tools()
    unknown = await mcp.call_tool("service_health", {"service": "db"})
    book = await mcp.read_resource("runbook://crashloop")
    prompt = await mcp.get_prompt("triage", {"alert_name": "KubePodCrashLooping", "namespace": "shop"})
    print(json.dumps({
        "tools": [t.name for t in tools],
        "read_only": tools[0].annotations.read_only_hint,
        "unknown": unknown.content[0].text,
        "runbook": book[0].content,
        "prompt": prompt.messages[0].content.text,
    }))
asyncio.run(main())
"""
failures: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"  ({detail})"))
    if not ok:
        failures.append(name)


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--python", default=sys.executable)
    py = parser.parse_args().python

    blocks = re.findall(r"^```python\n(.*?)^```", ARTICLE.read_text(), re.S | re.M)
    check("article has 5 python blocks", len(blocks) == len(BLOCK_SOURCES), str(len(blocks)))
    for block, src in zip(blocks, BLOCK_SOURCES):
        check(f"article block equals examples/{src}", block == (HERE / "examples" / src).read_text())

    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp) / "examples"
        shutil.copytree(HERE / "examples", work)
        run = lambda *args, **kw: subprocess.run([py, *args], cwd=work, capture_output=True, text=True, timeout=60, **kw)

        res = run("-m", "pytest", "-q", "-p", "no:cacheprovider", "test_retry.py")
        check("pytest test_retry.py passes", res.returncode == 0 and "3 passed" in res.stdout, res.stdout[-300:])

        (work / "access.log").write_text(SAMPLE_LOG)
        out = run("log_summary.py", "access.log").stdout
        check("log_summary counts statuses", "{'200': 3, '502': 1}" in out, out)
        check("log_summary groups query strings", "/api/cart?" not in out and "/api/cart" in out, out)
        check("log_summary top 5xx path", "[('/api/checkout', 1)]" in out, out)

        port = free_port()
        server = subprocess.Popen([py, "-m", "http.server", str(port), "--bind", "127.0.0.1"], cwd=work,
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            time.sleep(1.5)
            base = f"http://127.0.0.1:{port}"
            res = run("health_check.py", f"{base}/", f"{base}/missing", f"http://127.0.0.1:{free_port()}/")
            lines = res.stdout.splitlines()
            check("health_check exits 1 when any fail", res.returncode == 1, str(res.returncode))
            check("health_check reports 200", any(l.startswith("OK   200") for l in lines), res.stdout)
            check("health_check reports 404 as FAIL", any(l.startswith("FAIL 404") for l in lines), res.stdout)
            check("health_check reports refused connection", any(l.startswith("FAIL ---") for l in lines), res.stdout)
            res = run("health_check.py", f"{base}/")
            check("health_check exits 0 when all pass", res.returncode == 0, res.stdout)
        finally:
            server.terminate()

        res = run("-c", MCP_PROBE)
        try:
            probe = json.loads(res.stdout)
        except json.JSONDecodeError:
            probe = {}
        check("MCP server lists service_health", probe.get("tools") == ["service_health"], res.stderr[-500:])
        check("MCP tool is annotated read-only", probe.get("read_only") is True)
        check("MCP tool rejects unknown service", "unknown service" in probe.get("unknown", ""))
        check("MCP resource returns runbook", probe.get("runbook", "").startswith("# CrashLoopBackOff"))
        check("MCP prompt renders", "KubePodCrashLooping" in probe.get("prompt", ""))

        handshake = "\n".join([
            json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
                "protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "verify", "version": "0"}}}),
            json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}),
            json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list"}),
        ]) + "\n"
        proc = subprocess.Popen([py, "ops_mcp_server.py"], cwd=work, stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
        proc.stdin.write(handshake)
        proc.stdin.flush()
        replies = [proc.stdout.readline(), proc.stdout.readline()]
        proc.stdin.close()
        proc.wait(timeout=10)
        check("MCP server answers initialize over stdio", '"serverInfo"' in replies[0], replies[0][:200])
        check("MCP server lists tools over stdio", '"service_health"' in replies[1], replies[1][:200])

    print(f"\n{len(failures)} failure(s)" if failures else "\nall checks passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
