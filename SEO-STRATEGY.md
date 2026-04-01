# SEO & AI Search Strategy — Dr. Thundthornthep Yamoutai / LAS

**Prepared**: 1 April 2026
**Target site**: thundthornthep-ai.github.io (GitHub Pages)
**Linked site**: laslegal.co.th
**Goal**: Maximise visibility for target keywords in Google Search, Bing, and AI Search engines (ChatGPT, Perplexity, Google AI Overview)

---

## Part 1: Current State Assessment

### What We Have (Strengths)

| Asset | Status | SEO Value |
|-------|--------|-----------|
| GitHub Pages — 17 HTML pages | Live, indexed | High |
| 8 JSON-LD structured data blocks | Valid, no errors | High |
| FAQ Schema (6 Q&As) | Ready for rich results | High |
| Google Search Console | Verified | Essential |
| Bing Webmaster Tools | Verified | Good |
| IndexNow key | Active | Good |
| robots.txt — all AI crawlers allowed | Active | High for AI search |
| Sitemap — 15 URLs | Active (needs ep6) | Essential |
| Siam Rath coverage — 6 articles | Published | Very High |
| Nation TV — 3 video interviews | Published | Very High |
| LINE TODAY / THE POINT | Published | High |
| TCI-ThaiJO academic paper | Published | Very High |
| ASEAN Citation Index (ACI) | Indexed | Very High |
| Government backlinks (IEAT, NIA, SME Bank) | Active | Highest |

### What's Missing (Gaps)

| Gap | Priority | Impact |
|-----|----------|--------|
| Sitemap missing ep6.html | Quick fix | Low |
| No Google Business Profile for LAS | High | Local SEO |
| No laslegal.co.th Search Console cross-linking | High | Domain authority |
| No hreflang tags (EN/TH versions) | Medium | International SEO |
| No blog/article publish dates visible to users | Medium | Freshness signal |
| Limited internal linking between pages | Medium | Crawl depth |
| No performance monitoring routine | High | Ongoing |

---

## Part 2: Target Keywords & Content Mapping

### Primary Keywords (High Priority)

| Keyword | Language | Search Intent | Current Page | Gap |
|---------|----------|---------------|--------------|-----|
| Thundthornthep Yamoutai | EN | Navigational | index.html | Covered |
| Dr. Thundthornthep | EN | Navigational | index.html | Covered |
| Legal Advance Solution | EN | Navigational | index.html | Covered |
| LAS Legal | EN | Navigational | index.html | Covered |
| AI Legal Tech Thailand | EN | Informational | index.html | Covered |
| PDPA compliance Thailand | EN | Informational | pdpa-advisory.html | Covered |
| contract drafting Thailand | EN | Informational | knowledge-hub.html | Needs dedicated content |
| Thai business law | EN | Informational | knowledge-hub.html | Needs dedicated content |
| NIA legal technology | EN | Informational | index.html | Covered |
| Bangkok Metropolitan Council | EN | Informational | blog/bkk-council/ | Covered |

### Secondary Keywords (Content to Create)

| Keyword Cluster | Suggested New Page | Priority |
|-----------------|-------------------|----------|
| contract drafting, contract review, NDA, MOU | blog/contract-guide.html | High |
| due diligence, conditions precedent, CP | blog/due-diligence.html | High |
| Thai company formation, shareholder agreement | blog/corporate-law.html | Medium |
| labour law Thailand, employment contract | blog/labour-law.html | Medium |
| real estate law, condominium law Thailand | blog/real-estate-law.html | Medium |
| joint venture Thailand, foreign business act | blog/investment-law.html | Medium |

---

## Part 3: Google Search Console Action Plan

### Immediate Actions (This Week)

#### 1. Fix Structured Data Error
- [x] Fixed duplicate `jobTitle` in Person JSON-LD
- [x] Fixed duplicate `jobTitle` (3x) and `description` (2x) in microdata
- [ ] **Go to Search Console → Click "Validate Fix"** on the structured data error
- [ ] Wait 1-3 days for Google to re-crawl and confirm fix

#### 2. Update Sitemap
- [ ] Add missing `ep6.html` to sitemap.xml
- [ ] Update all `<lastmod>` dates to today
- [ ] Resubmit sitemap in Search Console → Sitemaps → Submit

#### 3. Request Indexing for Updated Pages
- [ ] Search Console → URL Inspection → paste `https://thundthornthep-ai.github.io/`
- [ ] Click "Request Indexing"
- [ ] Repeat for key pages: pdpa-advisory.html, knowledge-hub.html

