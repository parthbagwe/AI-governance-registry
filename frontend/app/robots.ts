import type { MetadataRoute } from "next";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000";

/**
 * robots.txt, generated rather than checked in so the sitemap URL follows
 * whatever the deployment actually is.
 *
 * Everything is crawlable. There's nothing private here and nothing worth
 * hiding — and a portfolio project that blocks indexing is working against
 * the only reason it's public.
 */
export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: "*",
      allow: "/",
    },
    sitemap: `${SITE_URL}/sitemap.xml`,
  };
}
