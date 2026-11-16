/* RISE Conference Navigator — optional, browser-local specialty profiles.
   Google Analytics is loaded ONLY after an explicit opt-in and configuration.
   Never transmit abstract text, patient information, search terms, or plans. */
(() => {
  'use strict';
  const STORAGE_KEY = 'rise_navigator_profile_v1';
  const el = id => document.getElementById(id);
  const allowed = [...new Set((window.RISE_DATA?.conferences || [])
    .map(item => item.specialty).filter(Boolean))].sort((a, b) => a.localeCompare(b));
  const profileChoices = [...allowed, 'Other / multidisciplinary', 'Undecided'];
  const analyticsId = typeof window.RISE_ANALYTICS_ID === 'string'
    ? window.RISE_ANALYTICS_ID.trim() : '';
  const analyticsConfigured = /^G-[A-Z0-9]{6,16}$/.test(analyticsId);
  let analyticsLoaded = false;
  let profile = readProfile();
  let opener = null;

  function readProfile() {
    try {
      const value = JSON.parse(localStorage.getItem(STORAGE_KEY) || 'null');
      if (!value || value.version !== 1) return null;
      if (typeof value.specialty !== 'string' || !profileChoices.includes(value.specialty) && value.specialty !== '') return null;
      return {
        version: 1,
        specialty: value.specialty,
        analytics: value.analytics === true,
        skipped: value.skipped === true
      };
    } catch (_) { return null; }
  }
  function storeProfile() {
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(profile)); } catch (_) {}
  }
  function currentSpecialty() {
    return profileChoices.includes(profile?.specialty) ? profile.specialty : '';
  }
  function filterSpecialty() {
    const value = currentSpecialty();
    return allowed.includes(value) ? value : '';
  }
  function analyticsSpecialty() {
    return currentSpecialty() || 'Not specified';
  }
  function updateUserProperty() {
    if (analyticsLoaded && profile?.analytics) {
      window.gtag('set', 'user_properties', { primary_specialty: analyticsSpecialty() });
    }
  }
  function initializeAnalytics() {
    if (!profile?.analytics || !analyticsConfigured) return;
    if (analyticsLoaded) {
      window.gtag('consent', 'update', { analytics_storage: 'granted' });
      updateUserProperty();
      return;
    }
    window.dataLayer = window.dataLayer || [];
    window.gtag = function () { window.dataLayer.push(arguments); };
    // Marketing and advertising consent are never requested.
    window.gtag('consent', 'default', {
      analytics_storage: 'granted',
      ad_storage: 'denied',
      ad_user_data: 'denied',
      ad_personalization: 'denied'
    });
    window.gtag('js', new Date());
    window.gtag('config', analyticsId, {
      send_page_view: false,
      allow_google_signals: false,
      allow_ad_personalization_signals: false
    });
    analyticsLoaded = true;
    updateUserProperty();
    const script = document.createElement('script');
    script.async = true;
    script.src = 'https://www.googletagmanager.com/gtag/js?id=' + encodeURIComponent(analyticsId);
    document.head.appendChild(script);
    track('page_view', {
      page_title: document.title,
      // Do not send query parameters, hashes, or clinical text to analytics.
      page_location: location.origin + location.pathname
    });
  }
  function track(eventName, params = {}) {
    if (!profile?.analytics || !analyticsConfigured || !analyticsLoaded) return;
    const approvedEvents = new Set([
      'page_view', 'profile_saved', 'section_view', 'conference_view',
      'matcher_used', 'roadmap_generated'
    ]);
    if (!approvedEvents.has(eventName)) return;
    const approvedParameters = new Set([
      'page_title', 'page_location', 'profile_action', 'section',
      'conference_id', 'conference_specialty', 'match_count', 'project_type'
    ]);
    const safe = { primary_specialty: analyticsSpecialty() };
    for (const [key, value] of Object.entries(params)) {
      if (!approvedParameters.has(key)) continue;
      if (typeof value === 'string') safe[key] = value.slice(0, 100);
      else if (Number.isInteger(value) && value >= 0 && value < 10000) safe[key] = value;
    }
    window.gtag('event', eventName, safe);
  }
  function syncAnalytics() {
    if (profile?.analytics) initializeAnalytics();
    else if (analyticsLoaded) {
      window.gtag('consent', 'update', { analytics_storage: 'denied' });
    }
  }
  function refreshButton() {
    const value = currentSpecialty();
    el('profileOpen').textContent = value ? 'My specialty · ' + value : 'Set my specialty';
    el('profileOpen').setAttribute('aria-label', value
      ? 'Edit specialty profile: ' + value : 'Set up your specialty profile');
    el('profileOpen').title = 'Edit your specialty preference and analytics choice';
  }
  function closeProfile() {
    const overlay = el('profileScrim');
    overlay.classList.add('hidden');
    document.body.classList.remove('profile-dialog-open');
    if (!profile) {
      profile = { version: 1, specialty: '', analytics: false, skipped: true };
      storeProfile();
    }
    if (opener && typeof opener.focus === 'function') opener.focus();
  }
  function openProfile(firstVisit = false) {
    opener = firstVisit ? null : document.activeElement;
    el('profileSpecialty').value = currentSpecialty();
    el('profileAnalytics').checked = profile?.analytics === true;
    el('profileError').textContent = '';
    el('profileSkip').classList.toggle('hidden', !!currentSpecialty());
    el('profileScrim').classList.remove('hidden');
    document.body.classList.add('profile-dialog-open');
    el('profileSpecialty').focus();
  }
  function saveProfile(event) {
    event.preventDefault();
    const selected = el('profileSpecialty').value;
    if (!profileChoices.includes(selected)) {
      el('profileError').textContent = 'Select a specialty, or choose Continue without a profile.';
      el('profileSpecialty').focus();
      return;
    }
    const wasCreated = !!profile?.specialty;
    const previousSpecialty = currentSpecialty();
    profile = {
      version: 1,
      specialty: selected,
      analytics: el('profileAnalytics').checked,
      skipped: false
    };
    storeProfile();
    syncAnalytics();
    updateUserProperty();
    refreshButton();
    if (selected !== previousSpecialty) {
      window.dispatchEvent(new CustomEvent('rise:profile-saved', {
        detail: { specialty: filterSpecialty() }
      }));
    }
    track('profile_saved', { profile_action: wasCreated ? 'updated' : 'created' });
    closeProfile();
  }

  const selector = el('profileSpecialty');
  for (const value of profileChoices) {
    const option = document.createElement('option');
    option.value = value;
    option.textContent = value;
    selector.appendChild(option);
  }
  el('profileForm').addEventListener('submit', saveProfile);
  el('profileOpen').addEventListener('click', () => openProfile());
  el('profileClose').addEventListener('click', closeProfile);
  el('profileSkip').addEventListener('click', closeProfile);
  el('profileScrim').addEventListener('click', event => {
    if (event.target === el('profileScrim')) closeProfile();
  });
  el('profileScrim').addEventListener('keydown', event => {
    if (event.key === 'Escape') { event.preventDefault(); closeProfile(); }
    if (event.key !== 'Tab') return;
    const focusables = [...el('profileDialog').querySelectorAll(
      'button:not([disabled]):not(.hidden), input:not([disabled]), select:not([disabled])'
    )].filter(element => element.getClientRects().length);
    if (!focusables.length) return;
    const first = focusables[0], last = focusables[focusables.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault(); last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault(); first.focus();
    }
  });

  window.RISE_PROFILE = Object.freeze({
    getSpecialty: filterSpecialty,
    track
  });
  refreshButton();
  syncAnalytics();
  if (!profile) {
    // Once-only, dismissible invitation. Browsing never requires a profile.
    window.setTimeout(() => { if (!profile) openProfile(true); }, 450);
  }
})();
