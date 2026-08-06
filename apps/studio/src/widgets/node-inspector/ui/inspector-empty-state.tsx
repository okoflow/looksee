export function NodeInspectorEmpty() {
  return (
    <aside className="flex h-full w-editor-inspector shrink-0 flex-col overflow-hidden rounded-xl border bg-card">
      <div className="flex h-12 items-center border-b px-4 font-medium text-sm">Inspector</div>

      <div className="flex flex-1 items-center justify-center px-6 text-center text-muted-foreground text-sm">
        Select a node to edit its configuration.
      </div>
    </aside>
  );
}
