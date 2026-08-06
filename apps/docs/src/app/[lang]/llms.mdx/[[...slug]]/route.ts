import { notFound } from "next/navigation";
import { getLLMText, getPageMarkdownUrl, source } from "@/lib/source";

export const revalidate = false;

export async function GET(
  _req: Request,
  { params }: RouteContext<"/[lang]/llms.mdx/[[...slug]]">,
) {
  const { lang, slug } = await params;
  const page = source.getPage(slug?.slice(0, -1), lang);

  if (!page) {
    return notFound();
  }

  return new Response(await getLLMText(page), {
    headers: {
      "Content-Type": "text/markdown",
    },
  });
}

export function generateStaticParams() {
  return source.getLanguages().flatMap(({ pages }) =>
    pages.map((page) => ({
      lang: page.locale,
      slug: getPageMarkdownUrl(page).segments,
    })),
  );
}
