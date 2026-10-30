import { notFound, permanentRedirect } from "next/navigation";
import { findRedirect } from "@/lib/redirects";
import { getCategoryMap } from "@/lib/categories";
import { collectionLabels, type Collection } from "@/config/taxonomy";
import { articlesInCategory, articlesWithTag, getAuthor, getPublishedContent, isCategoryIndexable, publishedTags } from "@/lib/content";
import { getSiteConfig } from "@/lib/site-config";
import type { Listing } from "./listing";

const home = { name: "Home", path: "/" };

/** Articles per listing page (Admin → Appearance → Blog). */
async function listingPageSize(): Promise<number> {
  return (await getSiteConfig()).config.blog.listing.pageSize;
}

export const collectionDescriptions: Record<Collection, string> = {
  blog:
    "Hands-on tutorials, deep dives and opinion on building and running AI, cloud and platform systems — Kubernetes, AWS, DevOps automation, observability and LLM tooling. Every post is written from real production work, with working code, configuration and the trade-offs behind each decision.",
  news:
    "Timely, sourced coverage of the releases, deprecations and security advisories that matter to engineers working with AI, cloud and cloud-native tooling. Each story links to its primary source, explains what changed and why it matters, and notes what you may need to do about it.",
  projects:
    "Engineering projects built end to end — from infrastructure as code and CI/CD pipelines to Kubernetes platforms and AI-powered applications. Each write-up covers the problem, the architecture, the tools chosen and the lessons learned along the way, with links to the source where it is public.",
};

export async function collectionListing(collection: Collection): Promise<Listing> {
  const articles = await getPublishedContent({ collection });
  return {
    pageSize: await listingPageSize(),
    title: collectionLabels[collection],
    description: collectionDescriptions[collection],
    basePath: `/${collection}`,
    crumbs: [home, { name: collectionLabels[collection], path: `/${collection}` }],
    articles,
    indexable: articles.length > 0,
  };
}

export async function categoryListing(slug: string): Promise<Listing> {
  const category = (await getCategoryMap()).get(slug);
  if (!category) {
    const moved = await findRedirect(`/category/${slug}`);
    if (moved) permanentRedirect(moved);
    notFound();
  }
  return {
    pageSize: await listingPageSize(),
    title: category.label,
    description: category.intro,
    basePath: `/category/${slug}`,
    crumbs: [home, { name: category.label, path: `/category/${slug}` }],
    articles: await articlesInCategory(slug),
    indexable: await isCategoryIndexable(slug),
    feedHref: `/category/${slug}/feed.xml`,
  };
}

/** Tag pages have no editorial intro, so they are always noindex, follow. */
export async function tagListing(slug: string): Promise<Listing> {
  const tag = (await publishedTags()).find((t) => t.slug === slug);
  if (!tag) notFound();
  return {
    pageSize: await listingPageSize(),
    title: `#${tag.label}`,
    description: `Every article, news story and project on Jithendar.com tagged “${tag.label}”, newest first — tutorials, analysis and hands-on notes on ${tag.label} from real AI, cloud and platform engineering work.`,
    basePath: `/tag/${slug}`,
    crumbs: [home, { name: `#${tag.label}`, path: `/tag/${slug}` }],
    articles: await articlesWithTag(slug),
    indexable: false,
  };
}

export async function authorListing(slug: string): Promise<Listing> {
  const author = await getAuthor(slug);
  if (!author) notFound();
  const articles = (await getPublishedContent()).filter((a) => a.frontmatter.author === slug);
  return {
    pageSize: await listingPageSize(),
    title: author.frontmatter.name,
    description: `Articles and projects by ${author.frontmatter.name} on Jithendar.com.`,
    basePath: author.path,
    crumbs: [home, { name: author.frontmatter.name, path: author.path }],
    articles,
    // An author page with no published work is thin content.
    indexable: articles.length > 0,
  };
}
