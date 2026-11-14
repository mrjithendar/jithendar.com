// shared/product.ts: imported by both the React page and the API route.
import { z } from "zod";

// One schema is the runtime check; the type is inferred from it.
export const Product = z.object({
  id: z.string().min(1),
  name: z.string().min(1),
  priceCents: z.number().int().nonnegative(),
  inStock: z.boolean(),
});
export type Product = z.infer<typeof Product>;

// A discriminated union: callers must check `ok` before reading `product`.
export type ProductResponse =
  | { ok: true; product: Product }
  | { ok: false; field: string };

export function parseProduct(raw: unknown): ProductResponse {
  const result = Product.safeParse(raw); // runtime validation
  if (!result.success) {
    return { ok: false, field: result.error.issues[0]?.path.join(".") ?? "body" };
  }
  return { ok: true, product: result.data };
}
