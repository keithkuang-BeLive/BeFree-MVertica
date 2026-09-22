/* Run after building and starting scripts/serve.mjs dist.
   Browser tools live outside application dependencies in .verification-tools.
   WhatsApp destinations are intercepted; no message is sent. */
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const { chromium } = require(path.join(process.cwd(), '.verification-tools/node_modules/playwright'));
const base = 'http://127.0.0.1:4173';
const output = '.verification-tools/evidence';
fs.mkdirSync(output, { recursive: true });
const report = {
  checkedAtUtc: new Date().toISOString(),
  environment: 'Chromium on GitHub Actions; local production build, not a Vercel deployment',
  status: 'running',
  checks: [], scenarios: [], externalFailures: [],
  messagesSent: 0,
  limitations: ['YouTube playback is not tested; embeds are isolated during browser checks.', 'External fonts and services remain third-party dependencies.', 'Vercel hosting and custom-domain DNS are not changed or verified by this test.']
};
function check(name, condition, details) {
  report.checks.push({ name, passed: Boolean(condition), ...(details === undefined ? {} : { details }) });
  console.log(condition ? 'PASS' : 'FAIL', name, details === undefined ? '' : JSON.stringify(details));
}
async function settle(page) {
  await page.locator('.site-shell').waitFor({ state: 'visible', timeout: 15000 });
  await page.evaluate(() => document.querySelectorAll('img').forEach(img => { img.loading = 'eager'; }));
  await page.waitForFunction(() => [...document.images].every(img => img.complete), { timeout: 15000 }).catch(() => {});
  await page.evaluate(() => Promise.race([document.fonts.ready, new Promise(resolve => setTimeout(resolve, 1500))]));
}
async function main() {
  const manifest = JSON.parse(fs.readFileSync('docs/migration-manifest.json', 'utf8'));
  check('Recovered asset hashes match the source manifest', manifest.assets.every(asset => {
    return crypto.createHash('sha256').update(fs.readFileSync(asset.path)).digest('hex') === asset.sha256;
  }), { assetCount: manifest.assetCount, bytes: manifest.assetBytes });
  check('Build contains every tracked public asset', manifest.assets.every(asset => fs.existsSync(asset.path.replace(/^public\//, 'dist/'))));
  const browser = await chromium.launch({ headless: true });
  try {
    for (const width of [1440, 390]) {
      for (const lang of ['en', 'zh', 'ms']) {
        const label = `${lang}-${width}`;
        const context = await browser.newContext({ viewport: { width, height: 900 }, deviceScaleFactor: 1, locale: 'en-MY' });
        const page = await context.newPage();
        page.setDefaultTimeout(6000);
        const scriptErrors = [], localFailures = [];
        page.on('pageerror', error => scriptErrors.push(String(error)));
        page.on('response', response => {
          if (response.url().startsWith(base) && response.status() >= 400) localFailures.push({ url: response.url(), status: response.status() });
        });
        page.on('requestfailed', request => {
          const item = { scenario: label, url: request.url(), error: request.failure()?.errorText };
          if (item.error === 'net::ERR_ABORTED') return;
          if (request.url().startsWith(base)) localFailures.push(item); else report.externalFailures.push(item);
        });
        await context.route('https://wa.me/**', route => route.fulfill({ status: 200, contentType: 'text/html', body: '<!doctype html><title>WhatsApp destination intercepted — no message sent</title>' }));
        await context.route('https://www.youtube.com/embed/**', route => route.fulfill({ status: 200, contentType: 'text/html', body: '<!doctype html><title>External video isolated for migration test</title>' }));
        try {
          // Deliberately conflict with remembered preference to test direct-entry precedence.
          await context.addInitScript(() => localStorage.setItem('belive-language', 'ms'));
          await page.goto(`${base}/${lang}`, { waitUntil: 'domcontentloaded' });
          await settle(page);
          check(`${label}: direct entry chooses requested language`, await page.locator('.site-shell').getAttribute('data-language') === lang, { finalUrl: page.url() });
          check(`${label}: correct document language`, await page.locator('html').getAttribute('lang') === (lang === 'zh' ? 'zh-Hans' : lang));
          check(`${label}: meaningful page content`, (await page.locator('main').innerText()).length > 1000 && (await page.locator('h1').innerText()).length > 15);
          const images = await page.evaluate(() => [...document.images].map(img => ({ path: new URL(img.currentSrc || img.src).pathname, complete: img.complete, width: img.naturalWidth })));
          check(`${label}: all page images load`, images.length >= 18 && images.every(img => img.complete && img.width > 0), images);
          const heroPath = await page.locator('.hero-photo-background img').getAttribute('src');
          check(`${label}: correct language-specific artwork`, heroPath.endsWith(lang === 'zh' ? 'ski-family-freedom-zh.webp' : 'ski-family-freedom.webp'));
          const anchors = await page.locator('a[href^="#"]').evaluateAll(links => links.map(link => ({ href: link.getAttribute('href'), exists: !!document.getElementById(link.getAttribute('href').slice(1)) })));
          check(`${label}: all in-page links have targets`, anchors.every(anchor => anchor.exists), { count: anchors.length });
          check(`${label}: analytics stays off without project ID`, await page.locator('meta[name="belive-clarity-project-id"]').getAttribute('content') === '' && await page.locator('script[src*="clarity.ms"]').count() === 0);
          await page.evaluate(() => scrollTo(0, 0));
          await page.screenshot({ path: `${output}/${label}.png`, fullPage: false, animations: 'disabled', timeout: 15000 });
          const whatsapps = await page.locator('a[href^="https://wa.me/"]').evaluateAll(links => links.map(link => ({ href: link.href, target: link.target, rel: link.rel })));
          check(`${label}: every WhatsApp link has correct number and draft`, whatsapps.length >= 5 && whatsapps.every(link => {
            const url = new URL(link.href);
            return url.pathname === '/601110854123' && Boolean(url.searchParams.get('text')) && link.target === '_blank' && link.rel.includes('noopener');
          }), { count: whatsapps.length });
          const popupPromise = page.waitForEvent('popup');
          await page.locator('.hero-button').click();
          const popup = await popupPromise;
          await popup.waitForLoadState('domcontentloaded');
          check(`${label}: WhatsApp button opens a draft destination`, popup.url().startsWith('https://wa.me/601110854123?text='));
          await popup.close();
          if (width < 600) {
            await page.locator('.mobile-menu').click();
            check(`${label}: mobile navigation opens`, await page.locator('.mobile-menu').getAttribute('aria-expanded') === 'true');
          }
          await page.locator('#site-navigation a[href="#performance"]').click();
          check(`${label}: results navigation works`, new URL(page.url()).hash === '#performance');
          if (width < 600) check(`${label}: menu closes after navigation`, await page.locator('.mobile-menu').getAttribute('aria-expanded') === 'false');
          for (const tab of [1, 2, 0]) {
            await page.locator(`#support-tab-${tab}`).click();
            check(`${label}: support tab ${tab + 1} responds`, await page.locator(`#support-tab-${tab}`).getAttribute('aria-selected') === 'true' && await page.locator(`#support-panel-${tab}`).isVisible());
          }
          const summary = page.locator('details.source-note summary');
          await summary.click();
          check(`${label}: credentials disclosure opens`, await page.locator('details.source-note').evaluate(element => element.open));
          await summary.click();
          if (width < 600) {
            await page.locator('.carousel-controls button').last().click();
            check(`${label}: mobile question carousel responds`, await page.locator('.challenge-track').evaluate(element => element.scrollLeft > 0));
          }
          await page.locator('.language-picker select').selectOption(lang === 'zh' ? 'en' : 'zh');
          const changedLang = lang === 'zh' ? 'en' : 'zh';
          await page.waitForFunction(expected => document.querySelector('.site-shell').dataset.language === expected, changedLang);
          check(`${label}: language selector updates the page and URL`, new URL(page.url()).searchParams.get('lang') === changedLang);
          await page.reload({ waitUntil: 'domcontentloaded' });
          await settle(page);
          check(`${label}: selected language survives reload`, await page.locator('.site-shell').getAttribute('data-language') === changedLang);
          check(`${label}: telephone and email destinations preserved`, await page.locator('a[href="tel:+601110854123"]').count() === 1 && await page.locator('a[href="mailto:info@belive.asia"]').count() === 1);
          check(`${label}: no application JavaScript exceptions`, scriptErrors.length === 0, scriptErrors);
          check(`${label}: no local missing resources`, localFailures.length === 0, localFailures);
          report.scenarios.push({ name: label, imageCount: images.length, whatsappLinks: whatsapps.length, screenshot: `${label}.png`, errors: scriptErrors, localFailures });
        } catch (error) {
          check(`${label}: scenario completes`, false, String(error));
          await page.screenshot({ path: `${output}/${label}-failure.png`, timeout: 10000 }).catch(() => {});
        } finally {
          await context.close();
        }
      }
    }
  } finally { await browser.close(); }
}
main().catch(error => check('Verification harness completed', false, String(error))).finally(() => {
  const failed = report.checks.filter(test => !test.passed);
  report.status = failed.length ? 'failed' : 'passed';
  report.passedChecks = report.checks.length - failed.length;
  report.failedChecks = failed.length;
  fs.writeFileSync('docs/browser-verification.json', JSON.stringify(report, null, 2) + '\n');
  fs.writeFileSync(`${output}/browser-verification.json`, JSON.stringify(report, null, 2) + '\n');
  console.log('VERIFICATION_SUMMARY', JSON.stringify({ status: report.status, passed: report.passedChecks, failed: report.failedChecks, scenarios: report.scenarios.length }));
  process.exitCode = failed.length ? 1 : 0;
});
