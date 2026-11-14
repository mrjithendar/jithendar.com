#!/usr/bin/env python3
"""Figures for the two Let's Encrypt articles: editable .drawio files and matching SVGs.

Reuses the layout, palette and draw.io writer of the RoboShop AI series. Run from www/. The SVGs are rendered here,
not exported by draw.io: if a .drawio file is edited by hand, re-export it from draw.io over the SVG.
The two mk4 figures follow Git only (mrjithendar/minikube 13be756, read on 2026-11-14); the cluster was not inspected.
"""
import importlib.util
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parents[3] / "public" / "images" / "lets-encrypt"
spec = importlib.util.spec_from_file_location("series_diagrams", HERE.parents[1] / "roboshop-ai" / "diagrams" / "build_diagrams.py")
series = importlib.util.module_from_spec(spec)
sys.modules["series_diagrams"] = series
spec.loader.exec_module(series)
Page = series.Page


def acme_flow():
    p = Page("lets-encrypt-acme-flow", "ACME issuance", 900, 560,
             "How an ACME client obtains a certificate from Let's Encrypt",
             "Five rows, the ACME client on the left and Let's Encrypt on the right. The client registers an account key, "
             "creates an order for its names and receives one challenge token per name. It publishes the proof over HTTP "
             "or DNS, Let's Encrypt validates it from several networks, the client sends a CSR, and Let's Encrypt returns "
             "the signed certificate with its intermediate chain. Renewal repeats the same steps.")
    p.zone("Your server: ACME client (Certbot, cert-manager, Caddy)", 15, 12, 420, 536)
    p.zone("Let's Encrypt (ACME server)", 465, 12, 420, 536)
    rows = (40, 142, 244, 346, 448)
    left = [
        ("c1", "service", "1. Register an account", "account key pair signs every request"),
        ("c2", "service", "2. Create an order", "names: example.com, www.example.com"),
        ("c3", "agent", "4. Publish the proof", "HTTP path or DNS TXT record"),
        ("c4", "service", "6. Finalize with a CSR", "certificate private key stays here"),
        ("c5", "store", "8. Install certificate + chain", "reload the server; renew = repeat"),
    ]
    right = [
        ("s1", "external", "Account stored", "public key only"),
        ("s2", "external", "3. Return challenges", "one random token per name"),
        ("s3", "gateway", "5. Validate", "fetches the proof from several networks"),
        ("s4", "external", "7. Sign the certificate", "logged to Certificate Transparency"),
        ("s5", "external", "Certificate + intermediate", "90 days today, 45 days by Feb 2028"),
    ]
    for y, (i, kind, title, line) in zip(rows, left):
        p.node(i, kind, 30, y, 390, 76, title, line)
    for y, (i, kind, title, line) in zip(rows, right):
        p.node(i, kind, 480, y, 390, 76, title, line)
    p.edge("c1", "s1", a_side="r", b_side="l")
    p.edge("c2", "s2", a_side="r", b_side="l")
    p.edge("s3", "c3", a_side="l", b_side="r", kind="dashed")
    p.edge("c4", "s4", a_side="r", b_side="l")
    p.edge("s5", "c5", a_side="l", b_side="r", kind="write")
    for a, b in (("c1", "c2"), ("c2", "c3"), ("c3", "c4"), ("c4", "c5"), ("s2", "s3"), ("s4", "s5")):
        p.edge(a, b, kind="dashed")
    return p


def challenge_types():
    p = Page("lets-encrypt-challenge-types", "HTTP-01 vs DNS-01", 900, 440,
             "HTTP-01 proves control of a web server, DNS-01 proves control of the DNS zone",
             "Two columns. HTTP-01: the ACME client writes a token file, and Let's Encrypt fetches it from port 80 of the "
             "server at /.well-known/acme-challenge. It needs a public port 80 and cannot issue wildcards. DNS-01: the ACME "
             "client calls the DNS provider's API to create a TXT record at _acme-challenge, and Let's Encrypt looks it up. "
             "It needs a DNS API token, works for private hosts and is the only way to get a wildcard certificate.")
    p.zone("HTTP-01: needs public port 80, no wildcards", 15, 12, 420, 416)
    p.zone("DNS-01: needs a DNS API token, wildcards allowed", 465, 12, 420, 416)
    p.node("h_le", "external", 30, 40, 390, 76, "Let's Encrypt validators", "GET http://example.com/.well-known/", "acme-challenge/<token>")
    p.node("h_srv", "edge", 30, 180, 390, 76, "Your server or ingress, port 80", "serves the token file", "redirects to HTTPS are followed")
    p.node("h_cl", "service", 30, 320, 390, 76, "ACME client", "writes the token before validation", "removes it afterwards")
    p.node("d_le", "external", 480, 40, 390, 76, "Let's Encrypt validators", "TXT lookup", "_acme-challenge.example.com")
    p.node("d_dns", "store", 480, 180, 390, 76, "Authoritative DNS (your provider)", "holds the TXT record", "the web server is never contacted")
    p.node("d_cl", "service", 480, 320, 390, 76, "ACME client", "creates the record over the DNS API", "token scoped to one zone")
    p.edge("h_le", "h_srv", kind="dashed", label="fetch", dx=30)
    p.edge("h_cl", "h_srv", a_side="t", b_side="b", kind="write", label="token", dx=30)
    p.edge("d_le", "d_dns", kind="dashed", label="query", dx=30)
    p.edge("d_cl", "d_dns", a_side="t", b_side="b", kind="write", label="TXT", dx=26)
    return p


