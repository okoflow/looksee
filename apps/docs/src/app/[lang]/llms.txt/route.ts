import { llms } from "fumadocs-core/source";
import { docsBasePath } from "@/lib/shared";
import { source } from "@/lib/source";

export const revalidate = false;

export async function GET(
  _req: Request,
  { params }: RouteContext<"/[lang]/llms.txt">,
) {
  const { lang } = await params;

  const index = llms(source)
    .index(lang)
    .replaceAll("](/", `](${docsBasePath}/`);

  return new Response(index);
}
