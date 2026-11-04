# Database access from the owner's Mac and the Hetzner host

| What | Where | How it is reached |
|---|---|---|
| Adminer web UI | `https://jithendar.com/db/` | Traefik HTTP route, IP allowlist, then a PostgreSQL login |
| PostgreSQL | `db.jithendar.com:443` | Traefik TCP route on the TLS server name, IP allowlist, Let's Encrypt certificate, PostgreSQL login |

A path such as `jithendar.com/db` works only for the web UI. Database clients (psql, DBeaver, TablePlus) speak
PostgreSQL's own protocol, which has no URL path, so they use the hostname `db.jithendar.com` on port 443 instead.

Allowed sources (`allowlist.yaml`): `122.177.247.138` (the Mac on 2026-11-04) and `46.224.38.14` (the Hetzner
host). Both routes also need the login from `scripts/create-db-remote-user.sh`: it can read and write table data, but
cannot change the schema or roles. The app's own `jithendar` login is never used from outside.

## Why the order below matters

On 2026-11-04 every request reached Traefik from `192.168.49.2`, a minikube node: the host's HAProxy forwards plain
TCP and kube-proxy rewrites the source of NodePort traffic. An IP allowlist cannot work like that. The fix is the
PROXY protocol: HAProxy prepends the real client address, and Traefik trusts it from the minikube network. Until that
is live, the allowlists refuse everyone (fail closed). It also gives the site real visitor IPs in its logs and
rate limits, which today all see the same address.

## Rollout

1. **Traefik accepts the PROXY protocol** (`tools`, from the repository root, Mac or host):
   `bash deploy/minikube/deploy-traefik.sh`. Connections without the header still work, so nothing changes yet.
   Check: `kubectl --context mk4 -n traefik get deploy traefik -o yaml | grep proxyProtocol` shows both entrypoints,
   and https://jithendar.com still loads.
2. **HAProxy sends it** (on the Hetzner host, `tools` checkout): `bash deploy/minikube/expose-ingress.sh`. The
   script refuses to run if step 1 is missing. Check: load https://jithendar.com from the Mac, then
   `kubectl --context mk4 -n jithendar logs deploy/jithendar-com | grep '"route":"/"' | tail -3`: `ip` must be
   `122.177.247.138`, not `192.168.49.x`. From the host: `curl -s -o /dev/null https://jithendar.com/` and look
   for `46.224.38.14`. **If the host shows up as another address (for example `192.168.49.1`), add that address to
   both lists in `allowlist.yaml`, and only if it is not also what other visitors show up as.**
3. **DNS:** an A record `db.jithendar.com → 46.224.38.14`, DNS only (no proxy), where jithendar.com's records are
   managed.
4. **Login:** `bash scripts/create-db-remote-user.sh` (prints the password once).
5. **Apply:** `kubectl --context mk4 apply -k k8s/db-access`. Wait for the certificate:
   `kubectl --context mk4 -n jithendar get certificate db-jithendar-com` → `READY True` (HTTP-01 over port 80).

## Verify

```bash
# From the Mac
psql "host=db.jithendar.com port=443 dbname=jithendar user=jithendar_remote sslmode=verify-full sslrootcert=system" -c 'select current_user'
# If psql says the server does not support SSL on this port, try the TLS-first handshake (libpq 17+):
psql "host=db.jithendar.com port=443 dbname=jithendar user=jithendar_remote sslmode=verify-full sslrootcert=system sslnegotiation=direct" -c 'select 1'
open https://jithendar.com/db/      # System: PostgreSQL, Server: jithendar-postgres
```

From any other network (a phone off Wi-Fi): `https://jithendar.com/db/` must answer **403**, and
`psql … db.jithendar.com` must fail to connect. Check the site itself still works from there.

## When the Mac's IP changes

Home connections often get a new address. Find it (`curl -s https://cloudflare.com/cdn-cgi/trace | grep ip=`),
replace it in both lists in `allowlist.yaml`, then `kubectl --context mk4 apply -k k8s/db-access`.

## Rollback

- Remove access: `kubectl --context mk4 delete -k k8s/db-access` (the login stays; to drop it:
  `kubectl --context mk4 -n jithendar exec -it jithendar-postgres-0 -c postgres -- psql -U jithendar -c 'DROP ROLE jithendar_remote'`).
- Undo the PROXY protocol, **in this order**: remove `send-proxy-v2` from `deploy/minikube/expose-ingress.sh` and
  rerun it on the host, then remove `proxyProtocol` from `deploy/minikube/traefik/values.yaml` and rerun
  `deploy-traefik.sh`.

## Limits

- An IP allowlist is one layer. Anything inside the minikube network could reach a NodePort and forge a PROXY
  header, and two devices behind the same home router share one address. The PostgreSQL password is the second
  layer; keep it in a password manager and rotate it by rerunning the script.
- Adminer cannot tell it is behind HTTPS, so its cookies lack the `Secure` flag. Use only `https://` URLs.
- The `adminer:6.3.0` image and its routing under `/db/` were checked against the image's Dockerfile, not run
  before this change was written.
