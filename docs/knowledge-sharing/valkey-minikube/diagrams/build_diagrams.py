#!/usr/bin/env python3
"""Figures for "One Redis for Every App: A Highly Available Valkey Cluster on Minikube with Terraform".

    python3 sites/jithendar.com/docs/knowledge-sharing/valkey-minikube/diagrams/build_diagrams.py   (from www/)
    bash sites/jithendar.com/docs/knowledge-sharing/valkey-minikube/diagrams/export.sh

The first command writes one editable .drawio file per figure beside this script; the second has the draw.io desktop
CLI export each to public/images/valkey-minikube/<name>.svg and .png. After editing a .drawio file by hand, run only
export.sh, or this script overwrites the edits.

Checked against the miniKube repository (minikube-infrastructure/redis.tf, deploy/minikube/redis) and the live mk4
cluster on 9 November 2026 (primary valkey-1 on mk4-m03, replicas valkey-0 on mk4-m06 and valkey-2 on mk4-m07).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from drawio_model import Diagram  # noqa: E402

HERE = Path(__file__).resolve().parent


def architecture():
    d = Diagram("valkey-architecture", 960, 640, "mk4: one shared Valkey for every application (9 November 2026)")

    # Applications
    d.zone("z-apps", "Application namespaces (meshed)", 20, 48, 300, 282)
    d.node("practice", "service", 35, 78, 270, 60, "practice executor", "ns jithendar · database 1")
    d.node("harbor", "service", 35, 152, 270, 60, "Harbor", "ns harbor · databases 2-5")
    d.node("roboshop", "service", 35, 226, 270, 60, "RoboShop cart + shipping", "ns roboshop-ai · database 6")
    d.text("apps-note", 35, 292, 270, 32, "Each reads redis-&lt;name&gt;-credentials (uri) in its own namespace.", size=11)

    # Owner access
    d.node("laptop", "client", 35, 345, 270, 56, "Owner's laptop", "browser, redis-cli")
    d.node("gw", "network", 35, 420, 270, 92, "Istio ingress gateway", "IP allowlist: DENY everyone else",
           "/redis: login, then RedisInsight", "redis.jithendar.com: TLS, then TCP")

    # Namespace redis
    d.zone("z-redis", "namespace redis · STRICT mTLS · enforced ALLOW policy", 360, 48, 580, 400, "cluster")
    d.node("master", "network", 380, 78, 540, 60, "Service valkey-master:6379",
           "selects all 3 pods; each HAProxy forwards to the current primary")
    pods = [("p0", 380, "valkey-0 · mk4-m06", "replica"), ("p1", 565, "valkey-1 · mk4-m03", "PRIMARY (now)"),
            ("p2", 750, "valkey-2 · mk4-m07", "replica")]
    for key, x, title, role in pods:
        d.node(key, "data", x, 164, 170, 150, title, role, "HAProxy → primary", "Sentinel (quorum 2)",
               "exporter :9121", "2Gi local-path")
    d.node("ui", "ops", 380, 370, 250, 56, "RedisInsight (redis-ui)", "user console, no admin commands")
    d.node("prom", "ops", 660, 370, 260, 56, "Prometheus (monitoring)", "4 alerts, Grafana dashboard")

    # Edges
    d.edge("practice", "master", exit=(1, 0.5), entry=(0, 0.5))
    d.edge("harbor", "master", exit=(1, 0.5), entry=(0, 0.5), via=[(340, 182), (340, 108)])
    d.edge("roboshop", "master", exit=(1, 0.5), entry=(0, 0.5), via=[(340, 256), (340, 108)])
    for key, fx in (("p0", 85 / 540), ("p1", 270 / 540), ("p2", 455 / 540)):
        d.edge("master", key, exit=(fx, 1), entry=(0.5, 0))
    d.edge("p1", "p0", kind="replicate", exit=(0.3, 1), entry=(0.5, 1), via=[(616, 340), (465, 340)])
    d.edge("p1", "p2", kind="replicate", exit=(0.7, 1), entry=(0.5, 1), via=[(684, 340), (835, 340)])
    d.edge("prom", "p2", kind="control", exit=((894.5 - 660) / 260, 0), entry=(0.85, 1))
    d.edge("laptop", "gw", exit=(0.5, 1), entry=(0.5, 0))
    d.edge("gw", "ui", exit=(1, 0.3), entry=(0, 0.5), via=[(340, 447.6), (340, 398)])
    d.edge("gw", "master", exit=(1, 0.75), entry=(1, 0.5), via=[(945, 489), (945, 108)],
           label="redis.jithendar.com:443", t=-0.15)

    d.text("facts", 20, 528, 920, 48, "Every pod runs Valkey 9.1, Sentinel, an HAProxy master proxy, the exporter and an Istio "
           "sidecar. Sentinel promotes a replica after 5 s without an answer from the primary; HAProxy in every pod follows "
           "the new primary, so applications keep one address and need no Sentinel support. Required anti-affinity puts the "
           "three pods on three nodes; Argo CD keeps its own Redis.", size=11)
    d.legend(590, labels={"data": "Valkey pods", "ops": "Tools and monitoring"})
    return d


def failover():
    d = Diagram("valkey-failover", 960, 600, "How the primary moves, and what keeps writes flowing")

    d.zone("z-planned", "Planned: rolling update, pod delete, node drain", 20, 48, 440, 102)
    d.node("a1", "compute", 35, 78, 200, 60, "Primary told to stop", "SIGTERM, then preStop hook")
    d.node("a2", "ops", 250, 78, 200, 60, "Hand over first", "SENTINEL FAILOVER mk4", "waits for a new primary")
    d.zone("z-unplanned", "Unplanned: pod crash, node lost", 20, 168, 440, 102, "risk")
    d.node("b1", "compute", 35, 198, 200, 60, "Primary goes silent", "crash, OOM, node lost")
    d.node("b2", "ops", 250, 198, 200, 60, "Sentinels agree", "no answer for 5 s", "2 of 3 mark it down")

    d.node("c3", "data", 490, 138, 200, 80, "Replica promoted", "leader Sentinel picks one", "REPLICAOF NO ONE")
    d.node("c4", "network", 730, 138, 210, 80, "HAProxy follows", "health check role:master", "valkey-master: same address")
    d.node("client", "client", 490, 250, 200, 80, "What clients see", "a few failed writes", "2 in about 4 s (9 Nov test)")
    d.node("c5", "data", 730, 250, 210, 80, "Old pod back as replica", "same node, same volume", "resyncs from new primary")

    d.edge("a1", "a2", exit=(1, 0.5), entry=(0, 0.5))
    d.edge("b1", "b2", exit=(1, 0.5), entry=(0, 0.5))
    d.edge("a2", "c3", exit=(1, 0.5), entry=(0, 0.3), via=[(470, 108), (470, 162)])
    d.edge("b2", "c3", exit=(1, 0.5), entry=(0, 0.7), via=[(470, 228), (470, 194)])
    d.edge("c3", "c4", exit=(1, 0.5), entry=(0, 0.5))
    d.edge("c4", "c5", exit=(0.5, 1), entry=(0.5, 0))
    d.edge("c3", "client", exit=(0.5, 1), entry=(0.5, 0))

    d.zone("z-guards", "What makes the hand-over safe (deploy/minikube/redis/values.yaml)", 20, 360, 920, 106, "cluster")
    guards = [("g1", "PDB minAvailable 2", "a drain never breaks quorum"),
              ("g2", "Grace period 60 s", "room for preStop failover"),
              ("g3", "Envoy outlives Valkey", "starts first, drains 45 s"),
              ("g4", "down-after 5000 ms", "no failover on a blip")]
    for i, (key, title, sub) in enumerate(guards):
        d.node(key, "security", 35 + i * 228, 390, 215, 60, title, sub)

    d.text("note", 20, 482, 920, 48, "A planned stop hands the primary over before Valkey exits, so writes pause for about a "
           "second. An unplanned loss waits 5 s for Sentinel to be sure, then elects. Either way the pod comes back on its "
           "own node (local-path volumes are pinned) and rejoins as a replica; a node gone for good needs its PVC deleted.",
           size=11)
    d.legend(546, labels={"compute": "Event", "ops": "Sentinel", "data": "Valkey", "security": "Safeguard"})
    return d


def tenancy():
    d = Diagram("valkey-tenancy-security", 960, 760, "One tenant end to end: what Terraform creates, what a connection passes")

    d.zone("z-tf", "Terraform: miniKube redis.tf", 20, 48, 400, 610)
    d.node("tfvars", "ops", 35, 78, 360, 92, "vars/mk4.tfvars: redis_tenants", "practice → ns jithendar, db 1",
           "harbor → ns harbor, db 2-5", "roboshop → ns roboshop-ai, db 6")
    d.node("tf", "ops", 35, 200, 360, 76, "redis.tf, per tenant", "random_password (encrypted state)",
           "validations: names, 0-31, no shared db")
    d.node("o1", "security", 35, 306, 360, 60, "ACL user line in valkey.conf", "user practice on #<sha256> ... db=1")
    d.node("o2", "security", 35, 380, 360, 60, "Secret jithendar/redis-practice-credentials",
           "host, port, username, password, db, uri")
    d.node("o3", "security", 35, 454, 360, 60, "Namespace added to the policies", "AuthorizationPolicy + NetworkPolicy")
    d.node("o4", "ops", 35, 528, 360, 60, "checksum/acl pod annotation", "rolls the StatefulSet, primary hands over")
    d.text("tf-note", 35, 600, 370, 50, "The server stores only SHA-256 hashes. Removing a tenant deletes its user and Secret; "
           "its keys stay until flushed by hand.", size=11)

    d.edge("tfvars", "tf", exit=(0.5, 1), entry=(0.5, 0))
    for key, y in (("o1", 336), ("o2", 410), ("o3", 484), ("o4", 558)):
        d.edge("tf", key, kind="control", exit=(0, 0.5), entry=(0, 0.5), via=[(28, 238), (28, y)])

    d.zone("z-path", "One connection: practice dispatcher → Valkey", 480, 48, 460, 610, "cluster")
    layers = [("l1", "service", "practice dispatcher (ns jithendar)", "EXECUTOR_REDIS_URL = uri"),
              ("l2", "network", "1. Egress NetworkPolicy", "to the Valkey pods on 6379 and 6380"),
              ("l3", "security", "2. Istio mTLS (STRICT)", "sidecar identity: namespace jithendar"),
              ("l4", "security", "3. AuthorizationPolicy valkey (ALLOW)", "namespace listed? else the sidecar resets"),
              ("l5", "network", "4. Ingress NetworkPolicy", "same namespaces, same ports"),
              ("l6", "network", "5. HAProxy behind valkey-master", "forwards to the current primary"),
              ("l7", "security", "6. Valkey ACL: user practice", "db=1 · -@admin -flushall -swapdb")]
    for i, (key, kind, title, sub) in enumerate(layers):
        d.node(key, kind, 495, 78 + i * 72, 430, 56, title, sub)
    d.node("l8", "data", 495, 582, 430, 60, "database 1", "the practice queue (no TTL, never evicted)", shape="db")
    keys = [k for k, *_ in layers] + ["l8"]
    for a, b in zip(keys, keys[1:]):
        d.edge(a, b, exit=(0.5, 1), entry=(0.5, 0))

    d.edge("o2", "l1", kind="control", exit=(1, 0.5), entry=(0, 0.5), via=[(448, 410), (448, 106)])
    d.edge("o1", "l7", kind="control", exit=(1, 0.5), entry=(0, 0.5), via=[(432, 336), (432, 538)])
    d.edge("o3", "l4", kind="control", exit=(1, 0.5), entry=(0, 0.5), via=[(464, 484), (464, 322)])

    d.text("note", 20, 670, 920, 32, "Layers 2-4 refuse a connection before a single Redis byte reaches Valkey. Pub/Sub "
           "channels are not isolated by database: every user shares one channel namespace.", size=11)
    d.legend(712, labels={"security": "Identity and policy", "ops": "Terraform", "data": "Tenant data"})
    return d


FIGURES = [architecture, failover, tenancy]


def main():
    names = []
    for make in FIGURES:
        d = make()
        (HERE / f"{d.name}.drawio").write_text(d.xml(), encoding="utf-8")
        names.append(d.name)
    (HERE / "figures.txt").write_text("\n".join(names) + "\n", encoding="utf-8")
    print(f"{len(names)} .drawio files: {', '.join(names)}")


if __name__ == "__main__":
    main()
