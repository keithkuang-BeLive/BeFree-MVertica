#!/usr/bin/env python3
"""Recover this owner's published website without redesigning or rebuilding its UI.
Run explicitly; a normal npm build never calls the old website.
"""
from __future__ import annotations
import concurrent.futures
import datetime as dt
import hashlib
import json
import re
import shutil
import time
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import unquote, urljoin, urlsplit
from urllib.request import Request, urlopen

ORIGIN = 'https://belive-m-vertica.keith-kuang.chatgpt.site'
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'public'
LIMIT = 30 * 1024 * 1024
EXTENSIONS = ('.js', '.css', '.png', '.jpg', '.jpeg', '.webp', '.svg', '.gif', '.avif', '.ico', '.json', '.mp4', '.webm', '.pdf', '.woff', '.woff2', '.ttf', '.txt')

class References(HTMLParser):
    def __init__(self):
        super().__init__()
        self.refs = set()
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        for key in ('src', 'poster'):
            if a.get(key): self.refs.add(a[key])
        if tag == 'link' and a.get('href'): self.refs.add(a['href'])
        if a.get('srcset'):
            self.refs.update(x.strip().split(' ')[0] for x in a['srcset'].split(','))

def fetch(url: str):
    for attempt in range(3):
        try:
            req = Request(url, headers={'User-Agent': 'Mozilla/5.0 BeLive-Owned-Site-Migration', 'Accept-Encoding': 'identity'})
            with urlopen(req, timeout=40) as response:
                raw = response.read(LIMIT + 1)
                if len(raw) > LIMIT: raise ValueError(f'Resource exceeds size limit: {url}')
                return raw, response.headers.get_content_type()
        except HTTPError:
            raise
        except Exception:
            if attempt == 2: raise
            time.sleep(1 + attempt)

def local_ref(value: str, base: str):
    value = value.strip().replace('\\/', '/')
    if not value or value.startswith(('data:', '#', 'mailto:', 'tel:', 'javascript:')): return None
    full = urljoin(base, value)
    parsed = urlsplit(full)
    if parsed.scheme != 'https' or parsed.netloc != urlsplit(ORIGIN).netloc: return None
    path = parsed.path
    if path.startswith('/cdn-cgi/') or '..' in unquote(path).split('/'): return None
    if not path.lower().endswith(EXTENSIONS): return None
    return path

def references(text: str, base: str, html=False):
    found = set()
    if html:
        parser = References(); parser.feed(text); found |= parser.refs
    found.update(re.findall(r'''["'`]((?:/assets/|\./|\.\./)[^"'`\s<>\\]+)["'`]''', text))
    found.update(re.findall(r'''url\(\s*["']?([^\s)"']+)["']?\s*\)''', text))
    found.update(re.findall(r'''["'](https?://[^"'\s<>]+)["']''', text))
    return {p for r in found if (p := local_ref(r, base))}

