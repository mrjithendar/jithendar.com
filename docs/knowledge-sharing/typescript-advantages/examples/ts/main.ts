import { readFileSync } from "node:fs";
import { parseProduct } from "./product.ts";

const cases: unknown[] = JSON.parse(readFileSync(process.argv[2]!, "utf8"));
for (const raw of cases) console.log(JSON.stringify(parseProduct(raw)));