def k3s_architecture():
    p = Page("lets-encrypt-k3s-architecture", "mk4 TLS architecture", 900, 700,
             "TLS on mk4: cert-manager issues one wildcard certificate over DNS-01 and the Istio gateway serves it",
             "Outside the cluster: a visitor, Cloudflare DNS for the zone jithendar.com and Let's Encrypt. A Hetzner load "
             "balancer named mk4-edge forwards ports 80 and 443 with a PROXY protocol header to the Istio ingress gateway in "
             "the k3s cluster, which terminates TLS with the Secret jithendar-com-gateway-tls. In namespace cert-manager, "
             "cert-manager v1.20.4 uses the ClusterIssuer letsencrypt-dns and the Secret cloudflare-api-token to write a TXT "
             "record through the Cloudflare API, Let's Encrypt looks the record up and signs, and cert-manager writes the "
             "certificate into the gateway Secret. A second Certificate, jithendar-com-wildcard in namespace jithendar, "
             "holds the same names. No HTTP route is involved in issuance or renewal.")
    p.zone("Internet", 15, 12, 870, 110)
    p.node("user", "browser", 30, 38, 250, 70, "Visitor", "https://jithendar.com", "and *.jithendar.com")
    p.node("cf", "store", 325, 38, 250, 70, "Cloudflare DNS", "zone jithendar.com", "TXT _acme-challenge")
    p.node("le", "external", 620, 38, 250, 70, "Let's Encrypt", "ACME v2, production", "staging issuer for tests")
    p.zone("Hetzner Cloud", 15, 138, 870, 96)
    p.node("lb", "edge", 30, 164, 250, 58, "Load balancer mk4-edge", "80/443 + PROXY protocol")
    p.zone("k3s cluster mk4: namespace istio-ingress", 15, 250, 870, 130)
    p.node("gw", "gateway", 30, 278, 250, 88, "Istio ingress gateway", "2 replicas, Gateway public", "TLS ends here", "reads the Secret over SDS")
    p.node("sec1", "store", 325, 278, 250, 88, "Gateway TLS Secret", "jithendar-com-gateway-tls", "tls.crt + tls.key")
    p.node("cert1", "gateway", 620, 278, 250, 88, "Certificate jithendar-com", "jithendar.com + *.jithendar.com", "issuer letsencrypt-dns")
    p.zone("k3s cluster mk4: namespace cert-manager", 15, 396, 870, 130)
    p.node("tok", "store", 30, 424, 250, 88, "Cloudflare API token Secret", "Zone DNS Edit + Zone Read", "created by hand, not in Git")
    p.node("issuer", "agent", 325, 424, 250, 88, "ClusterIssuer", "letsencrypt-dns", "DNS-01 solver: Cloudflare")
    p.node("cm", "agent", 620, 424, 250, 88, "cert-manager v1.20.4", "controller, webhook, cainjector", "Terraform Helm release")
    p.zone("k3s cluster mk4: namespace jithendar", 15, 542, 870, 146)
    p.node("cert2", "gateway", 325, 570, 250, 88, "Second Certificate", "jithendar-com-wildcard", "same two names, same issuer")
    p.node("sec2", "store", 30, 570, 250, 88, "Site TLS Secret", "jithendar-com-wildcard-tls", "second copy of the certificate")
    p.edge("user", "lb")
    p.edge("lb", "gw")
    p.edge("gw", "sec1", a_side="r", b_side="l", kind="dashed")
    p.edge("cert1", "sec1", a_side="l", b_side="r", kind="write")
    p.edge("cm", "cert1", a_side="t", b_side="b", kind="dashed")
    p.edge("cm", "issuer", a_side="l", b_side="r", kind="dashed")
    p.edge("issuer", "tok", a_side="l", b_side="r", kind="dashed")
    p.edge("issuer", "cf", a_side="t", b_side="b", a_at=0.5, b_at=0.5, via=[(450, 388), (302, 388), (302, 130), (450, 130)],
           kind="write", label="TXT record", dx=44, t=0.22)
    p.edge("le", "cf", a_side="l", b_side="r", kind="dashed")
    p.edge("cm", "le", a_side="r", b_side="r", a_at=0.3, b_at=0.5, via=[(880, 450), (880, 73)], label="ACME order", dx=-44, t=0.5)
    p.edge("cm", "cert2", a_side="b", b_side="r", a_at=0.5, b_at=0.5, via=[(745, 614)], kind="dashed")
    p.edge("cert2", "sec2", a_side="l", b_side="r", kind="write")
    return p


