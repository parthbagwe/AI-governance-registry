import type { MetadataRoute } from "next";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000";

/**
 * Only the two static routes.
 *
 * Model detail pages are deliberately excluded: listing them would mean
 * fetching the registry at build time, which makes the sitemap a hard
 * dependency on the API being up, and the URLs would go stale the moment a
 * model is registered or retired. A sitemap listing pages that 404 is worse
 * than a short one.
 */
export default function sitemap(): MetadataRoute.Sitemap {
  const now = new Date();
  return [
    { url: SITE_URL, lastModified: now, changeFrequency: "weekly", priority: 1 },
    {
      url: `${SITE_URL}/assess`,
      lastModified: now,
      changeFrequency: "monthly",
      priority: 0.8,
    },
    {
      url: `${SITE_URL}/privacy`,
      lastModified: now,
      changeFrequency: "yearly",
      priority: 0.2,
    },
  ];
}
