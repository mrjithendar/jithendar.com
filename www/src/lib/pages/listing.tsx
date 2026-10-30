import type { Metadata } from "next";
import { notFound, permanentRedirect } from "next/navigation";
import { ArticleList } from "@/components/ArticleList";
import { Container } from "@/components/Container";
import { JsonLd } from "@/components/JsonLd";
import { pageHref, Pagination } from "@/components/Pagination";
import { absoluteUrl, site } from "@/config/site";
import { paginate, parsePageParam, type Article, type Paged } from "@/lib/content";
import { breadcrumbLd, type Crumb } from "@/lib/seo/jsonld";

export type Listing = {
  title: string;
  description: string;
  basePath: string;
  crumbs: Crumb[];
  articles: Article[];
  /** False → noindex, follow (thin or intro-less taxonomy). */
  indexable: boolean;
  feedHref?: string;
  emptyText?: string;
  /** Items per page (configured; out-of-range pages 404). */
  pageSize?: number;
};

export type PageParams = { params: Promise<{ n: string }> };

/** Resolve the page for a /page/<n> route: 404 for invalid or out-of-range pages, 308 for /page/1. */
export function resolvePage(listing: Listing, raw?: string): Paged<Article> {
  if (raw === "1") permanentRedirect(listing.basePath);
  const page = raw === undefined ? 1 : parsePageParam(raw);
  const paged = page === undefined ? undefined : paginate(listing.articles, page, listing.pageSize);
  if (!paged) notFound();
  return paged;
}

/** Static params for pages 2..n of a listing. */
export function extraPageParams(articles: Article[], size?: number): { n: string }[] {
  const total = paginate(articles, 1, size)?.totalPages ?? 1;
  return Array.from({ length: Math.max(0, total - 1) }, (_, i) => ({ n: String(i + 2) }));
}

export function listingMetadata(listing: Listing, page = 1): Metadata {
  const path = pageHref(listing.basePath, page);
  const title = page > 1 ? `${listing.title} (page ${page})` : listing.title;
  return {
    title,
    description: listing.description,
    alternates: {
      canonical: absoluteUrl(path),
      ...(listing.feedHref ? { types: { "application/rss+xml": absoluteUrl(listing.feedHref) } } : {}),
    },
    openGraph: { type: "website", url: absoluteUrl(path), siteName: site.name, locale: site.locale, title, description: listing.description },
    ...(listing.indexable ? {} : { robots: { index: false, follow: true } }),
  };
}

export function ListingPage({ listing, paged }: { listing: Listing; paged: Paged<Article> }) {
  const crumbs = paged.page > 1 ? [...listing.crumbs, { name: `Page ${paged.page}`, path: pageHref(listing.basePath, paged.page) }] : listing.crumbs;
  return (
    <>
      <JsonLd data={breadcrumbLd(crumbs)} />
      {/* Description-only band: the visible title, breadcrumbs, count and topic chips were dropped on purpose.
          The h1 stays for screen readers and search engines; breadcrumbs stay in the JSON-LD. */}
      <div className="border-b border-line bg-surface-muted">
        <Container className="py-8 sm:py-10">
          <h1 className="sr-only">{paged.page > 1 ? `${listing.title} (page ${paged.page})` : listing.title}</h1>
          <p className="max-w-3xl text-[1.0625rem] leading-relaxed text-fg-muted text-pretty sm:text-lg">{listing.description}</p>
        </Container>
      </div>
      <Container className="pt-10 sm:pt-12">
        <ArticleList articles={paged.items} emptyText={listing.emptyText ?? "Nothing published here yet"} />
        <Pagination basePath={listing.basePath} page={paged.page} totalPages={paged.totalPages} />
      </Container>
    </>
  );
}
