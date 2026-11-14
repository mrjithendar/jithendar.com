#!/usr/bin/env python3
"""Figures for the three "Deploy Moks CMS" guides (Linux server, Kubernetes, Amazon EKS): editable .drawio files
and matching SVGs.

Reuses the layout, palette and draw.io writer of the RoboShop AI series. Run from www/. The SVGs are rendered here,
not exported by draw.io: if a .drawio file is edited by hand, re-export it from draw.io over the SVG.
"""
import importlib.util
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parents[3] / "public" / "images" / "deploy-moks-cms"
spec = importlib.util.spec_from_file_location("series_diagrams", HERE.parents[1] / "roboshop-ai" / "diagrams" / "build_diagrams.py")
series = importlib.util.module_from_spec(spec)
sys.modules["series_diagrams"] = series
spec.loader.exec_module(series)
Page = series.Page


# --- Part 1: one Linux server (EC2) -------------------------------------------------------------------------------


def server_architecture():
    p = Page("deploy-server-architecture", "One Linux server", 900, 620,
             "Moks CMS on one Linux server with Docker Compose",
             "A reader's browser looks up the domain in DNS, which points at the server's Elastic IP. On the server, "
             "Docker Compose runs three containers: Caddy terminates HTTPS with a Let's Encrypt certificate and proxies "
             "to the Next.js container on port 3000, which talks to PostgreSQL on port 5432. CI builds the image and "
             "pushes it to a registry, and the server pulls it. Media uploads go to R2 or S3, and a nightly pg_dump "
             "is copied to an S3 bucket.")
    p.node("browser", "browser", 60, 40, 250, 58, "Reader's browser", "https://your-domain")
    p.node("dns", "external", 350, 40, 250, 58, "DNS (Route 53 or Cloudflare)", "A record → Elastic IP")
    p.node("ci", "external", 670, 40, 200, 58, "CI (GitHub Actions)", "docker buildx --push")
    p.zone("EC2 instance (Ubuntu 24.04, Docker Compose)", 30, 130, 600, 460, corner="br")
    p.node("caddy", "gateway", 60, 175, 250, 74, "Caddy 2 (ports 80, 443)", "automatic Let's Encrypt TLS", "volume caddy_data")
    p.node("web", "service", 60, 295, 250, 74, "web: Moks CMS (Next.js)", "node server.js, port 3000", "read-only, user 1000")
    p.node("pg", "store", 60, 415, 250, 74, "postgres:18-alpine", "port 5432, not published", "volume pgdata")
    p.node("cron", "agent", 350, 415, 250, 74, "backup.sh (cron, 03:00)", "pg_dump -Fc", "→ S3, 30-day lifecycle")
    p.note(50, 530, "Security group: 80 and 443 from anywhere, 22 from your IP only (or SSM, no port 22).", size=12)
    p.note(50, 552, "Only Caddy publishes ports. web and postgres talk over the Compose network.", size=12)
    p.zone("Outside the server", 650, 130, 240, 460, corner="br")
    p.node("registry", "external", 670, 175, 200, 74, "Image registry", "GHCR or Amazon ECR", "tag = git commit")
    p.node("media", "external", 670, 295, 200, 74, "Object storage", "media uploads", "Cloudflare R2 or S3")
    p.node("s3", "external", 670, 415, 200, 74, "S3 bucket", "database dumps", "versioned, private")
    p.edge("browser", "dns", label="lookup", a_side="r", b_side="l", kind="dashed")
    p.edge("browser", "caddy", label="HTTPS 443", a_at=0.5, b_at=0.5)
    p.edge("caddy", "web", label="HTTP :3000")
    p.edge("web", "pg", label="SQL :5432")
    p.edge("web", "media", label="uploads", a_side="r", b_side="l")
    p.edge("pg", "cron", label="pg_dump", a_side="r", b_side="l", kind="dashed")
    p.edge("cron", "s3", a_side="r", b_side="l", kind="write")
    p.edge("ci", "registry", label="push", kind="write")
    p.edge("registry", "web", label="docker pull", a_side="l", b_side="r", a_at=0.5, b_at=0.2, via=[(330, 212), (330, 310)], kind="dashed", t=-0.4)
    return p


