# RISE Conference Navigator — Public Website

Live website: https://ugoma-o.github.io/Conference-Navigator/

This repository contains the **published static website only**: HTML, CSS, JavaScript, and curated conference/funding data. It does not host the private monitoring pipeline.

## How updates work

- The **private** `RISE-Conference-Navigator-Source` repository runs the official-source monitor every Monday and checks published meeting information, linked abstract and submission pages, and deadlines.
- Explicit, unambiguous dates can be promoted to the curated dataset under conservative validation rules. Missing dates, conflicting years, inaccessible sources, and low-confidence evidence remain flagged for review rather than guessed.
- After validation, the private deployment workflow exports only static site assets to this public repository. The Actions workflow here publishes those assets to GitHub Pages.
- The private repository's `RISE_PUBLIC_DEPLOY_TOKEN` Actions secret must have Contents read/write permission for this public repository. Without that credential, automatic cross-repository publishing cannot work.

This site should never contain monitoring Python files, private credentials, unpublished scan reports, or patient information.
