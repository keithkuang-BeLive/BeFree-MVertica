# BeLive M Vertica — published website migration

This repository preserves the production website published at
https://belive-m-vertica.keith-kuang.chatgpt.site/ .

## Important: production build, not original editable source

The recovered files are the actual published HTML, compiled JavaScript, stylesheet and local images. This is **not** a redesigned approximation. The original React/TypeScript component tree and original Vite configuration were not supplied by the website export interface. Do not mistake the compiled application for that editable source project. See `docs/migration-manifest.json` for source-map recovery results and exact asset checksums.

## Deploy on Vercel

Import `keithkuang-BeLive/BeFree-MVertica` and choose:

- Production branch: `main`
- Framework preset: **Other** (not Vite; this is already built)
- Root directory: repository root (`.`)
- Build command: `npm run build`
- Output directory: `dist`
- No application environment variables are required for this recovered static build.

`vercel.json` supplies the build settings and language-entry redirects for `/en`, `/zh` and `/ms` to the original `/?lang=en`, `/?lang=zh` and `/?lang=ms` URL format. The normal build only copies tracked local files. It does **not** scrape or proxy the ChatGPT-hosted website.

Only add `mvertica-freedom.belive.my` after verifying the Vercel preview. Configure the exact DNS record Vercel supplies for that subdomain; do not replace the `belive.my` root-domain records. A GitHub transfer does not itself make the custom domain live.

## Local preview

Node.js 22 or later is sufficient. There are no application npm dependencies.

```sh
npm ci
npm run dev
# http://127.0.0.1:4173
npm run build
npm run preview
```

## Files

- `public/index.html`: entry document; old-host Cloudflare challenge injection removed.
- `public/assets/`: original published application and media files.
- `scripts/build.mjs`: offline, dependency-free production build.
- `scripts/serve.mjs`: local preview with language routes.
- `scripts/complete-published-import.py`: explicit recovery entry point, including dynamic media and portable route aliases.
- `scripts/import-published-site.py`: underlying recovery utility; neither runs during normal deployment.
- `docs/migration-manifest.json`: provenance, hashes and dependencies.
- `docs/original-README.md`: previous repository documentation retained for reference.

## Preserved dependencies and limitations

External Google/CDN fonts, YouTube embeds and thumbnails, review destinations, email and WhatsApp links remain external as in the published site. WhatsApp links open a draft; automated verification must not send messages. Microsoft Clarity remains unconfigured unless its existing blank project identifier is explicitly configured.

For ongoing React/TypeScript development, obtain the original project export and replace this recovered build through a reviewed migration. Editing generated/minified JavaScript directly is not a maintainable substitute for original source.

## Language routing

The live published bundle uses `?lang=` and remembers the selector choice in local storage. The original README described pathname-aware language selection, but that was not present in the published bundle. This migration does not rewrite the application: `/en`, `/zh` and `/ms` redirect to its existing query-based language selector. Direct links therefore choose the requested language without changing the approved page design.
