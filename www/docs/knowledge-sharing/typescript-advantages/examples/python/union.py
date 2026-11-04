from product import parse_product

res = parse_product({"id": "p2"})

# Reading "product" without checking res["ok"] first.
print(res["product"])
