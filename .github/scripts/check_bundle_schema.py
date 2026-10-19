"""Check databricks.yml and resources/*.yml against the Databricks CLI bundle schema.

Usage: databricks bundle schema > schema.json && python check_bundle_schema.py schema.json

This needs no workspace login, so it runs on every pull request, forks included.
`databricks bundle validate` still runs in the deploy workflows, where credentials exist.
"""

import json
import sys
from pathlib import Path

import jsonschema
import yaml


def leaves(error):
    """Every specific error inside a oneOf, without the ${var} string branch."""
    if not error.context:
        # each field also accepts a "${...}" reference string; that branch is noise
        if error.validator in ("type", "pattern") and "string" in str(
            error.validator_value
        ) + str(error.schema.get("type")):
            return []
        return [error]
    return [leaf for child in error.context for leaf in leaves(child)]


def main(schema_path):
    schema = json.loads(Path(schema_path).read_text(encoding="utf-8"))
    validator = jsonschema.validators.validator_for(schema)(schema)
    files = [Path("databricks.yml"), *sorted(Path("resources").glob("*.yml"))]
    failed = False
    for path in files:
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
        messages = set()
        for error in validator.iter_errors(document):
            for leaf in leaves(error) or [error]:
                location = ".".join(str(part) for part in leaf.absolute_path)
                messages.add(f"{location}: {leaf.message}")
        for message in sorted(messages):
            print(f"::error file={path}::{message}")
            failed = True
        print(f"checked {path}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
