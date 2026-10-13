/* RISE Conference Navigator — dependency-free application logic.
   Data: ./data.js. Host applications can replace window.RISE_DATA or consume data.json.
   Everything here is read-only; authentication/personal projects are deliberately excluded. */
(() => {
'use strict';
const {conferences: C, awards: A, asOf} = window.RISE_DATA;
const get = id => document.getElementById(id);
const freshnessLabel = get('lastDatasetUpdated');
if(freshnessLabel && /^\d{4}-\d{2}-\d{2}$/.test(asOf||'')) freshnessLabel.textContent = new Date(asOf+'T12:00:00').toLocaleDateString('en-US',{month:'long',day:'numeric',year:'numeric'});
const today = (() => { const q = new URLSearchParams(location.search).get('demoDate'); return q && /^\d{4}-\d{2}-\d{2}$/.test(q) ? new Date(q+'T12:00:00') : new Date(); })();
const todayKey = key(today);
const state={view:'discover',exploreMode:'list', specialties:[],search:'',status:'all',sort:'meeting',monthKey:null,dateTypes:[],calDate:new Date(today.getFullYear(),today.getMonth(),1),funding:'all', fundingSpecialties:[], selected:null,plan:null};
function key(d){return d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0')}
function date(s){return s ? new Date(s+'T12:00:00'):null}
function shift(d,days){let r=new Date(d);r.setDate(r.getDate()+days);return r}
function fmt(s,opts={month:'short',day:'numeric',year:'numeric'}){if(!s)return 'Not announced';return date(s).toLocaleDateString('en-US',opts)}
function short(s){return s ? fmt(s,{month:'short',day:'numeric'}):'Not announced'}
function escape(s){return String(s??'').replace(/[&<>"']/g,ch=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]))}
const iconPaths={grid:'<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>',calendar:'<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M16 3v4M8 3v4M3 10h18"/>',layers:'<path d="m12 2 9 5-9 5-9-5 9-5ZM3 12l9 5 9-5M3 17l9 5 9-5"/>',award:'<circle cx="12" cy="8" r="6"/><path d="m8 14-1 8 5-3 5 3-1-8"/>',shield:'<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z"/><path d="m9 12 2 2 4-4"/>',download:'<path d="M12 3v12m-5-5 5 5 5-5M4 17v4h16v-4"/>',clock:'<circle cx="12" cy="12" r="9"/><path d="M12 7v5l4 2"/>',search:'<circle cx="11" cy="11" r="7"/><path d="m16 16 5 5"/>',stethoscope:'<path d="M6 3v6a5 5 0 0 0 10 0V3M4 3h4M14 3h4M11 14v2a4 4 0 0 0 8 0v-2"/><circle cx="19" cy="12" r="2"/>',info:'<circle cx="12" cy="12" r="10"/><path d="M12 10v7M12 7h.01"/>',map:'<path d="m3 6 6-3 6 3 6-3v15l-6 3-6-3-6 3V6Zm6-3v15m6-12v15"/>',external:'<path d="M14 4h6v6M20 4l-9 9"/><path d="M20 13v6a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V5a1 1 0 0 1 1-1h6"/>',check:'<path d="m4 12 5 5 11-11"/>',moon:'<path d="M20.6 13.4A8.6 8.6 0 0 1 10.6 3.4 8.6 8.6 0 1 0 20.6 13.4Z"/>',sun:'<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.93 4.93l1.42 1.42m11.3 11.3 1.42 1.42M2 12h2m16 0h2M4.93 19.07l1.42-1.42m11.3-11.3 1.42-1.42"/>',arrow:'<path d="M5 12h14m-6-6 6 6-6 6"/>'};
function ico(n){return `<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${iconPaths[n]||iconPaths.info}</svg>`}
document.querySelectorAll('[data-icon]').forEach(el=>el.innerHTML=ico(el.dataset.icon));
// The visitor's explicit choice is saved locally; the existing light design stays the default.
function applyTheme(theme) {
 const dark=theme==='dark';
 document.documentElement.dataset.theme=dark?'dark':'light';
 const button=get('themeToggle');
 const title=dark?'Switch to light mode':'Switch to dark mode';
 button.setAttribute('aria-pressed',String(dark));
 button.setAttribute('aria-label',title);
 button.title=title;
 get('themeToggleText').textContent=dark?'Light mode':'Dark mode';
 button.querySelector('.theme-toggle-icon').innerHTML=ico(dark?'sun':'moon');
 const themeMeta=document.querySelector('meta[name="theme-color"]');
 if(themeMeta)themeMeta.setAttribute('content',dark?'#101e2b':'#07527f');
}
applyTheme(document.documentElement.dataset.theme==='dark'?'dark':'light');
get('themeToggle').addEventListener('click',()=>{
 const next=document.documentElement.dataset.theme==='dark'?'light':'dark';
 applyTheme(next);
 try { localStorage.setItem('rise-theme',next); } catch (error) { /* Toggle still works. */ }
});
function status(c){
 if(c.flag==='conflict')return ['Source conflict','conflict'];
 const regularAvailable=!!c.deadline&&c.deadline>=todayKey;
 const lateAvailable=!!c.lateDeadline&&c.lateDeadline>=todayKey;
 if(lateAvailable&&!regularAvailable)
  return [c.lateOpen&&c.lateOpen<=todayKey?'Late-breaking open':'Late-breaking upcoming',
          c.lateOpen&&c.lateOpen<=todayKey?'open':'upcoming'];
 if(c.deadline&&c.deadline<todayKey)return ['Closed','closed'];
 if(c.lateDeadline&&c.lateDeadline<todayKey&&!c.deadline)return ['Late-breaking closed','closed'];
 if(c.evidence==='unannounced')return ['Not announced','pending'];
 if(!c.deadline)return ['Monitor cycle',c.evidence==='official'?'verified':'tracker'];
 if(!c.open)return ['Upcoming deadline','upcoming'];
 if(c.open<=todayKey)return ['Submissions open','open'];
 return ['Abstracts open · '+fmt(c.open),'upcoming'];
}
function source(c){return c.flag==='conflict'?'conflict':c.evidence==='tracker'?'tracker':c.evidence==='unannounced'?'pending':'verified'}
function sourceLabel(c){return ({conflict:'Source conflict',tracker:'Needs official verification',pending:'To be announced',verified:'Official source'})[source(c)]}
function daysAway(s){if(!s)return null;const a=date(todayKey),b=date(s);return Math.round((b-a)/86400000)}
function deadlineOrder(c){return c.deadline && c.deadline>=todayKey?c.deadline:'9999-12-31'}
function safeExternal(url,txt,cl='external-link'){return url ? `<a class="${cl}" target="_blank" rel="noopener noreferrer" href="${escape(url)}">${escape(txt)} ${ico('external')}</a>`:'<span class="muted">Contact local office</span>'}
/* Keep the navigator in session history so Back/Forward return to views and
   open conference details instead of unexpectedly leaving GitHub Pages. */
const NAV_VIEWS=['discover','matcher','planner','funding','sources'];
function routeFromHash(){
 const parts=location.hash.replace(/^#/,'').split('/').filter(Boolean);
 let view=NAV_VIEWS.includes(parts[0])?parts[0]:'discover';
 let offset=view==='discover'&&parts[0]!=='discover'?0:1;
 const mode=view==='discover'&&parts[offset]==='calendar'?'calendar':'list';
 if(mode==='calendar')offset++;
 let modal=null;
 if(parts[offset]==='conference'&&parts[offset+1]){
  try{modal=decodeURIComponent(parts[offset+1])}catch(error){modal=null}
 }
 if(modal&&!C.some(c=>c.id===modal))modal=null;
 return {view,mode,modal,depth:0};
}
function routeURL(route){
 const parts=[route.view];
 if(route.view==='discover'&&route.mode==='calendar')parts.push('calendar');
 if(route.modal)parts.push('conference',encodeURIComponent(route.modal));
 const fragment=route.view==='discover'&&route.mode==='list'&&!route.modal?'':'#'+parts.join('/');
 return location.pathname+location.search+fragment;
}
function routeSnapshot(){
 return {view:state.view,mode:state.exploreMode,
         modal:get('modalScrim').classList.contains('hidden')?null:state.selected};
}
function updateBackButton(){
 const button=get('navBack');
 if(button)button.classList.toggle('hidden',!(history.state?.riseNavigator?.depth>0));
}
function recordRoute(replace=false){
 const current=history.state?.riseNavigator;
 const route=routeSnapshot();
 if(!replace&&current&&current.view===route.view&&current.mode===route.mode&&current.modal===route.modal)return;
 const depth=replace?(current?.depth||0):(current?.depth||0)+1;
 history[replace?'replaceState':'pushState']({...history.state,riseNavigator:{...route,depth}},'',routeURL(route));
 updateBackButton();
}
function dismissModal(){
 get('modalScrim').classList.add('hidden');
 document.body.style.overflow='';
 state.selected=null;
}
function nav(view,track=true){
 if(!NAV_VIEWS.includes(view))return;
 const previousView=state.view;
 const wasModal=!get('modalScrim').classList.contains('hidden');
 if(wasModal)dismissModal();
 if(view==='funding'&&previousView==='discover'&&state.specialties.length)
  state.fundingSpecialties=state.specialties.filter(s=>fundingSpecialties.includes(s));
 state.view=view;
 document.querySelectorAll('.view').forEach(v=>v.classList.toggle('active',v.id===view+'View'));
 document.querySelectorAll('[data-view]').forEach(b=>b.classList.toggle('active',b.dataset.view===view));
 get('sidebar').classList.remove('open');get('mobileOverlay').classList.remove('open');
 if(track&&view!==previousView||track&&wasModal)recordRoute();
 if(track)window.scrollTo({top:0,behavior:'instant'});
 if(view==='discover'&&state.exploreMode==='calendar')renderCalendar();
 if(view==='funding')renderFunding();
 if(view==='sources')renderSources();
 if(view==='planner')renderPlan();
}
document.querySelectorAll('[data-view]').forEach(btn=>btn.addEventListener('click',()=>nav(btn.dataset.view)));
const MOBILE_LIST_ONLY=window.matchMedia('(max-width: 750px)');
function setExploreMode(mode,track=true){
 if(mode!=='list'&&mode!=='calendar')return;
 if(MOBILE_LIST_ONLY.matches)mode='list';
 const changed=state.exploreMode!==mode;
 state.exploreMode=mode;
 const calendar=mode==='calendar';
 get('discoverListPanel').classList.toggle('active',!calendar);
 get('calendarView').classList.toggle('active',calendar);
 document.querySelectorAll('[data-explore-mode]').forEach(btn=>{
  const selected=btn.dataset.exploreMode===mode;
  btn.classList.toggle('active',selected);
  btn.setAttribute('aria-pressed',String(selected));
 });
 if(calendar){
  syncCalendarSpecialty();
  if(state.monthKey){
   const [year,month]=state.monthKey.split('-').map(Number);
   state.calDate=monthStart(year,month-1);
  }
  renderCalendar();
 }
 if(changed&&track&&state.view==='discover')recordRoute();
}
document.querySelectorAll('[data-explore-mode]').forEach(btn=>btn.addEventListener('click',()=>setExploreMode(btn.dataset.exploreMode)));
MOBILE_LIST_ONLY.addEventListener('change',event=>{
 if(event.matches&&state.exploreMode==='calendar'){
  setExploreMode('list',false);
  recordRoute(true);
 }
});

get('menuBtn').addEventListener('click',()=>{get('sidebar').classList.add('open');get('mobileOverlay').classList.add('open')});get('mobileOverlay').addEventListener('click',()=>{get('sidebar').classList.remove('open');get('mobileOverlay').classList.remove('open')});
function initSummary(){get('asOfLabel').textContent='Data snapshot · '+fmt(asOf);}
function dateRange(a,b){if(!a)return 'Not announced';return b&&b!==a?`${fmt(a)} – ${fmt(b)}`:fmt(a)}
function monthId(s){return s?.slice(0,7)||''}
/* A month in the outlook refers to abstract events OR the conference itself.
   Keep the exact dates for an honest explanation on every filtered result. */
function monthMatches(c,m,type='all'){
 if(m&&!/^\d{4}-\d{2}$/.test(m))return [];
 const types=Array.isArray(type)?type:(type==='all'?[]:[type]),all=!types.length;
 if(!m&&all)return [];
 const begin=m?m+'-01':null,end=m?key(new Date(Number(m.slice(0,4)),Number(m.slice(5)),0)):null,found=[];
 for(const [field,label,kind] of [
  ['deadline','Abstract deadline','due'],['lateDeadline','Late-breaking deadline','due'],
  ['open','Abstract submissions open','open'],['lateOpen','Late-breaking submissions open','open']
 ]){
  const day=c[field];
  if(!all&&!types.includes(field))continue;
  if(day&&(!begin||(day>=begin&&day<=end)) &&
    !(field==='lateDeadline'&&day===c.deadline) &&
    !(field==='lateOpen'&&day===c.open))found.push({day,field,label,kind,display:fmt(day)});
 }
 if((all||types.includes('meeting'))&&c.start &&
    (!begin||(c.start<=end&&(c.end||c.start)>=begin)))
  found.push({day:begin&&c.start<begin?begin:c.start,field:'meeting',label:'Conference meeting',kind:'meeting',display:dateRange(c.start,c.end||c.start)});
 return found.sort((a,b)=>a.day.localeCompare(b.day)||
   ({due:0,open:1,meeting:2}[a.kind])-({due:0,open:1,meeting:2}[b.kind]));
}
function matchesMonth(c,m,type='all'){return (!m&&(type==='all'||Array.isArray(type)&&type.length===0))||monthMatches(c,m,type).length>0}
function selectedDate(c){return monthMatches(c,state.monthKey,state.dateTypes)[0]?.day||'9999'}
const DATE_TYPE_NAMES={all:'all dates',meeting:'meeting dates',open:'abstract openings',deadline:'abstract deadlines',lateOpen:'late-breaking openings',lateDeadline:'late-breaking deadlines'};
function horizonMonths(){const t=new Date(today.getFullYear(),today.getMonth(),1);return Array.from({length:18},(_,i)=>{const d=new Date(t.getFullYear(),t.getMonth()+i,1);return key(d).slice(0,7)})}
function renderHorizon(){
 const list=C.filter(c=>matchesSelectedSpecialty(c.specialty,state.specialties));
 const months=horizonMonths();const yearGroups=new Map();
 for(const m of months){
  // Use the same event classification for counts and selected-month results.
  const monthEvents=list.flatMap(c=>monthMatches(c,m,state.dateTypes));
  const abstracts=monthEvents.filter(e=>e.kind==='due').length;
  const meetings=monthEvents.filter(e=>e.kind==='meeting').length;
  const opens=monthEvents.filter(e=>e.kind==='open').length;
  const monthLabel=date(m+'-01').toLocaleString('en-US',{month:'short'});
  const countHTML=(n,word,plural)=>n?`<span class="horizon-count-row"><strong>${n}</strong> ${n===1?word:plural}</span>`:'';
  const totals=[countHTML(abstracts,'ABSTRACT DUE','ABSTRACTS DUE'),countHTML(meetings,'MEETING','MEETINGS'),countHTML(opens,'ABSTRACT OPENS','ABSTRACTS OPEN')].filter(Boolean).join('');
  const month=`<button type="button" class="horizon-month ${m===state.monthKey?'selected':''} ${m===monthId(todayKey)?'current':''}" data-outlook-month="${m}" aria-pressed="${m===state.monthKey}" aria-label="${monthLabel} ${m.slice(0,4)}: ${abstracts} abstracts due, ${meetings} meetings, ${opens} abstract submission openings"><span class="horizon-month-label">${monthLabel}</span><span class="horizon-count">${totals||'<span class="horizon-none">NO POSTED DATES</span>'}</span></button>`;
  const year=m.slice(0,4);
  if(!yearGroups.has(year))yearGroups.set(year,[]);
  yearGroups.get(year).push(month);
 }
 // Year labels stay aligned to the left edge of their own year group as the months move beneath.
 // When the next year enters the viewport, the previous year's header exits naturally.
 get('horizonStrip').innerHTML=[...yearGroups.entries()].map(([year,group])=>`<section class="horizon-year-group" data-outlook-year="${year}" aria-label="${year} conference outlook"><div class="horizon-year-heading"><span>${year}</span><small>CONFERENCE OUTLOOK</small></div><div class="horizon-year-months">${group.join('')}</div></section>`).join('');
 const when=state.monthKey?' in '+date(state.monthKey+'-01').toLocaleString('en-US',{month:'long',year:'numeric'}):'';
 const typeText=state.dateTypes.length?state.dateTypes.map(t=>DATE_TYPE_NAMES[t]).join(', '):'all date types';
 const msg=state.dateTypes.length?'Showing '+typeText+when+'.':state.monthKey?'Showing all recorded date types'+when+'.':'Select date types and/or a month to filter conferences.';
 get('horizonContext').textContent=msg;get('clearMonth').classList.toggle('hidden',!state.monthKey);
}
function applyDateView(){
 state.dateTypes=[...document.querySelectorAll('input[name="date-type"]:checked')].map(input=>input.value);
 const alphabetical=get('dateSortName').checked;
 state.sort=alphabetical?'name':(state.monthKey||state.dateTypes.length?'month':'meeting');
 const count=state.dateTypes.length;
 const label=count===0?'All dates':count===1?({
  meeting:'Meeting dates',open:'Abstract opens',deadline:'Abstract closes',
  lateOpen:'Late-breaking opens',lateDeadline:'Late-breaking closes'
 })[state.dateTypes[0]]:count+' date types';
 get('dateFilterLabel').textContent=label+(alphabetical?' · A–Z':'');
 renderHorizon();renderDirectory();
}
function selectOutlookMonth(next){state.monthKey=next;applyDateView()}
get('dateFilterMenu').addEventListener('change',applyDateView);
document.addEventListener('click',event=>{
 if(!get('dateFilterMenu').contains(event.target))get('dateFilterMenu').open=false;
});
get('dateFilterMenu').addEventListener('keydown',event=>{
 if(event.key==='Escape'){get('dateFilterMenu').open=false;get('dateFilterSummary').focus();}
});
function clearAllConferenceFilters(){
 state.specialties=[];
 state.search='';
 state.status='all';
 state.monthKey=null;
 state.dateTypes=[];
 state.sort='meeting';
 get('searchInput').value='';
 get('statusFilter').value='all';
 document.querySelectorAll('input[name="date-type"]').forEach(input=>{input.checked=false;});
 get('dateSortName').checked=false;
 get('dateFilterLabel').textContent='All dates';
 get('dateFilterMenu').open=false;
 initSpecialties();
 syncCalendarSpecialty();
 renderHorizon();renderDirectory();
 if(state.exploreMode==='calendar')renderCalendar();
}
get('clearAllFilters').addEventListener('click',clearAllConferenceFilters);
get('horizonStrip').addEventListener('click',e=>{const btn=e.target.closest('[data-outlook-month]');if(!btn)return;selectOutlookMonth(state.monthKey===btn.dataset.outlookMonth?null:btn.dataset.outlookMonth)});
get('clearMonth').addEventListener('click',()=>selectOutlookMonth(null));
get('outlookPrev').addEventListener('click',()=>get('horizonScroll').scrollBy({left:-530,behavior:'smooth'}));get('outlookNext').addEventListener('click',()=>get('horizonScroll').scrollBy({left:530,behavior:'smooth'}));
const specialties=['All specialties',...new Set(C.map(c=>c.specialty))].sort((a,b)=>a==='All specialties'?-1:b==='All specialties'?1:a.localeCompare(b));
const fundingSpecialties=['All specialties',...new Set(A.flatMap(a=>a.specialties||[]).filter(s=>s!=='All specialties'))].sort((a,b)=>a==='All specialties'?-1:b==='All specialties'?1:a.localeCompare(b));
function awardSpecialties(a){return a.specialties?.length?a.specialties:(a.conferenceId?[C.find(c=>c.id===a.conferenceId)?.specialty].filter(Boolean):['All specialties']);}
function awardMatchesSpecialty(a,selected){const terms=awardSpecialties(a);return !selected.length||terms.includes('All specialties')||selected.some(s=>terms.includes(s));}
function setFundingSpecialty(s){state.fundingSpecialties=toggleSelectedSpecialty(state.fundingSpecialties,s);renderFunding();}
get('clearFundingSpecialties').addEventListener('click',()=>{
 if(state.fundingSpecialties.length)setFundingSpecialty('All specialties');
});
function navigateToAward(id){const a=A.find(a=>a.id===id);if(!a)return;state.funding='all';state.fundingSpecialties=awardSpecialties(a).filter(s=>s!=='All specialties').slice(0,1);nav('funding');setTimeout(()=>{const card=document.querySelector('[data-award-card="'+id+'"]');if(card){card.scrollIntoView({behavior:'smooth',block:'center'});card.classList.add('funding-highlight');setTimeout(()=>card.classList.remove('funding-highlight'),2600)}},60)}
function matchesSelectedSpecialty(s,selected){return !selected.length||selected.includes(s)}
function toggleSelectedSpecialty(selected,s){if(s==='All specialties')return [];return selected.includes(s)?selected.filter(x=>x!==s):[...selected,s]}
function specialtyLabel(selected){return !selected.length?'All specialties':selected.length===1?selected[0]:selected.length===2?selected.join(' + '):selected.length+' specialties selected'}
function specialtyButtons(items,selected,attribute){return items.map(s=>{const active=s==='All specialties'?!selected.length:selected.includes(s);return `<button type="button" class="chip ${active?'active':''}" ${attribute}="${escape(s)}" aria-pressed="${active}">${escape(s)}</button>`}).join('')}
function syncCalendarSpecialty(){get('calendarSpecialty').value=state.specialties.length>1?'Selected':state.specialties[0]||'All'}
function initSpecialties(){
 get('specialtyChips').innerHTML=specialtyButtons(specialties,state.specialties,'data-specialty');
 get('mobileSpecialtyOptions').innerHTML=specialtyButtons(specialties,state.specialties,'data-specialty');
 get('mobileSpecialtySummary').textContent='Specialties: '+specialtyLabel(state.specialties);
 get('clearConferenceSpecialties').classList.toggle('hidden',!state.specialties.length);
 get('calendarSpecialty').innerHTML=`<option value="All">All specialties</option>`+(state.specialties.length>1?`<option value="Selected">${state.specialties.length} selected specialties</option>`:'')+specialties.filter(s=>s!=='All specialties').map(s=>`<option value="${escape(s)}">${escape(s)}</option>`).join('');
 syncCalendarSpecialty();
}
function selectSpecialty(s){state.specialties=toggleSelectedSpecialty(state.specialties,s);initSpecialties();renderHorizon();renderDirectory();if(state.exploreMode==='calendar')renderCalendar();}
get('clearConferenceSpecialties').addEventListener('click',()=>{
 if(state.specialties.length)selectSpecialty('All specialties');
});
get('specialtyChips').addEventListener('click',e=>{const t=e.target.closest('[data-specialty]');if(t)selectSpecialty(t.dataset.specialty)});get('mobileSpecialtyOptions').addEventListener('click',e=>{const t=e.target.closest('[data-specialty]');if(t)selectSpecialty(t.dataset.specialty)});
function visibleConferences(){let list=C.filter(c=>matchesSelectedSpecialty(c.specialty,state.specialties)).filter(c=>!state.search||[c.name,c.society,c.specialty,c.city,(c.types||[]).join(' ')].join(' ').toLowerCase().includes(state.search));list=list.filter(c=>{if(state.status==='all')return true;if(state.status==='active')return status(c)[1]!=='closed'&&(!c.end||c.end>=todayKey);if(state.status==='closed')return status(c)[1]==='closed'||!!c.end&&c.end<todayKey;if(state.status==='upcoming')return (!!c.deadline&&c.deadline>=todayKey)||!!c.lateDeadline&&c.lateDeadline>=todayKey;if(state.status==='open')return (!!c.deadline&&c.deadline>=todayKey&&!!c.open&&c.open<=todayKey)||!!c.lateDeadline&&c.lateDeadline>=todayKey&&!!c.lateOpen&&c.lateOpen<=todayKey;if(state.status==='unannounced')return !c.deadline&&!c.lateDeadline;if(state.status==='conflict')return !!c.flag;return true});list=list.filter(c=>matchesMonth(c,state.monthKey,state.dateTypes));list.sort((a,b)=>state.sort==='name'?a.name.localeCompare(b.name):state.sort==='month'&&(state.monthKey||state.dateTypes.length>0)?(selectedDate(a).localeCompare(selectedDate(b))||a.name.localeCompare(b.name)):state.sort==='meeting'?((a.start||a.deadline||'9999').localeCompare(b.start||b.deadline||'9999')||a.name.localeCompare(b.name)):(deadlineOrder(a).localeCompare(deadlineOrder(b))||(a.start||'9999').localeCompare(b.start||'9999')));return list}
function card(c){const st=status(c);const monthEvents=monthMatches(c,state.monthKey,state.dateTypes);const related=monthEvents.length?`<div class="month-match" aria-label="Dates matching the selected month"><span class="month-match-heading">MATCHING ${escape(state.monthKey?date(state.monthKey+'-01').toLocaleDateString('en-US',{month:'long',year:'numeric'}):state.dateTypes.map(t=>DATE_TYPE_NAMES[t]).join(', ').toUpperCase())}</span>${monthEvents.map(ev=>`<span class="month-match-item month-match-${ev.kind}"><strong>${escape(ev.label)}:</strong> ${escape(ev.display)}</span>`).join('')}</div>`:'';return `<article class="conference-card" data-conference="${c.id}" tabindex="0" role="button" aria-label="View ${escape(c.name)} details"><div class="row-identity"><div class="conf-titlewrap"><div class="mini-specialty">${escape(c.specialty)} · ${escape(c.society)}</div><div class="conf-title">${escape(c.name)}</div><span class="status-pill ${st[1]}">${escape(st[0])}</span>${related}</div></div><div class="row-date"><span class="row-label">ABSTRACT DEADLINE</span><strong>${escape(fmt(c.deadline))}</strong><small>${escape(c.open?'Opens '+fmt(c.open):c.deadline?'See submission requirements':'Awaiting official dates')}</small></div><div class="row-date"><span class="row-label">CONFERENCE</span><strong>${escape(dateRange(c.start,c.end))}</strong><small>${escape(c.city||'Location to be announced')}</small></div><span class="row-arrow" aria-hidden="true">→</span></article>`}
function renderDirectory(){const x=visibleConferences();get('selectedSpecialty').textContent=specialtyLabel(state.specialties);const totalInSpecialty=C.filter(c=>matchesSelectedSpecialty(c.specialty,state.specialties)).length;const activeOnly=state.status==='active'&&!state.search&&!state.monthKey;const closedOnly=state.status==='closed'&&!state.search&&!state.monthKey;get('visibleCount').textContent=x.length===totalInSpecialty?`${totalInSpecialty} conferences`:`${totalInSpecialty} total · ${x.length} ${activeOnly?'active':closedOnly?'closed':'shown'}`;get('directorySubtitle').textContent=(state.monthKey||state.dateTypes.length>0)?'Filtered by '+(state.dateTypes.length?state.dateTypes.map(t=>DATE_TYPE_NAMES[t]).join(', '):'all dates')+(state.monthKey?' in '+date(state.monthKey+'-01').toLocaleDateString('en-US',{month:'long',year:'numeric'}):'')+'.':state.specialties.length===0?'Published meeting dates and abstract opportunities across all specialties.':state.specialties.length===1?'Browse '+state.specialties[0].toLowerCase()+' conferences, submission periods and future opportunities.':'Browse conferences across '+state.specialties.length+' selected specialties, submission periods and future opportunities.';
 let last='';get('conferenceGrid').innerHTML=x.map(c=>{if(state.sort==='name')return card(c);let d=state.sort==='month'&&(state.monthKey||state.dateTypes.length>0)?selectedDate(c):state.sort==='meeting'?(c.start||c.deadline):(c.deadline||c.start);let group=d?fmt(d,{month:'long',year:'numeric'}):'Dates to be announced';let hd=group!==last?`<div class="directory-month-heading">${escape(group)}</div>`:'';last=group;return hd+card(c)}).join('');get('emptyDiscover').classList.toggle('hidden',!!x.length);get('emptyDiscover').querySelector('h3').textContent=(state.monthKey||state.dateTypes.length>0)?'No dates match this filter':'No matching conferences';get('emptyDiscover').querySelector('p').textContent=(state.monthKey||state.dateTypes.length>0)?'Choose another month or date type. Unannounced dates are not estimated.':'Try a different specialty, search term, or status filter.'}
get('conferenceGrid').addEventListener('click',e=>{const c=e.target.closest('[data-conference]');if(c)showConference(c.dataset.conference)});get('conferenceGrid').addEventListener('keydown',e=>{const c=e.target.closest('[data-conference]');if(c&&(e.key==='Enter'||e.key===' ')){e.preventDefault();showConference(c.dataset.conference)}});
get('searchInput').addEventListener('input',e=>{state.search=e.target.value.trim().toLowerCase();renderDirectory()});
get('statusFilter').addEventListener('change',e=>{state.status=e.target.value;renderDirectory()});
get('resetFilters').addEventListener('click',clearAllConferenceFilters);
function events(){const E=[];for(const c of C){if(c.deadline)E.push({day:c.deadline,kind:'deadline',title:c.name,label:'Abstract due: '+shortName(c),id:c.id});if(c.open)E.push({day:c.open,kind:'open',title:c.name,label:'Abstracts open: '+shortName(c),id:c.id});if(c.lateDeadline)E.push({day:c.lateDeadline,kind:'deadline',title:c.name+' late-breaking',label:'Late deadline: '+shortName(c),id:c.id});if(c.start){const begin=date(c.start),end=date(c.end||c.start);for(let d=begin;d<=end;d=shift(d,1))E.push({day:key(d),kind:'meeting',title:c.name,label:shortName(c),id:c.id});}}
for(const a of A){const shortAward=a.name.length>23?a.name.slice(0,22)+'…':a.name;if(a.open)E.push({day:a.open,kind:'awardOpen',title:a.name,label:'Award opens: '+shortAward,id:a.conferenceId||null,awardId:a.id});if(a.deadline)E.push({day:a.deadline,kind:'award',title:a.name,label:(a.deadlineLabel||'Award due')+': '+shortAward,id:a.conferenceId||null,awardId:a.id});for(const stage of a.stages||[])if(stage.date)E.push({day:stage.date,kind:'award',title:a.name+' — '+stage.label,label:stage.label+': '+shortAward,id:a.conferenceId||null,awardId:a.id});}
return E}
function shortName(c){return c.name.split(' 2027')[0].replace(' Annual Meeting','').replace(' Scientific Sessions','').slice(0,20)}
function monthStart(y,m){return new Date(y,m,1)}
function setCalendarMonth(y,m){state.calDate=monthStart(y,m);renderCalendar();const active=get('calendarMonthRail').querySelector('.rail-month.active');if(active){const sc=get('calendarMonthRail'),top=active.offsetTop-sc.offsetTop;if(top<sc.scrollTop+8||top>sc.scrollTop+sc.clientHeight-58)active.scrollIntoView({block:'nearest',behavior:'smooth'});}}
function filteredCalendarEvents(){return events().filter(e=>e.awardId?awardMatchesSpecialty(A.find(a=>a.id===e.awardId),state.specialties):matchesSelectedSpecialty(C.find(c=>c.id===e.id)?.specialty,state.specialties)).filter(e=>(e.kind==='deadline'&&get('calDeadlines').checked)||(e.kind==='meeting'&&get('calMeetings').checked)||((e.kind==='award'||e.kind==='awardOpen')&&get('calAwards').checked)||(e.kind==='open'&&get('calDeadlines').checked));}
function calendarMonthSpine(ev){const lower=Math.min(today.getFullYear(),...C.map(c=>Number((c.start||c.deadline||'9999').slice(0,4))).filter(y=>y<2099));const maxYear=Math.max(today.getFullYear()+6,state.calDate.getFullYear()+1);const months=[];for(let year=lower;year<=maxYear;year++){let buttons=[];for(let m=0;m<12;m++){const d=monthStart(year,m),mo=key(d).slice(0,7);const inMonth=ev.filter(x=>x.day.startsWith(mo));const counts={deadline:inMonth.filter(e=>e.kind==='deadline').length,meeting:new Set(inMonth.filter(e=>e.kind==='meeting').map(e=>e.id)).size,open:inMonth.filter(e=>e.kind==='open').length,awardOpen:inMonth.filter(e=>e.kind==='awardOpen').length,award:inMonth.filter(e=>e.kind==='award').length};const dots=['deadline','meeting','open','awardOpen','award'].filter(k=>counts[k]).map(k=>`<span class="rail-dot ${k}" title="${counts[k]} ${k} events"></span>`).join('');const active=d.getFullYear()===state.calDate.getFullYear()&&d.getMonth()===state.calDate.getMonth();buttons.push(`<button type="button" class="rail-month ${active?'active':''} ${mo===todayKey.slice(0,7)?'current':''}" data-rail-month="${mo}" aria-current="${active?'date':'false'}" aria-label="${d.toLocaleString('en-US',{month:'long',year:'numeric'})}, ${inMonth.length} recorded daily events"><span>${d.toLocaleString('en-US',{month:'long'})}</span><span class="rail-dots">${dots||'<span class="rail-empty" aria-label="No recorded dates">·</span>'}</span></button>`)}months.push(`<div class="rail-year"><div class="rail-year-label">${year}</div>${buttons.join('')}</div>`)}get('calendarMonthRail').innerHTML=months.join('');const sc=get('calendarMonthRail'),selected=sc.querySelector('.rail-month.active');if(selected){const delta=selected.getBoundingClientRect().top-sc.getBoundingClientRect().top;sc.scrollTop+=delta-sc.clientHeight/2+selected.clientHeight/2;}}
function calendarEventButton(e,small=false){const desc=e.kind==='deadline'?'Abstract due':e.kind==='meeting'?'Conference':e.kind==='open'?'Abstract submissions open':e.kind==='awardOpen'?'Award applications open':'Award deadline';return `<button type="button" class="${small?'event-pill':'calendar-agenda-event'} ${e.kind}" data-event-id="${escape(e.id||'')}" data-award-id="${escape(e.awardId||'')}" title="${escape(e.title)}">${small?escape(e.label):`<span class="agenda-kind">${desc}</span><strong>${escape(e.title)}</strong>`}</button>`}
function renderCalendar(){const t=state.calDate;get('calendarMonth').textContent=t.toLocaleString('en-US',{month:'long',year:'numeric'});get('calendarJump').value=key(t);let start=monthStart(t.getFullYear(),t.getMonth());let first=shift(start,-start.getDay());const ev=filteredCalendarEvents();calendarMonthSpine(ev);let cells=[];for(let i=0;i<42;i++){const d=shift(first,i),day=key(d),isIn=d.getMonth()===t.getMonth(),dayE=ev.filter(x=>x.day===day).sort((a,b)=>({deadline:0,award:1,awardOpen:2,open:3,meeting:4}[a.kind])-({deadline:0,award:1,awardOpen:2,open:3,meeting:4}[b.kind]));const meetings=dayE.filter(x=>x.kind==='meeting'),others=dayE.filter(x=>x.kind!=='meeting');const weekStart=Math.floor(i/7)*7,weekDays=Array.from({length:7},(_,j)=>key(shift(first,weekStart+j)));const weekMeetings=[...new Map(ev.filter(x=>x.kind==='meeting'&&weekDays.includes(x.day)).map(x=>[x.id,x])).values()].sort((x,y)=>x.id.localeCompare(y.id));const lanes=weekMeetings;const ribbons=lanes.map((meeting,lane)=>{if(!meetings.some(x=>x.id===meeting.id))return '';const prev=i%7!==0&&ev.some(x=>x.kind==='meeting'&&x.id===meeting.id&&x.day===key(shift(d,-1)));if(prev)return '';let span=1;for(let offset=1;offset<7-i%7;offset++){if(!ev.some(x=>x.kind==='meeting'&&x.id===meeting.id&&x.day===key(shift(d,offset))))break;span++;}return `<button type="button" class="meeting-ribbon" style="--meeting-lane:${lane};width:calc(${span*100}% - 14px)" data-event-id="${escape(meeting.id)}" title="${escape(meeting.title)}" aria-label="${escape(meeting.title)} — ${escape(day)}">${escape(meeting.title)}</button>`}).join('');const remaining=others;const shown=remaining.slice(0,2),left=remaining.length-shown.length;// Accommodate accessible 27px meeting ribbons and larger, readable event text.
const ribbonHeight=Math.max(0,lanes.length*30+14);const cellHeight=Math.max(145,110+ribbonHeight);cells.push(`<div class="day-cell ${isIn?'':'outside'} ${day===todayKey?'today':''} ${meetings.length?'has-meetings':''} ${ribbons?'has-ribbon':''}" style="min-height:${cellHeight}px;height:${cellHeight}px"><div class="day-head"><span class="day-num">${d.getDate()}</span></div>${shown.map(x=>calendarEventButton(x,true)).join('')}${left>0?`<button type="button" class="more-events" data-cal-day="${day}">+${left} more</button>`:''}${ribbons}</div>`)}get('calendarGrid').innerHTML=cells.join('');const m=key(t).slice(0,7);const monthEvents=ev.filter(e=>e.day.startsWith(m));const due=monthEvents.filter(e=>e.kind==='deadline').length,meet=new Set(monthEvents.filter(e=>e.kind==='meeting').map(e=>e.id)).size,open=monthEvents.filter(e=>e.kind==='open').length,awardOpens=monthEvents.filter(e=>e.kind==='awardOpen').length,awards=monthEvents.filter(e=>e.kind==='award').length;get('calendarMonthSummary').innerHTML=`<span><strong>${due}</strong> ${due===1?'abstract due':'abstracts due'}</span><span><strong>${meet}</strong> ${meet===1?'meeting':'meetings'}</span><span><strong>${open}</strong> ${open===1?'submissions opening':'submissions opening'}</span><span><strong>${awardOpens}</strong> award ${awardOpens===1?'opening':'openings'}</span><span><strong>${awards}</strong> award ${awards===1?'deadline':'deadlines'}</span>`;const unique=[...new Map(monthEvents.map(e=>[`${e.kind==='meeting'?'meeting':e.day}|${e.kind}|${e.id}|${e.awardId||''}`,e])).values()].sort((a,b)=>a.day.localeCompare(b.day));get('calendarMonthEventCount').textContent=unique.length?unique.length+' dated items':'No published dates';get('calendarMonthEventList').innerHTML=unique.length?unique.map(e=>`<div class="agenda-row"><span class="agenda-date">${e.kind==='meeting'?escape(dateRange(C.find(c=>c.id===e.id)?.start,C.find(c=>c.id===e.id)?.end)):fmt(e.day,{month:'short',day:'numeric',year:'numeric'})}</span>${calendarEventButton(e)}</div>`).join(''):'<div class="calendar-empty-month">No dates have been recorded for this month. This does not mean the societies have no meetings or abstract opportunities scheduled.</div>'}
get('calendarMonthRail').addEventListener('click',e=>{const b=e.target.closest('[data-rail-month]');if(b){const [y,m]=b.dataset.railMonth.split('-').map(Number);setCalendarMonth(y,m-1)}});
function onCalendarEventClick(e){const b=e.target.closest('button');if(!b)return;if(b.dataset.awardId){navigateToAward(b.dataset.awardId);return}if(b.dataset.eventId){showConference(b.dataset.eventId);return}if(b.dataset.calDay){openCalendarDayEvents(b.dataset.calDay)}}
function closeCalendarDayEvents(){get('calendarDayOverlay')?.classList.add('hidden');if(get('calendarDayList'))get('calendarDayList').innerHTML=''}
function openCalendarDayEvents(day){
 const entries=filteredCalendarEvents().filter(x=>x.day===day).sort((a,b)=>a.kind.localeCompare(b.kind)||a.title.localeCompare(b.title));
 get('calendarDayTitle').textContent=fmt(day,{weekday:'long',month:'long',day:'numeric',year:'numeric'});
 get('calendarDayList').innerHTML=entries.map(e=>calendarEventButton(e)).join('');
 get('calendarDayOverlay').classList.remove('hidden');
}
get('calendarDayClose')?.addEventListener('click',closeCalendarDayEvents);
get('calendarDayOverlay')?.addEventListener('click',e=>{if(e.target===get('calendarDayOverlay'))closeCalendarDayEvents()});
get('calendarDayList')?.addEventListener('click',e=>{const b=e.target.closest('button');if(!b)return;closeCalendarDayEvents();if(b.dataset.awardId)navigateToAward(b.dataset.awardId);else if(b.dataset.eventId)showConference(b.dataset.eventId)});
document.addEventListener('keydown',e=>{if(e.key==='Escape')closeCalendarDayEvents()});
get('calendarGrid').addEventListener('click',onCalendarEventClick);get('calendarMonthEventList').addEventListener('click',onCalendarEventClick);
get('prevMonth').addEventListener('click',()=>setCalendarMonth(state.calDate.getFullYear(),state.calDate.getMonth()-1));get('nextMonth').addEventListener('click',()=>setCalendarMonth(state.calDate.getFullYear(),state.calDate.getMonth()+1));get('todayMonth').addEventListener('click',()=>setCalendarMonth(today.getFullYear(),today.getMonth()));get('calendarJump').addEventListener('change',e=>{if(/^\d{4}-\d{2}-\d{2}$/.test(e.target.value)){const [y,m]=e.target.value.split('-').map(Number);setCalendarMonth(y,m-1)}});get('calendarSpecialty').addEventListener('change',e=>{if(e.target.value==='Selected')return;state.specialties=e.target.value==='All'?[]:[e.target.value];initSpecialties();renderHorizon();renderDirectory();renderCalendar()});['calDeadlines','calMeetings','calAwards'].forEach(id=>get(id).addEventListener('change',renderCalendar));
function downloadFile(name,body,mime){const a=document.createElement('a');let u=URL.createObjectURL(new Blob([body],{type:mime}));a.href=u;a.download=name;document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(u),1200)}
function cleanIcs(str){return String(str||'').replace(/\\/g,'\\\\').replace(/\r?\n/g,'\\n').replace(/,/g,'\\,').replace(/;/g,'\\;')}
// iCalendar content lines should not exceed 75 octets. Fold without splitting a Unicode character.
function foldIcsLine(text){let lines=[],part='',bytes=0;const enc=new TextEncoder();for(const char of text){const size=enc.encode(char).length;if(bytes+size>75){lines.push(part);part=' ';bytes=1;}part+=char;bytes+=size;}lines.push(part);return lines.join('\r\n')}
function icsEvents(items){
 const stamp=new Date().toISOString().replace(/[-:]/g,'').replace(/\.\d{3}Z$/,'Z');
 const lines=['BEGIN:VCALENDAR','VERSION:2.0','PRODID:-//RISE Collaborative//Conference Navigator//EN','CALSCALE:GREGORIAN','METHOD:PUBLISH','X-WR-CALNAME:RISE Conference Navigator Milestones'];
 for(const e of items.filter(x=>x.date)){
  const end=e.end&&e.end>=e.date?e.end:e.date;
  const values=['BEGIN:VEVENT','UID:rise-'+String(e.uid).replace(/[^A-Za-z0-9_.-]/g,'-')+'@conference-navigator','DTSTAMP:'+stamp,'DTSTART;VALUE=DATE:'+e.date.replaceAll('-',''),'DTEND;VALUE=DATE:'+key(shift(date(end),1)).replaceAll('-',''),'SUMMARY:'+cleanIcs(e.title),'DESCRIPTION:'+cleanIcs(e.description||'')];
  if(e.url&&/^https?:\/\//.test(e.url))values.push('URL:'+e.url);
  values.push('TRANSP:TRANSPARENT','END:VEVENT');lines.push(...values);
 }
 lines.push('END:VCALENDAR');return lines.map(foldIcsLine).join('\r\n')+'\r\n';
}
function conferenceExportOptions(c){
 const options=[];
 const add=(id,day,end,label,title,group='conference',checked=true,description='',url=c.url)=>{
  if(!day)return;options.push({id,uid:`${c.id}-${id}`,date:day,end:end||day,label,title,group,checked,description:[c.name,c.city||'',description,url||''].filter(Boolean).join(' | '),url});
 };
 add('abstract-open',c.open,null,'Abstract submissions open',c.name+' — Abstract submissions open');
 add('abstract-due',c.deadline,null,'Abstract submission deadline',c.name+' — Abstract submission deadline','conference',true,c.flag==='conflict'?'Deadline disputed across official sources; verify with organizer.': 'Check official cutoff time and time zone.');
 add('meeting',c.start,c.end||c.start,'Conference dates',c.name+' — Conference','conference',true,'All-day event covering the recorded meeting dates.');
 add('late-open',c.lateOpen,null,'Late-breaking submissions open',c.name+' — Late-breaking submissions open','conference',false);
 add('late-due',c.lateDeadline,null,'Late-breaking abstract deadline',c.name+' — Late-breaking abstract deadline','conference',false);
 // Only an explicit conferenceId makes an award conference-linked. Related-society
 // research grants with no meeting requirement should not be auto-attached.
 for(const a of A.filter(a=>a.conferenceId===c.id)){
  const url=a.url||c.url;
  add(`award-${a.id}-open`,a.open,null,a.name+' — Applications open',a.name+' — Applications open','funding',false,'Check award-specific eligibility and meeting requirements.',url);
  add(`award-${a.id}-due`,a.deadline,null,a.name+' — Application deadline',a.name+' — Application deadline','funding',false,'Check award-specific eligibility and closing time.',url);
  for(const [i,stage] of (a.stages||[]).entries())add(`award-${a.id}-stage-${i}`,stage.date,null,a.name+' — '+stage.label,a.name+' — '+stage.label,'funding',false,'Additional funding application milestone.',url);
 }
 return options;
}
function exportPanelMarkup(c,options){
 const rows=group=>options.filter(o=>o.group===group).map((o,i)=>{
  const dateLabel=o.end&&o.end!==o.date?dateRange(o.date,o.end):fmt(o.date);
  return `<label class="export-event-row"><input type="checkbox" data-ics-option="${escape(o.id)}" ${o.checked?'checked':''}><span class="export-event-main"><strong>${escape(o.label)}</strong><small>${escape(dateLabel)}${o.group==='funding'?' · Optional funding':''}</small></span><span class="export-event-dot ${o.id.startsWith('award-')?'award':o.id==='meeting'?'meeting':o.id.includes('open')?'open':'deadline'}"></span></label>`;
 }).join('');
 const available=options.length;
 return `<div class="calendar-export-panel hidden" id="calendarExportPanel"><div class="export-panel-head"><div><span class="panel-kicker">SAVE TO YOUR CALENDAR</span><h3>Choose the dates to export</h3><p>One calendar file, with a separate event for each checked milestone.</p></div><button class="export-panel-dismiss" type="button" id="closeCalendarExport" aria-label="Close calendar export">×</button></div><div class="export-event-group"><div class="export-group-heading">Conference milestones</div>${rows('conference')||'<p class="export-empty">No published conference milestones are recorded yet.</p>'}</div>${options.some(o=>o.group==='funding')?`<div class="export-event-group"><div class="export-group-heading">Linked funding & awards <span>optional</span></div>${rows('funding')}</div>`:''}${!c.open?'<p class="export-missing">Abstract opening date not announced — no opening event will be added.</p>':''}${!c.deadline?'<p class="export-missing">Abstract deadline not announced — provisional estimates are not exported as confirmed dates.</p>':''}<div class="export-panel-bottom"><p>Calendar exports are all-day events and a snapshot, not a live sync. Always verify official deadlines and time zones.</p><button type="button" class="btn btn-primary export-download" id="exportSelectedDates" ${available?'':'disabled'}>Download selected dates (.ics) <span id="exportSelectedCount"></span> →</button></div></div>`;
}
function downloadConference(c,events){
 if(!events?.length){showToast('Select at least one date');return}
 downloadFile('RISE_'+c.id+'_dates.ics',icsEvents(events),'text/calendar;charset=utf-8');
 showToast(`${events.length} calendar ${events.length===1?'event':'events'} exported in one .ics file`);
}
function closeModal(){
 if(get('modalScrim').classList.contains('hidden'))return;
 const route=history.state?.riseNavigator;
 if(route?.modal===state.selected&&route.depth>0){history.back();return}
 dismissModal();
 recordRoute(true);
}
get('modalClose').addEventListener('click',closeModal);
get('modalScrim').addEventListener('click',e=>{if(e.target===get('modalScrim'))closeModal()});
document.addEventListener('keydown',e=>{if(e.key==='Escape')closeModal()});
function awardLinkHTML(a){return `<div class="related-award"><div class="related-award-details"><span class="award-type">${escape(a.category)} · ${escape(a.amount)}</span><strong>${escape(a.name)}</strong><small>${a.open?'Opens '+escape(fmt(a.open))+' · ':''}${a.deadline?(a.deadlineLabel||'Apply by')+' '+escape(fmt(a.deadline)):'Closing date not confirmed'}</small></div><button type="button" class="btn btn-soft" data-related-award="${escape(a.id)}">View funding details →</button></div>`}
function presentationOptions(c){const formats=c.presentationFormats||[];const status=formats.length?`<strong>Formats confirmed for this meeting:</strong> ${escape(formats.join(' · '))}`:'<strong>Presentation formats have not been verified for this meeting year.</strong>';const guidance=c.presentationPolicy||'Your preferred format is not a guaranteed option. Societies may select oral/poster placement, restrict formats by category, or use a separate application.';return `<div class="format-note">${status}<p>${escape(guidance)}</p>${c.presentationSource?safeExternal(c.presentationSource,'Official presentation policy'):''}</div>`}
function showConference(id,track=true){const c=C.find(c=>c.id===id);if(!c)return;state.selected=id;const awardList=A.filter(a=>a.conferenceId===id||a.relatedConferenceId===id);let limitText=c.limit?`${c.limit.toLocaleString()} ${c.limitType==='words'?'words':'characters'}${c.limitType==='characters_no_spaces'?' (spaces excluded)':''}`:'Not yet confirmed';const detail=(label,value,sub='')=>`<div class="detail-block"><div class="detail-label">${label}</div><div class="detail-value">${escape(value)}</div>${sub?`<div class="detail-sub">${escape(sub)}</div>`:''}</div>`;get('modalBody').innerHTML=`<div class="modal-head"><div class="mini-specialty">${escape(c.specialty)} · ${escape(c.society)}</div><h2 id="modalTitle">${escape(c.name)}</h2><p>${ico('map')} ${escape(c.city)} &nbsp;·&nbsp; ${escape(c.start?fmt(c.start)+' – '+fmt(c.end||c.start):'Meeting date to be announced')}</p><div class="card-status"><span class="status-pill ${source(c)}">${escape(sourceLabel(c))}</span> <span class="status-pill ${status(c)[1]}">${escape(status(c)[0])}</span></div></div><div class="modal-content"><div class="modal-quick-actions"><div class="modal-quick-official">${safeExternal(c.url,'Official conference details','btn btn-soft modal-official-link')}</div><div class="modal-quick-plan"><button type="button" class="btn btn-primary modal-plan-button" id="modalPlan">Plan for this meeting →</button></div></div><div class="modal-section-title">Conference details</div><div class="modal-grid">${detail('Abstract submissions open',fmt(c.open),c.open?'':'Not posted / not checked')}${detail('Regular abstract deadline',fmt(c.deadline),c.deadlineTime||'')}${detail('Late-breaking deadline',fmt(c.lateDeadline),c.lateOpen?'Opens '+fmt(c.lateOpen):'')}${detail('Length requirement',limitText,c.limitNote||'Different categories may have separate rules')}${detail('Meeting location',c.city||'To be announced',dateRange(c.start,c.end))}<div class="detail-block conference-cost-detail"><div class="detail-label">Conference costs</div><div class="cost-detail-row"><span>Registration</span><strong>${escape(c.registrationFee||'Not verified')}</strong></div><div class="cost-detail-row"><span>Abstract submission</span><strong>${escape(c.fee||'Not verified')}</strong></div><div class="detail-sub">${safeExternal(c.registrationSource||c.url,'Check official fees')}</div></div></div>${c.note?`<div class="modal-section-title">Important notes</div><div class="modal-note ${c.flag==='conflict'?'warning':''}">${escape(c.note)}</div>`:''}<div class="modal-section-title">Submission categories and presentation formats</div><div class="submission-warning">Topic labels are provided for reference; confirm accepted submission categories and oral or poster presentation options in the official instructions.</div><div class="mini-tags">${(c.types||[]).map(t=>`<span class="mini-tag">${escape(t)}</span>`).join('')}</div><p class="category-provenance">${c.submissionCategoriesVerified?'Official meeting categories reviewed':'Tracker-listed topics; exact categories and eligibility not verified for this meeting year'}</p><div id="presentationOptions" aria-live="polite"></div>${awardList.length?`<div class="modal-section-title">Funding and awards</div><div class="related-awards">${awardList.map(awardLinkHTML).join('')}</div>`:''}<div class="modal-actions"><div class="modal-secondary-actions">${c.guideline?safeExternal(c.guideline,'Submission rules','btn btn-soft'):''}${c.submissionSource&&c.submissionSource!==c.guideline?safeExternal(c.submissionSource,'Submission portal','btn btn-soft'):''}<button type="button" class="btn btn-soft" id="modalExport" aria-controls="calendarExportPanel" aria-expanded="false">Export conference dates ↓</button></div></div>${exportPanelMarkup(c,conferenceExportOptions(c))}</div>`;get('modalScrim').classList.remove('hidden');document.body.style.overflow='hidden';get('conferenceModal').scrollTop=0;if(track)recordRoute();get('presentationOptions').innerHTML=presentationOptions(c);get('modalBody').querySelectorAll('[data-related-award]').forEach(b=>b.addEventListener('click',()=>navigateToAward(b.dataset.relatedAward)));const exportButton=get('modalExport'),exportPanel=get('calendarExportPanel'),allOptions=conferenceExportOptions(c);
 const chosenExportEvents=()=>allOptions.filter(o=>exportPanel.querySelector(`[data-ics-option=\"${o.id}\"]`)?.checked);
 const refreshExportCount=()=>{const n=chosenExportEvents().length;get('exportSelectedCount').textContent=`(${n})`;get('exportSelectedDates').disabled=!n};
 exportButton.addEventListener('click',()=>{const isHidden=exportPanel.classList.toggle('hidden');exportButton.setAttribute('aria-expanded',String(!isHidden));if(!isHidden){refreshExportCount();exportPanel.scrollIntoView({block:'nearest',behavior:'smooth'})}});
 get('closeCalendarExport').addEventListener('click',()=>{exportPanel.classList.add('hidden');exportButton.setAttribute('aria-expanded','false')});
 exportPanel.addEventListener('change',refreshExportCount);
 get('exportSelectedDates').addEventListener('click',()=>downloadConference(c,chosenExportEvents()));
 get('modalPlan').addEventListener('click',()=>{selectPlannerTarget(c.id);state.plan=null;nav('planner')})}
const defaults={retrospective:24,case:8,qi:24,systematic:20,medicaleducation:20,prospective:52};
const models={retrospective:[['Scope question & find mentor','Agree on study population, feasibility, endpoints and faculty oversight.',0],['Protocol, IRB/determination & data access','Obtain required IRB review/exemption/determination and permissions before regulated extraction.',.14],['Chart abstraction & data quality','Collect approved data, maintain secure records, validate inclusion criteria.',.32],['Analysis & interpretation','Run primary analyses and review limitations with collaborators.',.65],['Draft abstract & coauthor review','Check conference structure, word limits, authorship, originality and embargo.',.81],['Internal review & submit','Allow time for mentor sign-off, disclosures and submission portal checks.',.94]],case:[['Identify teaching point & mentor','Confirm novelty, learning objectives and conference fit.',0],['Consent and de-identification','Follow institutional case-report consent and privacy requirements.',.16],['Clinical narrative & literature review','Assemble chronology, differential and relevant comparisons.',.35],['Draft structured abstract','Match conference category and length/figure requirements.',.60],['Coauthor review & submit','Secure approvals and submit ahead of portal closure.',.89]],qi:[['Define aim & measures','Establish aim statement, balancing measures and stakeholder team.',0],['QI vs research determination','Obtain institutional determination and any required approvals.',.12],['Baseline measurement','Establish reliable data collection and process map.',.28],['Intervention / PDSA cycles','Test changes, monitor implementation and track outcomes.',.45],['Analyze results','Assess improvement, sustainability, limitations and unintended consequences.',.72],['Draft abstract & submit','Focus on intervention, methods, outcomes and conclusions.',.87]],systematic:[['Define PICO and protocol','Align on question, eligibility criteria, team and registration needs.',0],['Search strategy & registration','Develop reproducible search; register protocol where appropriate.',.14],['Screen and extract evidence','Duplicate screening and structured extraction.',.31],['Risk of bias & synthesis','Appraise evidence, consider quantitative pooling if appropriate.',.59],['Draft findings','Ensure conclusions reflect evidence and heterogeneity.',.80],['Coauthor approval & submit','Finalize disclosures, references, category and word count.',.93]],medicaleducation:[['Identify educational gap','Select learning objectives and evaluation strategy.',0],['Approvals and curriculum design','Confirm QI/research pathway and permissions as applicable.',.15],['Implement educational intervention','Deliver curriculum, gather appropriate evaluation data.',.36],['Evaluate outcomes','Analyze learner and implementation outcomes.',.66],['Write innovation abstract','Describe replicability, impact and barriers.',.83],['Coauthor review & submit','Finalize abstract and disclosures.',.94]],prospective:[['Feasibility & funding','Finalize hypothesis, design, site, recruitment and resources.',0],['Protocol & regulatory review','Obtain required approvals, consent processes and registration.',.17],['Recruitment & data collection','Prospective enrollment and prespecified data capture after clearance.',.35],['Data cleaning & analysis','Reconcile missing data and analyze planned endpoints.',.72],['Manuscript-level review','Interpret findings and meet coauthor obligations.',.87],['Finalize abstract & submit','Submit only when required results are sufficiently mature.',.96]]};
// A planning assumption is never persisted as, or styled as, an official submission deadline.
function planningTarget(c,leadMonths=6){
 if(c.deadline)return {day:c.deadline,estimated:false,conflict:!!c.flag,explanation:c.flag?'Reported abstract date needs organizer confirmation.':'Abstract date listed in the conference record.'};
 if(!c.start)return null;
 const meeting=date(c.start),lead=Math.max(1,Math.min(12,Number(leadMonths)||6));
 const month=meeting.getMonth()-lead,year=meeting.getFullYear(),last=new Date(year,month+1,0).getDate();
 const estimated=new Date(year,month,Math.min(meeting.getDate(),last));
 return {day:key(estimated),estimated:true,conflict:false,leadMonths:lead,explanation:`Illustrative target ${lead} months before the meeting. This is not an announced submission deadline.`};
}
// Recommended target, not an organizer's deadline: leave room for coauthor
// sign-off, upload errors and corrections. A very short published submission
// window limits how much advance buffer we can honestly recommend.
function submissionPlanTarget(c,leadMonths=6){
 const target=planningTarget(c,leadMonths);
 if(!target)return null;
 const due=date(target.day),opened=c.open?date(c.open):null;
 const windowDays=opened&&opened<=due?Math.round((due-opened)/86400000):null;
 const bufferDays=windowDays===null?10:Math.min(10,Math.max(0,Math.floor(windowDays/3)));
 return {...target,bufferDays,internalDay:key(shift(due,-bufferDays))};
}
function roadmapMarkup(c,type,weeks,compact=false,leadMonths=6,readiness='idea',presentation='either'){
 const target=submissionPlanTarget(c,leadMonths);
 if(!target)return `<div class="roadmap-empty">No meeting or abstract date is published yet. Please check the society website for updates.</div>`;
 const due=date(target.day),submitBy=date(target.internalDay),meetingStart=c.start?date(c.start):null;
 const meetingEnd=date(c.end||c.start)||(due?shift(due,28):null);
 // Plan to FINISH at the resident's earlier submission goal, not the society's final cutoff.
 const start=shift(submitBy,-weeks*7),end=meetingEnd&&meetingEnd>due?meetingEnd:shift(due,28);
 const open=c.open?date(c.open):null;
 const left=new Date(Math.min(start.getTime(),today.getTime()-86400000*14,open?open.getTime():start.getTime()));
 const right=new Date(Math.max(end.getTime()+86400000*7,today.getTime()+86400000*14));
 const total=right-left,pct=d=>Math.max(0,Math.min(100,100*(d-left)/total));
 const steps=models[type]||models.retrospective;
 const dates=steps.map(step=>shift(start,Math.round(weeks*7*step[2])));
 const phases=steps.map((step,i)=>({title:step[0],from:dates[i],to:i+1<dates.length?dates[i+1]:submitBy}));
 // A conference poster is NOT a months-long workstream. Reserve the last 2–4 weeks.
 if(meetingStart&&meetingStart>due){const prepStart=new Date(Math.max(shift(meetingStart,-28).getTime(),due.getTime()));if(prepStart<meetingStart)phases.push({title:(presentation==='oral'?'Oral presentation preparation':presentation==='poster'?'Poster preparation':'Presentation preparation')+' · ~2–4 weeks',from:prepStart,to:meetingStart});}
 const mons=[];let cur=new Date(left.getFullYear(),left.getMonth(),1);
 while(cur<=right&&mons.length<60){mons.push(new Date(cur));cur=new Date(cur.getFullYear(),cur.getMonth()+1,1)}
 const ticks=mons.map((m,i)=>{const x=pct(m);if(x<4||x>97||i%2!==0)return '';return `<span class="roadmap-tick" style="left:${x.toFixed(2)}%"><i></i>${escape(m.toLocaleDateString('en-US',{month:'short',year:'2-digit'}))}</span>`}).join('');
 const todayPct=pct(today),duePct=pct(due),internalPct=pct(submitBy),openPct=open?pct(open):null,meetingPct=meetingStart?pct(meetingStart):null;
 const guide=(klass,x)=>x===null?'':`<span class="v6-guide ${klass}" style="left:${x.toFixed(2)}%" aria-hidden="true"></span>`;
 // Only the external event dates get full vertical markers. The internal goal is a separate point, not another competing line.
 const guides=guide('today',todayPct)+guide('opening',openPct)+guide(target.estimated?'deadline estimated':'deadline',duePct)+guide('conference',meetingPct);
 const barRows=phases.map((phase,i)=>{const x=pct(phase.from),w=Math.max(.42,pct(phase.to)-x);return `<div class="roadmap-row"><div class="roadmap-row-label">${escape(phase.title)}</div><div class="roadmap-lane"><span class="roadmap-bar shade-${i===phases.length-1&&meetingStart?'5':Math.min(i,4)}" style="left:${x.toFixed(2)}%;width:${w.toFixed(2)}%" title="${escape(fmt(key(phase.from))+' – '+fmt(key(phase.to)))}"></span></div></div>`}).join('');
 const marker=(klass,label,display,x,row)=>x===null?'':`<span class="v6-event-label ${klass}" style="--event-x:${x.toFixed(2)}%;--event-row:${row}" title="${escape(label+' — '+display)}"><strong>${escape(label)}</strong><small>${escape(display)}</small></span>`;
 const eventFlags=marker('opening','Submissions open',fmt(c.open),openPct,0)
   +marker('internal','Aim to submit',fmt(target.internalDay),internalPct,1)
   +marker(target.estimated?'deadline estimated':'deadline',target.estimated?'Estimated abstract due':target.conflict?'Unverified abstract due':c.evidence==='official'?'Official abstract due':'Listed abstract due',fmt(target.day),duePct,2)
   +marker('conference','Conference',fmt(c.start),meetingPct,3);
 const days=daysAway(target.day),internalDays=daysAway(target.internalDay),shortPlan=Math.max(14,Math.round(weeks*7*.35));
 let signal,advice;
 if(days<0){signal='missed';advice=`The abstract cutoff was ${Math.abs(days)} days ago. Check for an eligible late-breaking category or consider the next annual cycle.`;}
 else if(days===0){signal='caution';advice='The listed abstract cutoff is today. The early-submission buffer is gone; check the official portal and closing time immediately.';}
 else if(internalDays<0){signal='caution';advice=`Your suggested submit-by target has passed. ${days} days remain until the ${target.estimated?'provisional':'published'} abstract cutoff. Prioritize coauthor sign-off and submit as soon as ready.`;}
 else if(internalDays===0){signal='caution';advice=`Today is your suggested submit-by date (${target.bufferDays}-day buffer). If the abstract is ready and approved, submit rather than waiting until the final cutoff.`;}
 else if(readiness==='ready'){signal='good';advice=`Your earlier submit-by goal is ${fmt(target.internalDay)} (${internalDays} days away). With results or a draft, prioritize mentor feedback, disclosures and formatting.`;}
 else if(readiness==='working'&&internalDays>=shortPlan){signal='good';advice=`You have ${internalDays} days to the early-submission goal. Work underway may fit if the required approvals and results can be completed on schedule.`;}
 else if(internalDays>=weeks*7){signal='good';advice=`You have about ${Math.floor(internalDays/7)} weeks until the early submit-by goal. There is room for an illustrative ${weeks}-week project plan.`;}
 else{signal='caution';advice=`Only ${internalDays} days remain before the recommended early-submission goal—less than the ${weeks}-week baseline for this project. Consider existing data, a narrower scope, or the next cycle.`;}
 const confidence=target.estimated?'The abstract cutoff itself is provisional, not officially announced.':target.conflict?'Published sources conflict: verify the organizer deadline.':'Confirm the official closing time and requirements before submitting.';
 const status=`<div class="v6-feasibility ${signal}"><span class="v6-feasibility-symbol">${signal==='good'?'↗':signal==='missed'?'!':'◷'}</span><div><strong>${signal==='good'?'Planning window available':signal==='missed'?'Regular deadline passed':'Time-sensitive planning'}</strong><p>${escape(advice)} <span>${escape(confidence)}</span></p></div></div>`;
 const tag=target.estimated?`<span class="estimate-chip">ESTIMATED · ${target.leadMonths} MONTHS PRE-MEETING</span>`:target.conflict?'<span class="estimate-chip caution">CONFLICTING DEADLINE — VERIFY</span>':'<span class="confirmed-chip">PUBLISHED DEADLINE</span>';
 const bufferNotice=`<div class="v7-buffer-note"><span class="v7-buffer-symbol">✓</span><div><strong>Submit early: ${escape(fmt(target.internalDay))}</strong><span>${target.bufferDays?`${target.bufferDays}-day planning buffer before the ${target.estimated?'estimated':'listed'} cutoff`:'Submission window is too short for an advance buffer'}. Aim to finish the draft and coauthor review before this date.</span></div></div>`;
 return `<div class="roadmap-block v6-roadmap v7-roadmap ${compact?'compact':''} ${target.estimated?'provisional':''}"><div class="roadmap-explainer"><div><strong>${escape(fmt(key(start)))} – ${escape(fmt(target.internalDay))}</strong><span>${weeks}-week illustrative plan to your early submit-by goal</span></div>${tag}</div>${status}${bufferNotice}<div class="v6-roadmap-heading">PROJECT STAGES <span>Suggested work periods—not mandatory time commitments</span></div><div class="v6-canvas"><div class="v6-guides">${guides}</div><div class="v6-today-top"><span class="v6-today-tag" style="left:clamp(50px,${todayPct.toFixed(2)}%,calc(100% - 50px))">YOU ARE HERE <small>${escape(fmt(todayKey,{month:'short',day:'numeric',year:'numeric'}))}</small></span></div><div class="v6-axis">${ticks}</div><div class="v6-stages">${barRows}</div><div class="v6-bottom-rail"><div class="v6-event-labels">${eventFlags}</div></div></div><p class="roadmap-disclaimer">${c.open?'':'Abstract submission opening date not yet announced. '}${escape(target.explanation)} Submit-by goal is a planning recommendation—not an organizer deadline. Timelines are illustrative; institutional approvals and conference requirements take precedence.</p></div>`;
}
function roadmapExportSvg(plan){
 const conf=C.find(c=>c.id===plan.id);
 if(!conf||!plan.target||!plan.steps.length)throw Error('No research roadmap is available');
 const W=1120, L=48, R=1072;
 const target=plan.target, due=date(target.day), submit=date(target.internalDay);
 const meetingStart=date(conf.start), meetingEnd=date(conf.end||conf.start);
 const typeNames={retrospective:'Retrospective chart review',case:'Case report / case series',qi:'Quality improvement',systematic:'Systematic review / meta-analysis',medicaleducation:'Medical education',prospective:'Prospective clinical study'};
 const readinessNames={idea:'Starting with an idea',working:'Project underway',ready:'Results or draft ready'};
 const presentationNames={either:'Poster or oral',poster:'Poster',oral:'Oral presentation'};
 const stages=plan.steps.map((step,i)=>({title:step.title,from:date(step.day),to:i+1<plan.steps.length?date(plan.steps[i+1].day):submit}));
 if(meetingStart && meetingStart>due){
   const from=new Date(Math.max(shift(meetingStart,-28).getTime(),due.getTime()));
   if(from<meetingStart)stages.push({title:plan.presentation==='oral'?'Oral presentation preparation':plan.presentation==='poster'?'Poster preparation':'Presentation preparation',from,to:meetingStart});
 }
 const chartY=485,rowH=49,chartBottom=chartY+stages.length*rowH;
 const legendY=chartBottom+40,milestoneTitleY=legendY+111,detailY=milestoneTitleY+35,detailH=90;
 const bottom=detailY+plan.steps.length*detailH+118;
 const parts=[`<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${bottom}" viewBox="0 0 ${W} ${bottom}" role="img" aria-labelledby="reportTitle reportDesc"><title id="reportTitle">RISE Conference Navigator research roadmap for ${escape(conf.name)}</title><desc id="reportDesc">Downloadable visual project timeline with conference dates, abstract submission goal, project phases, and detailed milestones.</desc>`];
 const add=markup=>parts.push(markup);
 const rect=(x,y,w,h,fill,rx=0,stroke='none')=>add(`<rect x="${x}" y="${y}" width="${w}" height="${h}" rx="${rx}" fill="${fill}" stroke="${stroke}"/>`);
 const text=(x,y,str,size=14,color='#1d3d48',weight=500,extra='')=>add(`<text x="${x}" y="${y}" font-family="Arial, Helvetica, sans-serif" font-size="${size}" fill="${color}" font-weight="${weight}" ${extra}>${escape(str)}</text>`);
 function lines(str,maxChars){
   const words=String(str||'').split(/\s+/).filter(Boolean),result=[];
   let current='';
   for(const word of words){
     if(current && (current+' '+word).length>maxChars){result.push(current);current=word;}
     else current=current?current+' '+word:word;
   }
   if(current)result.push(current);
   return result.length?result:[''];
 }
 rect(0,0,W,bottom,'#ffffff');
 rect(0,0,W,168,'#12363f');
 rect(48,28,288,5,'#e3b46e',3);
 text(L,61,'RISE CONFERENCE NAVIGATOR',15,'#f3d59f',800,'letter-spacing="2"');
 text(L,104,'RESEARCH ROADMAP',34,'#ffffff',800);
 const nameLines=lines(conf.name,86);
 nameLines.slice(0,2).forEach((line,i)=>text(L,137+i*21,line,17,'#d5e7e4',600));
 const dates=[
   ['PROJECT START',fmt(plan.start)],
   ['AIM TO SUBMIT',fmt(target.internalDay)],
   [target.estimated?'ESTIMATED ABSTRACT DUE':'ABSTRACT DEADLINE',fmt(target.day)]
 ];
 const cardY=191,cardW=322,cardGap=15;
 dates.forEach(([label,value],i)=>{
   const x=L+i*(cardW+cardGap);
   rect(x,cardY,cardW,91,'#f2f7f7',12,'#d9e8e6');
   text(x+20,cardY+29,label,12,'#63817e',700,'letter-spacing="1"');
   text(x+20,cardY+63,value,23,'#173e45',800);
 });
 rect(L,299,W-2*L,120,target.estimated?'#fff7ea':'#f5f9f6',12,target.estimated?'#e6d0af':'#ddeae4');
 const type=typeNames[plan.type]||plan.type;
 text(L+19,324,`${type}  •  ${plan.weeks}-week illustrative plan`,16,'#173e45',800);
 text(L+19,349,`Project status: ${readinessNames[plan.readiness]||'Not specified'}    |    Presentation: ${presentationNames[plan.presentation]||'Either'}`,13,'#4b716f',600);
 const guidance=lines(plan.guidance,122).slice(0,2);
 guidance.forEach((line,i)=>text(L+19,374+i*17,line,13,'#617f79',500));
 text(L,452,'PROJECT TIMELINE',17,'#173e45',800,'letter-spacing="1.2"');
 text(L,472,'Stage durations are illustrative; dates are not mandatory commitments.',12,'#6d8585',500);
 rect(48,chartY,1024,stages.length*rowH+4,'#f8fafb',9,'#e0ebe9');
 const xStart=350,xEnd=1040,chartSpan=xEnd-xStart;
 const day0=Math.min(date(plan.start).getTime(),conf.open?date(conf.open).getTime():Infinity,today.getTime()-14*86400000);
 const day1=Math.max((meetingEnd||due).getTime()+9*86400000,today.getTime()+14*86400000);
 const span=Math.max(1,day1-day0);
 const xDate=d=>xStart+Math.max(0,Math.min(1,(d.getTime()-day0)/span))*chartSpan;
 const milestoneGuides=[
  conf.open?{day:date(conf.open),color:'#4e93bd'}:null,
  {day:submit,color:'#d28a3b'},
  {day:due,color:'#bd697e'},
  meetingStart?{day:meetingStart,color:'#6d5eaf'}:null
 ].filter(Boolean);
 milestoneGuides.forEach(m=>add(`<line x1="${xDate(m.day)}" y1="${chartY}" x2="${xDate(m.day)}" y2="${chartBottom}" stroke="${m.color}" stroke-width="1.7" opacity=".65" stroke-dasharray="5,4"/>`));
 const barColors=['#337d9b','#368b88','#536caa','#7b77b0','#ba9071','#468f77','#926ba7'];
 stages.forEach((stage,i)=>{
   const y=chartY+i*rowH+10;
   if(i) add(`<line x1="56" x2="1064" y1="${chartY+i*rowH}" y2="${chartY+i*rowH}" stroke="#e6edec"/>`);
   const titleLines=lines(stage.title,34);
   titleLines.slice(0,2).forEach((line,j)=>text(64,y+10+j*15,line,12,'#314f59',700));
   const a=xDate(stage.from),b=xDate(stage.to);
   rect(a,y,Math.max(5,b-a),25,barColors[i%barColors.length],5);
   text(Math.min(a+7,xEnd-95),y+41,`${fmt(key(stage.from),{month:'short',day:'numeric'})}`,10,'#708486',500);
 });
 const legend=[
  conf.open?['Submissions open',fmt(conf.open),'#4e93bd']:['Submissions open','Not announced','#aeb5b7'],
  ['Your early submit-by goal',fmt(target.internalDay),'#d28a3b'],
  [target.estimated?'Illustrative abstract deadline':'Listed abstract deadline',fmt(target.day),'#bd697e'],
  ['Conference begins',fmt(conf.start),'#6d5eaf']
 ];
 legend.forEach(([label,value,color],i)=>{
   const x=L+(i%2)*515,y=legendY+Math.floor(i/2)*35;
   rect(x,y-10,8,8,color,2);
   text(x+18,y-2,label,12,'#395c63',700);
   text(x+280,y-2,value,12,'#395c63',600);
 });
 text(L,milestoneTitleY,'MILESTONES & DELIVERABLES',17,'#173e45',800,'letter-spacing="1"');
 plan.steps.forEach((step,i)=>{
   const y=detailY+i*detailH;
   rect(L,y,W-L*2,detailH-9,i%2?'#f8fbfa':'#f1f7f6',9);
   rect(L+15,y+16,26,26,'#2d7175',13);
   text(L+28,y+34,String(i+1),12,'#ffffff',800,'text-anchor="middle"');
   text(L+56,y+35,step.title,16,'#22434c',800);
   text(R-19,y+34,fmt(step.day),13,'#3a746f',700,'text-anchor="end"');
   lines(step.desc,136).slice(0,2).forEach((line,j)=>text(L+56,y+58+j*16,line,12,'#627c7e',500));
 });
 const footY=detailY+plan.steps.length*detailH+19;
 add(`<line x1="${L}" x2="${R}" y1="${footY}" y2="${footY}" stroke="#d9e7e3"/>`);
 const note=target.estimated?'The society abstract deadline is not announced. The indicated cutoff is an illustrative planning assumption.':target.conflict?'The listed abstract deadline has conflicting sources. Verify it directly with the organizer.':'Confirm the official abstract deadline, closing time, and submission requirements with the organizer.';
 lines(note+' Your submit-by date is an internal planning target, not the conference deadline.',145).slice(0,2).forEach((line,i)=>text(L,footY+25+i*16,line,12,'#516d71',500));
 text(L,footY+70,`RISE Conference Navigator  •  Generated ${new Date().toLocaleDateString('en-US')}`,12,'#7b9694',600);
 add('</svg>');
 return parts.join('');
}

function downloadRoadmapVisual(){
 if(!state.plan){showToast('Generate a roadmap first');return;}
 try{
  const filename='RISE_Conference_Navigator_'+state.plan.id+'_Research_Roadmap.svg';
  downloadFile(filename,roadmapExportSvg(state.plan),'image/svg+xml;charset=utf-8');
  showToast('Visual roadmap downloaded as SVG');
 }catch(err){showToast('Unable to export the visual roadmap');}
}

function printRoadmapPdf(){
 if(!state.plan){showToast('Generate a roadmap first');return;}
 const win=window.open('','_blank');
 if(!win){showToast('Allow pop-ups to save the roadmap as PDF, or download the SVG');return;}
 try{
  const svg=roadmapExportSvg(state.plan);
  win.document.open();
  win.document.write('<!doctype html><html lang="en"><head><meta charset="utf-8"><title>RISE Conference Navigator — Research Roadmap</title><style>@page{size:A4 portrait;margin:8mm}*{box-sizing:border-box}body{margin:0;background:#edf3f2;font:13px Arial,sans-serif}.toolbar{padding:12px;text-align:center}.toolbar button{background:#164e60;color:white;border:0;border-radius:7px;padding:10px 18px;font-weight:700;cursor:pointer}.report{max-width:900px;margin:auto;box-shadow:0 7px 30px #0002;background:white}.report svg{display:block;width:100%;height:auto}@media print{.toolbar{display:none}body{background:white}.report{box-shadow:none;max-width:none}.report svg{width:100%;max-height:calc(297mm - 16mm);height:auto}}</style></head><body><div class="toolbar"><button onclick="window.print()">Print / Save as PDF</button><p>Choose “Save as PDF” in the print destination to download a PDF copy.</p></div><div class="report">'+svg+'</div></body></html>');
  win.document.close();
  win.focus();
  win.setTimeout(()=>win.print(),350);
 }catch(err){win.close();showToast('Unable to open the printable roadmap');}
}

/* The selected conference stays independent from search/filter results so
   users can explore alternatives without silently changing their roadmap. */
const plannerConferences=C.filter(c=>c.deadline||c.start);
let plannerVisibleLimit=9;
function plannerTargetSort(a,b,sort){
 const alpha=()=>a.name.localeCompare(b.name);
 if(sort==='name')return alpha();
 if(sort==='latest')return (b.start||b.deadline||'').localeCompare(a.start||a.deadline||'')||alpha();
 const when=c=>sort==='deadline'?(c.deadline||c.lateDeadline||null):(c.start||c.deadline||null);
 const coming=d=>d&&d>=todayKey?d:'9999-12-31';
 return coming(when(a)).localeCompare(coming(when(b)))
     || (when(a)||'9999-12-31').localeCompare(when(b)||'9999-12-31')
     || alpha();
}
function plannerTargetMatches(){
 const terms=get('planSearch').value.trim().toLocaleLowerCase().split(/\s+/).filter(Boolean);
 const specialty=get('planSpecialty').value;
 const sort=get('planSort').value;
 return plannerConferences.filter(c=>{
  if(specialty!=='all'&&c.specialty!==specialty)return false;
  const haystack=[c.name,c.society,c.specialty,c.city,c.start,c.end,c.deadline,c.lateDeadline,
   c.start?fmt(c.start,{month:'long',day:'numeric',year:'numeric'}):'',
   c.deadline?fmt(c.deadline,{month:'long',day:'numeric',year:'numeric'}):''
  ].filter(Boolean).join(' ').toLocaleLowerCase();
  return terms.every(term=>haystack.includes(term));
 }).sort((a,b)=>plannerTargetSort(a,b,sort));
}
function renderPlannerTargets(){
 const active=get('planConference').value;
 const selected=C.find(c=>c.id===active);
 const results=plannerTargetMatches();
 const visible=results.slice(0,plannerVisibleLimit);
 get('planSelectedConference').innerHTML=selected?
  `<span class="planner-current-label">SELECTED CONFERENCE</span><strong>${escape(selected.name)}</strong><span>${escape(selected.specialty)} · ${escape(selected.start?dateRange(selected.start,selected.end):'Meeting date not announced')}</span>`:
  '<span class="planner-current-label">SELECT A CONFERENCE</span>';
 get('planResultCount').textContent=results.length?
  `Showing ${visible.length} of ${results.length} matching ${results.length===1?'conference':'conferences'}`:
  'No conferences match these filters';
 get('planConferenceMatches').innerHTML=visible.length?visible.map(c=>{
  const isActive=c.id===active,meeting=c.start?dateRange(c.start,c.end):'Meeting date not announced';
  const due=c.deadline?`Abstract due: ${fmt(c.deadline)}`:c.lateDeadline?`Late-breaking due: ${fmt(c.lateDeadline)}`:'Abstract deadline not announced';
  return `<button type="button" class="planner-target-option ${isActive?'selected':''}" data-planner-target="${escape(c.id)}" aria-pressed="${isActive?'true':'false'}"><strong>${escape(c.name)}</strong><span>${escape(c.specialty)} · ${escape(meeting)}</span><small>${escape(due)}</small></button>`;
 }).join(''):'<p class="planner-target-empty">No matches. Try another specialty or search term.</p>';
 get('planMoreConferences').classList.toggle('hidden',results.length<=plannerVisibleLimit);
 get('planMoreConferences').textContent=`Show more conferences (${results.length-visible.length} remaining) ↓`;
}
function selectPlannerTarget(id){
 if(!plannerConferences.some(c=>c.id===id))return;
 get('planConference').value=id;
 get('planSearch').value='';
 get('planSpecialty').value='all';
 plannerVisibleLimit=9;
 renderPlannerTargets();
}
function initPlanner(){
 const list=[...plannerConferences].sort((a,b)=>plannerTargetSort(a,b,'deadline'));
 get('planConference').innerHTML=plannerConferences.map(c=>`<option value="${escape(c.id)}">${escape(c.name)}</option>`).join('');
 get('planSpecialty').innerHTML='<option value="all">All specialties</option>'+
  [...new Set(plannerConferences.map(c=>c.specialty).filter(Boolean))].sort((a,b)=>a.localeCompare(b)).map(s=>`<option value="${escape(s)}">${escape(s)}</option>`).join('');
 get('planSearch').addEventListener('input',()=>{plannerVisibleLimit=9;renderPlannerTargets()});
 get('planSpecialty').addEventListener('change',()=>{plannerVisibleLimit=9;renderPlannerTargets()});
 get('planSort').addEventListener('change',()=>{plannerVisibleLimit=9;renderPlannerTargets()});
 get('planClearFilters').addEventListener('click',()=>{get('planSearch').value='';get('planSpecialty').value='all';get('planSort').value='meeting';plannerVisibleLimit=9;renderPlannerTargets()});
 get('planMoreConferences').addEventListener('click',()=>{plannerVisibleLimit+=9;renderPlannerTargets()});
 get('planConferenceMatches').addEventListener('click',e=>{
  const option=e.target.closest('[data-planner-target]');
  if(!option)return;
  get('planConference').value=option.dataset.plannerTarget;
  renderPlannerTargets();
  generatePlan();
 });
 get('planConference').addEventListener('change',()=>{renderPlannerTargets();generatePlan()});
 get('planLeadMonths').addEventListener('change',generatePlan);
 get('planType').addEventListener('change',generatePlan);
 get('planReadiness').addEventListener('change',generatePlan);
 get('planPresentation').addEventListener('change',generatePlan);
 get('generatePlan').addEventListener('click',generatePlan);
 get('downloadPlanVisual').addEventListener('click',downloadRoadmapVisual);
 get('printPlanPdf').addEventListener('click',printRoadmapPdf);
 get('downloadPlan').addEventListener('click',()=>{if(!state.plan){showToast('Generate a timeline first');return}const items=state.plan.steps.map((s,i)=>({date:s.day,uid:`${state.plan.id}-${i}`,title:`RISE Conference Navigator project milestone — ${s.title}${state.plan.estimated?' (provisional)':''}`,description:state.plan.name+' | '+s.desc+(state.plan.estimated?' | Dates based on assumed submission target, not official deadline.':'')}));downloadFile('RISE_research_roadmap.ics',icsEvents(items),'text/calendar;charset=utf-8');showToast('Research roadmap exported as .ics')});
 const next=list.find(c=>c.deadline&&c.deadline>=todayKey)||list.find(c=>c.start&&c.start>=todayKey);
 get('planConference').value=next?next.id:list[0]?.id||'';
 renderPlannerTargets();
 generatePlan();
}
function generatePlan(){
 const selectedType=get('planType').value;
 if(!selectedType){state.plan=null;get('planHeading').textContent='Choose your research project type';get('downloadPlan').disabled=true;get('downloadPlanVisual').disabled=true;get('printPlanPdf').disabled=true;get('planResult').innerHTML='<div class="roadmap-awaiting"><strong>Select a project type to begin</strong><span>Choose the type in the highlighted field to generate your research roadmap.</span></div>';return;}
 get('downloadPlan').disabled=false;get('downloadPlanVisual').disabled=false;get('printPlanPdf').disabled=false;
 const c=C.find(c=>c.id===get('planConference').value),lead=Number(get('planLeadMonths').value)||6;
 const target=c?submissionPlanTarget(c,lead):null;
 get('planLeadGroup').classList.toggle('hidden',!!c?.deadline);
 if(!c||!target){state.plan=null;get('downloadPlan').disabled=true;get('downloadPlanVisual').disabled=true;get('printPlanPdf').disabled=true;get('planResult').innerHTML='<div class="plan-summary plan-warning"><strong>No planning anchor available</strong><p>Select a conference with a meeting date or abstract submission deadline.</p></div>';return}
 const type=get('planType').value,w=Math.min(156,Math.max(2,defaults[type]));
 const end=date(target.internalDay),start=shift(end,-7*w),days=daysAway(target.day);
 const steps=models[type].map(([title,desc,portion])=>({title,desc,day:key(shift(start,Math.round(7*w*portion)))}));
 const needs=w<defaults[type]?`This ${w}-week schedule is shorter than the ${defaults[type]}-week illustrative baseline for this project type. `:'';
 const msg=days<0?'The planning target has passed; a future conference cycle may be more realistic.':key(start)<todayKey?'The suggested start date has passed. An already-in-progress project may be needed.':'This planning schedule can be adjusted as the submission window is announced.';
 state.plan={id:c.id,name:c.name,steps,estimated:target.estimated,type,weeks:w,lead,readiness:get('planReadiness').value,presentation:get('planPresentation').value,target,start:key(start),guidance:needs+msg};
 get('planHeading').textContent=c.name;
 get('planResult').innerHTML=`<div class="plan-summary ${days<0||key(start)<todayKey||w<defaults[type]?'plan-warning':''}"><strong>${escape(fmt(key(start)))} → ${escape(fmt(target.internalDay))}</strong><span class="plan-goal-caption">Your early submit-by goal · ${target.bufferDays}-day buffer before ${escape(fmt(target.day))}</span>${target.estimated?'<span class="estimate-chip">Provisional, not an announced deadline</span>':''}<p>${escape(needs+msg)} ${escape(target.explanation)}</p></div>${roadmapMarkup(c,type,w,false,lead,get('planReadiness').value,get('planPresentation').value)}<details class="milestone-disclosure"><summary>View milestone descriptions and exact dates</summary><div class="milestone-table">${steps.map(s=>`<div><strong>${escape(s.title)}</strong><span>${escape(fmt(s.day))}</span><p>${escape(s.desc)}</p></div>`).join('')}</div></details>`;
}
function renderPlan(){if(!state.plan)generatePlan()}
function renderFunding(){
 const spec=state.fundingSpecialties;
 get('fundingSpecialtyChips').innerHTML=specialtyButtons(fundingSpecialties,spec,'data-fund-specialty');
 get('fundingMobileSpecialtyOptions').innerHTML=specialtyButtons(fundingSpecialties,spec,'data-fund-specialty');
 get('fundingMobileSpecialtySummary').textContent='Specialties: '+specialtyLabel(spec);
 get('clearFundingSpecialties').classList.toggle('hidden',!spec.length);
 get('fundingSelectedSpecialty').textContent=specialtyLabel(spec);
 document.querySelectorAll('[data-funding]').forEach(x=>x.classList.toggle('active',x.dataset.funding===state.funding));
 const list=A.filter(a=>awardMatchesSpecialty(a,spec)&&(state.funding==='all'||a.category===state.funding)&&(get('fundingShowClosed')?.checked||!a.deadline||a.deadline>=todayKey));
 get('fundingCount').textContent=list.length+' opportunities';
 get('emptyFunding').classList.toggle('hidden',!!list.length);
 get('fundingGrid').innerHTML=list.map(a=>{
   const conference=C.find(c=>c.id===a.conferenceId);
   const related=C.find(c=>c.id===a.relatedConferenceId);
   const kind=conference?'Linked to a conference':a.scope==='institutional'?'Local / institutional':related?'Independent research grant':'Standalone research funding';
   const meeting=conference?`<div class="fund-conference"><span>LINKED CONFERENCE</span><button type="button" class="fund-conference-btn" data-fund-conference="${escape(conference.id)}">${escape(conference.name)} →</button><small>${escape(dateRange(conference.start,conference.end))}</small></div>`:related?`<div class="fund-conference independent"><span>RELATED SOCIETY MEETING — NOT REQUIRED FOR AWARD</span><button type="button" class="fund-conference-btn" data-fund-conference="${escape(related.id)}">${escape(related.name)} →</button></div>`:'';
   return `<article class="funding-card" data-award-card="${escape(a.id)}"><div class="fund-top"><div class="fund-ico">${ico('award')}</div><div class="fund-amount">${escape(a.amount)}</div></div><div><div class="fund-cat">${escape(a.category)} · ${escape(kind)}</div><div class="fund-title">${escape(a.name)}</div><div class="fund-society">${escape(a.society)}</div></div>${meeting}<div class="fund-desc">${escape(a.eligibility)} ${a.note?escape(a.note):''}</div><div class="award-window"><div><span>APPLICATIONS OPEN</span><strong>${a.open?fmt(a.open):'Not confirmed'}</strong></div><div><span>${escape(a.deadlineLabel||'APPLICATION DEADLINE').toUpperCase()}</span><strong>${a.deadline?fmt(a.deadline):'Not confirmed'}</strong></div></div>${a.stages?.length?'<div class="award-extra-steps">'+a.stages.map(s=>escape(s.label)+': '+fmt(s.date)).join(' · ')+'</div>':''}${a.applicationProcess?'<p class="award-extra-steps">'+escape(a.applicationProcess)+'</p>':''}<p class="award-verified">${a.lastVerified?'Award details reviewed '+escape(fmt(a.lastVerified)):a.scope==='institutional'?'Confirm funding with your institution':'Current-cycle details not fully verified'}</p><div class="fund-info-row"><span>${a.open&&a.deadline?'Application window: '+fmt(a.open)+' – '+fmt(a.deadline):a.deadline?'Deadline: '+fmt(a.deadline):'Dates to verify'}</span>${safeExternal(a.url,'Award details')}</div></article>`;
 }).join('');
}
get('fundingShowClosed').addEventListener('change',renderFunding);
get('fundingSpecialtyChips').addEventListener('click',e=>{const b=e.target.closest('[data-fund-specialty]');if(b)setFundingSpecialty(b.dataset.fundSpecialty)});
get('fundingMobileSpecialtyOptions').addEventListener('click',e=>{const b=e.target.closest('[data-fund-specialty]');if(b)setFundingSpecialty(b.dataset.fundSpecialty)});
get('fundingReset').addEventListener('click',()=>{state.funding='all';setFundingSpecialty('All specialties')});
get('fundingGrid').addEventListener('click',e=>{const b=e.target.closest('[data-fund-conference]');if(b)showConference(b.dataset.fundConference)});
document.querySelectorAll('[data-funding]').forEach(btn=>btn.addEventListener('click',()=>{state.funding=btn.dataset.funding;renderFunding()}));

/* Conference Abstract Matcher — all analysis stays in the current browser tab.
   Neither raw text nor extracted terms are persisted or sent to an API. */
function renderMatcherPlaceholder(){
 get('matchOutput').innerHTML='<div class="matcher-placeholder"><span class="matcher-placeholder-icon">'+ico('search')+'</span><h2>Your conference matches will appear here</h2><p>Enter an abstract to compare its topics and research methods with the currently listed meetings.</p></div>';
}
function matcherWordCount(){
 const value=get('matchAbstractText').value.trim();
 get('matchWordCount').textContent=(value?value.split(/\s+/).length:0)+' words';
}
function matcherDate(value){return value?fmt(value):'Not announced'}
function matcherResultItem(match,number){
 const labels=match.topics.map(x=>x.label);
 const why=labels.length?('Topic connections: '+labels.slice(0,3).join(', ')+'.'):match.matchedTerms.length?('Overlapping terminology: '+match.matchedTerms.join(', ')+'.'):'Broader specialty relationship.';
 const record=C.find(c=>c.id===match.id);
 const deadline=match.opportunity.date?matcherDate(match.opportunity.date):'Not announced';
 const statusName=match.opportunity.status==='open'?'Open':match.opportunity.status==='closed'?'Closed':match.opportunity.status==='upcoming'?'Upcoming':match.opportunity.status==='review'?'Verify dates':'Not announced';
 const late=record&&record.lateDeadline===match.opportunity.date && (record.deadline!==match.opportunity.date);
 const deadlineType=late?'Late-breaking due':'Submission deadline';
 const statusCls=match.opportunity.status==='open'?'open':match.opportunity.status==='closed'?'closed':match.opportunity.status==='upcoming'?'upcoming':'pending';
 const verified=match.fit.status==='confirmed';
 return `<article class="matcher-result-card">
 <div class="matcher-result-head"><div><span class="matcher-rank">#${number} matched conference</span><div class="matcher-specialty">${escape(match.specialty)}</div><h3>${escape(match.name)}</h3><p class="matcher-society">${escape(match.society)}</p></div><span class="matcher-strength">${escape(match.strength)}</span></div>
 <div class="matcher-reason"><strong>Why it matches</strong><p>${escape(why)}</p></div>
 <div class="matcher-result-details"><div><span>${escape(deadlineType)}</span><strong>${escape(deadline)}</strong></div><div><span>Submission status</span><strong><span class="status-pill ${statusCls}">${escape(statusName)}</span></strong></div></div>
 <p class="matcher-format ${verified?'matched':'check'}">${verified?'✓':'i'} ${escape(match.fit.label)}${verified?' — verify current call requirements.':' — do not assume this abstract type is accepted.'}</p>
 <div class="matcher-result-bottom"><button type="button" class="btn btn-soft" data-match-open="${escape(match.id)}">View conference details <span aria-hidden="true">→</span></button>${match.url?safeExternal(match.url,'Official submission source'):''}</div>
 </article>`;
}
function runMatcher(){
 const abstract=get('matchAbstractText').value;
 const engine=window.RISE_ABSTRACT_MATCHER;
 if(!engine||typeof engine.matchAbstract!=='function'){
  get('matchOutput').innerHTML='<div class="matcher-message" role="alert">The matcher could not be loaded. Refresh the page and try again.</div>';
  return;
 }
 const result=engine.matchAbstract(abstract,C,{
  format:get('matchFormat').value,
  includeClosed:get('matchShowClosed').checked,
  today:todayKey,
  limit:12
 });
 if(result.error){
  get('matchOutput').innerHTML='<div class="matcher-message" role="status">'+escape(result.error)+'</div>';
  return;
 }
 const n=result.results.length;
 const topicTags=result.topics.slice(0,9).map(t=>'<span class="matcher-topic">'+escape(t)+'</span>').join('');
 const topics=result.topics.length?'<div class="matcher-detected"><span>Recognized subjects</span><div class="matcher-topics">'+topicTags+'</div></div>':
 '<p class="matcher-no-topics">No specific subject phrase was recognized. These suggestions rely on overlapping terminology and should be reviewed particularly carefully.</p>';
 const heading=`<div class="matcher-results-head"><div><h2>${n} potential conference ${n===1?'match':'matches'}</h2><p>Abstract type: <strong>${escape(result.formatLabel)}</strong> · Ranked by topical alignment, not acceptance likelihood.</p></div></div>`;
 const notice='<p class="matcher-disclaimer">Matching considers subject matter and available organizer metadata. A strong topical match does not establish eligibility, acceptance, an active call for abstracts, or an appropriate presentation category. Check official requirements before submitting.</p>';
 const items=n?result.results.map((m,i)=>matcherResultItem(m,i+1)).join(''):'<div class="matcher-message">No sufficiently relevant conference was found in the current directory with these filters. Try including closed meetings or adding more clinical subject detail.</div>';
 get('matchOutput').innerHTML=heading+topics+notice+'<div class="matcher-results">'+items+'</div>';
}
get('matchAbstractText').addEventListener('input',matcherWordCount);
get('matchRun').addEventListener('click',runMatcher);
get('matchClear').addEventListener('click',()=>{
 get('matchAbstractText').value='';
 get('matchFormat').value='auto';
 get('matchShowClosed').checked=false;
 matcherWordCount();
 renderMatcherPlaceholder();
 get('matchAbstractText').focus();
});
get('matchFormat').addEventListener('change',()=>{
 if(get('matchOutput').querySelector('.matcher-results-head'))runMatcher();
});
get('matchShowClosed').addEventListener('change',()=>{
 if(get('matchOutput').querySelector('.matcher-results-head'))runMatcher();
});
get('matchOutput').addEventListener('click',event=>{
 const button=event.target.closest('button[data-match-open]');
 if(button)showConference(button.dataset.matchOpen);
});

function renderSources(){let v=C.filter(c=>source(c)==='verified').length,conf=C.filter(c=>source(c)==='conflict').length,unknown=C.filter(c=>!c.deadline).length;get('qualityCards').innerHTML=`<div class="quality-card"><strong>${v}</strong><span>Conference records with official-source review</span></div><div class="quality-card"><strong>${unknown}</strong><span>Abstract deadlines awaiting publication or confirmation</span></div><div class="quality-card"><strong>${conf}</strong><span>Conference records with conflicting source dates</span></div>`}
function exportCSV(){const cols=['name','society','specialty','open','deadline','lateOpen','lateDeadline','start','end','city','deadlineTime','limit','limitType','fee','evidence','flag','url','guideline','note'];const quote=s=>'"'+String(s??'').replaceAll('"','""')+'"';downloadFile('RISE_conferences_2026_2027.csv',[cols.join(','),...C.map(c=>cols.map(k=>quote(c[k])).join(','))].join('\r\n'),'text/csv;charset=utf-8');showToast('Conference CSV exported')}get('exportCsv').addEventListener('click',exportCSV);
let toastTimer;function showToast(msg){const el=get('toast');el.textContent=msg;el.classList.add('visible');clearTimeout(toastTimer);toastTimer=setTimeout(()=>el.classList.remove('visible'),3400)}
function restoreRoute(route){
 const view=NAV_VIEWS.includes(route?.view)?route.view:'discover';
 nav(view,false);
 setExploreMode(view==='discover'&&route?.mode==='calendar'?'calendar':state.exploreMode,false);
 if(MOBILE_LIST_ONLY.matches&&route?.mode==='calendar')recordRoute(true);
 if(route?.modal&&C.some(c=>c.id===route.modal))showConference(route.modal,false);
 updateBackButton();
}
window.addEventListener('popstate',event=>restoreRoute(event.state?.riseNavigator||routeFromHash()));
get('navBack').addEventListener('click',()=>{if(history.state?.riseNavigator?.depth>0)history.back()});
initSummary();initSpecialties();renderHorizon();renderDirectory();initPlanner();renderSources();
const initialRoute=history.state?.riseNavigator||routeFromHash();
history.replaceState({...history.state,riseNavigator:initialRoute},'',location.href);
restoreRoute(initialRoute);
})();