def server_release():
    p = Page("deploy-server-release", "Release on one server", 900, 330,
             "Releasing a new version on the server",
             "Five steps from left to right: CI builds an image tagged with the commit and pushes it. On the server you "
             "set the new tag in .env and run docker compose up, which replaces the web container. On start the app "
             "applies database migrations under an advisory lock, then the health check calls /api/health. If the "
             "check fails, you set the previous tag and run compose up again.")
    w, gap, x0, y = 168, 10, 10, 60
    steps = [
        ("b", "service", "1. Build the image", "tag: git commit SHA", "linux/arm64 or amd64"),
        ("p", "external", "2. Push it", "GHCR or ECR", "keep old tags"),
        ("u", "gateway", "3. compose up -d", "IMAGE=...:<new sha>", "web is replaced"),
        ("m", "store", "4. Migrations run", "on start, under a", "pg advisory lock"),
        ("h", "service", "5. Health check", "GET /api/health", "status ok + version"),
    ]
    for i, (id, kind, title, *lines) in enumerate(steps):
        p.node(id, kind, x0 + i * (w + gap), y, w, 74, title, *lines)
    for a, b in zip("bpumh", "pumh"):
        p.edge(a, b, a_side="r", b_side="l")
    p.node("rb", "reject", x0 + 4 * (w + gap), 200, w, 74, "Roll back", "IMAGE=...:<old sha>", "compose up -d again")
    p.edge("h", "rb", label="fails", kind="reject")
    p.note(10, 210, "The web container restarts, so a release on one server costs a few seconds of 502s.", size=12)
    p.note(10, 232, "Migrations only move forward: the previous image must still run on the new schema.", size=12)
    p.note(10, 254, "Postgres and Caddy keep running; only the web container changes.", size=12)
    return p


# --- Part 2: Kubernetes (k3s) ----------------------------------------------------------------------------------------


def k8s_architecture():
    p = Page("deploy-k8s-architecture", "k3s cluster", 900, 700,
             "Moks CMS on a k3s Kubernetes cluster",
             "The reader's browser reaches Traefik, the ingress controller bundled with k3s, on ports 80 and 443. "
             "Traefik terminates TLS with a certificate that cert-manager obtained from Let's Encrypt over HTTP-01 and "
             "stored in a Secret. It routes to the Service in namespace moks-cms, which balances over two web pods. "
             "The pods read their settings from a Secret, store media in R2 or S3, and connect to a CloudNativePG "
             "cluster: a primary behind the postgres-rw Service and a streaming replica.")
    p.node("browser", "browser", 40, 30, 260, 58, "Reader's browser", "https://your-domain")
    p.node("le", "external", 620, 30, 250, 58, "Let's Encrypt", "ACME HTTP-01 challenge")
    p.zone("k3s cluster (one or more nodes)", 20, 120, 860, 560, corner="br")
    p.node("traefik", "gateway", 40, 160, 260, 74, "Traefik (bundled with k3s)", "ports 80/443, Ingress", "externalTrafficPolicy Local")
    p.node("cm", "agent", 620, 160, 250, 74, "cert-manager", "ClusterIssuer letsencrypt", "renews before expiry")
    p.node("tls", "store", 620, 290, 250, 58, "Secret moks-cms-tls", "certificate + key")
    p.node("media", "external", 620, 420, 250, 58, "Object storage (R2 or S3)", "media uploads")
    p.zone("namespace moks-cms", 30, 270, 560, 395, corner="br")
    p.node("svc", "gateway", 60, 300, 240, 58, "Service moks-cms", "port 80 → 3000")
    p.node("env", "store", 320, 300, 240, 58, "Secret moks-cms-env", "auth + encryption keys")
    p.node("pod1", "service", 60, 400, 240, 74, "Pod: web (replica 1)", "Next.js, port 3000", "probes: /api/health")
    p.node("pod2", "service", 320, 400, 240, 74, "Pod: web (replica 2)", "spread across nodes", "PDB: minAvailable 1")
    p.node("pg1", "store", 60, 560, 240, 74, "Postgres primary", "CloudNativePG", "Service postgres-rw")
    p.node("pg2", "store", 320, 560, 240, 74, "Postgres replica", "streaming replication", "takes over on failure")
    p.edge("browser", "traefik", label="HTTPS")
    p.edge("traefik", "svc", label="Host rule")
    p.edge("svc", "pod1")
    p.edge("svc", "pod2", a_at=0.85, via=[(264, 380), (440, 380)])
    p.edge("pod1", "pg1", label="SQL")
    p.edge("pod2", "pg1", a_at=0.5, b_at=0.85, via=[(440, 520), (264, 520)])
    p.edge("pg1", "pg2", label="WAL", a_side="r", b_side="l", kind="async")
    p.edge("env", "pod2", label="envFrom", a_at=0.85, b_at=0.85, kind="dashed")
    p.edge("pod2", "media", label="uploads", a_side="r", b_side="l", a_at=0.5, b_at=0.29)
    p.edge("cm", "le", label="order + challenge", a_side="t", b_side="b", both=True, kind="dashed")
    p.edge("cm", "tls", kind="write")
    p.edge("tls", "traefik", label="TLS", a_side="l", b_side="r", a_at=0.5, b_at=0.5, via=[(605, 319), (605, 197)], t=0.5)
    return p


