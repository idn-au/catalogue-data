import os
from pathlib import Path
import argparse
import httpx
from rdflib import Graph, URIRef
from rdflib.namespace import RDF, SKOS, DCAT

TRIPLESTORE_URL = os.environ.get("TRIPLESTORE_URL", "")
TRIPLESTORE_USERNAME = os.environ.get("TRIPLESTORE_USERNAME", "")
TRIPLESTORE_PASSWORD = os.environ.get("TRIPLESTORE_PASSWORD", "")
TIMEOUT = 30.0

BACKGROUND_GRAPH_IRI = "https://background-data"

# if background files changed, clear & reupload to background named graph
def upload_background():
    """Uploads all background files from `data/_background/`."""
    print("Uploading background data...")

    # drop named graph
    sparql_update_query(f"DROP GRAPH <{BACKGROUND_GRAPH_IRI}>")

    # upload everything in data/_background/
    background_directory = Path(__file__).parent.parent / "data" / "_background"
    for f in background_directory.glob("*.ttl"):
        upload_named_graph(f, BACKGROUND_GRAPH_IRI, False)
    
    print("Upload complete")

# if catalog files changed, clear & reupload each catalog to its own named graph
def upload_catalogs():
    """Uploads all resource files from `data/catalogues/` and all catalogues from `data/system/`, both into their own named graphs."""
    print("Uploading catalogues...")
    
    # upload resources in data/catalogues/democat/
    demo_directory = Path(__file__).parent.parent / "data" / "catalogues" / "democat"
    for f in demo_directory.glob("*.ttl"):
        iri = find_named_graph(f, DCAT.Resource)
        upload_named_graph(f, iri)

    # upload resources in data/catalogues/isucat/
    isu_directory = Path(__file__).parent.parent / "data" / "catalogues" / "isucat"
    for f in isu_directory.glob("*.ttl"):
        iri = find_named_graph(f, DCAT.Resource)
        upload_named_graph(f, iri)

    # upload catalog in data/system/catalog-democat.ttl
    democat_path = Path(__file__).parent.parent / "data" / "system" / "catalog-democat.ttl"
    democat_iri = find_named_graph(democat_path, DCAT.Catalog)
    upload_named_graph(democat_path, democat_iri)
    # upload catalog in data/system/catalog-isu.ttl
    isucat_path = Path(__file__).parent.parent / "data" / "system" / "catalog-isu.ttl"
    isucat_iri = find_named_graph(isucat_path, DCAT.Catalog)
    upload_named_graph(isucat_path, isucat_iri)
    # upload catalog in data/system/catalog-system.ttl
    systemcat_path = Path(__file__).parent.parent / "data" / "system" / "catalog-system.ttl"
    systemcat_iri = find_named_graph(systemcat_path, DCAT.Catalog)
    upload_named_graph(systemcat_path, systemcat_iri)

    # remove entailment graphs
    sparql_update_query("""
        delete {
            graph ?g {
                ?s ?p ?o .   
            }
        } where {
            graph ?g {
                ?s ?p ?o .
            }
            filter(strEnds(str(?g), "-entailments"))
        }
    """)

    # reinsert entailments for dcterms:publisher & dcterms:creator
    sparql_update_query("""
        PREFIX iso: <http://def.isotc211.org/iso19115/-1/2018/CitationAndResponsiblePartyInformation/code/CI_RoleCode/>
        PREFIX prov: <http://www.w3.org/ns/prov#>
        PREFIX dcterms: <http://purl.org/dc/terms/>
        PREFIX dcat: <http://www.w3.org/ns/dcat#>
        insert {
            graph ?ent_grf {
                ?s dcterms:publisher ?agent . 
            }
        } where {
            graph ?g {
                ?s a dcat:Resource ;
                    prov:qualifiedAttribution [
                        dcat:hadRole iso:custodian ;
                        prov:agent ?agent 
                    ] .
            }
            BIND (IRI(CONCAT(STR(?g),"-entailments")) AS ?ent_grf)
        }
    """)
    sparql_update_query("""
        PREFIX iso: <http://def.isotc211.org/iso19115/-1/2018/CitationAndResponsiblePartyInformation/code/CI_RoleCode/>
        PREFIX prov: <http://www.w3.org/ns/prov#>
        PREFIX dcterms: <http://purl.org/dc/terms/>
        PREFIX dcat: <http://www.w3.org/ns/dcat#>
        insert {
            graph ?ent_grf {
                ?s dcterms:creator ?agent . 
            }
        } where {
            graph ?g {
                ?s a dcat:Resource ;
                    prov:qualifiedAttribution [
                        dcat:hadRole iso:rightsHolder ;
                        prov:agent ?agent 
                    ] .
            }
            BIND (IRI(CONCAT(STR(?g),"-entailments")) AS ?ent_grf)
        }
    """)

    print("Upload complete")

def upload_vocabs():
    """Uploads all vocabulary files from `data/vocabularies/` into their own named graphs."""
    print("Uploading vocabularies...")

    # upload vocabs in data/vocabularies/
    vocab_directory = Path(__file__).parent.parent / "data" / "vocabularies"
    for f in vocab_directory.glob("*.ttl"):
        iri = find_named_graph(f, SKOS.ConceptScheme)
        upload_named_graph(f, iri)
    
    print("Upload complete")

# returns named graph IRI from class
def find_named_graph(file: Path, object_class: URIRef) -> str:
    """Finds the IRI of the object from a file based on a specified class."""
    g = Graph().parse(file, format="ttl")
    for s in g.subjects(RDF.type, object_class):
        return s

# drop & upload named graph & add to default
def upload_named_graph(file: Path, iri: str, drop_graph: bool=True):
    """Uploads a named graph from an IRI to the triplestore."""
    # drop named graph
    if drop_graph:
        sparql_update_query(f"DROP GRAPH <{iri}>")

    # upload turtle to named graph
    sparql_upload_file(file, iri)

# POST request to triplestore with credentials
# need one function for turtle data, one for SPARQL update queries
def sparql_update_query(query: str):
    """Does a SPARQL update request to the triplestore."""
    r = httpx.post(
        url=f"{TRIPLESTORE_URL}/update",
        auth=(TRIPLESTORE_USERNAME, TRIPLESTORE_PASSWORD),
        timeout=TIMEOUT,
        data=query,
        headers={
            "Content-Type": "application/sparql-update"
        },
    )

def sparql_upload_file(file: Path, named_graph: str):
    """Uploads a turtle file in a named graph to the triplestore."""
    with open(file, "rb") as f:
        content = f.read()

    r = httpx.post(
        url=f"{TRIPLESTORE_URL}/data",
        auth=(TRIPLESTORE_USERNAME, TRIPLESTORE_PASSWORD),
        timeout=TIMEOUT,
        params={"graph": named_graph},
        content=content,
        headers={
            "Content-Type": "text/turtle"
        },
    )

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--background",
        help="Update the background data",
        action=argparse.BooleanOptionalAction
    )
    parser.add_argument(
        "--catalogs",
        help="Update the catalog data",
        action=argparse.BooleanOptionalAction
    )
    parser.add_argument(
        "--vocabs",
        help="Update the vocab data",
        action=argparse.BooleanOptionalAction
    )

    args = parser.parse_args()

    if args.background:
        upload_background()
    if args.catalogs:
        upload_catalogs()
    if args.vocabs:
        upload_vocabs()

if __name__ == "__main__":
    main()