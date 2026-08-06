"use client";

import { TriangleAlertIcon, UploadIcon, VideoOffIcon } from "lucide-react";
import { type ChangeEventHandler, useRef } from "react";
import { toast } from "sonner";
import { cn } from "@/shared/lib/cn";
import { formatBytes } from "@/shared/lib/format-bytes";
import { Button } from "@/shared/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/shared/ui/dialog";
import { Empty, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle } from "@/shared/ui/empty";
import { Skeleton } from "@/shared/ui/skeleton";
import { Spinner } from "@/shared/ui/spinner";
import { type Asset, assetContentUrl, useAssets, useUploadAsset } from "@/entities/asset";

const LOADING_TILE_KEYS = ["tile-1", "tile-2", "tile-3", "tile-4", "tile-5", "tile-6"];

interface AssetLibraryDialogProps {
  onOpenChange: (open: boolean) => void;
  onSelect: (key: string) => void;
  open: boolean;
  selectedKey: string;
}

export function AssetLibraryDialog({ onOpenChange, onSelect, open, selectedKey }: AssetLibraryDialogProps) {
  const assets = useAssets();

  const uploadAsset = useUploadAsset({
    onError: (error) => {
      toast.error(error.message);
    },
    onSuccess: (asset) => {
      onSelect(asset.key);
      onOpenChange(false);
      toast.success(`Uploaded ${asset.key}`);
    },
  });

  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const handleUploadClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange: ChangeEventHandler<HTMLInputElement> = (event) => {
    const file = event.currentTarget.files?.item(0);

    if (file) {
      uploadAsset.mutate(file);
    }

    event.currentTarget.value = "";
  };

  const handleSelect = (key: string) => {
    onSelect(key);
    onOpenChange(false);
  };

  return (
    <Dialog onOpenChange={onOpenChange} open={open}>
      <DialogContent className="sm:max-w-3xl">
        <DialogHeader>
          <DialogTitle>Video library</DialogTitle>

          <DialogDescription>Pick a video — the camera plays it on a loop as a live stream.</DialogDescription>
        </DialogHeader>

        <div className="no-scrollbar -mx-4 max-h-[70vh] overflow-y-auto px-4">
          <AssetLibraryContent assets={assets} onSelect={handleSelect} selectedKey={selectedKey} />
        </div>

        <DialogFooter>
          <input accept="video/*" className="hidden" onChange={handleFileChange} ref={fileInputRef} type="file" />

          <Button disabled={uploadAsset.isPending} onClick={handleUploadClick} type="button" variant="outline">
            {uploadAsset.isPending ? <Spinner data-icon="inline-start" /> : <UploadIcon data-icon="inline-start" />}
            Upload video
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

interface AssetLibraryContentProps {
  assets: ReturnType<typeof useAssets>;
  onSelect: (key: string) => void;
  selectedKey: string;
}

function AssetLibraryContent({ assets, onSelect, selectedKey }: AssetLibraryContentProps) {
  if (assets.isPending) {
    return (
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
        {LOADING_TILE_KEYS.map((tileKey) => {
          return <Skeleton className="aspect-video w-full rounded-lg" key={tileKey} />;
        })}
      </div>
    );
  }

  if (assets.data === undefined) {
    return (
      <Empty>
        <EmptyHeader>
          <EmptyMedia variant="icon">
            <TriangleAlertIcon />
          </EmptyMedia>

          <EmptyTitle>Could not load videos</EmptyTitle>

          <EmptyDescription>{assets.error.message}</EmptyDescription>
        </EmptyHeader>
      </Empty>
    );
  }

  if (assets.data.length === 0) {
    return (
      <Empty>
        <EmptyHeader>
          <EmptyMedia variant="icon">
            <VideoOffIcon />
          </EmptyMedia>

          <EmptyTitle>No videos yet</EmptyTitle>

          <EmptyDescription>Upload a video below to add it to the library.</EmptyDescription>
        </EmptyHeader>
      </Empty>
    );
  }

  return (
    <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
      {assets.data.map((asset) => {
        return (
          <AssetPreviewCard asset={asset} isSelected={asset.key === selectedKey} key={asset.key} onSelect={onSelect} />
        );
      })}
    </div>
  );
}

interface AssetPreviewCardProps {
  asset: Asset;
  isSelected: boolean;
  onSelect: (key: string) => void;
}

function AssetPreviewCard({ asset, isSelected, onSelect }: AssetPreviewCardProps) {
  const videoRef = useRef<HTMLVideoElement | null>(null);

  const handleClick = () => {
    onSelect(asset.key);
  };

  const handleMouseEnter = () => {
    videoRef.current?.play().catch(() => undefined);
  };

  const handleMouseLeave = () => {
    const video = videoRef.current;

    if (video) {
      video.pause();
      video.currentTime = 0;
    }
  };

  return (
    <button
      className={cn(
        "flex flex-col overflow-hidden rounded-lg border text-left outline-none transition-colors hover:border-ring/60 focus-visible:ring-2 focus-visible:ring-ring",
        isSelected && "border-ring ring-2 ring-ring/40"
      )}
      onClick={handleClick}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      type="button"
    >
      <video
        className="aspect-video w-full shrink-0 bg-black object-cover"
        loop
        muted
        playsInline
        preload="metadata"
        ref={videoRef}
        src={assetContentUrl(asset.key)}
      />

      <span className="flex w-full shrink-0 items-center gap-2 px-2 py-1.5">
        <span className="truncate text-xs">{asset.key}</span>

        <span className="ml-auto shrink-0 text-muted-foreground text-xs">{formatBytes(asset.size)}</span>
      </span>
    </button>
  );
}
