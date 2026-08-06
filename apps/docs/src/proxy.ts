import { createI18nMiddleware } from "fumadocs-core/i18n/middleware";
import { isMarkdownPreferred, rewritePath } from "fumadocs-core/negotiation";
import {
  type NextFetchEvent,
  type NextRequest,
  NextResponse,
} from "next/server";
import { i18n } from "@/lib/i18n";
import { docsContentRoute } from "@/lib/shared";

const EXCLUDED =
  /^\/(?:api\/|_next\/|icon\.svg$|apple-icon\.png$|favicon\.ico$)/;

const { rewrite: rewriteDocs } = rewritePath(
  "{/*path}",
  `${docsContentRoute}{/*path}/content.md`,
);
const { rewrite: rewriteSuffix } = rewritePath(
  "{/*path}.md",
  `${docsContentRoute}{/*path}/content.md`,
);

const i18nMiddleware = createI18nMiddleware(i18n);

function splitLocale(pathname: string): [string, string] {
  const [, first = "", ...rest] = pathname.split("/");

  if ((i18n.languages as readonly string[]).includes(first)) {
    return [first, `/${rest.join("/")}`];
  }

  return [i18n.defaultLanguage, pathname];
}

export default function proxy(request: NextRequest, event: NextFetchEvent) {
  const { basePath } = request.nextUrl;
  const raw = request.nextUrl.pathname;

  if (EXCLUDED.test(raw)) {
    return NextResponse.next();
  }

  const [locale, pathname] = splitLocale(raw);

  const suffixed = rewriteSuffix(pathname);

  if (suffixed) {
    return NextResponse.rewrite(
      new URL(`${basePath}/${locale}${suffixed}`, request.nextUrl),
    );
  }

  if (isMarkdownPreferred(request)) {
    const rewritten = rewriteDocs(pathname);

    if (rewritten) {
      return NextResponse.rewrite(
        new URL(`${basePath}/${locale}${rewritten}`, request.nextUrl),
        {
          headers: { Vary: "Accept" },
        },
      );
    }
  }

  if (raw === "" || raw === "/") {
    return NextResponse.rewrite(
      new URL(`${basePath}/${locale}`, request.nextUrl),
    );
  }

  return i18nMiddleware(request, event);
}
