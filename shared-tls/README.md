# One jithendar.com certificate

The site's Certificate `jithendar/jithendar-com` (Secret `jithendar-com-tls`) is the only
issuer-managed certificate for jithendar.com. [tlsstore.yaml](tlsstore.yaml) makes it Traefik's
default certificate, so every Traefik route for jithendar.com in any namespace uses it
without copying private keys. cert-manager renews it in one place and Traefik picks up the
renewed Secret automatically.

Argo CD deploys `tlsstore.yaml` through the `shared-tls` Application in roboshop-ai's
`argocd/` catalog.

## patch-ssl.sh

One-time cleanup for a cluster that still has per-namespace copies:

```bash
KUBE_CONTEXT=mk4 ./patch-ssl.sh
```

1. Checks that `jithendar/jithendar-com` is Ready, covers jithendar.com and writes
   `jithendar-com-tls`, and that no other `default` TLSStore exists. Otherwise it stops
   without changes.
2. Applies `tlsstore.yaml`.
3. In `argocd`, `monitoring` and `roboshop-ai`, removes `secretName: jithendar-com-tls` from
   Traefik ingresses for jithendar.com so they fall back to the default store. Hosts and
   routes are unchanged.
4. Deletes duplicate `jithendar-com` Certificates in those namespaces with
   `--cascade=orphan`. Their Secrets are kept.

Reruns are safe. It never requests a new certificate.

## Notes

- Only one `default` TLSStore may exist across the namespaces Traefik watches.
- This covers jithendar.com only. Other hostnames, such as `jfrog.jithendar.com`, keep their
  own certificates.
- Don't delete the `jithendar` namespace or its Certificate while other apps rely on it.

Verify:

```bash
kubectl --context=mk4 -n jithendar get certificate jithendar-com
kubectl --context=mk4 -n jithendar get tlsstore default
curl -I https://jithendar.com/argocd/
```

Tests: `cd shared-tls && python3 -m pytest -q test_configure.py`
