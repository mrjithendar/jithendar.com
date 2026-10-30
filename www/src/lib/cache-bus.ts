import { getRedis, getRedisSubscriber } from "./redis";

/** Per-process caches register here; invalidation clears locally and tells the other replicas via Redis. */
type Kind = "content" | "categories" | "settings" | "integrations";
const CHANNEL = "jithendar:invalidate";
// On globalThis: instrumentation.ts (which runs the Redis listener) and the app routes are separate bundles,
// each with its own copy of this module. Per-module state would leave the listener clearing an empty map.
const g = globalThis as unknown as { __cacheBus?: { handlers: Map<Kind, Set<() => void>>; origin: string } };
g.__cacheBus ??= { handlers: new Map(), origin: crypto.randomUUID() };
const { handlers, origin } = g.__cacheBus;

export function onInvalidate(kind: Kind, clear: () => void) {
  const set = handlers.get(kind) ?? new Set();
  set.add(clear);
  handlers.set(kind, set);
}

function clearLocal(kind: Kind) {
  for (const clear of handlers.get(kind) ?? []) clear();
}

export function broadcastInvalidate(kind: Kind) {
  clearLocal(kind);
  void getRedis()
    .then((r) => r?.publish(CHANNEL, JSON.stringify({ kind, origin })))
    .catch(() => {});
}

/** Called once at server start (instrumentation.ts). */
export async function listenForInvalidations() {
  const sub = await getRedisSubscriber();
  if (!sub) return;
  await sub.subscribe(CHANNEL);
  sub.on("message", (_channel, message) => {
    try {
      const { kind, origin: from } = JSON.parse(message) as { kind: Kind; origin: string };
      if (from !== origin) clearLocal(kind);
    } catch {
      // ignore malformed messages
    }
  });
}
