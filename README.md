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
| `weo-align.ttl` | interoperability | Optional bridges — schema.org (`WebSite`, `WebPage`, `Brand`, `Observation`), PROV-O (`Crawl`→`Activity`, `Engine`→`SoftwareAgent`, `LLMResponse`→`Entity`), SKOS (`Topic`→`Concept`, `childOf`→`broader`). **Alignments, not dependencies.** |
| `context.jsonld` | interoperability | A JSON-LD `@context` mapping graph labels/relationships/properties to IRIs — turns a Neo4j export into valid RDF/JSON-LD in one pass. |
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

## Interoperability — stands alone, bridges out

WEO has **no hard dependency**: core, visibility, and engagement load and reason
with zero external vocabularies present. It grounds its own terms in primary
standards (HTTP, WHATWG, the GSC API) rather than borrowing another SEO ontology.

For anyone who already speaks the foundational web vocabularies, `weo-align.ttl`
is an **optional crosswalk** — alignments, not imports:

- **schema.org** (the neutral base for web entities): `Website`→`schema:WebSite`,
  `URL`→`schema:WebPage`, `Brand`→`schema:Brand`, `SearchPerformanceFact`→`schema:Observation`.
  Two calibrated choices keep the bridges honest: `weo:URL` is a `skos:closeMatch`
  (not an equivalence) to `schema:WebPage`, because WEO deliberately keeps the
  address (entity) separate from the page's rendered state (a Fetch observation);
  metrics map to `schema:Observation`, never a reified score class.
- **PROV-O** (the provenance spine): WEO's epistemic layering *is* provenance.
  `Crawl` is a `prov:Activity`, `Engine` a `prov:SoftwareAgent`, a captured
  `LLMResponse` a `prov:Entity` attributed (`onEngine`→`prov:wasAttributedTo`) to
  the engine that generated it.
- **SKOS** (the taxonomy spine): `Topic` is a `skos:Concept`, `childOf` is
  `skos:broader`. This is the seam where users slot in their **own** concept
  scheme — of topics, gaps, or funnel stages — without editing the ontology.

Alignment uses `skos:closeMatch` where the correspondence is approximate (no
forced logical entailment) and `rdfs:subClassOf`/`subPropertyOf` only where a WEO
term is a genuine specialization. The bridges assert nothing false and can be
ignored entirely.

`context.jsonld` is the operational half: point it at a Neo4j export and the
graph's labels, relationship types, and properties become valid RDF/JSON-LD —
object properties resolve to node references, datatype properties carry their
`xsd` types. Legible names in the graph, real IRIs on export.

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

The TTL files are plain OWL — load `weo-core`, `weo-visibility`,
`weo-engagement`, and (if you want the crosswalk) `weo-align` into any triple
store or ontology editor. To publish graph data as linked data, serve your
Neo4j export under `context.jsonld` and it validates as RDF/JSON-LD.

**Namespace.** Terms currently resolve under GitHub Pages
(`https://inboundfound.github.io/weo-ontology/weo#`). The intended permanent home
is **weoontology.org** — served with content negotiation so each term IRI
resolves to human docs (HTML) or the ontology (Turtle). Local term names never
change, so a w3id.org-style redirect can front either host without breaking any
published IRI.

## Maintained by

[Inbound Found](https://github.com/inboundfound). Built by working backwards
from a production marketing knowledge graph, then generalized. Contributions,
counter-proposals, and rude questions about our modeling choices are all welcome.

## License

[CC BY 4.0](LICENSE) — use it, extend it, ship it; just attribute.
