import json
import sys

from product import parse_product

with open(sys.argv[1], encoding="utf-8") as fh:
    for raw in json.load(fh):
        print(json.dumps(parse_product(raw), separators=(",", ":")))
