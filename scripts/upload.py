import os
from pathlib import Path
import argparse

import httpx
from rdflib import Graph, URIRef
from rdflib.namespace import RDF, DCAT

TRIPLESTORE_URL = os.environ.get("TRIPLESTORE_URL", "")
TRIPLESTORE_USERNAME = os.environ.get("TRIPLESTORE_USERNAME", "")
TRIPLESTORE_PASSWORD = os.environ.get("TRIPLESTORE_PASSWORD", "")

TIMEOUT = 30.0
RETRIES = 3
BACKGROUND_GRAPH_IRI = "https://background-data"
SCORES_GRAPH_IRI = "https://scores"

data_dir = Path(__file__).parent.parent / "data"

client = httpx.Client(
    auth=httpx.BasicAuth(username=TRIPLESTORE_USERNAME, password=TRIPLESTORE_PASSWORD),
    transport=httpx.HTTPTransport(retries=RETRIES),
    timeout=TIMEOUT,
)


# if background files changed, clear & reupload to background named graph
def upload_background():
    """Uploads all background files from `data/_background/` into the background data graph."""
    print("Uploading background data...")

    # drop named graph
    sparql_update_query(f"DROP GRAPH <{BACKGROUND_GRAPH_IRI}>")

    # upload everything in data/_background/
    background_directory = data_dir / "_background"
    for f in background_directory.glob("*.ttl"):
        upload_named_graph(f, BACKGROUND_GRAPH_IRI, False)

    # prez profile
    upload_named_graph(
        data_dir / "system" / "idn-prez-profile.ttl", BACKGROUND_GRAPH_IRI, False
    )

    print("Upload complete")


# if catalog files changed, clear & reupload each catalog & resource to its own named graph
def upload_catalogs():
    """Uploads all resource files from `data/catalogues/` and all catalogues from `data/system/`, both into their own named graphs."""
    print("Uploading catalogues...")

    resource_iris = get_iris()

    sparql_update_query(f"DROP GRAPH <{SCORES_GRAPH_IRI}>")

    # upload resources in data/catalogues/democat/
    demo_directory = data_dir / "catalogues" / "democat"
    for f in demo_directory.glob("*.ttl"):
        iri = find_named_graph(f, DCAT.Resource)
        status = resource_iris[iri]
        if status != "remove":
            upload_named_graph(f, iri, status == "update")
            # upload scores
            upload_named_graph(
                f"{demo_directory / 'scores'}/{f.stem}-fair.ttl",
                SCORES_GRAPH_IRI,
                False,
            )
            upload_named_graph(
                f"{demo_directory / 'scores'}/{f.stem}-care.ttl",
                SCORES_GRAPH_IRI,
                False,
            )

    # upload resources in data/catalogues/isucat/
    demo_directory = data_dir / "catalogues" / "isucat"
    for f in demo_directory.glob("*.ttl"):
        iri = find_named_graph(f, DCAT.Resource)
        status = resource_iris[iri]
        if status != "remove":
            upload_named_graph(f, iri, status == "update")
            # upload scores
            upload_named_graph(
                f"{demo_directory / 'scores'}/{f.stem}-fair.ttl",
                SCORES_GRAPH_IRI,
                False,
            )
            upload_named_graph(
                f"{demo_directory / 'scores'}/{f.stem}-care.ttl",
                SCORES_GRAPH_IRI,
                False,
            )

    # remove old resources
    for iri in [iri for iri, status in resource_iris.items() if status == "delete"]:
        sparql_update_query(f"DROP GRAPH <{iri}>")

    # upload catalog in data/system/catalog-democat.ttl
    democat_path = data_dir / "system" / "catalog-democat.ttl"
    democat_iri = find_named_graph(democat_path, DCAT.Catalog)
    upload_named_graph(democat_path, democat_iri)
    # upload catalog in data/system/catalog-isu.ttl
    isucat_path = data_dir / "system" / "catalog-isu.ttl"
    isucat_iri = find_named_graph(isucat_path, DCAT.Catalog)
    upload_named_graph(isucat_path, isucat_iri)
    # upload catalog in data/system/catalog-system.ttl
    systemcat_path = data_dir / "system" / "catalog-system.ttl"
    systemcat_iri = find_named_graph(systemcat_path, DCAT.Catalog)
    upload_named_graph(systemcat_path, systemcat_iri)

    upload_entailments()

    print("Upload complete")


