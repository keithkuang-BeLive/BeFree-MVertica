/* Heatmaps stay inactive until Keith supplies the site's own Clarity project ID.
   Put the ID in <meta name="belive-clarity-project-id" content="...">.
   No Clarity script, consent prompt, or analytics request runs with an empty ID. */
(() => {
  'use strict';
  const projectId = document.querySelector('meta[name="belive-clarity-project-id"]')?.content.trim();
  if (!projectId || !/^[a-z0-9]+$/i.test(projectId)) return;
  if (navigator.globalPrivacyControl === true || navigator.doNotTrack === '1') return;

  const notice = document.getElementById('analytics-notice');
  const settings = document.getElementById('analytics-settings');
  const accept = document.getElementById('analytics-accept');
  const decline = document.getElementById('analytics-decline');
  if (!notice || !settings || !accept || !decline) return;

  const storageKey = 'belive:mvertica:analytics:v1';
  let preference = null, started = false;
  try { preference = localStorage.getItem(storageKey); } catch { /* Page still works without storage. */ }
  const persist = value => {
    preference = value;
    try { localStorage.setItem(storageKey, value); } catch { /* Remember for this page only. */ }
  };
  const start = () => {
    window.clarity = window.clarity || function () { (window.clarity.q = window.clarity.q || []).push(arguments); };
    window.clarity('consentv2', { analytics_Storage: 'granted', ad_Storage: 'denied' });
    if (started) return;
    started = true;
    window.clarity('set', 'property', 'm_vertica');
    window.clarity('set', 'page_audience', 'prospective_property_partners');
    const script = document.createElement('script');
    script.async = true;
    script.src = 'https://www.clarity.ms/tag/' + projectId;
    document.head.appendChild(script);
  };
  const close = () => {
    const restoreFocus = notice.contains(document.activeElement);
    notice.hidden = true;
    if (restoreFocus) settings.focus({ preventScroll: true });
  };
  settings.hidden = false;
  settings.addEventListener('click', () => { notice.hidden = false; accept.focus({ preventScroll: true }); });
  accept.addEventListener('click', () => { persist('accepted'); start(); close(); });
  decline.addEventListener('click', () => {
    persist('declined');
    if (started && typeof window.clarity === 'function') {
      window.clarity('consentv2', { analytics_Storage: 'denied', ad_Storage: 'denied' });
      window.clarity('consent', false); // Documented cookie removal and tracking stop on withdrawal.
    }
    close();
  });
  if (preference === 'accepted') start();
  else if (preference !== 'declined') notice.hidden = false;

  // These measure the invitation click, never a sent message or WhatsApp conversation.
  const allowedEvents = new Set(['whatsapp_floating_click', 'whatsapp_contact_click']);
  document.addEventListener('click', event => {
    if (preference !== 'accepted' || typeof window.clarity !== 'function') return;
    const link = event.target instanceof Element ? event.target.closest('a[data-analytics-event]') : null;
    const name = link?.dataset.analyticsEvent;
    if (allowedEvents.has(name)) window.clarity('event', name);
  });
})();
