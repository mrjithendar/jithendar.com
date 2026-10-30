import { describe, expect, it, vi } from "vitest";

vi.mock("@/lib/redis", () => ({ getRedis: async () => null, getRedisSubscriber: async () => null }));

describe("cache bus", () => {
  it("shares handlers between separate copies of the module (instrumentation vs app bundles)", async () => {
    // The app registers its caches in one module instance…
    const app = await import("@/lib/cache-bus");
    const cleared = vi.fn();
    app.onInvalidate("integrations", cleared);

    // …while instrumentation.ts (the Redis listener) loads its own copy.
    vi.resetModules();
    const listener = await import("@/lib/cache-bus");
    expect(listener).not.toBe(app);

    listener.broadcastInvalidate("integrations");
    expect(cleared).toHaveBeenCalledTimes(1);
  });
});
