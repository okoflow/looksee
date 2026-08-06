import { Trash2Icon } from "lucide-react";
import { Button } from "@/shared/ui/button";
import { Hint } from "@/shared/ui/hint";

interface NodeInspectorHeaderProps {
  description: string;
  label: string;
  onDelete: () => void;
}

export function NodeInspectorHeader({ description, label, onDelete }: NodeInspectorHeaderProps) {
  return (
    <div className="flex h-12 items-center gap-1.5 border-b px-4">
      <span className="font-medium text-sm">{label}</span>

      <Hint hint={description} />

      <Button aria-label="Delete node" className="ml-auto" onClick={onDelete} size="icon-xs" variant="destructive">
        <Trash2Icon />
      </Button>
    </div>
  );
}
