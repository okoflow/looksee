"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/shared/lib/cn";
import { workflowMonitorRoute, workflowRoute } from "@/shared/routes";

interface WorkflowViewSwitcherProps {
  workflowId: string;
}

export function WorkflowViewSwitcher({ workflowId }: WorkflowViewSwitcherProps) {
  const pathname = usePathname();

  const views = [
    { href: workflowRoute(workflowId), label: "Editor" },
    { href: workflowMonitorRoute(workflowId), label: "Monitor" },
  ];

  return (
    <nav className="flex items-center gap-0.5 rounded-lg bg-muted p-0.5">
      {views.map((view) => {
        const isActive = pathname === view.href;

        return (
          <Link
            className={cn(
              "rounded-md px-3 py-1 font-medium text-sm transition",
              isActive ? "bg-background text-foreground shadow-xs" : "text-muted-foreground hover:text-foreground"
            )}
            href={view.href}
            key={view.href}
          >
            {view.label}
          </Link>
        );
      })}
    </nav>
  );
}
