// WEO Ontology — Neo4j 5.x schema (core + visibility + engagement + decision + strategy)
// Entities are durable, episodes are immutable, tenancy lives in properties.

// ========== CORE ==========

// ---------- Entities ----------
CREATE CONSTRAINT website_id IF NOT EXISTS
FOR (w:Website) REQUIRE w.id IS UNIQUE;

CREATE CONSTRAINT website_origin IF NOT EXISTS
FOR (w:Website) REQUIRE w.origin IS UNIQUE;

// URL identity is (address, websiteId) — same address can exist under two tenants.
CREATE CONSTRAINT url_identity IF NOT EXISTS
FOR (u:URL) REQUIRE (u.address, u.websiteId) IS UNIQUE;

CREATE CONSTRAINT term_name IF NOT EXISTS
FOR (t:Term) REQUIRE t.name IS UNIQUE;

// Topics are derivations, scoped per site.
CREATE CONSTRAINT topic_identity IF NOT EXISTS
FOR (t:Topic) REQUIRE (t.name, t.websiteId) IS UNIQUE;

// ---------- Episodes ----------
CREATE CONSTRAINT crawl_id IF NOT EXISTS
FOR (c:Crawl) REQUIRE c.id IS UNIQUE;

CREATE CONSTRAINT serp_snapshot_id IF NOT EXISTS
FOR (s:SerpSnapshot) REQUIRE s.id IS UNIQUE;

// ---------- Secondary indexes ----------
CREATE INDEX serp_snapshot_captured IF NOT EXISTS
FOR (s:SerpSnapshot) ON (s.capturedAt);

CREATE INDEX crawl_started IF NOT EXISTS
FOR (c:Crawl) ON (c.startedAt);

// RANKS_FOR is period-scoped; range scans by window are the hot path.
CREATE INDEX ranks_for_period IF NOT EXISTS
FOR ()-[r:RANKS_FOR]-() ON (r.periodStart);

// Link liveness checks resolve against the crawl that last saw the edge.
CREATE INDEX links_to_last_seen IF NOT EXISTS
FOR ()-[l:LINKS_TO]-() ON (l.lastSeenCrawlId);

CREATE INDEX fetched_status IF NOT EXISTS
FOR ()-[f:FETCHED]-() ON (f.statusCode);

// ========== VISIBILITY (the xEO layer) ==========

// ---------- Entities ----------
CREATE CONSTRAINT engine_id IF NOT EXISTS
FOR (e:Engine) REQUIRE e.id IS UNIQUE;

// Brands are tenant-scoped: the same market name can be tracked by two tenants.
CREATE CONSTRAINT brand_identity IF NOT EXISTS
FOR (b:Brand) REQUIRE (b.name, b.websiteId) IS UNIQUE;

CREATE CONSTRAINT prompt_identity IF NOT EXISTS
FOR (p:Prompt) REQUIRE (p.text, p.websiteId) IS UNIQUE;

// ---------- Episodes ----------
CREATE CONSTRAINT llm_response_id IF NOT EXISTS
FOR (r:LLMResponse) REQUIRE r.id IS UNIQUE;

CREATE INDEX llm_response_captured IF NOT EXISTS
FOR (r:LLMResponse) ON (r.capturedAt);

// ---------- Rollups ----------
// VISIBILITY_FOR mirrors RANKS_FOR: period-scoped projection over responses.
CREATE INDEX visibility_for_period IF NOT EXISTS
FOR ()-[v:VISIBILITY_FOR]-() ON (v.periodStart);

// MENTIONS rank is the list-position analysis hot path.
CREATE INDEX mentions_rank IF NOT EXISTS
FOR ()-[m:MENTIONS]-() ON (m.mentionRank);

// ========== ENGAGEMENT (draft) ==========

CREATE CONSTRAINT conversion_point_id IF NOT EXISTS
FOR (c:ConversionPoint) REQUIRE c.id IS UNIQUE;

CREATE CONSTRAINT conversion_event_id IF NOT EXISTS
FOR (e:ConversionEvent) REQUIRE e.id IS UNIQUE;

