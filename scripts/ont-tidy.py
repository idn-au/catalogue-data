from rdflib import Graph, Literal, URIRef, BNode, Namespace
from rdflib.namespace import DCAT, DCTERMS, PROV, RDF, RDFS, SDO, SKOS, XSD
from pathlib import Path

g = Graph().parse(Path(__file__).parent.parent / "data" / "ontologies" / "sdo.ttl")
g2 = Graph()
g.bind("dcat", DCAT)
g.bind("dcterms", DCTERMS)
for s, o in g.subject_objects(RDF.type):
    print(s)
    # g2.add((s, RDF.type, o))
    for p2, o2 in g.predicate_objects(s):
        if p2 == RDFS.label:
            if o2.language == "en" or o2.language == "" or o2.language is None:
                g2.add((s, RDFS.label, o2))
        elif p2 == RDFS.comment or p2 == PROV.definition:
            if o2.language == "en" or o2.language == "" or o2.language is None:
                g2.add((s, RDFS.comment, o2))


g2.serialize(destination=Path(__file__).parent.parent / "data" / "ontologies" / "sdo-labels.ttl", format="longturtle")