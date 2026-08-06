import { generate as DefaultImage } from "fumadocs-ui/og";
import { notFound } from "next/navigation";
import { ImageResponse } from "next/og";
import { appName } from "@/lib/shared";
import { getPageImageUrl, source } from "@/lib/source";

export const revalidate = false;

export async function GET(
  _req: Request,
  { params }: RouteContext<"/[lang]/og/[...slug]">,
) {
  const { lang, slug } = await params;
  const page = source.getPage(slug.slice(0, -1), lang);

  if (!page) {
    return notFound();
  }

  return new ImageResponse(
    <DefaultImage
      title={page.data.title}
      description={page.data.description}
      site={appName}
    />,
    {
      width: 1200,
      height: 630,
    },
  );
}

export function generateStaticParams() {
  return source.getLanguages().flatMap(({ pages }) =>
    pages.map((page) => ({
      lang: page.locale,
      slug: getPageImageUrl(page).segments,
    })),
  );
}
