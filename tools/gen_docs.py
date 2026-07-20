#!/usr/bin/env python3
"""Generate weo/index.html — human-readable docs for the WEO ontology.

Reads the weo-*.ttl modules and emits ONE self-contained HTML page. Because WEO
uses a hash namespace (…/weo#Term), the whole ontology is a single document and
each term is a #fragment within it — so giving every term an ``id`` here is what
makes its IRI resolve (…/weo#Gap scrolls to the Gap section).

Requires rdflib (``pip install rdflib``).
Usage:  python tools/gen_docs.py        # writes weo/index.html
"""
import html
import os
from rdflib import Graph, RDF, RDFS, OWL, URIRef
from rdflib.namespace import DCTERMS

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NS = "https://inboundfound.github.io/weo-ontology/weo#"
MODULES = [
    "weo-core.ttl", "weo-visibility.ttl", "weo-engagement.ttl",
    "weo-decision.ttl", "weo-strategy.ttl", "weo-align.ttl",
]
EPI = URIRef(NS + "epistemicLayer")
GROUNDED = URIRef(NS + "groundedIn")
STORE = URIRef(NS + "canonicalStore")

PREFIXES = {
    NS: "weo:",
    "https://schema.org/": "schema:",
    "http://www.w3.org/ns/prov#": "prov:",
    "http://www.w3.org/2004/02/skos/core#": "skos:",
    "http://www.w3.org/2001/XMLSchema#": "xsd:",
    "http://www.w3.org/2000/01/rdf-schema#": "rdfs:",
    "http://purl.org/dc/terms/": "dct:",
}
LAYERS = ["entity", "episode", "observation", "derivation", "interpretation", "norm"]
LAYER_HUE = {  # the stratigraphic palette
    "entity": "#718096", "episode": "#319795", "observation": "#38A169",
    "derivation": "#805AD5", "interpretation": "#DD6B20", "norm": "#D69E2E",
}


def qname(uri):
    s = str(uri)
    for base, pre in PREFIXES.items():
        if s.startswith(base):
            return pre + s[len(base):]
    return s


def local(uri):
    return str(uri).split("#")[-1].split("/")[-1]


def link(uri):
    s = str(uri)
    if s.startswith(NS):
        return f'<a href="#{local(uri)}">{html.escape(qname(uri))}</a>'
    return f'<a href="{html.escape(s)}" class="ext">{html.escape(qname(uri))}</a>'


def main():
    g = Graph()
    origin = {}
    for m in MODULES:
        mg = Graph()
        mg.parse(os.path.join(HERE, m), format="turtle")
        for s in set(mg.subjects()):
            if str(s).startswith(NS) and s not in origin:
                origin[s] = m
        g += mg

    def val(s, p):
        o = g.value(s, p)
        return str(o) if o is not None else None

    def render(term):
        lbl = val(term, RDFS.label) or local(term)
        layer = val(term, EPI)
        desc = val(term, DCTERMS.description) or val(term, RDFS.comment) or ""
        rows = []
        dom = list(g.objects(term, RDFS.domain))
        rng = list(g.objects(term, RDFS.range))
        sc = list(g.objects(term, RDFS.subClassOf))
        sp = list(g.objects(term, RDFS.subPropertyOf))
        cm = list(g.objects(term, URIRef("http://www.w3.org/2004/02/skos/core#closeMatch")))
        sa = list(g.objects(term, RDFS.seeAlso))
        gr = val(term, GROUNDED)
        st = val(term, STORE)
        if dom: rows.append(("domain", " · ".join(link(x) for x in dom)))
        if rng: rows.append(("range", " · ".join(link(x) for x in rng)))
        if sc:  rows.append(("subclass of", " · ".join(link(x) for x in sc)))
        if sp:  rows.append(("subproperty of", " · ".join(link(x) for x in sp)))
        if cm:  rows.append(("closeMatch", " · ".join(link(x) for x in cm)))
        if sa:  rows.append(("seeAlso", " · ".join(link(x) for x in sa)))
        if gr:  rows.append(("grounded in", html.escape(gr)))
        if st:  rows.append(("canonical store", html.escape(st)))
        badge = (f'<span class="layer" style="--h:{LAYER_HUE[layer]}">{layer}</span>'
                 if layer in LAYER_HUE else "")
        dl = "".join(f'<div class="row"><dt>{k}</dt><dd>{v}</dd></div>' for k, v in rows)
        mod = origin.get(term, "").replace(".ttl", "")
        return f'''<section id="{local(term)}" class="term">
  <h3>{html.escape(lbl)} {badge}<span class="mod">{html.escape(mod)}</span></h3>
  <code class="iri">{html.escape(qname(term))}</code>
  <p>{html.escape(desc)}</p>
  {f'<dl>{dl}</dl>' if dl else ''}
</section>'''

    def grp(pred_type, title):
        terms = sorted((s for s in set(g.subjects(RDF.type, pred_type))
                        if str(s).startswith(NS)), key=local)
        if not terms:
            return ""
        body = "\n".join(render(t) for t in terms)
        return f'<h2 id="{title.lower().replace(" ", "-")}">{title} <span class="n">{len(terms)}</span></h2>\n{body}'

    classes = grp(OWL.Class, "Classes")
    objprops = grp(OWL.ObjectProperty, "Object properties")
    dataprops = grp(OWL.DatatypeProperty, "Datatype properties")
    annprops = grp(OWL.AnnotationProperty, "Annotation properties")
    # individuals: typed by a weo class, not themselves a class/property
    typed = {s for s in set(g.subjects()) if str(s).startswith(NS)}
    meta = set(g.subjects(RDF.type, OWL.Class)) | set(g.subjects(RDF.type, OWL.ObjectProperty)) \
        | set(g.subjects(RDF.type, OWL.DatatypeProperty)) | set(g.subjects(RDF.type, OWL.AnnotationProperty))
    inds = sorted((s for s in typed if s not in meta
                   and any(str(o).startswith(NS) for o in g.objects(s, RDF.type))), key=local)
    individuals = ""
    if inds:
        body = "\n".join(render(t) for t in inds)
        individuals = f'<h2 id="individuals">Individuals <span class="n">{len(inds)}</span></h2>\n{body}'

    legend = "".join(
        f'<span class="layer" style="--h:{LAYER_HUE[l]}">{l}</span>' for l in LAYERS)

    out = f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>WEO — Web Engine Optimization ontology (terms)</title>