def get_iris() -> dict[str, str]:
    """Gets a dict of IRIs with flags for if the resources is to be added, updated or deleted"""
    # get existing IRIs from triplestore
    remote_iris = get_existing_item(DCAT.Resource)

    # get IRIs in repo across all folders
    local_iris = set()

    demo_directory = data_dir / "catalogues" / "democat"
    for f in demo_directory.glob("*.ttl"):
        iri = find_named_graph(f, DCAT.Resource)
        local_iris.add(iri)

    isu_directory = data_dir / "catalogues" / "isucat"
    for f in isu_directory.glob("*.ttl"):
        iri = find_named_graph(f, DCAT.Resource)
        local_iris.add(iri)

    iris = (
        {iri: "add" for iri in local_iris - remote_iris}
        | {iri: "update" for iri in remote_iris & local_iris}
        | {iri: "delete" for iri in remote_iris - local_iris}
    )

    symbols = {
        "add": "+",
        "update": "~",
        "delete": "-",
    }

    print("Resource changes (+ add, ~ update, - delete):")
    for iri, status in iris.items():
        print(f"{symbols[status]} {iri}")

    return iris


def get_existing_item(object_class: URIRef) -> set[str]:
    """Does a SPARQL query to get the list of current items of a class in its own named graph in the triplestore"""
    query = f"""
        SELECT ?s
        WHERE {{
            GRAPH ?s {{
                ?s a <{str(object_class)}> .
            }}
        }}
    """

    results = sparql_query(query)
    return {result["s"]["value"] for result in results}


def upload_entailments():
    """Uploads creator & publisher entailments based on data roles into seperate graphs"""
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


# returns named graph IRI from class
def find_named_graph(file: Path, object_class: URIRef) -> str:
    """Finds the IRI of the object from a file based on a specified class."""
    g = Graph().parse(file, format="ttl")
    for s in g.subjects(RDF.type, object_class):
        return str(s)


# drop & upload named graph & add to default
def upload_named_graph(file: Path, iri: str, drop_graph: bool = True):
    """Uploads a named graph from an IRI to the triplestore."""
    # drop named graph
    if drop_graph:
        sparql_update_query(f"DROP GRAPH <{iri}>")

    # upload turtle to named graph
    sparql_upload_file(file, iri)


def sparql_query(query: str) -> list[dict]:
    """Does a SPARQL query to the triplestore."""
    r = client.post(
        url=f"{TRIPLESTORE_URL}/query",
        data=query,
        headers={"Content-Type": "application/sparql-query"},
    )

    return r.json()["results"]["bindings"]


def sparql_update_query(query: str):
    """Does a SPARQL update request to the triplestore."""
    r = client.post(
        url=f"{TRIPLESTORE_URL}/update",
        data=query,
        headers={"Content-Type": "application/sparql-update"},
    )


def sparql_upload_file(file: Path, named_graph: str):
    """Uploads a turtle file in a named graph to the triplestore."""
    with open(file, "rb") as f:
        content = f.read()

    r = client.post(
        url=f"{TRIPLESTORE_URL}/data",
        params={"graph": named_graph},
        content=content,
        headers={"Content-Type": "text/turtle"},
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--background",
        help="Update the background data",
        action=argparse.BooleanOptionalAction,
    )
    parser.add_argument(
        "--catalogs",
        help="Update the catalog data",
        action=argparse.BooleanOptionalAction,
    )

    args = parser.parse_args()

    if args.background:
        upload_background()
    if args.catalogs:
        upload_catalogs()


if __name__ == "__main__":
    main()