def main():
    OUT.mkdir(exist_ok=True)
    (ROOT / 'docs').mkdir(exist_ok=True)
    raw, mime = fetch(ORIGIN + '/')
    original_html = raw.decode('utf-8')
    if 'id="root"' not in original_html or '/assets/' not in original_html:
        raise RuntimeError('The public response is not the expected application document.')
    removed = []
    def sanitize_script(match):
        block = match.group(0)
        if '__CF$cv$params' in block or '/cdn-cgi/challenge-platform/' in block:
            removed.append('Removed old hosting provider Cloudflare challenge injection from index.html.')
            return ''
        return block
    html = re.sub(r'<script\b[^>]*>.*?</script>', sanitize_script, original_html, flags=re.S|re.I)
    html = html.replace(ORIGIN + '/assets/', '/assets/')
    (OUT / 'index.html').write_text(html, encoding='utf-8')
    pending = references(html, ORIGIN + '/', html=True)
    downloaded = {}
    text_resources = {}
    while pending:
        if len(downloaded) + len(pending) > 350: raise RuntimeError('Unexpectedly large asset graph.')
        batch = sorted(pending - downloaded.keys())
        if not batch: break
        pending = set()
        def one(path):
            asset, asset_type = fetch(ORIGIN + path)
            if asset_type == 'text/html': raise RuntimeError('Missing asset returned HTML instead: ' + path)
            return path, asset, asset_type
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
            for path, asset, asset_type in pool.map(one, batch):
                dest = OUT / path.lstrip('/')
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(asset)
                downloaded[path] = {'path': 'public' + path, 'bytes': len(asset), 'sha256': hashlib.sha256(asset).hexdigest(), 'contentType': asset_type}
                print('RECOVERED', path, len(asset), asset_type, flush=True)
                if path.endswith(('.js', '.css', '.json', '.svg')):
                    text = asset.decode('utf-8')
                    text_resources[path] = text
                    pending |= references(text, ORIGIN + path)
        pending -= downloaded.keys()
    source_maps = []
    for path, text in text_resources.items():
        if not path.endswith('.js'): continue
        hints = re.findall(r'sourceMappingURL=([^\s*]+)', text)
        candidates = hints or [path + '.map']
        for hint in candidates:
            map_url = urljoin(ORIGIN + path, hint)
            if urlsplit(map_url).netloc != urlsplit(ORIGIN).netloc: continue
            try:
                map_raw, map_type = fetch(map_url)
                obj = json.loads(map_raw)
                if not isinstance(obj, dict) or 'sources' not in obj: continue
                map_dest = ROOT / 'docs' / 'source-maps' / (Path(path).name + '.map')
                map_dest.parent.mkdir(exist_ok=True)
                map_dest.write_bytes(map_raw)
                source_maps.append({'url': map_url, 'sources': obj['sources'], 'includesSourceContents': bool(obj.get('sourcesContent'))})
            except (HTTPError, ValueError, UnicodeError):
                pass
    js = '\n'.join(v for k, v in text_resources.items() if k.endswith('.js'))
    external_urls = sorted(set(re.findall(r'''https?://[^\s"'`<>\\)]+''', '\n'.join(text_resources.values()))))
    if (ROOT / 'README.md').exists() and not (ROOT / 'docs/original-README.md').exists():
        shutil.copy2(ROOT / 'README.md', ROOT / 'docs/original-README.md')
    package = {'name': 'belive-mvertica', 'version': '1.0.0', 'private': True, 'type': 'module', 'description': 'Preserved published BeLive M Vertica website', 'scripts': {'build': 'node scripts/build.mjs', 'dev': 'node scripts/serve.mjs', 'preview': 'node scripts/serve.mjs dist'}, 'engines': {'node': '>=22'}}
    (ROOT / 'package.json').write_text(json.dumps(package, indent=2) + '\n')
    (ROOT / '.gitignore').write_text('node_modules/\ndist/\n.vercel/\n.verification-tools/\n.env\n.env.*\n!.env.example\n')
    vercel = {'$schema': 'https://openapi.vercel.sh/vercel.json', 'framework': None, 'buildCommand': 'npm run build', 'outputDirectory': 'dist', 'rewrites': [{'source': '/en', 'destination': '/index.html'}, {'source': '/zh', 'destination': '/index.html'}, {'source': '/ms', 'destination': '/index.html'}, {'source': '/en/', 'destination': '/index.html'}, {'source': '/zh/', 'destination': '/index.html'}, {'source': '/ms/', 'destination': '/index.html'}]}
    (ROOT / 'vercel.json').write_text(json.dumps(vercel, indent=2) + '\n')
    (ROOT / 'scripts/build.mjs').write_text("import { cp, mkdir, rm, stat } from 'node:fs/promises';\nawait stat('public/index.html');\nawait rm('dist', { recursive: true, force: true });\nawait mkdir('dist', { recursive: true });\nawait cp('public', 'dist', { recursive: true });\nconsole.log('Built published website into dist without downloading from the old host.');\n")
    (ROOT / 'scripts/serve.mjs').write_text("import http from 'node:http';\nimport { readFile, stat } from 'node:fs/promises';\nimport path from 'node:path';\nconst root = path.resolve(process.argv[2] || 'public');\nconst port = Number(process.env.PORT || 4173);\nconst types = {'.html':'text/html; charset=utf-8','.js':'text/javascript; charset=utf-8','.css':'text/css; charset=utf-8','.svg':'image/svg+xml','.webp':'image/webp','.png':'image/png','.jpg':'image/jpeg','.jpeg':'image/jpeg','.json':'application/json','.ico':'image/x-icon','.mp4':'video/mp4','.woff':'font/woff','.woff2':'font/woff2'};\nhttp.createServer(async (req, res) => {\n try {\n  const url = new URL(req.url, 'http://localhost');\n  let pathname = decodeURIComponent(url.pathname);\n  if (/^\\/(?:en|zh|ms)?\\/?$/.test(pathname)) pathname = '/index.html';\n  const file = path.resolve(root, '.' + pathname);\n  if (!file.startsWith(root + path.sep)) { res.writeHead(403); res.end(); return; }\n  if (!(await stat(file)).isFile()) throw new Error('Not a file');\n  const body = await readFile(file);\n  res.writeHead(200, {'Content-Type': types[path.extname(file)] || 'application/octet-stream', 'Cache-Control':'no-cache'});\n  res.end(req.method === 'HEAD' ? undefined : body);\n } catch { res.writeHead(404); res.end('Not found'); }\n}).listen(port, '127.0.0.1', () => console.log('Website: http://127.0.0.1:' + port));\n")
    report = {'source': ORIGIN, 'recoveredAtUtc': dt.datetime.now(dt.timezone.utc).isoformat(), 'recoveryType': 'published-production-build', 'originalEditableProjectRecovered': bool(source_maps), 'sourceMaps': source_maps, 'assetCount': len(downloaded), 'assetBytes': sum(v['bytes'] for v in downloaded.values()), 'changesToPublishedHtml': removed, 'applicationJavaScriptAndCssModified': False, 'assets': sorted(downloaded.values(), key=lambda a:a['path']), 'externalUrls': external_urls, 'verificationStatus': 'Browser checks must be recorded separately.'}
    (ROOT / 'docs/migration-manifest.json').write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n')
    (ROOT / 'README.md').write_text('''# BeLive M Vertica — published website migration\n\nThis repository preserves the production website published at\nhttps://belive-m-vertica.keith-kuang.chatgpt.site/ .\n\n## Important: production build, not original editable source\n\nThe recovered files are the actual published HTML, compiled JavaScript, stylesheet and local images. This is **not** a redesigned approximation. The original React/TypeScript component tree and original Vite configuration were not supplied by the website export interface. Do not mistake the compiled application for that editable source project. See `docs/migration-manifest.json` for source-map recovery results and exact asset checksums.\n\n## Deploy on Vercel\n\nImport `keithkuang-BeLive/BeFree-MVertica` and choose:\n\n- Production branch: `main`\n- Framework preset: **Other** (not Vite; this is already built)\n- Root directory: repository root (`.`)\n- Build command: `npm run build`\n- Output directory: `dist`\n- No application environment variables are required for this recovered static build.\n\n`vercel.json` supplies the build settings and direct-route rewrites for `/en`, `/zh` and `/ms`. The normal build only copies tracked local files. It does **not** scrape or proxy the ChatGPT-hosted website.\n\nOnly add `mvertica-freedom.belive.my` after verifying the Vercel preview. Configure the exact DNS record Vercel supplies for that subdomain; do not replace the `belive.my` root-domain records. A GitHub transfer does not itself make the custom domain live.\n\n## Local preview\n\nNode.js 22 or later is sufficient. There are no application npm dependencies.\n\n```sh\nnpm ci\nnpm run dev\n# http://127.0.0.1:4173\nnpm run build\nnpm run preview\n```\n\n## Files\n\n- `public/index.html`: entry document; old-host Cloudflare challenge injection removed.\n- `public/assets/`: original published application and media files.\n- `scripts/build.mjs`: offline, dependency-free production build.\n- `scripts/serve.mjs`: local preview with language routes.\n- `scripts/import-published-site.py`: explicit one-time recovery utility, not part of normal deployment.\n- `docs/migration-manifest.json`: provenance, hashes and dependencies.\n- `docs/original-README.md`: previous repository documentation retained for reference.\n\n## Preserved dependencies and limitations\n\nExternal Google/CDN fonts, YouTube embeds and thumbnails, review destinations, email and WhatsApp links remain external as in the published site. WhatsApp links open a draft; automated verification must not send messages. Microsoft Clarity remains unconfigured unless its existing blank project identifier is explicitly configured.\n\nFor ongoing React/TypeScript development, obtain the original project export and replace this recovered build through a reviewed migration. Editing generated/minified JavaScript directly is not a maintainable substitute for original source.\n''', encoding='utf-8')
    print('MIGRATION_SUMMARY', json.dumps({k:report[k] for k in ('assetCount','assetBytes','originalEditableProjectRecovered','applicationJavaScriptAndCssModified')}), flush=True)
    print('EXTERNAL_URLS', json.dumps(external_urls, ensure_ascii=False), flush=True)

if __name__ == '__main__':
    main()