### Weekly Routine (Every Monday)

#### Performance Check
1. Search Console → Performance → Last 7 days
2. Note: Total clicks, impressions, average CTR, average position
3. Check which queries are driving traffic
4. Check which pages get the most impressions but low CTR (opportunity pages)

#### Index Coverage Check
1. Search Console → Pages → check for errors
2. Any new "Not indexed" pages? Investigate why
3. Any new "Crawled but not indexed"? May need content improvement

#### Structured Data Check
1. Search Console → Enhancements → check all structured data types
2. Ensure 0 errors, 0 warnings
3. If new content added, verify rich results eligibility

### Monthly Strategy Review

#### Content Performance
1. Which blog posts get the most impressions?
2. Which keywords are you ranking position 5-20 for? (improvement opportunity)
3. Are there new keyword opportunities from the Queries report?

#### Technical Health
1. Core Web Vitals report → any issues?
2. Mobile usability → any issues?
3. Security issues → should always be 0

---

## Part 4: Content Strategy for Keyword Targeting

### Strategy: Topical Authority Clusters

Instead of targeting individual keywords, build **topic clusters** that establish LAS/Dr. Thundthornthep as the authoritative source.

```
                    index.html (Pillar: Dr. Thundthornthep)
                           |
            +--------------+--------------+
            |              |              |
    knowledge-hub    pdpa-advisory    blog/bkk-council/
     (Pillar)         (Pillar)         (Pillar)
        |                |                |
   [Cluster]        [Cluster]        [Cluster]
   - contract       - PDPA guide     - ep1-ep6
   - corporate      - DPA review     (Bangkok policy)
   - labour         - breach notify
   - real estate    - cross-border
```

### New Content Priorities (Recommended)

#### Priority 1: Contract Drafting Guide
**Why**: "contract drafting" and "contract review" are high-value keywords with clear search intent
**Format**: Comprehensive guide page (like knowledge-hub.html)
**Target keywords**: contract drafting Thailand, contract review, NDA template, MOU drafting, business agreement
**JSON-LD**: Article or HowTo schema

#### Priority 2: Due Diligence & CP Guide  
**Why**: This is Dr. Thundthornthep's signature methodology — unique content
**Format**: In-depth article with methodology explanation
**Target keywords**: due diligence Thailand, conditions precedent, legal due diligence checklist
**JSON-LD**: Article schema

#### Priority 3: Expand Knowledge Hub
**Why**: knowledge-hub.html is already indexed — expand with sub-articles
**Format**: Add individual article pages linked from knowledge-hub.html
**Target keywords**: Thai business law, company formation Thailand, shareholder agreement

### Content Quality Rules (Google E-E-A-T)

1. **Experience**: Include real case references (MahaNakhon, Ritz-Carlton, IEAT)
2. **Expertise**: Cite specific laws (PDPA B.E. 2562, Condominium Act B.E. 2522)
3. **Authoritativeness**: Link to government sources (NIA, IEAT, PDPC)
4. **Trustworthiness**: Include author bio, credentials, contact information

---

## Part 5: Technical SEO Improvements

### Quick Wins

#### 1. Fix Sitemap (5 minutes)
Add ep6.html and update dates.

#### 2. Add Breadcrumb JSON-LD to Blog Pages
Each blog post should have BreadcrumbList schema:
```json
{
  "@type": "BreadcrumbList",
  "itemListElement": [
    {"@type": "ListItem", "position": 1, "name": "Home", "item": "https://thundthornthep-ai.github.io/"},
    {"@type": "ListItem", "position": 2, "name": "Bangkok Possible", "item": "https://thundthornthep-ai.github.io/blog/bkk-council/"},
    {"@type": "ListItem", "position": 3, "name": "Episode 1"}
  ]
}
```

#### 3. Add Article Schema to Blog Posts
Each blog post should have Article JSON-LD with:
- headline, author, datePublished, dateModified
- This enables rich results in Google Search

#### 4. Internal Linking Enhancement
- Every blog post should link back to index.html (author page)
- knowledge-hub.html should link to relevant blog posts
- pdpa-advisory.html should link to PDPA-related knowledge articles

#### 5. Page Speed Optimisation
- Compress images (banner-las-nia.jpg, dr-thundthornthep-photo.jpg)
- Add `loading="lazy"` to non-critical images
- Minimise CSS (inline styles → single stylesheet)

### Medium-Term Improvements

