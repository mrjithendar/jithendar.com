import Image from "next/image";
import Link from "next/link";
import type { ReactNode } from "react";
import { Container } from "@/components/Container";
import { JsonLd } from "@/components/JsonLd";
import { mdxComponents } from "@/components/Mdx";
import { PageHeader } from "@/components/PageHeader";
import { getPages, type Page } from "@/lib/content";
import { formatDate } from "@/lib/dates";
import { compileMdx } from "@/lib/mdx/compile";
import { breadcrumbLd } from "@/lib/seo/jsonld";

const ORDER = ["about", "contact", "editorial-policy", "corrections-policy", "ai-use-policy", "privacy-policy", "cookies", "terms"];

/** Static page layout, shared by the public page and the editor preview. */
export async function PageView({ page, notice, after }: { page: Page; notice?: ReactNode; after?: ReactNode }) {
  const fm = page.frontmatter;
  const { Content } = await compileMdx(page.body);
  const crumbs = [
    { name: "Home", path: "/" },
    { name: fm.title, path: page.path },
  ];
  // Menu order set in the editor; the historical order breaks ties (all pages start at 100).
  const rank = (slug: string) => (ORDER.indexOf(slug) === -1 ? ORDER.length : ORDER.indexOf(slug));
  const siblings = (await getPages()).sort((a, b) => a.frontmatter.sortOrder - b.frontmatter.sortOrder || rank(a.slug) - rank(b.slug));

  return (
    <>
      <JsonLd data={breadcrumbLd(crumbs)} />
      {notice}
      {page.slug === "about" ? (
        // Same description-only band as the listings: title, breadcrumbs, label and date dropped on purpose.
        <div className="border-b border-line bg-surface-muted">
          <Container className="py-8 sm:py-10">
            <h1 className="sr-only">{fm.title}</h1>
            {fm.description && (
              <p className="max-w-3xl text-[1.0625rem] leading-relaxed text-fg-muted text-pretty sm:text-lg">{fm.description}</p>
            )}
          </Container>
        </div>
      ) : (
        <PageHeader
          title={fm.title}
          description={fm.description}
          eyebrow="Publication info"
          crumbs={crumbs}
        >
          {fm.updatedAt && (
            <p className="text-sm text-fg-subtle">
              Last updated <time dateTime={fm.updatedAt}>{formatDate(fm.updatedAt)}</time>
            </p>
          )}
        </PageHeader>
      )}
      <Container className="pt-8 sm:pt-12">
        {fm.featuredImage && (
          <figure className="mb-8 overflow-hidden rounded-xl border border-line bg-surface-sunken sm:mb-12">
            <Image
              src={fm.featuredImage.src}
              alt={fm.featuredImage.alt}
              width={fm.featuredImage.width}
              height={fm.featuredImage.height}
              sizes="(min-width: 1280px) 1200px, 100vw"
              priority
              className="aspect-[21/9] w-full object-cover"
              style={{ objectPosition: `${fm.featuredImage.focalX ?? 50}% ${fm.featuredImage.focalY ?? 50}%` }}
            />
          </figure>
        )}
        <div className="grid grid-cols-[minmax(0,1fr)] gap-8 lg:grid-cols-[14rem_minmax(0,1fr)] lg:gap-16">
          <nav aria-label="Publication info" className="min-w-0 lg:sticky lg:top-[calc(var(--spacing-header)+2rem)] lg:self-start">
            <ul className="-mx-1 flex gap-2 overflow-x-auto px-1 pb-2 [scrollbar-width:thin] lg:mx-0 lg:flex-col lg:gap-1 lg:overflow-visible lg:px-0 lg:pb-0">
              {siblings.map((p) => {
                const current = p.slug === page.slug;
                return (
                  <li key={p.slug} className="shrink-0">
                    <Link
                      href={p.path}
                      aria-current={current ? "page" : undefined}
                      className={`flex min-h-10 items-center whitespace-nowrap rounded-lg px-3 text-sm font-medium transition-colors lg:whitespace-normal ${
                        current
                          ? "bg-accent-soft text-accent-text"
                          : "text-fg-muted hover:bg-surface-sunken hover:text-fg"
                      }`}
                    >
                      {p.frontmatter.title}
                    </Link>
                  </li>
                );
              })}
            </ul>
          </nav>
          <div className="min-w-0 max-w-reading">
            <div className="article-body prose max-w-none dark:prose-invert">
              <Content components={mdxComponents} />
            </div>
            {after}
          </div>
        </div>
      </Container>
    </>
  );
}
