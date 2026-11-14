"""A small read-only MCP server for an internal ops tool (MCP Python SDK 2.x)."""
from pathlib import Path

from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations

from health_check import check

RUNBOOKS = Path(__file__).parent / "runbooks"
# The model never chooses a URL: it picks a service name from this allowlist.
SERVICES = {
    "web": "http://localhost:8080/healthz",
    "api": "http://localhost:8081/healthz",
}

mcp = MCPServer("ops-tools", instructions="Read-only health and runbook access.")


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=False))
def service_health(service: str) -> dict:
    """Return the HTTP status and latency of one known service."""
    if service not in SERVICES:
        return {"error": f"unknown service; choose one of {sorted(SERVICES)}"}
    _, status, detail = check(SERVICES[service], timeout=2.0)
    return {"service": service, "status": status, "detail": detail}


@mcp.resource("runbook://{name}", mime_type="text/markdown")
def runbook(name: str) -> str:
    """A runbook by name, e.g. runbook://crashloop."""
    path = (RUNBOOKS / f"{name}.md").resolve()
    if path.parent != RUNBOOKS.resolve() or not path.is_file():
        raise ValueError(f"no runbook named {name!r}")
    return path.read_text(encoding="utf-8")


@mcp.prompt()
def triage(alert_name: str, namespace: str) -> str:
    """Start an alert triage conversation."""
    return (
        f"Alert {alert_name} fired in namespace {namespace}. "
        "Check service_health first, read the matching runbook, and propose "
        "next steps. Do not suggest commands that change the cluster."
    )


if __name__ == "__main__":
    mcp.run()  # stdio by default; mcp.run(transport="streamable-http") for remote