#### 6. Create a Dedicated 404 Page
Customise 404.html with navigation links to help users find content.

#### 7. Add Last-Modified Headers
GitHub Pages handles this automatically, but ensure `<lastmod>` in sitemap matches actual content dates.

#### 8. Implement hreflang (if Thai version is created)
```html
<link rel="alternate" hreflang="en" href="https://thundthornthep-ai.github.io/" />
<link rel="alternate" hreflang="th" href="https://thundthornthep-ai.github.io/th/" />
```

---

## Part 6: Quality Link Building Strategy

### Principle: 1 authoritative link > 300 spam links

### Tier 1: Government & Institutional (Highest Value)

| Source | Action | Status |
|--------|--------|--------|
| NIA (nia.or.th) | Ensure LAS is listed on NIA funded projects page | Check |
| IEAT (ieat.go.th) | Already linked | Active |
| SME D Bank (dx.smebank.co.th) | Already linked (coach profile) | Active |
| Lawyers Council of Thailand | Request listing as registered attorney | Action needed |
| Thai Bar Association | Request listing | Action needed |
| Kasetsart University | Request faculty profile link | Action needed |
| Bangkokthonburi University | Request faculty profile link | Action needed |

### Tier 2: News & Media (High Value)

| Source | Action | Status |
|--------|--------|--------|
| Siam Rath (siamrath.co.th) | 6 articles published | Active |
| Nation TV | 3 video interviews | Active |
| LINE TODAY | 1 article published | Active |
| THE POINT | 1 article published | Active |
| **New**: Pitch Bangkok Post | English article on AI Legal Tech | Opportunity |
| **New**: Pitch Nikkei Asia | Thai legal tech innovation story | Opportunity |
| **New**: Pitch TechSauce / Technode | AI Legal Tech startup story | Opportunity |

### Tier 3: Academic & Research (High Value)

| Source | Action | Status |
|--------|--------|--------|
| TCI-ThaiJO | 1 paper published | Active |
| ASEAN Citation Index | Indexed | Active |
| **New**: Submit to more academic journals | Cybercrime paper, AI legal paper | Opportunity |
| **New**: ResearchGate profile | Create and link publications | Opportunity |
| **New**: Google Scholar profile | Create and link publications | Opportunity |
| **New**: ORCID profile | Create and link publications | Opportunity |

### Tier 4: Professional Directories (Medium Value)

| Source | Action | Status |
|--------|--------|--------|
| LinkedIn (personal + company) | Create/update with links | Action needed |
| Google Business Profile | Create for LAS office | Action needed |
| Asia Law Profiles | Request listing | Opportunity |
| Legal500 | Request listing | Opportunity |
| Chambers & Partners | Request listing | Opportunity |

### DO NOT USE (Negative Value)
- Classified ad sites (usnetads, freewebads, etc.)
- Micro social networks (bresdel, vevioz, etc.)
- Article spinning directories
- Bulk link building services
- PBN (Private Blog Network) links

---

## Part 7: AI Search Optimisation

### Why AI Search Matters

AI search engines (ChatGPT with search, Perplexity, Google AI Overview, Bing Copilot) are increasingly used for professional queries like "best PDPA lawyer Thailand" or "AI legal technology Thailand". These engines:

1. **Prioritise authoritative, well-structured content** over link quantity
2. **Read JSON-LD structured data** to understand entities
3. **Cite sources** they consider trustworthy
4. **Favour comprehensive, factual content** with verifiable claims

### What We Already Do Well

- [x] robots.txt allows all AI crawlers (GPTBot, Claude-Web, PerplexityBot, etc.)
- [x] 8 JSON-LD blocks provide rich entity information
- [x] FAQ schema provides pre-formatted Q&A for AI to cite
- [x] Content includes verifiable claims (NIA funding, government appointments, publications)
- [x] External validation from news media (Siam Rath, Nation TV)

### Additional AI Search Actions

#### 1. Expand FAQ Schema
Add more questions that people might ask AI:
- "Who is the best AI legal tech lawyer in Thailand?"
- "What law firms in Thailand use AI for legal research?"
- "How does the LAS AI legal research system work?"
- "What is the best PDPA compliance service in Thailand?"

#### 2. Create Structured How-To Content
AI search engines love step-by-step guides they can cite:
- "How to draft a business contract in Thailand — 10-step guide"
- "How to comply with PDPA — complete checklist"
- "How to set up a company in Thailand — legal requirements"

