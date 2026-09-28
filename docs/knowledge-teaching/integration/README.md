# Additive Knowledge link card — owner clarification 2026-09-28

The existing laslegal.tech/knowledge page remains the landing/link page. Add exactly ONE new card at the bottom of its content, after Additional Resources and before the copyright footer. Preserve all existing cards, order, text, search, categories, statistics, routes and styling. Do not replace this page with the teaching preview.

KnowledgeTeachingCard.tsx is a prepared integration component, not installed in the LAS runtime. It uses existing shared glass-card/cute-icon classes and lucide icons. Its href must be the verified deployed destination selected during integration, never localhost in production.

The new card opens the separate teaching library, which contains the article inventory, learning paths and user-supplied BTU PDF. The PDF is a resource inside that destination, not another card on the existing landing page.

Current local KnowledgeHubPage.tsx has unrelated uncommitted changes. Do not overwrite it or take its complete contents as a deployable baseline. Reconcile against the authenticated live version before inserting the component. Verify the destination route, assets, PDFs and access behavior before enabling the card. Production merge/deploy requires owner approval.

Acceptance: one new bottom card; existing page unchanged; destination reachable; teaching search and PDF work; desktop/mobile review; production approval outstanding.
