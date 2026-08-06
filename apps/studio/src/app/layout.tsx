import type { Metadata } from "next";
import { Geist } from "next/font/google";
import type { PropsWithChildren } from "react";
import { AppProviders } from "@/_app/providers";
import "@/_app/styles/globals.css";
import { EnvironmentScript } from "@/shared/config/index.server";
import { cn } from "@/shared/lib/cn";
import { Toaster } from "@/shared/ui/sonner";

const geist = Geist({
  subsets: ["latin"],
  variable: "--font-geist",
});

export const metadata: Metadata = {
  applicationName: "LookSee",
  title: {
    default: "LookSee",
    template: "%s · LookSee",
  },
  description: "Self-hosted video analytics and visual automation workflows.",
};

export default function RootLayout({ children }: PropsWithChildren) {
  return (
    <html className={cn("font-sans", geist.variable)} lang="en">
      <head>
        <EnvironmentScript />
      </head>

      <body className="min-h-screen antialiased">
        <AppProviders>{children}</AppProviders>

        <Toaster closeButton />
      </body>
    </html>
  );
}
