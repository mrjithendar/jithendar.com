from product import Product

product = Product.model_validate({"id": "p1", "name": "Mug", "priceCents": 1299, "inStock": True})

# The same typo as the TypeScript example.
print(product.price_cent)
