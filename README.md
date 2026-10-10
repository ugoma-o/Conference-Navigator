# RISE Conference Navigator — Version 11 (scheduled update infrastructure)

This is the **working source project** for an academic conference directory with a review-gated automatic monitoring system. Its resident-facing app retains the 66 conference records and 14 funding opportunities from V10. The database is still a curated October 2026 snapshot **until approved changes are deployed**.

## What is implemented

| Component | Result |
|---|---|
| Conference/funding dataset | `data.json`, synchronized to `data.js` for the browser |
| Weekly scheduler | `.github/workflows/monitor.yml` (Monday 10:17 UTC), plus manual run |
| Official-source monitoring | Monitor conference URLs, submission/guideline URLs, and linked award sources over HTTPS; obey robots.txt; rate-limit; deduplicate shared URLs; fingerprint visible text |
| Date extraction | Strict explicit-year, labeled submission/award opening and deadline candidates (including late-breaking dates where clearly labeled) |
| Conflicts and site failures | Never alter published dates automatically; unresolved dates, contradictory evidence, unsupported PDFs/dynamic sites and unreachable URLs are flagged rather than guessed |
| Review packet | `pipeline/reports/review_queue.json` + a safe HTML report; uploaded to GitHub Actions artifacts |
| Review alerts | One continually updated GitHub issue summarizing the current queue; prevents weekly issue spam |
| Approval | Manual GitHub Actions workflow (`review-date.yml`) can apply *one* specified candidate to a pull request with reviewer attribution and source URL |
| Publication | `deploy.yml` runs tests and deploys `data.js` and the web app on **merge to main** (after GitHub Pages is configured) |
| Annual continuity | Monthly-ready `draft-cycle` produces *unpublished* successor records without copying dates, abstract formats, fees, or eligibility |
| Audit trail | Reviewer attribution and official URL stored in individual date fields; `pipeline/approved_changes.jsonl` generated locally (not committed by default) |

**No API key or AI subscription is required to operate this basic version.** The extractor intentionally recognizes only conservative, explicitly labeled date patterns. Changes to locations, abstract length, awards, eligibility and presentation policies are detectable through source changes, but require manual review/update; PDFs, JavaScript-only content and portal-gated announcements may require society APIs or another authorized connector. Running the monitor does **not** mean every deadline has been verified.

## Local development and tests

Requirements: Python 3.10+ (Python 3.12 in CI); a recent browser. No third-party Python dependencies.

```bash
# From the unzipped project directory:
python -m unittest discover -s tests -v
python -m pipeline.cli validate
python -m pipeline.build_site
python -m http.server 8000
```

Open `http://localhost:8000`. `dist/` contains the allowlisted static website. The separate `RISE_Conference_Navigator_v11_Demo.html` is a **frozen, portable preview**, not a continuously updating website.

To manually scan a few live official pages from a machine with internet access:

```bash
python -m pipeline.cli scan --limit 5 --timeout 12 --delay 1
```

Check `pipeline/reports/review_queue.html` and its underlying `review_queue.json`. First-time fingerprints are called `baseline`. A changed source might or might not yield an extracted date; source text must be reviewed. Blocked or inaccessible pages show `unavailable`. The scan never changes `data.json`.

To trial an **explicitly reviewed** candidate from the report locally:

```bash
# Review the official source URL and snippet independently first.
python -m pipeline.cli approve --candidate <ID_FROM_REPORT> --reviewer "Research Coordinator"
# Dry-run: no data changed. When the proposed date is independently confirmed:
python -m pipeline.cli approve --candidate <ID_FROM_REPORT> --reviewer "Research Coordinator" --apply
```

The second command updates the applicable field in `data.json`, records its verified source and reviewer, regenerates browser-readable `data.js`, and records a local audit entry. Use Git version control to review/commit the approved change. If the source has conflicting dates, do **not** approve until resolved.

To prepare unpublished records for the next conference year:

```bash
python -m pipeline.cli draft-cycle --year 2028
```

Output is a draft in `pipeline/reports/`, not automatically added to the resident-facing database. Meeting dates and deadlines must be established against official sources before publishing.

## Turn on the weekly automation and hosting (required one-time setup)

