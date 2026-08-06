import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import type { PropsWithChildren } from "react";
import { SidebarInset, SidebarProvider } from "@/shared/ui/sidebar";
import { fetchServerAuthStatus, fetchServerSessionUser } from "@/entities/session/index.server";
import { AppSidebar } from "@/widgets/app-sidebar";

export default async function StudioLayout({ children }: PropsWithChildren) {
  const cookieStore = await cookies();

  const user = await fetchServerSessionUser(cookieStore.toString());
  if (user === null) {
    const status = await fetchServerAuthStatus();

    redirect(status.requires_setup ? "/setup" : "/login");
  }

  const defaultOpen = cookieStore.get("sidebar_state")?.value === "true";

  return (
    <SidebarProvider defaultOpen={defaultOpen}>
      <AppSidebar />

      <SidebarInset>{children}</SidebarInset>
    </SidebarProvider>
  );
}
