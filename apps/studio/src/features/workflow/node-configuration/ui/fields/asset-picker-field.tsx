"use client";

import { FilmIcon } from "lucide-react";
import { useState } from "react";
import { cn } from "@/shared/lib/cn";
import { Button } from "@/shared/ui/button";
import { Field, FieldDescription } from "@/shared/ui/field";
import { HintedFieldLabel } from "@/shared/ui/hint";
import { useAssets } from "@/entities/asset";
import { AssetLibraryDialog } from "./asset-library-dialog";

interface AssetPickerFieldProps {
  id: string;
  onValueChange: (key: string) => void;
  value: string;
}

export function AssetPickerField({ id, onValueChange, value }: AssetPickerFieldProps) {
  const [isLibraryOpen, setIsLibraryOpen] = useState(false);

  const assets = useAssets();

  const isValueMissing =
    value.length > 0 &&
    assets.data !== undefined &&
    !assets.data.some((asset) => {
      return asset.key === value;
    });

  const handleOpenLibrary = () => {
    setIsLibraryOpen(true);
  };

  return (
    <Field>
      <HintedFieldLabel
        hint="Videos live in the asset store bucket; the selected one plays on a loop as a live stream."
        htmlFor={id}
      >
        Video
      </HintedFieldLabel>

      <Button
        className="w-full justify-between font-normal"
        id={id}
        onClick={handleOpenLibrary}
        type="button"
        variant="outline"
      >
        <span className={cn("truncate", value.length === 0 && "text-muted-foreground")}>
          {value.length > 0 ? value : "Choose a video…"}
        </span>

        <FilmIcon className="text-muted-foreground" data-icon="inline-end" />
      </Button>

      {isValueMissing ? <FieldDescription>This video is no longer in the asset store.</FieldDescription> : null}

      <AssetLibraryDialog
        onOpenChange={setIsLibraryOpen}
        onSelect={onValueChange}
        open={isLibraryOpen}
        selectedKey={value}
      />
    </Field>
  );
}