#### 3. Ensure Content is "AI-Citable"
- Write clear topic sentences at the start of each section
- Use specific numbers and facts (not vague claims)
- Include dates, law references, and named sources
- Structure content with clear headings and bullet points

---

## Part 8: Monitoring & KPIs

### Weekly KPIs (Google Search Console)

| Metric | Where to Check | Target |
|--------|---------------|--------|
| Total impressions | Performance → Search results | Growing week-over-week |
| Total clicks | Performance → Search results | Growing |
| Average CTR | Performance → Search results | > 3% |
| Average position | Performance → Search results | < 20 for target keywords |
| Indexed pages | Pages → Indexed | Should match sitemap count |
| Structured data errors | Enhancements | 0 errors |

### Monthly KPIs

| Metric | How to Check | Target |
|--------|-------------|--------|
| Keyword rankings | Search Console → Queries | Top 10 for name, top 20 for topics |
| New backlinks | Search Console → Links | Quality over quantity |
| Rich results eligibility | Rich Results Test tool | All pages eligible |
| AI search presence | Ask ChatGPT/Perplexity about Dr. Thundthornthep | Accurate, sourced answers |

### Quarterly Review

1. Which content strategies worked? Create more like that.
2. Which keywords moved up/down? Adjust content.
3. Any Google algorithm updates? Check Search Central Blog.
4. Competitor analysis: Who else ranks for our target keywords?

---

## Part 9: Implementation Priority

### Phase 1 — This Week (Quick Wins)
1. ✅ Fix structured data errors (DONE)
2. ✅ Convert to English-only (DONE)
3. ✅ Add press coverage + research paper (DONE)
4. [ ] Validate fix in Search Console
5. [ ] Fix sitemap (add ep6)
6. [ ] Request indexing for updated pages

### Phase 2 — This Month (Foundation)
7. [ ] Create Google Business Profile for LAS
8. [ ] Create LinkedIn company page with backlink
9. [ ] Create Google Scholar / ResearchGate / ORCID profiles
10. [ ] Add Article schema to all blog posts
11. [ ] Add BreadcrumbList schema to all blog posts
12. [ ] Compress images for page speed

### Phase 3 — Next 2-3 Months (Content Growth)
13. [ ] Create Contract Drafting Guide page
14. [ ] Create Due Diligence & CP Guide page
15. [ ] Expand Knowledge Hub with sub-articles
16. [ ] Pitch English-language media (Bangkok Post, TechSauce)
17. [ ] Request university faculty profile links

### Phase 4 — Ongoing (Maintenance)
18. [ ] Weekly Search Console check (every Monday)
19. [ ] Monthly content performance review
20. [ ] Quarterly strategy review
21. [ ] Submit new content to IndexNow after every push
22. [ ] Monitor AI search presence quarterly

---

## Appendix: Search Console Quick Reference

### How to Validate the Structured Data Fix
1. Go to https://search.google.com/search-console
2. Select property: thundthornthep-ai.github.io
3. Left menu → Enhancements → Unparsable structured data (or the specific error)
4. Click "Validate Fix" button
5. Google will re-crawl within 1-3 days

### How to Submit Sitemap
1. Search Console → Sitemaps (left menu)
2. Enter: sitemap.xml
3. Click Submit
4. Status should show "Success" after processing

### How to Request Indexing
1. Search Console → URL Inspection (top bar)
2. Paste the full URL
3. Wait for inspection result
4. Click "Request Indexing"
5. Limit: ~10 requests per day

### How to Check Performance
1. Search Console → Performance → Search results
2. Enable all 4 metrics: Clicks, Impressions, CTR, Position
3. Use date filter: Compare last 28 days vs previous 28 days
4. Check Queries tab for keyword performance
5. Check Pages tab for page performance

### IndexNow Command (after every git push)
```bash
curl -s -X POST "https://api.indexnow.org/IndexNow" \
  -H "Content-Type: application/json" \
  -d '{
    "host": "thundthornthep-ai.github.io",
    "key": "edf7224080ca4a2cab334f2c9ae43ea7",
    "keyLocation": "https://thundthornthep-ai.github.io/edf7224080ca4a2cab334f2c9ae43ea7.txt",
    "urlList": [
      "https://thundthornthep-ai.github.io/",
      "https://thundthornthep-ai.github.io/pdpa-advisory.html",
      "https://thundthornthep-ai.github.io/knowledge-hub.html"
    ]
  }' -w "\nHTTP Status: %{http_code}\n"
```