def k8s_rollout():
    p = Page("deploy-k8s-rollout", "Rolling update", 900, 330,
             "A rolling update with no downtime",
             "Five steps: Kubernetes starts one extra pod with the new image while both old pods keep serving. The new "
             "pod applies migrations under an advisory lock, its startup probe passes on /api/health, and its readiness "
             "probe adds it to the Service. Then one old pod is removed from the Service, sleeps five seconds in "
             "preStop so in-flight requests finish, and stops. If the startup probe never passes, the rollout stalls "
             "and the old pods keep serving.")
    w, gap, x0, y = 168, 10, 10, 60
    steps = [
        ("n", "service", "1. New pod starts", "maxSurge: 1", "maxUnavailable: 0"),
        ("m", "store", "2. Migrations run", "under a pg advisory", "lock, once per release"),
        ("s", "gateway", "3. Startup probe OK", "GET /api/health", "up to 60 s (30 × 2 s)"),
        ("r", "service", "4. Receives traffic", "readiness probe passes", "Service adds the pod"),
        ("o", "external", "5. Old pod drains", "preStop: sleep 5", "SIGTERM, 30 s grace"),
    ]
    for i, (id, kind, title, *lines) in enumerate(steps):
        p.node(id, kind, x0 + i * (w + gap), y, w, 74, title, *lines)
    for a, b in zip("nmsr", "msro"):
        p.edge(a, b, a_side="r", b_side="l")
    p.node("stall", "reject", x0 + 2 * (w + gap), 200, w, 74, "Never becomes ready", "rollout stalls; the old", "pods keep serving")
    p.edge("s", "stall", label="fails", kind="reject")
    p.note(10, 210, "Steps 1 to 5 repeat for", size=12)
    p.note(10, 232, "each replica in turn.", size=12)
    p.note(540, 210, "kubectl rollout status deploy/moks-cms", size=12)
    p.note(540, 232, "kubectl rollout undo deploy/moks-cms", size=12)
    return p


# --- Part 3: Amazon EKS ---------------------------------------------------------------------------------------------


def eks_architecture():
    p = Page("deploy-eks-architecture", "Amazon EKS", 900, 720,
             "Moks CMS on Amazon EKS with RDS",
             "Route 53 points the domain at an Application Load Balancer in the public subnets, which ends TLS with an "
             "ACM certificate and sends traffic straight to the web pods' IP addresses. The pods run on a Graviton "
             "managed node group in two private subnets. The AWS Load Balancer Controller creates the ALB from an "
             "Ingress, and External Secrets Operator copies the app's settings from Secrets Manager into a Kubernetes "
             "Secret. Pods pull the image from ECR, store media in object storage, and connect to Amazon RDS for "
             "PostgreSQL, Multi-AZ, in private database subnets. A NAT gateway carries outbound traffic.")
    p.node("browser", "browser", 40, 30, 220, 58, "Reader's browser", "https://your-domain")
    p.node("r53", "external", 300, 30, 260, 58, "Route 53", "alias A record → ALB")
    p.node("acm", "external", 650, 30, 220, 58, "ACM certificate", "apex + www, DNS-validated")
    p.zone("VPC (2 Availability Zones)", 20, 110, 600, 590, corner="br")
    p.zone("Public subnets", 40, 150, 560, 110, corner="br")
    p.node("alb", "edge", 60, 180, 300, 58, "Application Load Balancer", "HTTPS 443, target type ip")
    p.node("nat", "external", 400, 180, 180, 58, "NAT gateway", "outbound traffic")
    p.zone("Private subnets: managed node group (t4g, arm64)", 40, 290, 560, 230, corner="br")
    p.node("pod1", "service", 70, 330, 240, 74, "Pod: web (AZ a)", "Next.js, port 3000", "readiness /api/health")
    p.node("pod2", "service", 340, 330, 240, 74, "Pod: web (AZ b)", "same Deployment", "PDB: minAvailable 1")
    p.node("lbc", "agent", 70, 430, 240, 74, "AWS Load Balancer Controller", "Ingress → ALB rules", "Pod Identity role")
    p.node("eso", "agent", 340, 430, 240, 74, "External Secrets Operator", "Secrets Manager →", "Secret moks-cms-env")
    p.zone("Private database subnets", 40, 550, 560, 130, corner="br")
    p.node("rds", "store", 70, 585, 510, 74, "Amazon RDS for PostgreSQL", "Multi-AZ, encrypted, automated backups", "port 5432 from the cluster security group only")
    p.zone("Regional services", 640, 110, 240, 590, corner="br")
    p.node("ecr", "external", 650, 300, 220, 58, "Amazon ECR", "moks-cms images")
    p.node("sm", "external", 650, 420, 220, 74, "Secrets Manager", "secret moks-cms/web", "read by ESO only")
    p.node("media", "external", 650, 560, 220, 58, "Object storage", "R2 or S3 (media)")
    p.edge("browser", "r53", label="lookup", a_side="r", b_side="l", kind="dashed")
    p.edge("browser", "alb", label="HTTPS", a_at=0.5, b_at=0.3)
    p.edge("acm", "alb", label="certificate", a_side="b", b_side="r", via=[(760, 140), (380, 140), (380, 209)], kind="dashed", t=-0.3)
    p.edge("alb", "pod1", a_at=0.3, b_at=0.5, via=[(150, 300), (190, 300)])
    p.edge("alb", "pod2", a_at=0.8, via=[(300, 300), (460, 300)])
    p.edge("pod1", "rds", label="SQL, TLS", a_side="l", b_side="l", via=[(52, 367), (52, 622)], t=0.2)
    p.edge("ecr", "pod2", label="pull", a_side="l", b_side="r", via=[(615, 329), (615, 352)], b_at=0.3, kind="dashed")
    p.edge("sm", "eso", a_side="l", b_side="r", a_at=0.5, b_at=0.365, kind="dashed")
    p.edge("pod2", "media", label="uploads", a_side="r", b_side="l", a_at=0.8, via=[(630, 389), (630, 589)], t=0.6)
    return p


