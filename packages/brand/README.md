# @looksee/brand

Canonical LookSee brand assets. Single source of truth — edit here only.

Use from an app (each app is its own pnpm root, no workspace needed):

```bash
pnpm add @looksee/brand@file:../../packages/brand
```

```tsx
import logomark from "@looksee/brand/logomark.svg";
```

Files that must exist at a fixed URL (favicons, `og.png`) cannot be imported
from a package — copy those into the app's `public/` and keep the source here.
