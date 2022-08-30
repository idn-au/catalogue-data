from rdflib import Graph, Literal, URIRef, BNode, Namespace
from rdflib.namespace import DCAT, DCTERMS, PROV, RDF, SDO, XSD
from pathlib import Path

fs = Path(Path(__file__).parent.parent / "data" / "resources").glob("*.ttl")

for f in sorted(fs):
    print(f)
    g = Graph().parse(f)
    r = g.value(predicate=RDF.type, object=DCAT.Resource)
    g.add((URIRef("https://linked.data.gov.au/dataset/idndc"), DCTERMS.hasPart, r))
    open(f, "w").write(g.serialize(format="longturtle"))
