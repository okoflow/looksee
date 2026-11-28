import type { PropsWithChildren } from "react";

export default function AuthLayout({ children }: PropsWithChildren) {
  return (
    <main className="bg-muted/30 flex min-h-screen items-center justify-center p-6">
      <div className="w-full max-w-sm">{children}</div>
    </main>
  );
}
