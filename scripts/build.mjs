import { cp, mkdir, rm, stat } from 'node:fs/promises';
await stat('public/index.html');
await rm('dist', { recursive: true, force: true });
await mkdir('dist', { recursive: true });
await cp('public', 'dist', { recursive: true });
console.log('Built published website into dist without downloading from the old host.');
