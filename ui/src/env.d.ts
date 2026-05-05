/// <reference path="../.astro/types.d.ts" />
/// <reference path="../node_modules/@astrojs/svelte/svelte-shims.d.ts" />

// Tell TypeScript that *.svelte files are valid modules.
// The Astro language server transforms them at runtime; this declaration
// satisfies the type-checker when the LS plugin hasn't loaded yet.
declare module '*.svelte' {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const component: any;
  export default component;
}

interface ImportMetaEnv {
  readonly PUBLIC_API_BASE_URL: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
