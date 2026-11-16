/* RISE Conference Navigator — browser-local residency and specialty profiles.
   Optional Google Analytics only loads after explicit consent and configuration.
   Never transmit abstracts, clinical text, search terms, or research plans. */
(() => {
  'use strict';
  const STORAGE_KEY = 'rise_navigator_profile_v2';
  const LEGACY_KEY = 'rise_navigator_profile_v1';
  const el = id => document.getElementById(id);
  const allowed = [...new Set((window.RISE_DATA?.conferences || [])
    .map(item => item.specialty).filter(Boolean))].sort((a, b) => a.localeCompare(b));
  const specialtyChoices = [...allowed, 'Other / multidisciplinary', 'Undecided'];
  const programs = [
    'Internal Medicine', 'General Surgery', 'Family Medicine',
    'Obstetrics & Gynecology', 'Pediatrics', 'Emergency Medicine',
    'Psychiatry', 'Neurology', 'Anesthesiology', 'Diagnostic Radiology',
    'Radiation Oncology', 'Pathology', 'Dermatology',
    'Orthopaedic Surgery', 'Neurosurgery', 'Otolaryngology',
    'Ophthalmology', 'Urology', 'Plastic Surgery',
    'Physical Medicine & Rehabilitation', 'Internal Medicine–Pediatrics',
    'Preventive Medicine', 'Transitional Year', 'Other'
  ];
  const analyticsId = typeof window.RISE_ANALYTICS_ID === 'string'
    ? window.RISE_ANALYTICS_ID.trim() : '';
  const analyticsConfigured = /^G-[A-Z0-9]{6,16}$/.test(analyticsId);
  let analyticsLoaded = false;
  let profile = readProfile();
  let opener = null;

  function readProfile() {
    try {
      let value = JSON.parse(localStorage.getItem(STORAGE_KEY) || 'null');
      if (!value) {
        const legacy = JSON.parse(localStorage.getItem(LEGACY_KEY) || 'null');
        if (legacy?.version === 1) {
          // Migrate the original single-specialty profile without losing consent.
          value = {
            version: 2,
            residencyProgram: '',
            specialties: specialtyChoices.includes(legacy.specialty) ? [legacy.specialty] : [],
            analytics: legacy.analytics === true,
            skipped: legacy.skipped === true,
            promptedProgram: legacy.skipped === true
          };
        }
      }
      if (!value || value.version !== 2 || !Array.isArray(value.specialties)) return null;
      const specialties = [...new Set(value.specialties.filter(
        specialty => typeof specialty === 'string' && specialtyChoices.includes(specialty)
      ))];
      return {
        version: 2,
        residencyProgram: programs.includes(value.residencyProgram) ? value.residencyProgram : '',
        specialties,
        analytics: value.analytics === true,
        skipped: value.skipped === true,
        promptedProgram: value.promptedProgram === true
      };
    } catch (_) { return null; }
  }
  function storeProfile() {
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(profile)); } catch (_) {}
  }
  function interests() {
    return Array.isArray(profile?.specialties) ? [...profile.specialties] : [];
  }
  function filterSpecialties() {
    return interests().filter(specialty => allowed.includes(specialty));
  }
  function userProgram() {
    return profile?.residencyProgram || 'Not specified';
  }
  function updateUserProperties() {
    if (analyticsLoaded && profile?.analytics) {
      window.gtag('set', 'user_properties', {
        residency_program: userProgram(),
        specialty_count: String(interests().length)
      });
    }
  }
  function track(eventName, params = {}) {
    if (!profile?.analytics || !analyticsConfigured || !analyticsLoaded) return;
    const approvedEvents = new Set([
      'page_view', 'profile_saved', 'specialty_interest', 'section_view',
      'conference_view', 'matcher_used', 'roadmap_generated'
    ]);
    if (!approvedEvents.has(eventName)) return;
    const approvedParameters = new Set([
      'page_title', 'page_location', 'profile_action', 'section',
      'conference_id', 'conference_specialty', 'match_count',
      'project_type', 'interest_specialty'
    ]);
    const safe = {
      residency_program: userProgram(),
      specialty_count: interests().length
    };
    for (const [key, value] of Object.entries(params)) {
      if (!approvedParameters.has(key)) continue;
      if (typeof value === 'string') safe[key] = value.slice(0, 100);
      else if (Number.isInteger(value) && value >= 0 && value < 10000) safe[key] = value;
    }
    window.gtag('event', eventName, safe);
  }
  function trackInterests() {
    // Event-scoped specialty dimension can represent multiple interests per user.
    // Use Total users, not summed event counts, to estimate representation.
    for (const specialty of interests()) {
      track('specialty_interest', { interest_specialty: specialty });
    }
  }
  function initializeAnalytics() {
    if (!profile?.analytics || !analyticsConfigured) return;
    if (analyticsLoaded) {
      window.gtag('consent', 'update', { analytics_storage: 'granted' });
      updateUserProperties();
      return;
    }
    window.dataLayer = window.dataLayer || [];
    window.gtag = function () { window.dataLayer.push(arguments); };
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
    updateUserProperties();
    const script = document.createElement('script');
    script.async = true;
    script.src = 'https://www.googletagmanager.com/gtag/js?id=' + encodeURIComponent(analyticsId);
    document.head.appendChild(script);
    track('page_view', {
      page_title: document.title,
      page_location: location.origin + location.pathname
    });
    trackInterests();
  }
  function syncAnalytics() {
    if (profile?.analytics) initializeAnalytics();
    else if (analyticsLoaded) {
      window.gtag('consent', 'update', { analytics_storage: 'denied' });
    }
  }
  function refreshButton() {
    const program = profile?.residencyProgram;
    el('profileOpen').textContent = program ? 'Profile · ' + program : 'My profile';
    el('profileOpen').setAttribute('aria-label', 'Edit residency program and specialty interests');
    el('profileOpen').title = 'Edit residency program, specialty interests and analytics preference';
  }
  function selectedInterests() {
    return [...el('profileSpecialtyOptions').querySelectorAll('input[type="checkbox"]:checked')]
      .map(input => input.value);
  }
  function renderInterestCount() {
    const count = selectedInterests().length;
    el('profileInterestCount').textContent = count
      ? count + (count === 1 ? ' selected' : ' selected')
      : 'None selected';
  }
  function closeProfile() {
    el('profileScrim').classList.add('hidden');
    document.body.classList.remove('profile-dialog-open');
    if (!profile) {
      profile = {
        version: 2, residencyProgram: '', specialties: [],
        analytics: false, skipped: true, promptedProgram: true
      };
    } else {
      profile.promptedProgram = true;
    }
    storeProfile();
    if (opener && typeof opener.focus === 'function') opener.focus();
  }
  function openProfile(firstVisit = false) {
    opener = firstVisit ? null : document.activeElement;
    el('profileProgram').value = profile?.residencyProgram || '';
    const selected = new Set(interests());
    el('profileSpecialtyOptions').querySelectorAll('input[type="checkbox"]').forEach(input => {
      input.checked = selected.has(input.value);
    });
    renderInterestCount();
    el('profileAnalytics').checked = profile?.analytics === true;
    el('profileError').textContent = '';
    el('profileSkip').classList.toggle('hidden', !!profile?.residencyProgram);
    el('profileScrim').classList.remove('hidden');
    document.body.classList.add('profile-dialog-open');
    el('profileProgram').focus();
  }
  function saveProfile(event) {
    event.preventDefault();
    const residencyProgram = el('profileProgram').value;
    const specialties = selectedInterests();
    if (!programs.includes(residencyProgram)) {
      el('profileError').textContent = 'Select your residency program.';
      el('profileProgram').focus();
      return;
    }
    if (!specialties.length) {
      el('profileError').textContent = 'Select at least one specialty interest.';
      el('profileSpecialtyOptions').querySelector('input[type="checkbox"]')?.focus();
      return;
    }
    const hadProfile = !!profile?.residencyProgram;
    const oldInterests = interests();
    const oldProgram = profile?.residencyProgram || '';
    const wasEnabled = profile?.analytics === true;
    profile = {
      version: 2,
      residencyProgram,
      specialties,
      analytics: el('profileAnalytics').checked,
      skipped: false,
      promptedProgram: true
    };
    storeProfile();
    syncAnalytics();
    updateUserProperties();
    refreshButton();
    if (oldInterests.join('\u001F') !== specialties.join('\u001F')) {
      window.dispatchEvent(new CustomEvent('rise:profile-saved', {
        detail: { specialties: filterSpecialties() }
      }));
    }
    track('profile_saved', { profile_action: hadProfile ? 'updated' : 'created' });
    if (wasEnabled && (oldProgram !== residencyProgram ||
        oldInterests.join('\u001F') !== specialties.join('\u001F'))) {
      trackInterests();
    }
    closeProfile();
  }

  const programSelect = el('profileProgram');
  for (const program of programs) {
    const option = document.createElement('option');
    option.value = program;
    option.textContent = program;
    programSelect.appendChild(option);
  }
  const options = el('profileSpecialtyOptions');
  for (const specialty of specialtyChoices) {
    const label = document.createElement('label');
    label.className = 'profile-specialty-option';
    const checkbox = document.createElement('input');
    checkbox.type = 'checkbox';
    checkbox.value = specialty;
    checkbox.name = 'specialty-interest';
    const span = document.createElement('span');
    span.textContent = specialty;
    label.appendChild(checkbox);
    label.appendChild(span);
    options.appendChild(label);
  }
  options.addEventListener('change', renderInterestCount);
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
    getSpecialties: filterSpecialties,
    getResidencyProgram: () => profile?.residencyProgram || '',
    track
  });
  refreshButton();
  syncAnalytics();
  if (!profile || (!profile.residencyProgram && !profile.skipped && !profile.promptedProgram)) {
    window.setTimeout(() => { if (!profile?.promptedProgram) openProfile(true); }, 450);
  }
})();
