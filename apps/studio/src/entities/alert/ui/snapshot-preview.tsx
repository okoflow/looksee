"use client";

import Image from "next/image";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/shared/ui/dialog";

interface SnapshotPreviewProps {
  caption: string;
  url: string;
}

export function SnapshotPreview({ caption, url }: SnapshotPreviewProps) {
  return (
    <Dialog>
      <DialogTrigger
        aria-label={`Open snapshot: ${caption}`}
        render={<button className="hover:border-ring shrink-0 rounded border transition" type="button" />}
      >
        <Image alt="" className="h-8 w-14 rounded object-cover" height={32} src={url} unoptimized width={56} />
      </DialogTrigger>

      <DialogContent className="sm:max-w-3xl">
        <DialogHeader>
          <DialogTitle>{caption}</DialogTitle>
        </DialogHeader>

        <Image alt={caption} className="h-auto w-full rounded-md" height={720} src={url} unoptimized width={1280} />
      </DialogContent>
    </Dialog>
  );
}