CREATE INDEX conversion_event_time IF NOT EXISTS
FOR (e:ConversionEvent) ON (e.occurredAt);

// The CRM join contract: look up graph objects from a CRM record id.
CREATE INDEX conversion_point_crm_ref IF NOT EXISTS
FOR (c:ConversionPoint) ON (c.crmRecordRef);

// ========== DECISION (the interpretation tier) ==========

// ---------- Entities ----------
// Tactics are a shared library (global); intervention category is a slotted-in concept.
CREATE CONSTRAINT tactic_id IF NOT EXISTS
FOR (t:Tactic) REQUIRE t.id IS UNIQUE;

CREATE CONSTRAINT diagnostic_id IF NOT EXISTS
FOR (d:Diagnostic) REQUIRE d.id IS UNIQUE;

// Capabilities are the scope-gate levers, approved per tenant.
CREATE CONSTRAINT capability_identity IF NOT EXISTS
FOR (c:Capability) REQUIRE (c.name, c.websiteId) IS UNIQUE;

// Gaps are diagnosed per tenant.
CREATE CONSTRAINT gap_id IF NOT EXISTS
FOR (g:Gap) REQUIRE g.id IS UNIQUE;

CREATE CONSTRAINT recommendation_id IF NOT EXISTS
FOR (r:Recommendation) REQUIRE r.id IS UNIQUE;

// ---------- Episodes ----------
CREATE CONSTRAINT experiment_id IF NOT EXISTS
FOR (e:Experiment) REQUIRE e.id IS UNIQUE;

CREATE INDEX experiment_concluded IF NOT EXISTS
FOR (e:Experiment) ON (e.concludedAt);

// Precedent lookup: "tactics tried against a gap of this kind" scans by gapType.
CREATE INDEX gap_website IF NOT EXISTS
FOR (g:Gap) ON (g.websiteId);

// ========== STRATEGY (the norms tier) ==========
// Practices and Playbooks are authored once and reused; what varies per tenant is
// which Playbooks are activated and which Practices are overridden. Both are
// global by id — tenancy rides on the activation and override edges, not on the
// rule itself. Matches weo-graph-kit/seed/practices.cypher.

CREATE CONSTRAINT practice_id IF NOT EXISTS
FOR (p:Practice) REQUIRE p.id IS UNIQUE;

CREATE CONSTRAINT playbook_id IF NOT EXISTS
FOR (pb:Playbook) REQUIRE pb.id IS UNIQUE;

// Only 'active' Practices fire; 'proposed' is visible but inert, 'deprecated' is
// retired-not-deleted (superseding one deprecates it). Every evaluation filters
// on this, so it is the hot path.
CREATE INDEX practice_status IF NOT EXISTS
FOR (p:Practice) ON (p.status);

// A claimed Practice decays unless experiments promote it; the sweep scans by source.
CREATE INDEX practice_source IF NOT EXISTS
FOR (p:Practice) ON (p.source);

// The audit trail: "which rules fired on this recommendation, and why".
CREATE INDEX applied_practice_method IF NOT EXISTS
FOR ()-[a:APPLIED_PRACTICE]-() ON (a.method);

// ========== NOTES ==========
// Embeddings live in an external vector store; the graph keeps only the
// derivation claim (embeddingRef, embeddingModel, embeddedAt) on :Term.
// Daily search-performance grain lives in a column store (e.g. BigQuery) as
// SearchPerformanceFact rows; the graph keeps windowed RANKS_FOR rollups.
// Raw LLM responses may be archived outside the graph at scale; keep the
// episode node + observation edges here and point datasetUri at the archive.

// Optional — only if you later choose to colocate vectors in Neo4j:
// CREATE VECTOR INDEX term_embedding IF NOT EXISTS
// FOR (t:Term) ON (t.embedding)
// OPTIONS {indexConfig: {
//   `vector.dimensions`: 1536,   // must match embeddingModel
//   `vector.similarity_function`: 'cosine'
// }};
