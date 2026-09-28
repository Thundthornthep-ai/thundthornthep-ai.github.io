# Validation — 2026-09-28

Scope: isolated teaching preview, not an integrated `/knowledge` release.

- Catalogue tests: 11 PASS (complete HTML accounting, alias exclusion, preserved variants, no implied legal approval, missing-discovery retention, prerequisite cycle/missing-ID checks, source dates, parser, real paths, placeholder exclusion, stored hashes).
- Existing publication gates: 59 citation unit tests PASS; all 146 tracked article files passed registry gate; Knowledge Hub 8/8 PASS; comparison-range tests PASS.
- Exact-slug delta: not applicable; no existing article HTML changed.
- Browser: 109 initial items; search อายุความ -> 1 correct article; invalid search -> 0 with recovery message; PDPA + English -> 4 items; foundation path -> 7 links and exercise; reset -> 109.
- Mobile: actual browser viewport 390 × 844, document width 390, single-column cards visually inspected. Desktop preview visually inspected. This is viewport simulation, not physical-device verification.
- Thai-word verifier: plan, learning-paths and catalogue titles CLEAN. This is not a legal or exhaustive spelling verdict.
- Production: no deployment, merge or change to existing HTML/CSS/JS. Existing LAS checkout was read only. Authenticated `/knowledge` verification remains pending; unauthenticated request redirected to login.
- Source identity: 44 local mapped routes, 33 differing headings. These are reconciliation candidates, not 33 proven substantive legal conflicts.
- Legal review queue: 141 article variants, 24 high-priority by conservative keyword triage, 1,556 unique candidate statute/section keys. Extractor limitations disclosed; candidates are neither confirmed sections nor audited claims.

Release prerequisites: authenticated baseline reconciliation, instructor acceptance, source and semantic review of selected teaching articles, scoped LAS integration with flag off, independent legal review where required, fresh production approval.