<meta name="description" content="Term reference for the WEO ontology: classes, properties, and individuals across the core, visibility, engagement, decision, and strategy modules.">
<link rel="alternate" type="text/turtle" href="weo-core.ttl">
<style>
:root {{ color-scheme: light dark; --bg:#f7f5ef; --surface:#fffdf8; --text:#17181c;
  --muted:#5b5f5a; --border:#ddd8c8; --accent:#1f4d4d; --link:#1f4d4d; }}
@media (prefers-color-scheme: dark) {{ :root {{ --bg:#0d0f0d; --surface:#141714;
  --text:#e6e8e1; --muted:#8a9089; --border:#262a24; --accent:#5fd9c0; --link:#5fd9c0; }} }}
* {{ box-sizing:border-box; }}
body {{ margin:0; background:var(--bg); color:var(--text);
  font:16px/1.55 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif; }}
.wrap {{ max-width:900px; margin:0 auto; padding:2.5rem 1.25rem 6rem; }}
h1,h2,h3 {{ font-family:Charter,"Iowan Old Style",Georgia,serif; line-height:1.2; }}
h1 {{ font-size:2rem; margin:0 0 .25rem; }}
.tag {{ color:var(--muted); font-size:.9rem; }}
h2 {{ margin:3rem 0 1rem; padding-bottom:.35rem; border-bottom:1px solid var(--border);
  font-size:1.4rem; }}
h2 .n, h3 .mod {{ color:var(--muted); font-size:.7em; font-weight:400; }}
.term {{ background:var(--surface); border:1px solid var(--border); border-radius:8px;
  padding:1rem 1.15rem; margin:.9rem 0; scroll-margin-top:1rem; }}
.term h3 {{ margin:0 0 .35rem; font-size:1.12rem; display:flex; align-items:center;
  gap:.5rem; flex-wrap:wrap; }}
.term h3 .mod {{ margin-left:auto; }}
.iri {{ color:var(--muted); font-size:.82rem; }}
.term p {{ margin:.5rem 0 .25rem; }}
dl {{ margin:.5rem 0 0; border-top:1px dashed var(--border); padding-top:.5rem; }}
.row {{ display:flex; gap:.75rem; padding:.15rem 0; }}
.row dt {{ flex:0 0 8.5rem; color:var(--muted); font-size:.85rem; }}
.row dd {{ margin:0; font-size:.9rem; }}
a {{ color:var(--link); text-decoration:none; }}
a:hover {{ text-decoration:underline; }}
a.ext::after {{ content:" ↗"; font-size:.75em; opacity:.6; }}
code {{ font-family:ui-monospace,SFMono-Regular,Menlo,monospace; }}
.layer {{ font-size:.65rem; text-transform:uppercase; letter-spacing:.04em;
  padding:.1rem .45rem; border-radius:999px; color:#fff; background:var(--h);
  font-family:system-ui; font-weight:600; }}
.legend {{ display:flex; gap:.4rem; flex-wrap:wrap; margin:1rem 0 0; }}
.lead {{ color:var(--muted); max-width:60ch; }}
.modnote {{ background:var(--surface); border:1px solid var(--border); border-radius:8px;
  padding:.75rem 1rem; margin:1.25rem 0; font-size:.9rem; }}
</style>
</head>
<body>
<div class="wrap">
<h1>WEO — the Web Engine Optimization ontology</h1>
<p class="tag">Namespace <code>{NS}</code> · prefix <code>weo:</code> · v0.2 ·
<a href="https://github.com/inboundfound/weo-ontology">repo</a> · CC BY 4.0</p>
<p class="lead">One standards-grounded vocabulary for how web engines — search,
generative, answer, conversational — see, cite, and serve content. Every term is
typed by the kind of claim it makes; the strata run from durable bedrock to
interpretive surface:</p>
<div class="legend">{legend}</div>
<div class="modnote">Modules: <code>weo-core</code> (substrate) ·
<code>weo-visibility</code> (xEO) · <code>weo-engagement</code> (draft) ·
<code>weo-decision</code> (interpretation tier) · <code>weo-strategy</code> (norms tier) ·
<code>weo-align</code> (schema.org / PROV-O / SKOS bridges). Machine-readable Turtle:
<a href="weo-core.ttl">core</a>, <a href="weo-visibility.ttl">visibility</a>,
<a href="weo-engagement.ttl">engagement</a>, <a href="weo-decision.ttl">decision</a>,
<a href="weo-strategy.ttl">strategy</a>, <a href="weo-align.ttl">align</a>;
JSON-LD <a href="context.jsonld">context</a>.</div>
{classes}
{objprops}
{dataprops}
{annprops}
{individuals}
</div>
</body>
</html>
'''
    os.makedirs(os.path.join(HERE, "weo"), exist_ok=True)
    dest = os.path.join(HERE, "weo", "index.html")
    with open(dest, "w", encoding="utf-8") as fh:
        fh.write(out)
    n = out.count('class="term"')
    print(f"wrote {dest}  ({n} terms documented)")


if __name__ == "__main__":
    main()
