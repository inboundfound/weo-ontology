# References — prior art

Ontologies and vocabularies WEO relates to. Distilled so the source repos don't need to be
checked out locally.

---

## SEOntology (`seovoc`) — WordLift et al.

<https://github.com/seontology/seontology> · namespace `https://w3id.org/seovoc/` · 96 commits, none ours

The closest prior art to WEO: an open-source SEO domain ontology, initially developed by
WordLift and enriched by SEO practitioners and knowledge engineers. Described by its authors as
"a semantic operating system for modern SEO" — a shared vocabulary letting agents, apps and
researchers reason about, audit and optimise content. Self-described as an early draft.

Accepted at **SEMANTiCS 2026** (Research & Innovation Track).

Ships `seovoc.ttl` / `seovoc.owl` (~134 KB). Imports/relates to `schema.org`, `skos`, `voaf`,
`dc`/`dcterms`, and WordLift's earlier `SEO_Ontology`.

```bibtex
@software{gjorgjevska2026seontology,
  title        = {SEOntology: A Domain Ontology for Semantic Modeling of Search Engine Optimization Workflows},
  author       = {Gjorgjevska, Emilija and Riccitelli, David and Jovanovik, Milos and Volpini, Andrea},
  year         = {2026},
  url          = {https://github.com/seontology/seontology},
  note         = {Accepted at SEMANTiCS 2026 Research & Innovation Track}
}
```

### Alignment status: none yet

`weo-align.ttl` currently aligns WEO to `schema.org`, `prov`, `skos` and `dcterms`. **It does
not mention `seovoc`.** Given SEOntology covers adjacent ground and is now peer-reviewed, an
explicit alignment — or an explicit, reasoned statement of where WEO deliberately diverges —
is an open piece of work rather than an oversight to fix silently.

---

## Also related

The runnable consumer of this ontology is
[`weo-graph-kit`](https://github.com/inboundfound/weo-graph-kit), which carries its own
`REFERENCES.md` for the implementation-side prior art (Neo4j context graphs, GEO tactics
planning).
