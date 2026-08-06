"use client";

import { CircleCheckIcon, InfoIcon, Loader2Icon, OctagonXIcon, TriangleAlertIcon } from "lucide-react";
import type { CSSProperties } from "react";
import { Toaster as Sonner, type ToasterProps } from "sonner";

const toasterIcons = {
  success: <CircleCheckIcon className="size-4 text-emerald-600" />,
  info: <InfoIcon className="size-4 text-sky-600" />,
  warning: <TriangleAlertIcon className="size-4 text-amber-600" />,
  error: <OctagonXIcon className="size-4 text-red-600" />,
  loading: <Loader2Icon className="size-4 animate-spin" />,
};

const toasterStyle: CSSProperties = {
  "--normal-bg": "var(--popover)",
  "--normal-text": "var(--popover-foreground)",
  "--normal-border": "var(--border)",
  "--border-radius": "var(--radius)",
} as CSSProperties;

function Toaster(props: Omit<ToasterProps, "theme">) {
  return <Sonner className="toaster group" icons={toasterIcons} style={toasterStyle} {...props} theme="light" />;
}

export { Toaster };
