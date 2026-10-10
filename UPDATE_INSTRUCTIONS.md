# RISE Monitor — v12 Date Reliability Fix

**Status:** implementation and offline regression tests completed. This is **not yet installed** in your GitHub repository. The existing site and dates do not change until you upload and commit the patch and rerun GitHub Actions.

## What changed

1. Parse paired abstract opening/closing ranges as **two separate dates**, including phrases like “submissions are open from September 11 through November 23, 2026” and “abstract submissions open July 22 and close October 5, 2026.”
2. Stop extracting 2026-only conference submission rules into a 2027 conference when no evidence ties the webpage to the 2027 meeting.
3. Aggregate conflicting dates **across the same page and across multiple official pages**; block approval for that field and show conflicting evidence in the review HTML and GitHub issue.
4. Continue the human-review gate for valid proposed updates. The 2026 AANS discrepancies remain **blocked**, not guessed.
5. Reset **city, venue, and prior-cycle URLs** as well as dates in *unpublished* annual-rollover drafts. Keep the previous-year source only for historical reference.
6. Reject **all pre-v12 monitoring reports** in the approval tool. Old artifacts must not be used for approval; run the monitor again.
7. Run the Python safety suite before every weekly/manual monitoring job.

## If you use the GitHub website (no command line)

Download `RISE_v12_GitHub_Patch.zip` and extract it locally. All ZIP paths are relative to your repository root.

For **each** of these five files, in your GitHub repository click **Code**, locate the path, open the file, click the pencil icon (**Edit this file**), open the matching local patch file in a text editor, **select all / copy** the patch content, select all in the GitHub editor and paste, then click **Commit changes** to the `main` branch:

- `pipeline/core.py`
- `pipeline/cli.py`
- `pipeline/issue_queue.py`
- `tests/test_pipeline.py`
- `.github/workflows/monitor.yml`

For the **new** regression test `tests/test_live_regressions.py`: navigate to the `tests` folder in GitHub → **Add file → Create new file** → name `test_live_regressions.py` → paste its contents → **Commit changes**.

You can also use GitHub Desktop or a local Git clone to replace all six paths and commit once. Do **not** upload just the ZIP as a file; GitHub must contain the actual files and folders.

> If `pipeline/` is missing entirely, or its filenames are different, do not overwrite unrelated files. Upload the complete v12 source tree or ask for help based on a screenshot of the Code tab.

## Test after uploading

1. GitHub → **Actions** → **Monitor official conference sources** → **Run workflow** → branch `main` → green **Run workflow**.
2. On the new run, open `monitor`; confirm `Run safety and first-run regression tests` reports **22 tests passing** before the website checks.
3. After the run, open the **Summary** → **Artifacts** → download `rise-review-<run ID>` → open `review_queue.html`.
4. Conflicted dates now appear in **Conflicting official dates — blocked**, and **no matching proposal ID** can be approved.
5. If the run is green but sources are unavailable, the report should say `unavailable`; unavailable pages do not change data. A green check alone does not prove every source succeeded.
6. Only manually review a valid non-conflicted proposal against the live official page. The separate **Review and propose a dated change** workflow generates a pull request; it does not bypass review.

## Baseline expectations based on the first report

- AANS 2027: competing Oct 1 / Oct 4 / Oct 5 2026 dates → **conflict, no proposed deadline**.
- ACG 2027: old ACG 2026 deadline → **ignored**.
- SHM Converge 2027: opening Sept 11, closing Nov 23, 2026 → **no change**, matching stored fields.
- SGIM Southwest 2027: opening Aug 28, 2026 → **reviewable proposal** if the page still publishes it.

These are *test expectations*, not a promise of live-source behavior. Websites can change between runs.

## Known limitations

- The heuristic detector is deliberately conservative: it will miss some websites rather than speculate.
- This update fixes **date parsing and annual draft propagation**. It does not extract or publish new cities, character limits, or newly discovered conferences, or guarantee access to sites using PDFs, JavaScript, paywalls, or anti-bot protections.
- This workflow does not auto-publish changes. Human verification and a merged pull request remain necessary.
- Hosted automation depends on GitHub Actions permissions and the repository's own configuration.
