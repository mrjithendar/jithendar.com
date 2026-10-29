import { PGlite } from "@electric-sql/pglite";
import { drizzle } from "drizzle-orm/pglite";
import { setDbForTests, schema, type Db } from "@/db";
import { migrateDb } from "@/db/migrate";

/**
 * One migrated database per test file (worker), cloned for every test: replaying all migrations into a new
 * PGlite for each test took ~5× longer and timed out in CI, where tests share the CPU with the production build.
 */
let template: Promise<PGlite> | undefined;

function migratedTemplate(): Promise<PGlite> {
  template ??= (async () => {
    const pg = new PGlite();
    await migrateDb(drizzle(pg, { schema }) as unknown as Db);
    return pg;
  })().catch((err) => {
    template = undefined;
    throw err;
  });
  return template;
}

/** Fresh in-memory Postgres (PGlite) with all migrations applied, installed as the app database. */
export async function freshDb(): Promise<Db> {
  const pg = (await (await migratedTemplate()).clone()) as PGlite;
  const db = drizzle(pg, { schema }) as unknown as Db;
  // Still runs the migrator: a no-op on the clone, it keeps the start-up path (advisory lock, ledger) exercised.
  await migrateDb(db);
  setDbForTests(db);
  return db;
}
