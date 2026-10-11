# RISE Conference Navigator — Conference Curation Standard

**Purpose.** Curate conferences that are genuinely useful for residents, fellows, medical students, and physician-investigators seeking reputable scientific presentation, scholarship, education, and mentorship opportunities. **Count is not a success metric.**

## Inclusion hierarchy

1. **Core scientific meetings:** flagship conferences of nationally/internationally recognized specialty societies, academic medical organizations, major clinical research consortia, or established specialty-led scientific associations. Prioritize meetings with independently reviewed original-research abstracts, poster/oral sessions, resident/trainee participation, established publication or program records, and transparent organizers.
2. **Focused subspecialty meetings:** credible, society-organized conferences in important subspecialties that support legitimate research presentation. Smaller or international events may be highly valuable; do not infer lower scientific quality from size or geography.
3. **Educational, QI, and regional meetings:** include only where there is concrete academic value (educational scholarship, QI, well-established resident competitions, training or mentorship), and clearly state when the meeting is **not equivalent to an open, peer-reviewed original-research abstract forum**.
4. **Restricted scientific meetings:** prestigious or high-value meetings with invitation, membership, special eligibility, or project-participation restrictions may be listed, but explicitly disclose access limitations. Do not imply that all residents can submit.
5. **Unconfirmed future editions:** do not present meeting dates or submission windows without an organizer-supported 2027 edition. A well-established annual series with unannounced 2027 dates may remain in the dataset with `start: null`, `end: null`, appropriate `unannounced` status and an organizer-controlled website; never carry forward prior-year dates.

## Exclusion / removal rules

- Predatory conferences, generic "submit to any field" events, pay-to-present schemes, misleading society impersonations, conference aggregators that cannot establish the organizing body, and untraceable commercial meetings.
- Duplicate meeting editions, or unverified 2027 meetings created merely to fill out a specialty.
- Courses, trade shows, administrative gatherings, and CME-only events that are presented as original-research opportunities without an actual scholarly submission pathway.
- Incorrectly matched abbreviations (for example, AUA Urology vs. Association of University Anesthesiologists; AAO Ophthalmology vs. AAO-HNS Otolaryngology).
- Individual abstract **fees** do not by themselves imply that an event is predatory; use the organizer, review process, historical scientific program, and legitimacy of published proceedings together.

## Verification rules

- Establish the *identity of the organizer* on its society site, official meeting microsite, or a verified official publication.
- Prefer an edition-specific 2027 page for meeting dates and the exact abstract/call-for-science page for submission data. A genuine society homepage does **not** establish a specific 2027 abstract deadline.
- Independently confirm scientific submission categories and oral/poster formats before setting `submissionCategoriesVerified = true`. Do not mistake educational proposals or workshop invitations for original-research abstracts.
- Preserve all verified opening/closing dates, timezone, late-breaking restrictions, source URLs and evidence. Never infer an unknown abstract deadline from a prior year or generic submission date.
- Distinguish **abstract submission** fees from **registration, travel, accommodation and membership** costs. Unknown is not free.
- Disclose when meeting access is invitation-only or when abstracts are restricted to special membership, research consortia or invited speakers.
- On unclear/conflicting dates, leave the affected field unset and flag the need for a human review.

## Quality review for each future addition

For every proposed meeting, document: (1) organizer, (2) identity and edition, (3) research/education/quality-improvement purpose, (4) abstract presentation path or explicit "not yet established," (5) trainee eligibility and relevant barriers where known, (6) direct official URL, and (7) date/deadline source and verification status. Remove speculative meetings rather than backfilling the directory to reach a target count.

**Categories are descriptive, not rankings**: a narrowly focused subspecialty meeting can be more useful than a prestigious flagship conference for a particular project. Counts and titles should never imply a conference's suitability to a particular manuscript or case report unless accepted formats have been checked.

## Source monitoring

The weekly scanner checks **only already-listed conferences and follow-on organizer URLs**; it is *not* a guarantee that newly created conferences or overlooked societies will be discovered automatically. Perform periodic specialty-by-specialty discovery audits and revalidate new society meetings before adding to the dataset.
