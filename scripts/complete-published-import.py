#!/usr/bin/env python3
"""Application-specific entry point for recovering the published M Vertica site.
The application constructs media URLs by adding bare filenames to /assets/,
and derives four Chinese artwork paths with its Qi(...) function. Resolve
those expressions without executing or modifying the application bundle.
"""
import importlib.util
import re
from pathlib import Path

spec = importlib.util.spec_from_file_location('published_import', Path(__file__).with_name('import-published-site.py'))
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)
original_references = base.references

def complete_references(text, url, html=False):
    refs = original_references(text, url, html)
    # Include dynamically appended root-level scripts such as /analytics.js.
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
readme = base.ROOT / 'README.md'
text = readme.read_text(encoding='utf-8')
text = text.replace('- `scripts/import-published-site.py`: explicit one-time recovery utility, not part of normal deployment.', '- `scripts/complete-published-import.py`: explicit recovery entry point, including dynamically generated image references.\n- `scripts/import-published-site.py`: underlying recovery utility; neither script runs during normal deployment.')
readme.write_text(text, encoding='utf-8')
