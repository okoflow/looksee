import type { ReactNode } from "react";
import { Badge } from "@/shared/ui/badge";

interface PresetCardProps {
  description: string;
  icon: ReactNode;
  onClick: () => void;
  title: string;
  vertical?: string;
}

export function PresetCard({ description, icon, onClick, title, vertical }: PresetCardProps) {
  return (
    <button
      className="flex flex-col gap-1 rounded-md border bg-card p-3 text-left transition hover:border-ring"
      onClick={onClick}
      type="button"
    >
      <span className="flex w-full items-center gap-2">
        <span className="text-muted-foreground">{icon}</span>

        <span className="font-medium text-sm">{title}</span>

        {vertical ? (
          <Badge className="ml-auto" variant="secondary">
            {vertical}
          </Badge>
        ) : null}
      </span>

      <span className="text-muted-foreground text-xs">{description}</span>
    </button>
  );
}
