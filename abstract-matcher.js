/* RISE Abstract Matcher: deterministic, browser-only medical-topic matching.
   No remote services, AI inference, API calls, storage, or abstract logging.
   Scores reflect topic alignment only; they do not estimate acceptance probability. */
(function(root, factory) {
  var api=factory();
  if (typeof module!=='undefined' && module.exports) module.exports=api;
  if (root) root.RISE_ABSTRACT_MATCHER=api;
})(typeof window!=='undefined'?window:null,function() {
'use strict';
var STOP=new Set(('a an the and or of in on to for with without by from between among based study studies patient patients participant participants group groups test testing analysis analyses using used use evaluation evaluated assess assessed assessment investigate investigated aim aims objective objectives purpose background introduction results result methods method methodology conclusion conclusions discussion data finding findings statistically significant significance associated association compared comparison increased decreased impact effect effects clinical clinically medicine medical healthcare health outcomes outcome research original observational prospective retrospective cohort cross sectional controlled randomized multicenter multi center institution institutions university academic annual meeting meetings congress conference society scientific association american international national europe european abstract poster oral new was were are is been be can may that this these those it we our they their who which included including reported reports more less high low significant differences difference year years months treatment treatments intervention interventions disease diseases disorder disorders diagnosis diagnoses patients adults adult men women female male age ages frequency rate rates level levels outcome outcomes total overall prevalence incidence risk risks factors group population populations presented presenting demonstrated demonstrate demonstrates suggest suggests').split(' '));
function norm(text){return String(text||'').toLowerCase().normalize('NFKD').replace(/[\u0300-\u036f]/g,'').replace(/[^a-z0-9]+/g,' ').replace(/\s+/g,' ').trim()}
function stem(s) {
 if(s.length>6 && s.endsWith('ies')) return s.slice(0,-3)+'y';
 if(s.length>6 && s.endsWith('ing')) return s.slice(0,-3);
 if(s.length>5 && s.endsWith('ed'))return s.slice(0,-2);
 if(s.length>5 && s.endsWith('s') && !s.endsWith('ss') && !s.endsWith('us'))return s.slice(0,-1);
 return s;
}
function tokenize(s) {
 return norm(s).split(' ').filter(function(t){return t.length>=3 && !STOP.has(t) && !/^\d+$/.test(t)})
 .map(stem);
}
function topic(label,phrases,affinity) {
 return {label:label,phrases:phrases.split('|').map(norm),affinity:affinity};
}
/* Alias groups are subject matter, not statements of an organizer's accepted
   abstract categories. A topic may legitimately map across specialties. */
var TOPICS=[
 topic('Cancer / oncology','cancer|oncology|malignancy|malignant|neoplasm|tumor|tumour|carcinoma|metastatic|metastasis|chemotherapy|immunotherapy',{Oncology:1,'Hematology & Oncology':.9,'Radiation Oncology':.65,Pathology:.25,Surgery:.2}),
 topic('Brain tumors','glioblastoma|gbm|glioma|brain tumor|brain tumour|neuro oncology|neurooncology|astrocytoma|meningioma',{Neurosurgery:1,'Radiation Oncology':1,Oncology:.9,Neurology:.7,Radiology:.55,Pathology:.45,'Hematology & Oncology':.65}),
 topic('Radiotherapy','radiotherapy|radiation therapy|radiation oncology|radiation treatment|sbrt|srs|stereotactic radiosurgery|brachytherapy|proton therapy|particle therapy|imrt|radiation dose|fractionation',{ 'Radiation Oncology':1,'Medical Physics':.85,Oncology:.65}),
 topic('Breast cancer','breast cancer|breast carcinoma|ductal carcinoma|lobular carcinoma|her2|triple negative breast',{Oncology:1,'Radiation Oncology':.93,Surgery:.6,Pathology:.5,'Hematology & Oncology':.85}),
 topic('Lung cancer','lung cancer|nsclc|sclc|non small cell lung|small cell lung|pulmonary adenocarcinoma',{Oncology:1,'Radiation Oncology':.9,'Pulmonary & Critical Care':.7,'Cardiothoracic Surgery':.6,Surgery:.3}),
 topic('Gastrointestinal cancers','colorectal cancer|colon cancer|rectal cancer|pancreatic cancer|gastric cancer|hepatocellular carcinoma|hcc|esophageal cancer',{Oncology:1,Gastroenterology:.85,'Radiation Oncology':.7,Surgery:.65,'Hematology & Oncology':.7}),
 topic('Genitourinary cancers','prostate cancer|bladder cancer|renal cell carcinoma|testicular cancer|genitourinary cancer',{Urology:1,Oncology:.95,'Radiation Oncology':.8,Surgery:.45}),
 topic('Gynecologic cancers','ovarian cancer|cervical cancer|endometrial cancer|uterine cancer|gynecologic oncology',{ 'Obstetrics & Gynecology':1,Oncology:.95,'Radiation Oncology':.8}),
 topic('Hematologic malignancies','leukemia|lymphoma|myeloma|hematologic malignancy|myelodysplastic|acute myeloid leukemia|chronic lymphocytic leukemia',{Hematology:1,'Hematology & Oncology':1,Oncology:.75,Pathology:.55}),
 topic('Cancer immunology','checkpoint inhibitor|car t|car t cell|tumor microenvironment|immune checkpoint|pd l1|tumor infiltrating lymphocyte',{Oncology:.95,'Hematology & Oncology':.9,Hematology:.75,'Allergy & Immunology':.4,Pathology:.3}),
 topic('Precision medicine / genomics','genomics|genomic|sequencing|next generation sequencing|molecular profiling|mutation|crispr|gene editing|transcriptomics|biomarker|spatial omics',{Pathology:.8,Oncology:.75,'Hematology & Oncology':.65,'Medical Physics':.25}),
 topic('Neurology','neurology|neurological|neurologic|neuroscience|neuron|neural',{Neurology:1,Neurosurgery:.35,'Physical Medicine & Rehabilitation':.4}),
 topic('Stroke and cerebrovascular disease','stroke|ischemic stroke|haemorrhagic stroke|hemorrhagic stroke|cerebrovascular|thrombectomy|tia|transient ischemic attack|brain ischemia',{Neurology:1,Neurosurgery:.85,'Vascular Surgery':.55, 'Physical Medicine & Rehabilitation':.5,Radiology:.4}),
 topic('Multiple sclerosis / neuroimmunology','multiple sclerosis|neuroimmunology|demyelinating|optic neuritis|neuromyelitis optica|mogad',{Neurology:1,'Allergy & Immunology':.5, 'Physical Medicine & Rehabilitation':.25}),
 topic('Movement disorders / Parkinson disease','parkinson|parkinsonism|movement disorder|tremor|dystonia|deep brain stimulation|levodopa|huntington',{Neurology:1,Neurosurgery:.8,'Physical Medicine & Rehabilitation':.6,Geriatrics:.35}),
 topic('Epilepsy / seizures','epilepsy|epileptic|seizure|status epilepticus|eeg|electroencephalography',{Neurology:1,Neurosurgery:.55,Pediatrics:.3}),
 topic('Headache and migraine','headache|migraine|cluster headache|cephalalgia',{Neurology:1,'General Internal Medicine':.2}),
 topic('Neurodegeneration / cognition','dementia|alzheimers|alzheimer|frontotemporal dementia|cognitive impairment|neurodegeneration|memory disorder',{Neurology:1,Geriatrics:.85,Psychiatry:.5,'Physical Medicine & Rehabilitation':.4}),
 topic('Neurorehabilitation','neurorehabilitation|neurologic rehabilitation|stroke rehabilitation|brain injury rehabilitation|neuroplasticity|functional recovery',{ 'Physical Medicine & Rehabilitation':1,Neurology:.85,Geriatrics:.35}),
 topic('Psychiatry / mental health','depression|anxiety|psychiatry|psychiatric|psychosis|schizophrenia|bipolar disorder|suicide|ptsd|post traumatic stress|substance use disorder|addiction',{Psychiatry:1,'General Internal Medicine':.25,Pediatrics:.25,Geriatrics:.25}),
 topic('Child and adolescent mental health','child psychiatry|adolescent psychiatry|autism|adhd|attention deficit hyperactivity|pediatric mental health',{Psychiatry:1,Pediatrics:.9,Neurology:.3}),
 topic('Medical imaging','magnetic resonance imaging|mri|functional mri|fmri|computed tomography|ct scan|pet scan|positron emission tomography|ultrasound imaging|radiomics|medical imaging',{Radiology:1,'Medical Physics':.65,Neurology:.25,'Radiation Oncology':.3}),
 topic('Nuclear medicine','nuclear medicine|spect|pet ct|pet mri|radiotracer|theranostics|radioisotope',{Radiology:1,'Medical Physics':.8,'Radiation Oncology':.7,Oncology:.5}),
 topic('Cardiology and cardiovascular disease','cardiovascular|cardiology|heart failure|myocardial infarction|coronary artery|acute coronary syndrome|arrhythmia|atrial fibrillation|valvular|echocardiography|heart disease',{Cardiology:1,'Cardiothoracic Surgery':.6,'General Internal Medicine':.35,'Vascular Surgery':.3}),
 topic('Interventional cardiology','pci|percutaneous coronary intervention|stent|coronary intervention|structural heart|transcatheter|tavr|cardiac catheterization',{Cardiology:1,'Cardiothoracic Surgery':.65,'Vascular Surgery':.3}),
 topic('Vascular surgery','peripheral arterial disease|vascular surgery|aortic aneurysm|endovascular|carotid stenosis|limb ischemia|revascularization',{ 'Vascular Surgery':1,Cardiology:.6,Surgery:.6,'Cardiothoracic Surgery':.4}),
 topic('Pulmonology / respiratory','asthma|copd|chronic obstructive pulmonary|pulmonary fibrosis|interstitial lung disease|pulmonology|respiratory failure|bronchoscopy|bronchiectasis',{ 'Pulmonary & Critical Care':1,'Allergy & Immunology':.55,'General Internal Medicine':.3}),
 topic('Critical care / sepsis','critical care|intensive care|icu|sepsis|septic shock|ventilator|mechanical ventilation|ards|acute respiratory distress syndrome',{ 'Pulmonary & Critical Care':1,'Anesthesiology':.75,'Emergency Medicine':.7,Hospital Medicine:.55,Surgery:.3}),
 topic('Infectious disease','infection|infectious disease|bacteremia|antibiotic|antimicrobial|mrsa|tuberculosis|hiv|viral infection|fungal infection|covid 19',{ 'Infectious Diseases':1,'General Internal Medicine':.4,'Pulmonary & Critical Care':.3,Pediatrics:.3}),
 topic('Infection prevention / stewardship','infection prevention|hospital acquired infection|healthcare associated infection|nosocomial|antimicrobial stewardship|antibiotic stewardship|clabsi|cauti|hand hygiene',{ 'Infectious Diseases':1,Hospital Medicine:.8,'General Internal Medicine':.45,PublicHealth:.1,'Public Health':.6}),
 topic('Endocrinology / metabolism','diabetes|diabetic|insulin resistance|glucose|thyroid|endocrine|obesity|metabolic syndrome|adrenal|pituitary',{Endocrinology:1,'General Internal Medicine':.45,Pediatrics:.2}),
 topic('Nephrology / kidney disease','renal failure|chronic kidney disease|acute kidney injury|nephrology|dialysis|glomerulonephritis|proteinuria|kidney transplantation|nephrotic',{Nephrology:1,Transplantation:.55,'General Internal Medicine':.4}),
 topic('Gastroenterology / hepatology','inflammatory bowel disease|crohn|ulcerative colitis|colonoscopy|endoscopy|gastroenterology|cirrhosis|hepatitis|liver disease|pancreatitis',{Gastroenterology:1,Surgery:.5,'General Internal Medicine':.3}),
 topic('Rheumatology / autoimmunity','lupus|rheumatoid arthritis|autoimmune|rheumatology|vasculitis|scleroderma|sjogren|psoriatic arthritis',{Rheumatology:1,'Allergy & Immunology':.65,Nephrology:.3}),
 topic('Allergy / clinical immunology','anaphylaxis|allergy|allergic|urticaria|immunodeficiency|atopic dermatitis|eczema|food allergy|immunology',{ 'Allergy & Immunology':1,Dermatology:.5,Pediatrics:.3}),
 topic('Dermatology','dermatology|skin disease|psoriasis|melanoma|acne|cutaneous|dermatitis|skin cancer',{Dermatology:1,Oncology:.4,Pathology:.4}),
 topic('Hematology / blood disorders','hematology|hemoglobin|anemia|sickle cell|thrombocytopenia|coagulation|thromboembolism|hemophilia|bleeding disorder',{Hematology:1,'Hematology & Oncology':.7,'General Internal Medicine':.3}),
 topic('Pediatrics / newborns','pediatric|paediatric|childhood|neonatal|newborn|infant|premature birth|nicu|adolescent medicine',{Pediatrics:1,'Obstetrics & Gynecology':.35,Neurology:.2}),
 topic('Obstetrics / maternal-fetal medicine','pregnancy|pregnant|obstetric|maternal|fetal|preeclampsia|gestational|placenta|prenatal|postpartum|preterm birth',{ 'Obstetrics & Gynecology':1,Pediatrics:.5}),
 topic('Reproductive health / fertility','infertility|fertility|reproductive medicine|ivf|in vitro fertilization|endometriosis|polycystic ovary',{ 'Obstetrics & Gynecology':1,Endocrinology:.4,Urology:.25}),
 topic('Urology','urology|urologic|prostate|bladder|urinary incontinence|kidney stone|nephrolithiasis|erectile dysfunction',{Urology:1,Nephrology:.35}),
 topic('Ophthalmology','ophthalmology|retina|retinal|macular degeneration|glaucoma|cataract|cornea|visual acuity|optic nerve',{Ophthalmology:1,Neurology:.25}),
 topic('Otolaryngology / ear nose throat','otolaryngology|hearing loss|cochlear|otology|neurotology|vestibular|vertigo|sinusitis|head neck surgery|laryngology',{Otolaryngology:1,Neurology:.35,Neurosurgery:.25}),
 topic('Orthopedics / musculoskeletal','orthopedic|orthopaedic|bone fracture|arthroplasty|joint replacement|anterior cruciate ligament|rotator cuff|sports medicine|musculoskeletal',{ 'Orthopedic Surgery':1,'Physical Medicine & Rehabilitation':.6,Surgery:.3}),
 topic('Surgery / perioperative care','surgery|surgical|laparoscopy|laparoscopic|robotic surgery|postoperative|perioperative|operative complication',{Surgery:1,'Anesthesiology':.5,'Cardiothoracic Surgery':.4,'Vascular Surgery':.35,'Plastic Surgery':.35}),
 topic('Anesthesia / analgesia','anesthesia|anaesthesia|anesthesiology|airway management|regional anesthesia|nerve block|perioperative analgesia|postoperative pain',{Anesthesiology:1,Surgery:.4,'Physical Medicine & Rehabilitation':.25}),
 topic('Plastic and reconstructive surgery','plastic surgery|reconstructive surgery|free flap|microsurgery|burn reconstruction|cleft palate',{ 'Plastic Surgery':1,Surgery:.65}),
 topic('Transplantation','transplantation|organ transplantation|allogeneic transplant|solid organ transplant|graft rejection|donor recipient',{Transplantation:1,Hematology:.65,Nephrology:.65,Surgery:.5}),
 topic('Geriatrics / aging','geriatrics|geriatric|older adults|aging|ageing|frailty|falls prevention|nursing home|long term care',{Geriatrics:1,'General Internal Medicine':.45,'Palliative Medicine':.3}),
 topic('Palliative medicine','palliative care|hospice|end of life|goals of care|serious illness communication|advance care planning|symptom burden',{ 'Palliative Medicine':1,Oncology:.45,Geriatrics:.4,Hospital Medicine:.3}),
 topic('Emergency medicine','emergency department|emergency medicine|trauma resuscitation|prehospital|ambulance|ems|triage|emergency medical services',{ 'Emergency Medicine':1,'Pulmonary & Critical Care':.45}),
 topic('Public health / epidemiology','public health|health disparities|health equity|population health|epidemiology|vaccination|vaccine hesitancy|community based|social determinants',{ 'Public Health':1,'General Internal Medicine':.6,'Family Medicine':.6,MedicalEducation:.1,'Medical Education':.35}),
 topic('Primary care / family medicine','primary care|family medicine|outpatient clinic|ambulatory care|preventive care|screening program|family practice',{ 'Family Medicine':1,'General Internal Medicine':.85,Hospital Medicine:.25}),
 topic('Quality improvement / patient safety','quality improvement|quality assurance|patient safety|root cause analysis|plan do study act|pdsa|reducing readmissions|workflow improvement',{Hospital Medicine:1,'General Internal Medicine':.8,'Medical Education':.55,'Family Medicine':.65,'Public Health':.4}),
 topic('Health professions education','medical education|resident education|residency curriculum|simulation education|clinical teaching|trainee education|medical student education|graduate medical education|educational innovation|osce',{ 'Medical Education':1,'General Internal Medicine':.55,'Family Medicine':.6,Pediatrics:.4}),
 topic('Machine learning / AI','machine learning|deep learning|artificial intelligence|neural network|computer vision|prediction model|large language model|natural language processing|radiomics',{Radiology:.65,'Medical Physics':.6,Pathology:.45,Oncology:.35,'Medical Education':.2}),
 topic('Healthcare systems / implementation','implementation science|health services|health policy|cost effectiveness|value based care|hospital readmission|healthcare delivery',{ 'Public Health':1,'General Internal Medicine':.8,Hospital Medicine:.8,'Family Medicine':.6})
];
var FORMATS=[
 {value:'original',label:'Original research',check:/\b(?:original research|clinical research|clinical trials?|scientific abstracts?|research|prospective clinical|basic science|translational|cohort)\b/i},
 {value:'case',label:'Case report / clinical vignette',check:/\b(?:case reports?|case series|clinical vignettes?|vignettes?|clinical images?|excerpta|case stud(?:y|ies))\b/i},
 {value:'qi',label:'Quality improvement',check:/\b(?:quality improvement|patient safety|\bqi\b|improvement projects?|implementation science)\b/i},
 {value:'education',label:'Medical education',check:/\b(?:medical education|educational (?:research|innovation|poster|exhibit|abstract)|curricul|teaching|training|resident education|graduate medical education)\b/i},
 {value:'review',label:'Systematic review / meta-analysis',check:/\b(?:systematic reviews?|meta[ -]?analys(?:is|es)|evidence synthesi[sz])\b/i}
];
function detectFormat(text) {
 var x=norm(text);
 if(/\b(?:case report|case series|clinical vignette)\b/.test(x))return 'case';
 if(/\b(?:systematic review|meta analysis|meta analyses|scoping review)\b/.test(x))return 'review';
 if(/\b(?:quality improvement|patient safety initiative|pdsa|plan do study act)\b/.test(x))return 'qi';
 if(/\b(?:medical education|resident education|curriculum|educational intervention|teaching intervention)\b/.test(x))return 'education';
 return 'original';
}
function formatLabel(v){return (FORMATS.find(function(f){return f.value===v})||FORMATS[0]).label}
function getTopics(input) {
 var x=' '+norm(input)+' ';
 return TOPICS.filter(function(t){
  return t.phrases.some(function(p){return p && x.indexOf(' '+p+' ')>=0});
 });
}
function scoreTermVectors(items) {
 var df={};
 items.forEach(function(doc){Array.from(new Set(doc)).forEach(function(token){df[token]=(df[token]||0)+1})});
 var n=items.length||1;
 return function(tok){return 1+Math.log((n+1)/(1+(df[tok]||0)))};
}
function tf(tokens,idf) {
 var vec={},total=0;
 tokens.forEach(function(t){vec[t]=(vec[t]||0)+1});
 Object.keys(vec).forEach(function(t){vec[t]=(1+Math.log(vec[t]))*idf(t);total+=vec[t]*vec[t]});
 return {vec:vec,norm:Math.sqrt(total)};
}
function similarity(a,b) {
 if(!a.norm||!b.norm)return 0;
 var dot=0;
 Object.keys(a.vec).forEach(function(k){if(b.vec[k])dot+=a.vec[k]*b.vec[k]});
 return dot/(a.norm*b.norm);
}
function formatFit(c,format) {
 if(!c.submissionCategoriesVerified)return {status:'unverified',label:'Presentation format not verified'};
 var text=norm([].concat(c.types||[],c.presentationFormats||[]).join(' '));
 var formatPattern=(FORMATS.find(function(f){return f.value===format})||FORMATS[0]).check;
 if(formatPattern.test(text))return {status:'confirmed',label:'Listed submission category matches'};
 // General original research labels do not establish eligibility for reviews/case reports.
 return {status:'unconfirmed',label:'Check submission category eligibility'};
}
function opportunity(c,today) {
 if(c.flag==='conflict')return {status:'review',label:'Dates need verification',date:c.deadline||null};
 var late=c.lateDeadline && c.lateDeadline>=today;
 var regular=c.deadline && c.deadline>=today;
 if(late && (!regular||c.deadline<today)) {
  if(c.lateOpen && c.lateOpen>today)return {status:'upcoming',label:'Late-breaking opens '+c.lateOpen,date:c.lateDeadline};
  if(!c.lateOpen)return {status:'upcoming',label:'Late-breaking deadline '+c.lateDeadline+' — opening unverified',date:c.lateDeadline};
  return {status:'open',label:'Late-breaking window open until '+c.lateDeadline,date:c.lateDeadline};
 }
 if(regular) {
  if(c.open && c.open>today)return {status:'upcoming',label:'Opens '+c.open,date:c.deadline};
  if(!c.open)return {status:'upcoming',label:'Deadline '+c.deadline+' — opening unverified',date:c.deadline};
  return {status:'open',label:'Regular submissions open until '+c.deadline,date:c.deadline};
 }
 if(c.deadline && c.deadline<today)return {status:'closed',label:'Recorded submission window closed',date:c.deadline};
 return {status:'unknown',label:'Abstract deadline not confirmed',date:null};
}
function confText(c) {
 return [(c.name||''),(c.name||''),(c.specialty||''),(c.society||''),...(c.types||[])].join(' ');
}
function matchAbstract(abstract,conferences,options) {
 options=options||{};
 var input=String(abstract||'').slice(0,14000);
 var format=options.format && options.format!=='auto'?options.format:detectFormat(input);
 if(!FORMATS.some(function(f){return f.value===format}))format='original';
 var today=options.today||new Date().toISOString().slice(0,10);
 var topical=getTopics(input);
 var words=tokenize(input);
 if(words.length<12)return {error:'Paste a longer abstract (approximately 30 or more words) so the topic can be identified reliably.',format:format,topics:[],results:[]};
 var conferenceList=Array.isArray(conferences)?conferences:[];
 var docs=conferenceList.map(function(c){return tokenize(confText(c))});
 var idf=scoreTermVectors(docs);
 var query=tf(words,idf);
 var results=conferenceList.map(function(c,i) {
  var topicItems=topical.map(function(t){
   var aff=t.affinity[c.specialty]||0;
   var ctext=' '+norm(confText(c))+' ';
   var specific=t.phrases.some(function(p){return p.length>=5 && ctext.indexOf(' '+p+' ')>=0});
   return {label:t.label,affinity:aff,focused:specific};
  }).filter(function(t){return t.affinity>.0||t.focused});
  var ranked=topicItems.map(function(t){return Math.max(t.affinity*.75,t.focused ? 0.98 : 0)}).sort(function(a,b){return b-a});
  var strength=ranked.length?Math.min(1,(ranked[0]||0)*.90+(ranked[1]||0)*.08+(ranked[2]||0)*.02):0;
  var keyword=similarity(query,tf(docs[i],idf));
  var fit=formatFit(c,format);
  // Topic fit dominates generic research terms; format matters only if verified.
  var score=.82*strength+.15*keyword+(fit.status==='confirmed' ? .03 : 0);
  if(fit.status==='unconfirmed')score*=.93;
  if(topical.length===0)score=.85*keyword+(fit.status==='confirmed' ? .02 : 0);
  var opportunityInfo=opportunity(c,today);
  var shared=Array.from(new Set(words.filter(function(t){return docs[i].indexOf(t)>=0}))).slice(0,4);
  return {
   id:c.id,name:c.name,society:c.society,specialty:c.specialty,
   url:c.guideline||c.url,sourceUrl:c.url,score:Math.round(score*1000)/1000,
   fit:fit,opportunity:opportunityInfo,
   topics:topicItems.sort(function(a,b){return (b.focused?2:0)+b.affinity-((a.focused?2:0)+a.affinity)}).slice(0,4),
   matchedTerms:shared,
   strength:score>=.55?'Strong topic alignment':score>=.3?'Relevant topic alignment':'Broader specialty match',
   focused:topicItems.some(function(t){return t.focused})
  };
 }).filter(function(r){return r.score>=.065 && (options.includeClosed||r.opportunity.status!=='closed')})
 .sort(function(a,b){
  return b.score-a.score || (a.opportunity.status==='open'?-1:0)-(b.opportunity.status==='open'?-1:0) ||
    a.name.localeCompare(b.name);
 }).slice(0,options.limit||12);
 return {error:null,format:format,formatLabel:formatLabel(format),
  topics:topical.map(function(t){return t.label}),results:results,
  hasSpecificTerms:topical.length>0,wordCount:words.length};
}
return {matchAbstract:matchAbstract,tokenize:tokenize,getTopics:getTopics,detectFormat:detectFormat,opportunity:opportunity,formatFit:formatFit,TOPICS:TOPICS};
});
