"use client";

import { InfoIcon } from "lucide-react";
import type { PropsWithChildren, ReactNode } from "react";
import { FieldLabel } from "@/shared/ui/field";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/shared/ui/tooltip";

interface HintProps {
  hint: ReactNode;
}

function Hint({ hint }: HintProps) {
  return (
    <Tooltip>
      <TooltipTrigger aria-label="More details" className="text-muted-foreground transition hover:text-foreground">
        <InfoIcon className="size-3.5" />
      </TooltipTrigger>

      <TooltipContent>{hint}</TooltipContent>
    </Tooltip>
  );
}

interface HintedFieldLabelProps extends PropsWithChildren {
  hint?: ReactNode;
  htmlFor?: string;
  id?: string;
}

function HintedFieldLabel({ children, hint, htmlFor, id }: HintedFieldLabelProps) {
  if (hint === undefined) {
    return (
      <FieldLabel htmlFor={htmlFor} id={id}>
        {children}
      </FieldLabel>
    );
  }

  return (
    <div className="flex items-center gap-1.5">
      <FieldLabel htmlFor={htmlFor} id={id}>
        {children}
      </FieldLabel>

      <Hint hint={hint} />
    </div>
  );
}

export { Hint, HintedFieldLabel };
