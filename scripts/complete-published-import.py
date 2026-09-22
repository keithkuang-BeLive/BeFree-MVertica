#!/usr/bin/env python3
"""Application-specific entry point for recovering the published M Vertica site.
Resolve dynamic media paths without executing or modifying its application.
"""
import importlib.util
import json
import re
from pathlib import Path

spec = importlib.util.spec_from_file_location('published_import', Path(__file__).with_name('import-published-site.py'))
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)
original_references = base.references

def complete_references(text, url, html=False):
    refs = original_references(text, url, html)
    for literal in re.findall(r'''["'`](/[^/"'`\s<>\\][^"'`\s<>\\]*)["'`]''', text):
        path = base.local_ref(literal, url)
        if path:
            refs.add(path)
    if url.endswith('.js') and '"/assets/"' in text:
        # Confirmed source pattern: Se="/assets/"; src:Se+"filename.webp".
        for filename in re.findall(r'''["']([A-Za-z][A-Za-z0-9_.-]*\.(?:png|jpe?g|webp|avif|gif|svg|ico))["']''', text):
            refs.add('/assets/' + filename)
        # Confirmed source transformation for Chinese-only lifestyle images.
        if 'function Qi(' in text and '-zh.webp' in text:
            for filename in re.findall(r'''Qi\(["']([^"']+\.(?:png|webp))["']\)''', text):
                refs.add('/assets/' + re.sub(r'\.(?:png|webp)$', '-zh.webp', filename))
    return refs

base.references = complete_references
base.main()

# The actual published app selects languages from ?lang=, not pathname.
# Route aliases redirect to that existing format; application bundles stay intact.
config_path = base.ROOT / 'vercel.json'
config = json.loads(config_path.read_text())
config.pop('rewrites', None)
config['redirects'] = [
    {'source': '/' + language + suffix, 'destination': '/?lang=' + language, 'permanent': False}
    for language in ('en', 'zh', 'ms') for suffix in ('', '/')
]
config_path.write_text(json.dumps(config, indent=2) + '\n')
server_path = base.ROOT / 'scripts/serve.mjs'
server = server_path.read_text()
old = "if (/^\\/(?:en|zh|ms)?\\/?$/.test(pathname)) pathname = '/index.html';"
new = """const languageRoute = pathname.match(/^\/(en|zh|ms)\/?$/);
  if (languageRoute) {
    url.searchParams.set('lang', languageRoute[1]);
    res.writeHead(307, { Location: '/' + url.search });
    res.end(); return;
  }
  if (pathname === '/') pathname = '/index.html';"""
if old not in server:
    raise RuntimeError('Preview server route implementation changed; review route adapter.')
server = server.replace(old, new).replace("'.woff':'font/woff'", "'.ttf':'font/ttf','.woff':'font/woff'")
server_path.write_text(server)

readme = base.ROOT / 'README.md'
text = readme.read_text(encoding='utf-8')
text = text.replace('direct-route rewrites for `/en`, `/zh` and `/ms`', 'language-entry redirects for `/en`, `/zh` and `/ms` to the original `/?lang=en`, `/?lang=zh` and `/?lang=ms` URL format')
text = text.replace('- `scripts/import-published-site.py`: explicit one-time recovery utility, not part of normal deployment.', '- `scripts/complete-published-import.py`: explicit recovery entry point, including dynamic media and portable route aliases.\n- `scripts/import-published-site.py`: underlying recovery utility; neither runs during normal deployment.')
text += '\n## Language routing\n\nThe live published bundle uses `?lang=` and remembers the selector choice in local storage. The original README described pathname-aware language selection, but that was not present in the published bundle. This migration does not rewrite the application: `/en`, `/zh` and `/ms` redirect to its existing query-based language selector. Direct links therefore choose the requested language without changing the approved page design.\n'
readme.write_text(text, encoding='utf-8')
manifest_path = base.ROOT / 'docs/migration-manifest.json'
manifest = json.loads(manifest_path.read_text())
manifest['languageRouting'] = 'Host aliases /en, /zh and /ms redirect to original query-based language selection; application code is unchanged.'
manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + '\n')
