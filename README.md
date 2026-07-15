# WEO — the Web Engine Optimization ontology

A small, standards-grounded vocabulary for how **web engines** — search engines,
generative overviews, answer engines, conversational agents — see, cite, and serve
web content. One graph model for the whole **xEO** family: SEO, GEO, AEO, and
whatever letter comes next.

**Prefix:** `weo:` · **Namespace:** `https://inboundfound.github.io/weo-ontology/weo#`
· **Status:** v0.2 — open draft, built to be riffed on. Issues and PRs welcome.

## Why "WEO"

Marketers already think in `-EO`: SEO, then GEO, then AEO. The engines keep
changing; the discipline — *make your content legible and creditable to the machine
between you and your audience* — doesn't. WEO names that discipline once, and the
ontology's `Engine` taxonomy absorbs new surfaces as subclasses instead of new
acronyms.

## What makes this one different

1. **Observations are grounded in primary standards.** Every observational term
   cites the spec or API contract that defines it — HTTP (RFC 9110), WHATWG
   HTML/URL, RFC 6596, the GSC Search Analytics API, per-provider response
   annotations. No dependency on any third-party SEO vocabulary.
2. **Epistemic layering.** Every term is typed by the kind of claim it makes:
   `entity` (durable identity) · `episode` (happened at a time, immutable) ·
   `observation` (measured fact) · `derivation` (model output — carries method,
   model, confidence) · `judgment` (a strategist's claim, labeled as one).
   An agent assembling context can filter to observations only.
3. **Storage-agnostic.** The ontology defines meaning and identity keys; every
   term declares a *canonical store*. The graph holds what you traverse; the
   column store holds high-cardinality time-series facts; the vector store holds
   geometry; the CRM holds the pipeline. Identity keys join across stores.
4. **Tenancy is data, not schema.** Scope lives in properties (`websiteId`),
   never in dynamic labels.
5. **Integrate with data sources, not vocabularies.** Mapping modules for your
   CRM/analytics stack are operational pointers (identity keys), never baked-in
   vendor vocabularies.

## Modules

| File | Layer | Contents |
|---|---|---|
| `weo-core.ttl` | the SEO substrate | `Website`, `URL`, `Term`, `Crawl`, `SerpSnapshot`, `Topic`, `SearchPerformanceFact`; `FETCHED`, `LINKS_TO`, `REDIRECTS_TO`, `HAS_CANONICAL`, `RANKS_FOR` (windowed rollups with `datasetUri` provenance), `HAS_RESULT`, `IN_TOPIC` |
| `weo-visibility.ttl` | the xEO layer | `Engine` (+ `SearchEngine` / `GenerativeEngine` / `AnswerEngine` / `ConversationalAgent`), `Brand`, `Prompt`, `LLMResponse`; `CITES`, `MENTIONS {mentionRank}`, `FANS_OUT_TO` (fan-out queries **are** Terms — the join back to rank data), `VISIBILITY_FOR` rollups (`mentionRate`, `citationRate`) |
| `weo-engagement.ttl` | draft v0 | `SearchIntent` individuals (Broder 2002, extended), `ConversionPoint` (+ `CallToAction` / `LeadCaptureForm` / `GatedAsset`), `ConversionEvent`, `crmRecordRef` (the CRM join key), `attributedResponse` (pre-click attribution — a labeled judgment) |
| `schema.cypher` | property graph | Neo4j 5.x constraints + indexes for all three modules |

The core module is the stable substrate. Visibility is field-tested against a
working tracker/response-capture/Neo4j implementation. Engagement is an early
draft published for discussion — the "pre-click funnel" seam that engine-side
data has been missing.

## The mental model

```
                        entities (durable)          episodes (immutable)
  core        Website · URL · Term · Topic     Crawl · SerpSnapshot
  visibility  Engine · Brand · Prompt          LLMResponse
  engagement  ConversionPoint · SearchIntent   ConversionEvent

  observations attach facts to entities/episodes (FETCHED, CITES, MENTIONS…)
  derivations carry method/model/confidence (IN_TOPIC, embeddingRef…)
  judgments are labeled claims (targetsIntent, attributedResponse)
  high-cardinality facts live in column stores; graphs keep windowed rollups
  with datasetUri pointing at the authoritative table
```

Two rollup patterns rhyme on purpose:

- `(:URL)-[:RANKS_FOR {clicks, impressions, avgPosition, periodStart, periodEnd, datasetUri}]->(:Term)`
- `(:Prompt)-[:VISIBILITY_FOR {mentionRate, citationRate, responses, periodStart, periodEnd, datasetUri}]->(:Brand)`

The first summarizes the SEO world (facts in your column store); the second
summarizes the xEO world (facts in your response archive). Same discipline,
new engine.

## Example queries the model is shaped for

```cypher
// Cited but not named: pages that ground answers naming someone else
MATCH (r:LLMResponse)-[:CITES]->(u:URL {websiteId: $tenant})
WHERE NOT EXISTS { MATCH (r)-[:MENTIONS]->(:Brand {websiteId: $tenant}) }
RETURN u.address, count(r) AS ghost_citations ORDER BY ghost_citations DESC;

// List filler: mentioned often, ranked late
MATCH (r:LLMResponse)-[m:MENTIONS]->(b:Brand)
RETURN b.name, count(r) AS mentions, avg(m.mentionRank) AS avg_rank
ORDER BY mentions DESC;

// The fan-out join: engine retrieval queries you already rank for
MATCH (p:Prompt)-[:FANS_OUT_TO]->(t:Term)<-[rf:RANKS_FOR]-(u:URL)
WHERE rf.avgPosition <= 10
RETURN p.text, t.name, u.address, rf.avgPosition;

// Pre-click to pipeline (engagement draft): visibility windows around a conversion
MATCH (e:ConversionEvent)-[:CAPTURED_BY]->(cp:ConversionPoint)<-[:HAS_CONVERSION_POINT]-(u:URL)
MATCH (r:LLMResponse)-[:CITES]->(u)
WHERE r.capturedAt < e.occurredAt <= r.capturedAt + duration('P7D')
RETURN e.id, cp.crmRecordRef, collect(r.id) AS candidate_responses;
```

## What is deliberately NOT here

- **Judgment/decision machinery** (recommendations, playbooks, experiments,
  outcomes) — that layer references these terms but lives above them.
- **Vendor vocabularies** — your CRM and analytics stack join via identity keys
  (`crmRecordRef`, `datasetUri`), never as imported schemas.
- **Quality scores and other unfalsifiable constructs** — if it isn't an
  observation, a provenance-carrying derivation, or a labeled judgment, it
  doesn't get a term.

## Using it

```bash
# property graph
cat schema.cypher | cypher-shell -u neo4j -p <password>
```

The TTL files are plain OWL — load them into any triple store or ontology
editor. The namespace is served from GitHub Pages; a persistent-identifier
redirect (w3id.org) may be added later without changing term local names.

## Maintained by

[Inbound Found](https://github.com/inboundfound). Built by working backwards
from a production marketing knowledge graph, then generalized. Contributions,
counter-proposals, and rude questions about our modeling choices are all welcome.

## License

[CC BY 4.0](LICENSE) — use it, extend it, ship it; just attribute.
