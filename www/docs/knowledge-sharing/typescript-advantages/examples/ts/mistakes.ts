import { parseProduct } from "./product.ts";

const res = parseProduct({ id: "p1", name: "Mug", priceCents: 1299, inStock: true });

// Mistake 1: reading `product` without checking `ok`.
console.log(res.product.name);

if (res.ok) {
  // Mistake 2: a typo in a field name.
  console.log(res.product.priceCent);
}
