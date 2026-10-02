# Learning Hub data (generated)

`catalog.json` and `legal-reviews.json` are the data files of the LAS Learning Hub library page
(laslegal.tech/learning-hub). They are generated in the las-billing repository by
`scripts/knowledge-teaching/build-library-data.py` from this repository's article pages and the audit
records of each publication wave, and published here so that the library page can read the current copy
after every wave merge without an application deploy. The page reads this copy first and falls back to the
copy packaged with the application.

- `catalog.json`: every article page under `articles/`, `en/articles/` and `blog/` (redirect stubs, series
  index pages and `.bak` copies excluded), with the SHA-256 of each published file.
- `legal-reviews.json`: one record per reviewed language variant — the review date shown on the page itself,
  the SHA-256 of the published file, and the evidence (release note under `docs/legal-reviews/` and the
  pull request of the wave). The library page shows a check mark only when the live page still hashes to the
  registered digest.

Do not edit these files by hand; regenerate them in las-billing and copy them here (`--gh-out`).
