import type { Metadata } from "next";
import { absoluteUrl, site } from "@/config/site";
import { ogSize } from "@/lib/og/card";
import { getSiteConfig } from "@/lib/site-config";

/** Search results cut titles at roughly 60 characters (about 600px). */
export const TITLE_BUDGET = 60;

/**
 * The root layout's `%s | Site` template, unless the suffix would push the title past the budget: then the
 * bare title, so the words that describe the page are the ones shown rather than a truncated brand name.
 */
export async function seoTitle(title: string): Promise<Metadata["title"]> {
  const { config } = await getSiteConfig();
  const full = `${title} ${config.seo.titleSeparator} ${config.general.siteName}`;
  return full.length > TITLE_BUDGET ? { absolute: title } : title;
}

/**
 * The site-wide card (src/app/opengraph-image.tsx). A page that sets its own `openGraph` replaces the root
 * one, file-based image included, so pages without an image of their own pass this explicitly.
 */
export function defaultShareImage(): ShareImage {
  return { url: absoluteUrl("/opengraph-image"), ...ogSize, alt: site.name };
}

type ShareImage = { url: string; width?: number; height?: number; alt?: string };

/** Open Graph images plus the matching large Twitter/X card, falling back to the site-wide card. */
export function shareImages(image?: ShareImage): { og: ShareImage[]; twitter: NonNullable<Metadata["twitter"]> } {
  const img = image ?? defaultShareImage();
  return { og: [img], twitter: { card: "summary_large_image", images: [img.url] } };
}