def k3s_renewal():
    p = Page("lets-encrypt-k3s-renewal", "Automatic renewal", 900, 520,
             "How cert-manager renews the wildcard certificate with no manual step",
             "A loop of eight steps. The Certificate is Ready and cert-manager records a renewal time two thirds of the way "
             "through the certificate's lifetime, day 60 of 90. When that time passes it marks the Certificate as Issuing, "
             "generates a new private key and a CertificateRequest, and creates an ACME Order with a DNS-01 Challenge. It "
             "writes a TXT record through the Cloudflare API and checks it over DNS over HTTPS. Let's Encrypt validates and "
             "signs. cert-manager replaces tls.crt and tls.key in the same Secret, and the Istio gateway picks the Secret up "
             "without a restart. If a step fails, cert-manager retries with a backoff from 1 hour up to 32 hours while the old "
             "certificate keeps working for about 30 more days.")
    p.zone("cert-manager decides", 15, 12, 870, 130)
    p.zone("ACME DNS-01 round trip", 15, 158, 870, 130)
    p.zone("Result", 15, 304, 870, 204)
    p.node("ready", "service", 30, 40, 270, 88, "1. Certificate Ready", "status.renewalTime set at", "2/3 of the lifetime (day 60 of 90)")
    p.node("due", "gateway", 315, 40, 270, 88, "2. Renewal time passes", "condition Issuing = True", "no cron job, no human")
    p.node("csr", "gateway", 600, 40, 270, 88, "3. New key + CertificateRequest", "rotationPolicy Always by default", "since cert-manager v1.18")
    p.node("order", "agent", 600, 186, 270, 88, "4. Order + DNS-01 Challenge", "one authorization per name")
    p.node("txt", "agent", 315, 186, 270, 88, "5. TXT record via Cloudflare API", "self-check over DNS over HTTPS", "(pods cannot reach port 53)")
    p.node("le", "external", 30, 186, 270, 88, "6. Let's Encrypt validates", "looks up the TXT record", "signs the certificate")
    p.node("secret", "store", 30, 332, 270, 88, "7. Secret updated in place", "same name, new tls.crt + tls.key")
    p.node("gw", "edge", 315, 332, 270, 88, "8. Istio gateway reloads", "Envoy gets the Secret over SDS", "no pod restart")
    p.node("fail", "reject", 600, 332, 270, 88, "If a step fails", "retry: 1 h, doubling up to 32 h", "old certificate still valid ~30 days")
    p.edge("ready", "due", a_side="r", b_side="l")
    p.edge("due", "csr", a_side="r", b_side="l")
    p.edge("csr", "order")
    p.edge("order", "txt", a_side="l", b_side="r")
    p.edge("txt", "le", a_side="l", b_side="r")
    p.edge("le", "secret", kind="write")
    p.edge("secret", "gw", a_side="r", b_side="l")
    p.edge("order", "fail", kind="dashed")
    p.edge("secret", "ready", a_side="l", b_side="l", a_at=0.5, b_at=0.5, via=[(22, 376), (22, 84)], kind="dashed")
    p.note(30, 452, "The loop restarts with the new certificate. With 45-day certificates the same rule renews on day 30.", size=12)
    p.note(30, 474, "Nothing in the Certificate sets renewBefore, so the timing follows whatever lifetime Let's Encrypt issues.", size=12)
    return p


FILES = (acme_flow, challenge_types, k3s_architecture, k3s_renewal)


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
