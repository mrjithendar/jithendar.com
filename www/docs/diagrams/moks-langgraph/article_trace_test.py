"""Article evidence: real API/graph/executor/detectors/skills/validation, fixture cluster, scripted model."""
import json, os, uuid, yaml
from pathlib import Path
import pytest
from sqlalchemy import select
from moks.db import session_scope
from moks.llm import budget
from moks.llm.providers import LLMError, LLMResponse
from moks.models import Evidence, Investigation, InvestigationEvent, LLMConfig
from moks.orchestrator import engine, graph
from moks.orchestrator.engine import Investigator
from moks.evals.fixture import FixtureKubernetes
from tests.conftest import login, make_env, make_user

OUT = Path(os.environ["TRACE_OUT"])
DATA = yaml.safe_load((Path(engine.__file__).parents[1] / "evals/datasets/lab.yaml").read_text())
CASE = next(c for c in DATA["cases"] if c["id"] == "crashloop-invalid-config")
Q = "Why is the payments deployment repeatedly restarting?"

class P:
    name = "scripted"
    cfg = None

@pytest.fixture
def nodes(monkeypatch):
    seen = []
    real = graph._traced
    def traced(name, fn):
        async def wrapped(state):
            seen.append(name)
            return await fn(state)
        return real(name, wrapped)
    monkeypatch.setattr(graph, "_traced", traced)
    return seen

@pytest.fixture
async def scripted(monkeypatch):
    st = {"replies": [], "prompts": []}
    async def complete(provider, system, messages, **kw):
        st["prompts"].append({"system_chars": len(system), "user": messages[-1]["content"], "turns": len(messages), "kw": {k: str(v) for k, v in kw.items()}})
        r = st["replies"].pop(0) if st["replies"] else '{"tool_calls": [], "done": true}'
        if isinstance(r, Exception):
            raise r
        return LLMResponse(r, 10, 5, "scripted", "m")
    monkeypatch.setattr(budget, "complete", complete)
    monkeypatch.setattr(engine, "provider_for", lambda cfg: P())
    return st

async def llm_on(on):
    async with session_scope() as db:
        for c in (await db.execute(select(LLMConfig).where(LLMConfig.purpose == "chat"))).scalars():
            c.is_active = False
        await db.flush()
        if on:
            db.add(LLMConfig(name=f"t-{uuid.uuid4().hex[:6]}", purpose="chat", provider="openai", model="m", is_active=True))

async def go(client, use_llm):
    name = f"tr-{uuid.uuid4().hex[:6]}"
    await make_env(name)
    await make_user(f"{name}@example.com", [f"investigator:{name}:*"])
    h = await login(client, f"{name}@example.com")
    r = await client.post("/moks/api/investigations", json={"question": Q, "environment": name, "namespace": "moks-lab"}, headers=h)
    assert r.status_code == 201, r.text
    iid = uuid.UUID(r.json()["id"])
    w = Investigator(iid, "t", connectors_override={"kubernetes": (None, FixtureKubernetes(CASE))}, use_llm=use_llm)
    await w.run()
    async with session_scope() as db:
        inv = await db.get(Investigation, iid)
        ev = (await db.execute(select(InvestigationEvent).where(InvestigationEvent.investigation_id == iid).order_by(InvestigationEvent.seq))).scalars().all()
        evd = (await db.execute(select(Evidence).where(Evidence.investigation_id == iid))).scalars().all()
    return {"status": inv.status, "mode": inv.mode, "error": inv.error, "tool_calls": inv.tool_calls, "report": inv.report,
            "events": [{"seq": e.seq, "type": e.type, "p": e.payload} for e in ev],
            "evidence": sorted([{"ref": e.ref, "tool": e.tool, "args": e.args, "ok": e.ok, "summary": e.summary, "error": e.error, "data": e.data} for e in evd], key=lambda e: int(e["ref"][1:])),
            "rejected": w.rejected, "notes": w.notes}

def plan(*calls, done=False):
    return json.dumps({"tool_calls": [{"tool": t, "args": a, "purpose": p} for t, a, p in calls], "done": done})

# Run from backend/ with TRACE_OUT=<dir> and MOKS_TEST_DATABASE_URL set. Copy into backend/tests first.
async def test_rules(client, nodes):
    await llm_on(False)
    r = await go(client, True)
    r["nodes"] = list(nodes)
    (OUT / "rules.json").write_text(json.dumps(r, indent=1, default=str))

async def test_llm(client, nodes, scripted):
    await llm_on(True)
    scripted["replies"] = [
        plan(("k8s_events", {"namespace": "moks-lab"}, "events around the restarts"),
             ("k8s_pod_logs", {"namespace": "moks-lab", "pod": "payments-5c4-z9", "previous": True, "tail_lines": 150}, "repeat of an existing call"),
             ("restart_deployment", {"name": "payments"}, "not a planner tool"),
             ("k8s_events", {"namespace": "kube-system"}, "outside nothing here")),
        plan(("k8s_events", {"namespace": "moks-lab"}, "duplicate")),
        json.dumps({"summary": "payments exits at start-up. The root cause is confirmed as an invalid PAYMENT_MODE.",
                    "observed_facts": [{"statement": "A cited fact", "evidence": ["E3"]}, {"statement": "An uncited claim", "evidence": []}, {"statement": "A fake citation", "evidence": ["E99"]}],
                    "suspected_causes": [{"cause": "Invalid PAYMENT_MODE", "confidence": "high", "evidence": ["E3"], "reasoning": "log line"}, {"cause": "Node pressure", "confidence": "high", "evidence": ["E99"], "reasoning": "guess"}],
                    "missing_evidence": ["no Prometheus connector"], "next_steps": ["check the ConfigMap"],
                    "proposed_remediation": [{"action": "fix PAYMENT_MODE in Git", "target": "ConfigMap/payments-config", "requires_approval": False, "executable": True}]}),
    ]
    r = await go(client, True)
    r["nodes"] = list(nodes)
    r["prompts"] = scripted["prompts"]
    (OUT / "llm.json").write_text(json.dumps(r, indent=1, default=str))

async def test_self_arg(client, nodes, scripted):
    await llm_on(True)
    scripted["replies"] = [plan(("k8s_events", {"namespace": "moks-lab", "self": "x"}, "odd arg"))]
    r = await go(client, True)
    r["nodes"] = list(nodes)
    (OUT / "self.json").write_text(json.dumps(r, indent=1, default=str))

async def test_failure(client, nodes, scripted):
    await llm_on(True)
    scripted["replies"] = [LLMError("unavailable", "provider down"), LLMError("unavailable", "provider down")]
    r = await go(client, True)
    r["nodes"] = list(nodes)
    (OUT / "fail.json").write_text(json.dumps(r, indent=1, default=str))

async def test_rounds(client, nodes, scripted):
    await llm_on(True)
    scripted["replies"] = [plan(("k8s_events", {"namespace": "moks-lab", "limit": i + 1}, "r")) for i in range(30)]
    r = await go(client, True)
    r["nodes"] = list(nodes)
    r["llm_calls"] = len(scripted["prompts"])
    (OUT / "rounds.json").write_text(json.dumps(r, indent=1, default=str))
