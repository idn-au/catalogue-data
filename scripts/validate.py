from typing import List
from pathlib import Path
import argparse
import httpx
from pyshacl import validate

def validate_files(data_files: List[str], validator: str):
    """Runs pySHACL validation on a list of files against a provided SHACL validator."""
    invalid_files = {}

    for f in data_files:
        v = validate(
            f,
            shacl_graph=validator,
            allow_infos=True,
            allow_warnings=True
        )
        file = f.split("/")[-1]
        print(f"{file} - {'Valid' if v[0] else 'Invalid'}")
        if not v[0]:
            invalid_files[file] = v[2]
    
    if len(invalid_files) > 0:
        print("Invalid data:\n\n{}".format("\n\n".join([f"{filename}\n{message}" for filename, message in invalid_files.items()])))
        raise ValueError("\n\n{} invalid files: {}\n See above for details.".format(len(invalid_files.keys()), ", ".join([filename for filename in invalid_files.keys()])))

def validate_catalogs():
    """Validates all resources in `data/catalogues/` and all catalogues in `data/system/`."""
    print("Validating catalogues...")
    
    demo_directory = Path(__file__).parent.parent / "data" / "catalogues" / "democat"
    isu_directory = Path(__file__).parent.parent / "data" / "catalogues" / "isucat"
    system_base_directory = Path(__file__).parent.parent / "data" / "system"
    system_directory = [
        system_base_directory / "catalog-democat.ttl",
        system_base_directory / "catalog-isu.ttl",
        system_base_directory / "catalog-system.ttl"
    ]
    catalog_files = [
        *[str(f) for f in demo_directory.glob("*.ttl")],
        *[str(f) for f in isu_directory.glob("*.ttl")],
        *[str(f) for f in system_directory],
    ]

    validator_content = httpx.get("https://raw.githubusercontent.com/idn-au/idn-catalogue-profile/main/rd/validator.ttl").text
    
    validate_files(catalog_files, validator_content)

    print("Validation complete")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--catalogs",
        help="Validate the catalog data",
        action=argparse.BooleanOptionalAction
    )

    args = parser.parse_args()

    if args.catalogs:
        validate_catalogs()

        
if __name__ == "__main__":
    main()