import { absoluteUrl } from "@/config/site";

/**
 * Path routes on jithendar.com served by other workloads on the cluster (Argo CD, Grafana, Adminer, …).
 * They send no noindex of their own, so robots.txt is the only signal. Each is blocked as `/x$` plus
 * `/x/`, never a bare `/x` prefix, so site pages such as `/dbt-basics` stay crawlable. `/moks` is left
 * out: it serves `<meta name="robots" content="noindex">` and a Disallow would hide that.
 */
export const FOREIGN_PATH_ROUTES = [
  "argocd",
  "db",
  "grafana",
  "harbor",
  "jfrog",
  "loki",
  "opensearch",
  "opensearch-dashboards",
  "prometheus",
  "vault",
] as const;

/**
 * Production: everything crawlable except API endpoints (not pages) and other workloads' path routes;
 * private pages are protected by login and carry noindex. Other hosts/environments: crawlable but
 * every response sends `X-Robots-Tag: noindex` (src/proxy.ts) — a Disallow would hide that noindex
 * from crawlers and could leave bare URLs indexed. No sitemap is advertised there.
 */
export function robotsTxt(indexable: boolean): string {
  if (!indexable) return "User-agent: *\nAllow: /\n";
  return [
    "User-agent: *",
    "Allow: /",
    "Disallow: /api/",
    ...FOREIGN_PATH_ROUTES.flatMap((route) => [`Disallow: /${route}$`, `Disallow: /${route}/`]),
    "",
    `Sitemap: ${absoluteUrl("/sitemap.xml")}`,
    `Sitemap: ${absoluteUrl("/news-sitemap.xml")}`,
    "",
  ].join("\n");
}
