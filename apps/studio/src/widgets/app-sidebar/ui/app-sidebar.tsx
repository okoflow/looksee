"use client";

import { BookOpenIcon, KeyRoundIcon, LogOutIcon, StarIcon, WorkflowIcon } from "lucide-react";
import Image from "next/image";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { getDocsUrl, getGithubUrl } from "@/shared/config";
import logomark from "@/shared/ui/logomark.svg";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuAction,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarRail,
} from "@/shared/ui/sidebar";
import { useLogout, useSessionUser } from "@/entities/session";
import { formatStars, useGithubStars } from "../lib/use-github-stars";
import { GithubMarkIcon } from "./github-mark-icon";

export function AppSidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const githubUrl = getGithubUrl();
  const stars = useGithubStars(githubUrl);
  const session = useSessionUser();

  const logout = useLogout({
    onSuccess: () => {
      router.push("/login");
      router.refresh();
    },
  });

  return (
    <Sidebar collapsible="icon">
      <SidebarHeader>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton render={<Link href="/" />} tooltip="LookSee">
              <Image alt="LookSee" className="size-5 shrink-0" src={logomark} />

              <span className="font-semibold">LookSee</span>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>

      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupContent>
            <SidebarMenu>
              <SidebarMenuItem>
                <SidebarMenuButton
                  isActive={!pathname.startsWith("/credentials")}
                  render={<Link href="/" />}
                  tooltip="Workflows"
                >
                  <WorkflowIcon />

                  <span>Workflows</span>
                </SidebarMenuButton>
              </SidebarMenuItem>

              <SidebarMenuItem>
                <SidebarMenuButton
                  isActive={pathname.startsWith("/credentials")}
                  render={<Link href="/credentials" />}
                  tooltip="Credentials"
                >
                  <KeyRoundIcon />

                  <span>Credentials</span>
                </SidebarMenuButton>
              </SidebarMenuItem>
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>

      <SidebarFooter>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton
              render={<a href={getDocsUrl()} rel="noreferrer" target="_blank" />}
              tooltip="Documentation"
            >
              <BookOpenIcon />

              <span>Documentation</span>
            </SidebarMenuButton>
          </SidebarMenuItem>

          <SidebarMenuItem>
            <SidebarMenuButton render={<a href={githubUrl} rel="noreferrer" target="_blank" />} tooltip="GitHub">
              <GithubMarkIcon />

              <span>GitHub</span>

              {typeof stars.data === "number" ? (
                <span className="ml-auto flex items-center gap-1 text-muted-foreground text-xs">
                  <StarIcon className="size-3" />

                  {formatStars(stars.data)}
                </span>
              ) : null}
            </SidebarMenuButton>
          </SidebarMenuItem>

          {session.data ? (
            <SidebarMenuItem>
              <SidebarMenuButton className="pointer-events-none" tooltip={session.data.email}>
                <span className="flex size-4 shrink-0 items-center justify-center rounded-full bg-primary/15 font-medium text-[10px] text-primary uppercase">
                  {session.data.name.charAt(0)}
                </span>

                <span className="truncate">{session.data.name}</span>
              </SidebarMenuButton>

              <SidebarMenuAction aria-label="Sign out" onClick={() => logout.mutate()} title="Sign out">
                <LogOutIcon />
              </SidebarMenuAction>
            </SidebarMenuItem>
          ) : null}
        </SidebarMenu>
      </SidebarFooter>

      <SidebarRail />
    </Sidebar>
  );
}
