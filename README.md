# M Vertica by BeLive

React + TypeScript + Vite marketing website. Production domain: mvertica-freedom.belive.my.

## Local use

Run `npm ci`, then `npm run dev`. Run `npm run build` for production.

## Vercel

Import this repository as a Vite project. Build: `npm run build`. Output: `dist`.
Add `mvertica-freedom.belive.my` to the project and configure the exact DNS record Vercel supplies. Do not replace the belive.my root-domain records.

Language routes: `/en` (English), `/zh` (Simplified Chinese), `/ms` (Bahasa Melayu). Direct routes override remembered language preferences. The selector keeps the route in sync. Existing `?lang=` links remain accepted at the root.

All editorial changes apply to all three languages unless explicitly requested otherwise. Chinese has separate fictional lifestyle images. All page motion is disabled. WhatsApp opens a draft only. Microsoft Clarity remains inactive until a valid project ID is configured.

## Publishing status

This package is prepared for deployment; the custom domain is not live until Vercel deployment and DNS verification succeed.
