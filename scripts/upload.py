import os
import httpx
import asyncio

TIMEOUT = 30.0

client = httpx.AsyncClient(
    url=os.environ.get("TRIPLESTORE_URL"),
    auth=(os.environ.get("TRIPLESTORE_USERNAME"), os.environ.get("TRIPLESTORE_PASSWORD")),
    timeout=TIMEOUT
)

# if background files changed, clear & reupload to background named graph & default
async def upload_background():
    """Uploads all background files from `data/_background/`."""
    # upload everything in data/_background/

    pass

# if catalog files changed, clear & reupload each catalog to its own named graph & default
async def upload_catalogs():
    """Uploads all resource files from `data/catalogues/` and all catalogues from `data/system/`, both into their own named graphs."""
    
    # upload resources in data/catalogues/democat/
    # upload resources in data/catalogues/isucat/
    # asyncio.gather(...)

    # upload catalog in data/system/catalog-democat.ttl
    # upload catalog in data/system/catalog-isu.ttl
    # upload catalog in data/system/catalog-system.ttl
    # asyncio.gather(...)

    pass

# if vocab files changed, clear & reupload each vocab to its own named graph & default
async def upload_vocabs():
    """Uploads all vocabulary files from `data/vocabularies/` into their own named graphs."""
    # upload vocabs in data/vocabularies/
    # asyncio.gather(...)

    pass

# returns named graph IRI from class
def find_named_graph(object_class: str) -> str:
    """Finds the IRI of the object from a file based on a specified class."""
    # use string parsing or RDFlib to get IRI from class
    pass

# drop & upload named graph & add to default
async def upload_named_graph(iri: str):
    """Uploads a named graph from an IRI to the triplestore."""
    # drop named graph
    # f"DROP SILENT GRAPH <{iri}>"

    # add named graph
    # upload turtle

    # drop from default?


    # add to default
    # f"ADD <{iri}> to DEFAULT"

    pass

# POST request to triplestore with credentials
# need one function for turtle data, one for SPARQL update queries
async def sparql_update(data: str):
    """Does an async SPARQL update request to the triplestore."""
    r = await client.post(
        data=data,
        headers={
            "Content-Type": "application/sparql-update"
        },
    )

    pass

# need CLI args to run specific functions
