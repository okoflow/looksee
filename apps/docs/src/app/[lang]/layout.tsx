import { RootProvider } from "fumadocs-ui/provider/next";
import "../global.css";
import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { docsBasePath } from "@/lib/shared";
import { provider } from "@/lib/translations";

const inter = Inter({
  subsets: ["latin", "cyrillic"],
});

export const metadata: Metadata = {
  metadataBase: new URL("https://looksee.okoflow.com"),
};

export default async function Layout({
  params,
  children,
}: LayoutProps<"/[lang]">) {
  const { lang } = await params;

  const dir = lang === "he" ? "rtl" : "ltr";

  return (
    <html
      className={inter.className}
      dir={dir}
      lang={lang}
      suppressHydrationWarning
    >
      <body className="flex flex-col min-h-screen">
        <RootProvider
          dir={dir}
          i18n={provider(lang)}
          search={{ options: { api: `${docsBasePath}/api/search` } }}
        >
          {children}
        </RootProvider>
      </body>
    </html>
  );
}
