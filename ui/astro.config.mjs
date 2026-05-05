import { defineConfig } from 'astro/config';
import svelte from '@astrojs/svelte';
import tailwindcss from '@tailwindcss/vite';

// https://docs.astro.build/en/reference/configuration-reference/
export default defineConfig({
  // base: '/app' so production build works under FastAPI's /app mount point.
  // Dev server will be at http://localhost:4321/app
  base: '/app',

  // All pages are statically rendered at build time.
  output: 'static',

  integrations: [
    svelte(),
  ],

  vite: {
    plugins: [
      tailwindcss(),
    ],
  },
});
