import { docs } from "collections/server";
import { loader } from "fumadocs-core/source";
import { lucideIconsPlugin } from "fumadocs-core/source/lucide-icons";
import { i18n } from "./i18n";
import { docsBasePath, docsContentRoute, docsImageRoute } from "./shared";

export const source = loader({
  baseUrl: "/",
  i18n,
  source: docs.toFumadocsSource(),
  plugins: [lucideIconsPlugin()],
});

function urlLocale(page: (typeof source)["$inferPage"]) {
  return page.locale === i18n.defaultLanguage ? undefined : page.locale;
}

function pageAssetUrl(
  page: (typeof source)["$inferPage"],
  route: string,
  file: string,
) {
  const segments = [...page.slugs, file];

  return {
    segments,
    url:
      docsBasePath +
      "/" +
      [urlLocale(page), ...route.split("/"), ...segments]
        .filter(Boolean)
        .join("/"),
  };
}

export function getPageImageUrl(page: (typeof source)["$inferPage"]) {
  return pageAssetUrl(page, docsImageRoute, "image.png");
}

export function getPageMarkdownUrl(page: (typeof source)["$inferPage"]) {
  return pageAssetUrl(page, docsContentRoute, "content.md");
}

export async function getLLMText(page: (typeof source)["$inferPage"]) {
  const processed = await page.data.getText("processed");

  return `# ${page.data.title} (${docsBasePath}${page.url})

${processed}`;
}