1. Create or select an institutional GitHub repository. Upload **the contents of this project directory to the repository root**, preserving `.github/workflows/`. Ensure default branch is `main`; otherwise update the workflows' `main` references to match. No resident accounts or patient data are involved.
2. In **GitHub → Settings → Actions → General**, enable workflows and allow the **Actions GITHUB_TOKEN to create pull requests** if you intend to use the approval workflow. Apply least-privilege organization policies and require human review of PRs. If Actions-generated PRs are prohibited, use the local CLI and open a PR manually.
3. In **Settings → Pages → Build and deployment**, choose **GitHub Actions** as the source. Ensure Pages is permitted for the repository's visibility. **Ordinary GitHub Pages is not an institutional-access-control layer**; do not publish private resident projects or any PHI on an unrestricted site.
4. In **Actions → Monitor official conference sources**, select **Run workflow**. Wait for the first source check and download the `rise-review-<run ID>` artifact containing HTML and JSON review reports. A single review issue is created/updated if sources need attention. Initial source fingerprints are a baseline, not proof dates are correct.
5. Open the report, verify a proposed date on the official organizer webpage, then select **Actions → Review and propose a dated change**. Enter the monitoring run ID and proposal ID. The workflow creates a pull request; **review and merge** it to publish. GitHub may require enabling Actions pull-request creation and repository organization approval.
6. Run **Test and publish RISE** manually for the initial deployment, or push a commit affecting `data.json` / app files to `main`. Visit the GitHub Pages URL displayed under the deployment. Subsequent merges trigger deployment without rebuilding ZIPs or manually sending residents new files.
7. Confirm the schedule remains active. GitHub scheduled workflows can run late, and public repositories with no activity for 60 days can have scheduled workflows disabled. Assign an owner to check the Actions status and the open review issue periodically.

For private/internal deployment, replace Pages with your institutional hosting and use the same `pipeline.build_site` output. The collaborator's login and project reminders can later consume this approved `data.json` or a database synchronized from it.

## Limitations and safety

- **This project has NOT been connected to a GitHub repository or activated on a live server in this chat.** A connection and repository settings are required. Live internet fetches from the current sandbox failed DNS resolution; integration tests used deterministic official-style excerpts and simulated changes rather than a false claim of a successful internet crawl.
- The default update is **semi-automatic**: checks and candidate generation are automatic, dates publish only after approval. This is deliberate. The scanner is not an authoritative submission portal and cannot guarantee up-to-the-minute accuracy.
- Society webpages may contain multiple meeting years, unrelated award deadlines, tracking banners, or conflicting dates. These all require review; generic source URLs may yield false-positive candidates. The app must keep linking to the official source.
- Raw/source page content is never inserted into the public app. Review HTML escapes untrusted text. A deployment uploads only `index.html`, `styles.css`, `app.js`, `data.js`, and `data.json`.
- Existing imported data is **not reverified** merely by checking whether a page changed. Missing opening dates stay missing until confirmed. No unannounced date is fabricated.
- To implement true live subscribed-calendar sync for residents, or more complex PDF/portal extraction, further integration with the collaborator's authenticated application will be needed.

## Project layout

```
index.html, styles.css, app.js   # existing interactive resident app
 data.json                       # curated source-of-truth
 data.js                         # generated browser data
 sync_data.py                    # regenerate browser bundle
 pipeline/core.py                # cautious page monitor/extractor
 pipeline/cli.py                 # scan, approve, draft-cycle, validate
 pipeline/issue_queue.py         # one GitHub issue for review alerts
 pipeline/build_site.py          # publish only safe app assets
 pipeline/make_demo.py           # make frozen offline demo
 tests/test_pipeline.py          # deterministic tests + end-to-end approval
 .github/workflows/monitor.yml   # scheduled monitor and evidence artifacts
 .github/workflows/review-date.yml  # one reviewed proposal -> PR
 .github/workflows/deploy.yml    # test -> publish after merge
```

Sources for GitHub operational behavior: [scheduled workflows](https://docs.github.com/en/actions/reference/events-that-trigger-workflows#schedule), [Pages via GitHub Actions](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site). Primary medical organizer links reside in the existing `data.json` records.
