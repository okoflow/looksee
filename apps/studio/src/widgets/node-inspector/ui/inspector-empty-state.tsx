export function NodeInspectorEmpty() {
  return (
    <aside className="w-editor-inspector bg-card flex h-full shrink-0 flex-col overflow-hidden rounded-xl border">
      <div className="flex h-12 items-center border-b px-4 text-sm font-medium">Inspector</div>

      <div className="text-muted-foreground flex flex-1 items-center justify-center px-6 text-center text-sm">
        Select a node to edit its configuration.
      </div>
    </aside>
  );
}