def eks_delivery():
    p = Page("deploy-eks-delivery", "Delivery to EKS", 900, 330,
             "From a merged pull request to running pods on EKS",
             "Five steps: a GitHub Actions job gets a short-lived AWS session through OIDC with no stored keys, builds "
             "an arm64 image on an arm runner and pushes it to ECR tagged with the commit. It then updates its "
             "kubeconfig through an EKS access entry limited to namespace moks-cms, sets the new image on the "
             "Deployment and waits for the rollout, and finally runs the smoke test. A failed rollout is undone "
             "with kubectl rollout undo.")
    w, gap, x0, y = 168, 10, 10, 60
    steps = [
        ("o", "external", "1. OIDC to AWS", "AssumeRoleWith-", "WebIdentity, 1 hour"),
        ("b", "service", "2. Build + push", "ubuntu-24.04-arm", "ECR tag: commit SHA"),
        ("a", "gateway", "3. kubeconfig", "EKS access entry", "namespace moks-cms"),
        ("d", "service", "4. Set image", "rollout status", "--timeout 5m"),
        ("s", "store", "5. Smoke test", "health, sitemap,", "redirects"),
    ]
    for i, (id, kind, title, *lines) in enumerate(steps):
        p.node(id, kind, x0 + i * (w + gap), y, w, 74, title, *lines)
    for a, b in zip("obad", "bads"):
        p.edge(a, b, a_side="r", b_side="l")
    p.node("undo", "reject", x0 + 3 * (w + gap), 200, w, 74, "Roll back", "kubectl rollout undo", "(immutable tags)")
    p.edge("d", "undo", label="fails", kind="reject")
    p.note(10, 210, "No AWS keys are stored in GitHub: the role trusts only", size=12)
    p.note(10, 232, "this repository's default branch.", size=12)
    return p


FILES = (server_architecture, server_release, k8s_architecture, k8s_rollout, eks_architecture, eks_delivery)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    built = []
    for make in FILES:
        page = make()
        for e in page.edges:
            for x, y in e["points"]:
                if not (0 <= x <= page.w and 0 <= y <= page.h):
                    raise SystemExit(f"{page.figure}: edge {e['id']} leaves the page")
        for n in page.nodes.values():
            if n["x"] < 0 or n["y"] < 0 or n["x"] + n["w"] > page.w or n["y"] + n["h"] > page.h:
                raise SystemExit(f"{page.figure}: {n['id']} leaves the page")
        mxfile = ET.Element("mxfile", host="app.diagrams.net", agent="build_diagrams.py", version="24.7.17", type="device")
        mxfile.append(series.page_xml(page, 0))
        ET.indent(mxfile)
        (HERE / f"{page.figure}.drawio").write_bytes(ET.tostring(mxfile, encoding="utf-8", xml_declaration=False))
        (OUT / f"{page.figure}.svg").write_text(series.page_svg(page), encoding="utf-8")
        built.append((page.figure, page.w, page.h))
    (HERE / "figures.txt").write_text("".join(f"{f} {w} {h}\n" for f, w, h in built), encoding="utf-8")
    print(f"{len(built)} .drawio files and SVGs")


if __name__ == "__main__":
    main()
