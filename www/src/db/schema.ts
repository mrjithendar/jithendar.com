import { sql } from "drizzle-orm";
import {
  bigint,
  boolean,
  foreignKey,
  index,
  integer,
  jsonb,
  pgTable,
  primaryKey,
  text,
  timestamp,
  uniqueIndex,
  uuid,
} from "drizzle-orm/pg-core";


const ts = (name: string) => timestamp(name, { withTimezone: true, mode: "date" });

// --- Better Auth (email + password, admin plugin, database rate limiting) -------------

export type SocialLinks = {
  github?: string;
  linkedin?: string;
  x?: string;
  youtube?: string;
  instagram?: string;
  facebook?: string;
  bluesky?: string;
  mastodon?: string;
};

export const user = pgTable("user", {
  id: text("id").primaryKey(),
  name: text("name").notNull(),
  email: text("email").notNull().unique(),
  emailVerified: boolean("email_verified").notNull().default(false),
  image: text("image"),
  createdAt: ts("created_at").notNull().defaultNow(),
  updatedAt: ts("updated_at").notNull().defaultNow(),
  // Private account profile (shown on /account; the public byline lives in author_profile).
  bio: text("bio").notNull().default(""),
  website: text("website"),
  socialLinks: jsonb("social_links").$type<SocialLinks>().notNull().default({}),
  // admin plugin
  role: text("role").notNull().default("user"),
  banned: boolean("banned").default(false),
  banReason: text("ban_reason"),
  banExpires: ts("ban_expires"),
  /** Unused since comments dropped Turnstile (kept to avoid a destructive migration). */
  humanVerifiedAt: ts("human_verified_at"),
});

export const session = pgTable(
  "session",
  {
    id: text("id").primaryKey(),
    expiresAt: ts("expires_at").notNull(),
    token: text("token").notNull().unique(),
    createdAt: ts("created_at").notNull().defaultNow(),
    updatedAt: ts("updated_at").notNull().defaultNow(),
    ipAddress: text("ip_address"),
    userAgent: text("user_agent"),
    userId: text("user_id")
      .notNull()
      .references(() => user.id, { onDelete: "cascade" }),
    impersonatedBy: text("impersonated_by"),
  },
  (t) => [index("session_user_idx").on(t.userId)],
);

export const account = pgTable(
  "account",
  {
    id: text("id").primaryKey(),
    accountId: text("account_id").notNull(),
    providerId: text("provider_id").notNull(),
    userId: text("user_id")
      .notNull()
      .references(() => user.id, { onDelete: "cascade" }),
    accessToken: text("access_token"),
    refreshToken: text("refresh_token"),
    idToken: text("id_token"),
    accessTokenExpiresAt: ts("access_token_expires_at"),
    refreshTokenExpiresAt: ts("refresh_token_expires_at"),
    scope: text("scope"),
    password: text("password"),
    createdAt: ts("created_at").notNull().defaultNow(),
    updatedAt: ts("updated_at").notNull().defaultNow(),
  },
  (t) => [index("account_user_idx").on(t.userId)],
);

export const verification = pgTable("verification", {
  id: text("id").primaryKey(),
  identifier: text("identifier").notNull(),
  value: text("value").notNull(),
  expiresAt: ts("expires_at").notNull(),
  createdAt: ts("created_at").notNull().defaultNow(),
  updatedAt: ts("updated_at").notNull().defaultNow(),
});

export const rateLimit = pgTable("rate_limit", {
  id: text("id").primaryKey(),
  key: text("key").notNull().unique(),
  count: integer("count").notNull(),
  lastRequest: bigint("last_request", { mode: "number" }).notNull(),
});

// --- Publication --------------------------------------------------------------------

/** Public author profile for a user with role author or admin. */
export const authorProfile = pgTable("author_profile", {
  userId: text("user_id")
    .primaryKey()
    .references(() => user.id, { onDelete: "cascade" }),
  slug: text("slug").notNull().unique(),
  displayName: text("display_name").notNull(),
  jobTitle: text("job_title"),
  bio: text("bio").notNull().default(""),
  sameAs: jsonb("same_as").$type<string[]>().notNull().default([]),
  updatedAt: ts("updated_at").notNull().defaultNow(),
});

export type Source = { title: string; url: string; publisher: string };
export type Correction = { date: string; note: string };
/** Cover image. `focalX`/`focalY` (0–100, default 50) keep the subject in view when cards crop it. */
export type FeaturedImage = { src: string; alt: string; width: number; height: number; focalX?: number; focalY?: number };

export const post = pgTable(
  "post",
  {
    id: uuid("id").primaryKey().defaultRandom(),
    collection: text("collection").notNull(),
    slug: text("slug").notNull(),
    title: text("title").notNull(),
    description: text("description").notNull(),
    body: text("body").notNull().default(""),
    category: text("category").notNull(),
    tags: text("tags").array().notNull().default(sql`'{}'::text[]`),
    contentType: text("content_type").notNull(),
    status: text("status").notNull().default("draft"),
    publishedAt: ts("published_at"),
    /** Substantive-update time shown to readers (not every save). */
    updatedAt: ts("updated_at"),
    canonicalUrl: text("canonical_url"),
    featuredImage: jsonb("featured_image").$type<FeaturedImage | null>(),
    sources: jsonb("sources").$type<Source[]>().notNull().default([]),
    corrections: jsonb("corrections").$type<Correction[]>().notNull().default([]),
    sponsored: boolean("sponsored").notNull().default(false),
    sponsor: text("sponsor"),
    related: text("related").array().notNull().default(sql`'{}'::text[]`),
    /** Overrides for search results and social cards; empty → title/description/cover are used. */
    seoTitle: text("seo_title"),
    seoDescription: text("seo_description"),
    socialTitle: text("social_title"),
    socialDescription: text("social_description"),
    socialImage: jsonb("social_image").$type<FeaturedImage | null>(),
    /** Published but kept out of search results (noindex, not in sitemaps). */
    noindex: boolean("noindex").notNull().default(false),
    /** Discussion under the post: open, locked (shown, no new comments or edits) or closed (not shown). */
    discussion: text("discussion").notNull().default("open"),
    /** Optimistic concurrency: incremented by every committed save. */
    version: integer("version").notNull().default(1),
    /** In the trash (hidden everywhere; restorable) since this time. */
    deletedAt: ts("deleted_at"),
    authorId: text("author_id")
      .notNull()
      .references(() => user.id, { onDelete: "restrict" }),
    createdAt: ts("created_at").notNull().defaultNow(),
    savedAt: ts("saved_at").notNull().defaultNow(),
  },
  (t) => [
    uniqueIndex("post_collection_slug_idx").on(t.collection, t.slug),
    index("post_status_published_idx").on(t.status, t.publishedAt),
  ],
);

export const page = pgTable("page", {
  slug: text("slug").primaryKey(),
  title: text("title").notNull(),
  description: text("description").notNull(),
  body: text("body").notNull().default(""),
  updatedAt: ts("updated_at"),
  savedAt: ts("saved_at").notNull().defaultNow(),
  seoTitle: text("seo_title"),
  seoDescription: text("seo_description"),
  featuredImage: jsonb("featured_image").$type<FeaturedImage | null>(),
  noindex: boolean("noindex").notNull().default(false),
  /** Order in the "Publication info" navigation (lower first). */
  sortOrder: integer("sort_order").notNull().default(100),
  version: integer("version").notNull().default(1),
  deletedAt: ts("deleted_at"),
});

/** Committed versions of posts and pages (a snapshot per save, publish, schedule or restore). */
export const revision = pgTable(
  "revision",
  {
    id: uuid("id").primaryKey().defaultRandom(),
    entity: text("entity").notNull(),
    entityId: text("entity_id").notNull(),
    version: integer("version").notNull(),
    reason: text("reason").notNull(),
    payload: jsonb("payload").$type<Record<string, unknown>>().notNull(),
    authorId: text("author_id").references(() => user.id, { onDelete: "set null" }),
    createdAt: ts("created_at").notNull().defaultNow(),
  },
  (t) => [index("revision_entity_idx").on(t.entity, t.entityId, t.createdAt)],
);

/** One working copy per user and document; never visible to readers until committed. */
export const autosave = pgTable(
  "autosave",
  {
    entity: text("entity").notNull(),
    entityId: text("entity_id").notNull(),
    userId: text("user_id")
      .notNull()
      .references(() => user.id, { onDelete: "cascade" }),
    baseVersion: integer("base_version").notNull(),
    payload: jsonb("payload").$type<Record<string, unknown>>().notNull(),
    savedAt: ts("saved_at").notNull().defaultNow(),
  },
  (t) => [primaryKey({ name: "autosave_pk", columns: [t.entity, t.entityId, t.userId] })],
);

/** Background jobs with retries (IndexNow submissions). Pending jobs are de-duplicated by dedupeKey. */
export const job = pgTable(
  "job",
  {
    id: uuid("id").primaryKey().defaultRandom(),
    kind: text("kind").notNull(),
    dedupeKey: text("dedupe_key"),
    payload: jsonb("payload").$type<Record<string, unknown>>().notNull(),
    status: text("status").notNull().default("queued"),
    attempts: integer("attempts").notNull().default(0),
    maxAttempts: integer("max_attempts").notNull().default(5),
    runAt: ts("run_at").notNull().defaultNow(),
    lockedUntil: ts("locked_until"),
    lastError: text("last_error"),
    createdAt: ts("created_at").notNull().defaultNow(),
    finishedAt: ts("finished_at"),
  },
  (t) => [index("job_due_idx").on(t.status, t.runAt)],
);

export const setting = pgTable("setting", {
  key: text("key").primaryKey(),
  value: jsonb("value").notNull(),
  updatedAt: ts("updated_at").notNull().defaultNow(),
  updatedBy: text("updated_by"),
});

/**
 * Site configuration (Admin → Appearance). Two rows: "published" (what readers see) and "draft" (shared by
 * admins, private). `version` increments on every write and guards against conflicting edits; the draft's
 * `base_version` is the published version it started from. Published history lives in `revision`
 * (entity "site-config").
 */
export const siteConfig = pgTable("site_config", {
  key: text("key").primaryKey(),
  config: jsonb("config").$type<Record<string, unknown>>().notNull(),
  schemaVersion: integer("schema_version").notNull(),
  version: integer("version").notNull(),
  baseVersion: integer("base_version").notNull().default(0),
  updatedAt: ts("updated_at").notNull().defaultNow(),
  updatedBy: text("updated_by"),
});

export const comment = pgTable(
  "comment",
  {
    id: uuid("id").primaryKey().defaultRandom(),
    postId: uuid("post_id")
      .notNull()
      .references(() => post.id, { onDelete: "cascade" }),
    userId: text("user_id")
      .notNull()
      .references(() => user.id, { onDelete: "cascade" }),
    /** Markdown source; rendered (and sanitised) on every read. Emptied when the author deletes the comment. */
    body: text("body").notNull(),
    /** pending → approved ⇄ hidden | removed. Older rows may also be rejected or spam (treated like removed). */
    status: text("status").notNull().default("pending"),
    createdAt: ts("created_at").notNull().defaultNow(),
    moderatedAt: ts("moderated_at"),
    moderatedBy: text("moderated_by"),
    /** The comment this one replies to (same post: enforced by the composite foreign key below) and its thread root. */
    parentId: uuid("parent_id"),
    rootId: uuid("root_id"),
    /** Real nesting depth (0 = top level); the page indents at most MAX_DISPLAY_DEPTH levels. */
    depth: integer("depth").notNull().default(0),
    editedAt: ts("edited_at"),
    /** Deleted by its author: kept as a neutral placeholder while replies exist. */
    deletedAt: ts("deleted_at"),
    /** Per-submission key from the composer: a resubmitted form returns the first comment instead of a duplicate. */
    clientKey: text("client_key"),
  },
  (t) => [
    index("comment_post_status_idx").on(t.postId, t.status),
    index("comment_status_idx").on(t.status, t.createdAt),
    uniqueIndex("comment_id_post_idx").on(t.id, t.postId),
    index("comment_parent_idx").on(t.parentId),
    uniqueIndex("comment_user_client_key_idx").on(t.userId, t.clientKey).where(sql`${t.clientKey} is not null`),
    foreignKey({ name: "comment_parent_same_post_fk", columns: [t.parentId, t.postId], foreignColumns: [t.id, t.postId] }).onDelete("cascade"),
  ],
);

/** One like per user per comment. */
export const commentLike = pgTable(
  "comment_like",
  {
    commentId: uuid("comment_id")
      .notNull()
      .references(() => comment.id, { onDelete: "cascade" }),
    userId: text("user_id")
      .notNull()
      .references(() => user.id, { onDelete: "cascade" }),
    createdAt: ts("created_at").notNull().defaultNow(),
  },
  (t) => [primaryKey({ name: "comment_like_pk", columns: [t.commentId, t.userId] }), index("comment_like_user_idx").on(t.userId)],
);

/** Reader reports (one per user per comment); resolved by a moderator's decision. */
export const commentReport = pgTable(
  "comment_report",
  {
    id: uuid("id").primaryKey().defaultRandom(),
    commentId: uuid("comment_id")
      .notNull()
      .references(() => comment.id, { onDelete: "cascade" }),
    userId: text("user_id")
      .notNull()
      .references(() => user.id, { onDelete: "cascade" }),
    /** spam | abuse | off-topic | other */
    reason: text("reason").notNull(),
    note: text("note").notNull().default(""),
    createdAt: ts("created_at").notNull().defaultNow(),
    resolvedAt: ts("resolved_at"),
    resolvedBy: text("resolved_by"),
    /** The moderation action that closed the report (approve = dismissed, hide, remove, purge). */
    resolution: text("resolution"),
  },
  (t) => [uniqueIndex("comment_report_user_idx").on(t.commentId, t.userId), index("comment_report_open_idx").on(t.resolvedAt, t.createdAt)],
);

export const contactMessage = pgTable(
  "contact_message",
  {
    id: uuid("id").primaryKey().defaultRandom(),
    name: text("name").notNull(),
    email: text("email").notNull(),
    subject: text("subject").notNull(),
    message: text("message").notNull(),
    /** new → read → archived */
    status: text("status").notNull().default("new"),
    createdAt: ts("created_at").notNull().defaultNow(),
  },
  (t) => [index("contact_status_idx").on(t.status, t.createdAt)],
);

/**
 * Uploaded media. Bytes live in object storage at `storageKey`; this row holds metadata only.
 * New objects go to Cloudflare R2 under jithendar/www/media/{kind}/{yyyy}/{mm}/{id}.{ext};
 * rows created before R2 stay on the legacy S3 bucket until the migration tool copies them.
 * Public URLs are always /media/{id}/{filename}, so moving bytes never changes a reference.
 */
export const media = pgTable(
  "media",
  {
    id: uuid("id").primaryKey().defaultRandom(),
    filename: text("filename").notNull(),
    contentType: text("content_type").notNull(),
    storageKey: text("storage_key").notNull().unique(),
    /** "r2" or "s3-legacy" (rows uploaded before the move to R2). Always set explicitly when inserting. */
    storageBackend: text("storage_backend").notNull().default("s3-legacy"),
    /** The S3 key the object was copied from (set by the R2 migration; used for rollback). */
    legacyKey: text("legacy_key"),
    /** images | videos | audio | documents */
    kind: text("kind").notNull().default("images"),
    /** public (served at /media/…) or private (staff only, short-lived signed links). */
    visibility: text("visibility").notNull().default("public"),
    /** pending (presigned upload not yet verified) or ready. */
    status: text("status").notNull().default("ready"),
    checksumSha256: text("checksum_sha256"),
    /** Folder context, e.g. posts/blog/my-post, pages/about, authors/jane, library. */
    context: text("context").notNull().default("library"),
    sizeBytes: integer("size_bytes").notNull(),
    /** Pixel size for images (null for audio and documents). */
    width: integer("width"),
    height: integer("height"),
    alt: text("alt").notNull().default(""),
    /** Attachment details (as in WordPress): a title for the library, a caption shown under the image, private notes. */
    title: text("title").notNull().default(""),
    caption: text("caption").notNull().default(""),
    description: text("description").notNull().default(""),
    uploadedBy: text("uploaded_by").references(() => user.id, { onDelete: "set null" }),
    createdAt: ts("created_at").notNull().defaultNow(),
  },
  (t) => [index("media_status_created_idx").on(t.status, t.createdAt)],
);

/**
 * AI image generations (Gemini). Prompts are not stored: only their SHA-256 and length.
 * An unaccepted result lives under jithendar/www/tmp/generated/ until accepted, discarded or expired.
 */
export const imageGeneration = pgTable(
  "image_generation",
  {
    id: uuid("id").primaryKey().defaultRandom(),
    userId: text("user_id").references(() => user.id, { onDelete: "set null" }),
    model: text("model").notNull(),
    aspectRatio: text("aspect_ratio").notNull(),
    imageSize: text("image_size").notNull(),
    promptSha256: text("prompt_sha256").notNull(),
    promptChars: integer("prompt_chars").notNull(),
    /** running → succeeded → accepted | discarded | expired; or failed | cancelled */
    status: text("status").notNull(),
    errorCode: text("error_code"),
    tempKey: text("temp_key"),
    contentType: text("content_type"),
    sizeBytes: integer("size_bytes"),
    width: integer("width"),
    height: integer("height"),
    checksumSha256: text("checksum_sha256"),
    latencyMs: integer("latency_ms"),
    mediaId: uuid("media_id").references(() => media.id, { onDelete: "set null" }),
    createdAt: ts("created_at").notNull().defaultNow(),
    completedAt: ts("completed_at"),
  },
  (t) => [index("image_generation_user_created_idx").on(t.userId, t.createdAt), index("image_generation_status_idx").on(t.status, t.createdAt)],
);

export const apiKey = pgTable(
  "api_key",
  {
    id: uuid("id").primaryKey().defaultRandom(),
    name: text("name").notNull(),
    /** First characters of the key, shown in the admin so keys can be told apart. */
    prefix: text("prefix").notNull(),
    /** SHA-256 of the full key; the key itself is shown once and never stored. */
    hash: text("hash").notNull().unique(),
    scopes: text("scopes").array().notNull(),
    userId: text("user_id")
      .notNull()
      .references(() => user.id, { onDelete: "cascade" }),
    createdAt: ts("created_at").notNull().defaultNow(),
    lastUsedAt: ts("last_used_at"),
    expiresAt: ts("expires_at"),
    revokedAt: ts("revoked_at"),
  },
  (t) => [index("api_key_user_idx").on(t.userId)],
);

export const auditLog = pgTable(
  "audit_log",
  {
    id: uuid("id").primaryKey().defaultRandom(),
    actorId: text("actor_id"),
    actor: text("actor").notNull(),
    action: text("action").notNull(),
    target: text("target"),
    detail: jsonb("detail"),
    /** Client IP and user agent of the request that caused the entry (when there was one). */
    ip: text("ip"),
    userAgent: text("user_agent"),
    /** info | notice | warning | critical (see lib/audit.ts). */
    severity: text("severity").notNull().default("info"),
    createdAt: ts("created_at").notNull().defaultNow(),
  },
  (t) => [index("audit_created_idx").on(t.createdAt), index("audit_action_created_idx").on(t.action, t.createdAt), index("audit_ip_created_idx").on(t.ip, t.createdAt)],
);


/** Editable categories. Built-in defaults are seeded at setup; slugs are permanent URL parts. */
export const category = pgTable("category", {
  slug: text("slug").primaryKey(),
  label: text("label").notNull(),
  intro: text("intro").notNull(),
  icon: text("icon").notNull().default("layers"),
  tone: text("tone").notNull().default("slate"),
  sort: integer("sort").notNull().default(100),
  createdAt: ts("created_at").notNull().defaultNow(),
  updatedAt: ts("updated_at").notNull().defaultNow(),
});

/** Permanent redirects recorded when a post or page slug changes (old path → new path). */
export const redirect = pgTable("redirect", {
  fromPath: text("from_path").primaryKey(),
  toPath: text("to_path").notNull(),
  createdAt: ts("created_at").notNull().defaultNow(),
});

/** Short-lived previews of unsaved editor content (post or page), visible only to their creator or an admin. */
export const preview = pgTable(
  "preview",
  {
    token: text("token").primaryKey(),
    kind: text("kind").notNull(),
    payload: jsonb("payload").notNull(),
    userId: text("user_id")
      .notNull()
      .references(() => user.id, { onDelete: "cascade" }),
    createdAt: ts("created_at").notNull().defaultNow(),
    expiresAt: ts("expires_at").notNull(),
  },
  (t) => [index("preview_expires_idx").on(t.expiresAt)],
);

/** History of backup runs (manual or scheduled). */
export const backupRun = pgTable(
  "backup_run",
  {
    id: uuid("id").primaryKey().defaultRandom(),
    trigger: text("trigger").notNull(),
    status: text("status").notNull(),
    filename: text("filename"),
    sizeBytes: integer("size_bytes"),
    results: jsonb("results").$type<{ destination: string; ok: boolean; detail: string }[]>().notNull().default([]),
    startedAt: ts("started_at").notNull().defaultNow(),
    finishedAt: ts("finished_at"),
    triggeredBy: text("triggered_by"),
  },
  (t) => [index("backup_run_started_idx").on(t.startedAt)],
);

// --- Python practice (/python-practice; see docs/PYTHON_PRACTICE.md) --------------------------------------
// Users are the site's Better Auth users (no separate identity). Hidden test cases live in practice_test_case
// and are read only by lib/practice/evaluator.ts and the admin editor (tests/practice-boundaries.test.ts).

export type PracticeDifficultyMix = Partial<Record<"beginner" | "easy" | "medium" | "hard" | "expert", number>>;

/** Engineering roles (seeded from content/python-practice/roles.yaml, then edited in Admin → Python practice). */
export const practiceRole = pgTable("practice_role", {
  slug: text("slug").primaryKey(),
  name: text("name").notNull(),
  description: text("description").notNull(),
  icon: text("icon").notNull().default("code"),
  competencies: jsonb("competencies").$type<string[]>().notNull().default([]),
  learningPath: jsonb("learning_path").$type<string[]>().notNull().default([]),
  topics: text("topics").array().notNull().default(sql`'{}'::text[]`),
  difficultyMix: jsonb("difficulty_mix").$type<PracticeDifficultyMix>().notNull().default({}),
  scenarios: jsonb("scenarios").$type<string[]>().notNull().default([]),
  libraries: jsonb("libraries").$type<string[]>().notNull().default([]),
  sort: integer("sort").notNull().default(100),
  /** active | hidden */
  status: text("status").notNull().default("active"),
  createdAt: ts("created_at").notNull().defaultNow(),
  updatedAt: ts("updated_at").notNull().defaultNow(),
});

export const practiceTopic = pgTable("practice_topic", {
  slug: text("slug").primaryKey(),
  name: text("name").notNull(),
  /** One of the dashboard's skill areas (lib/practice/types.ts SKILL_AREAS). */
  area: text("area").notNull(),
  description: text("description").notNull().default(""),
  sort: integer("sort").notNull().default(100),
});

export const practiceProblem = pgTable(
  "practice_problem",
  {
    id: uuid("id").primaryKey().defaultRandom(),
    slug: text("slug").notNull().unique(),
    title: text("title").notNull(),
    difficulty: text("difficulty").notNull(),
    roles: text("roles").array().notNull().default(sql`'{}'::text[]`),
    topics: text("topics").array().notNull().default(sql`'{}'::text[]`),
    /** draft | published | archived */
    status: text("status").notNull().default("draft"),
    /** The version users get; earlier versions stay for interpreting old submissions. */
    currentVersion: integer("current_version").notNull().default(1),
    estimatedMinutes: integer("estimated_minutes").notNull().default(15),
    /** seed (from the repository catalog; updated by later seeds) or admin (edited here; seeds never touch it). */
    source: text("source").notNull().default("admin"),
    seedHash: text("seed_hash"),
    dailyEligible: boolean("daily_eligible").notNull().default(true),
    createdBy: text("created_by"),
    createdAt: ts("created_at").notNull().defaultNow(),
    updatedAt: ts("updated_at").notNull().defaultNow(),
    publishedAt: ts("published_at"),
  },
  (t) => [index("practice_problem_status_idx").on(t.status, t.difficulty)],
);

export type PracticeSolution = {
  code: string;
  explanation: string;
  time: string;
  space: string;
  alternatives: string[];
  edgeCases: string[];
  production: string[];
  alternativeCode?: string[];
};
export type PracticeLimits = { perTestSeconds: number; totalSeconds: number; memoryMb: number };

/** Immutable content of one problem version (statement, starter, hints, solution, grading settings). */
export const practiceProblemVersion = pgTable(
  "practice_problem_version",
  {
    problemId: uuid("problem_id")
      .notNull()
      .references(() => practiceProblem.id, { onDelete: "cascade" }),
    version: integer("version").notNull(),
    title: text("title").notNull(),
    description: text("description").notNull(),
    entrypoint: text("entrypoint").notNull(),
    starterCode: text("starter_code").notNull(),
    /** Helper code (fakes, harness) run before the submission inside the sandbox. Shown to users. */
    prelude: text("prelude").notNull().default(""),
    /** exact | unordered | float */
    comparator: text("comparator").notNull().default("exact"),
    tolerance: jsonb("tolerance").$type<number>().notNull().default(1e-6),
    constraints: jsonb("constraints").$type<string[]>().notNull().default([]),
    io: jsonb("io").$type<{ input?: string; output?: string }>().notNull().default({}),
    hints: jsonb("hints").$type<string[]>().notNull().default([]),
    solution: jsonb("solution").$type<PracticeSolution>().notNull(),
    limits: jsonb("limits").$type<PracticeLimits>().notNull(),
    contentHash: text("content_hash").notNull(),
    note: text("note").notNull().default(""),
    createdBy: text("created_by"),
    createdAt: ts("created_at").notNull().defaultNow(),
  },
  (t) => [primaryKey({ name: "practice_problem_version_pk", columns: [t.problemId, t.version] })],
);

/** Test cases per problem version. Expected outputs and every hidden case are evaluator-only. */
export const practiceTestCase = pgTable(
  "practice_test_case",
  {
    id: uuid("id").primaryKey().defaultRandom(),
    problemId: uuid("problem_id").notNull(),
    version: integer("version").notNull(),
    ordinal: integer("ordinal").notNull(),
    /** public | hidden */
    visibility: text("visibility").notNull(),
    isExample: boolean("is_example").notNull().default(false),
    label: text("label").notNull().default(""),
    explanation: text("explanation").notNull().default(""),
    args: jsonb("args").$type<unknown[]>().notNull().default([]),
    kwargs: jsonb("kwargs").$type<Record<string, unknown>>().notNull().default({}),
    expected: jsonb("expected"),
  },
  (t) => [
    index("practice_test_case_problem_idx").on(t.problemId, t.version, t.ordinal),
    foreignKey({ name: "practice_test_case_version_fk", columns: [t.problemId, t.version], foreignColumns: [practiceProblemVersion.problemId, practiceProblemVersion.version] }).onDelete("cascade"),
  ],
);

/** Per-user practice settings and verified aggregates (XP and streaks are written by the server only). */
export const practiceProfile = pgTable("practice_profile", {
  userId: text("user_id")
    .primaryKey()
    .references(() => user.id, { onDelete: "cascade" }),
  roles: text("roles").array().notNull().default(sql`'{}'::text[]`),
  leaderboardOptIn: boolean("leaderboard_opt_in").notNull().default(false),
  publicName: text("public_name"),
  xp: integer("xp").notNull().default(0),
  currentStreak: integer("current_streak").notNull().default(0),
  longestStreak: integer("longest_streak").notNull().default(0),
  lastActiveDay: text("last_active_day"),
  preferences: jsonb("preferences").$type<Record<string, unknown>>().notNull().default({}),
  createdAt: ts("created_at").notNull().defaultNow(),
  updatedAt: ts("updated_at").notNull().defaultNow(),
});

export type PracticeSessionConfig = {
  roles: string[];
  difficulties: string[];
  topics: string[];
  count: number;
  durationMinutes: number | null;
  includeFailed: boolean;
  excludeSolved: boolean;
};

export const practiceSession = pgTable(
  "practice_session",
  {
    id: uuid("id").primaryKey().defaultRandom(),
    userId: text("user_id")
      .notNull()
      .references(() => user.id, { onDelete: "cascade" }),
    /** guided | timed | mock | adaptive | daily */
    mode: text("mode").notNull(),
    config: jsonb("config").$type<PracticeSessionConfig>().notNull(),
    /** active | completed | expired | abandoned */
    status: text("status").notNull().default("active"),
    currentIndex: integer("current_index").notNull().default(0),
    startedAt: ts("started_at").notNull().defaultNow(),
    /** Server-side deadline (timed and mock sessions). Refreshing or reconnecting cannot move it. */
    deadlineAt: ts("deadline_at"),
    completedAt: ts("completed_at"),
    score: jsonb("score").$type<Record<string, unknown> | null>(),
    /** Why the problems were chosen (adaptive mode). */
    rationale: jsonb("rationale").$type<string[]>().notNull().default([]),
  },
  (t) => [index("practice_session_user_idx").on(t.userId, t.startedAt), index("practice_session_status_idx").on(t.status, t.deadlineAt)],
);

export const practiceSessionItem = pgTable(
  "practice_session_item",
  {
    sessionId: uuid("session_id")
      .notNull()
      .references(() => practiceSession.id, { onDelete: "cascade" }),
    position: integer("position").notNull(),
    problemId: uuid("problem_id")
      .notNull()
      .references(() => practiceProblem.id, { onDelete: "cascade" }),
    version: integer("version").notNull(),
    /** pending | submitted | skipped */
    status: text("status").notNull().default("pending"),
    hintsUsed: integer("hints_used").notNull().default(0),
    solutionRevealed: boolean("solution_revealed").notNull().default(false),
    bestSubmissionId: uuid("best_submission_id"),
    passed: integer("passed").notNull().default(0),
    total: integer("total").notNull().default(0),
    score: integer("score").notNull().default(0),
    feedback: jsonb("feedback").$type<Record<string, unknown> | null>(),
  },
  (t) => [primaryKey({ name: "practice_session_item_pk", columns: [t.sessionId, t.position] })],
);

export type PracticeTestResult = {
  /** Position among the tests of this run (public tests carry their ordinal; hidden tests are only counted). */
  index: number;
  visibility: "public" | "hidden";
  status: "passed" | "failed" | "error" | "timeout" | "memory" | "skipped";
  args?: unknown[];
  kwargs?: Record<string, unknown>;
  expected?: unknown;
  actual?: unknown;
  actualRepr?: string;
  stdout?: string;
  error?: { type: string; message: string; traceback?: string };
  ms?: number;
  /** A custom input the user added on Run (no expected value). */
  custom?: boolean;
};

export const practiceSubmission = pgTable(
  "practice_submission",
  {
    id: uuid("id").primaryKey().defaultRandom(),
    userId: text("user_id")
      .notNull()
      .references(() => user.id, { onDelete: "cascade" }),
    problemId: uuid("problem_id")
      .notNull()
      .references(() => practiceProblem.id, { onDelete: "cascade" }),
    problemVersion: integer("problem_version").notNull(),
    sessionId: uuid("session_id").references(() => practiceSession.id, { onDelete: "set null" }),
    /** run (public tests) | submit (public + hidden, graded) */
    kind: text("kind").notNull(),
    idempotencyKey: text("idempotency_key").notNull(),
    code: text("code").notNull(),
    codeSha256: text("code_sha256").notNull(),
    runtime: text("runtime").notNull(),
    /** queued | running | completed | error */
    status: text("status").notNull().default("queued"),
    /** accepted | wrong_answer | runtime_error | timeout | memory | syntax_error | missing_entrypoint | infrastructure_error | cancelled */
    verdict: text("verdict"),
    passed: integer("passed").notNull().default(0),
    total: integer("total").notNull().default(0),
    /** User-visible results: details for public tests only; hidden tests are pass/fail. */
    results: jsonb("results").$type<PracticeTestResult[]>().notNull().default([]),
    loadError: jsonb("load_error").$type<{ type: string; message: string; line?: number; offset?: number } | null>(),
    maxMs: jsonb("max_ms").$type<number | null>(),
    maxMemoryKb: integer("max_memory_kb"),
    pythonVersion: text("python_version"),
    hintsUsed: integer("hints_used").notNull().default(0),
    solutionRevealed: boolean("solution_revealed").notNull().default(false),
    /** Accepted without having revealed the solution (hints allowed, recorded separately). */
    independent: boolean("independent").notNull().default(false),
    score: integer("score"),
    createdAt: ts("created_at").notNull().defaultNow(),
    finishedAt: ts("finished_at"),
  },
  (t) => [
    uniqueIndex("practice_submission_idem_idx").on(t.userId, t.idempotencyKey),
    index("practice_submission_user_idx").on(t.userId, t.createdAt),
    index("practice_submission_problem_idx").on(t.problemId, t.createdAt),
    index("practice_submission_session_idx").on(t.sessionId),
    index("practice_submission_pending_idx").on(t.status, t.createdAt).where(sql`${t.status} in ('queued', 'running')`),
  ],
);

/** The executor job behind a submission (operations view: queue times, retries, infrastructure errors). */
export const practiceExecutionJob = pgTable(
  "practice_execution_job",
  {
    id: uuid("id").primaryKey().defaultRandom(),
    submissionId: uuid("submission_id")
      .notNull()
      .unique()
      .references(() => practiceSubmission.id, { onDelete: "cascade" }),
    executorJobId: text("executor_job_id"),
    status: text("status").notNull().default("queued"),
    error: text("error"),
    queuedAt: ts("queued_at").notNull().defaultNow(),
    finishedAt: ts("finished_at"),
  },
  (t) => [index("practice_execution_job_status_idx").on(t.status, t.queuedAt)],
);

export const practiceProgress = pgTable(
  "practice_progress",
  {
    userId: text("user_id")
      .notNull()
      .references(() => user.id, { onDelete: "cascade" }),
    problemId: uuid("problem_id")
      .notNull()
      .references(() => practiceProblem.id, { onDelete: "cascade" }),
    /** attempted | solved (independently) | solved_assisted (accepted after revealing the solution) */
    status: text("status").notNull().default("attempted"),
    runs: integer("runs").notNull().default(0),
    submits: integer("submits").notNull().default(0),
    hintsUsed: integer("hints_used").notNull().default(0),
    solutionRevealedAt: ts("solution_revealed_at"),
    firstAttemptAt: ts("first_attempt_at").notNull().defaultNow(),
    solvedAt: ts("solved_at"),
    independentSolvedAt: ts("independent_solved_at"),
    /** Time from the first attempt to the first accepted submit (ms). */
    solveMs: bigint("solve_ms", { mode: "number" }),
    bestMs: jsonb("best_ms").$type<number | null>(),
    lastSubmissionId: uuid("last_submission_id"),
    draftCode: text("draft_code"),
    draftSavedAt: ts("draft_saved_at"),
    updatedAt: ts("updated_at").notNull().defaultNow(),
  },
  (t) => [primaryKey({ name: "practice_progress_pk", columns: [t.userId, t.problemId] }), index("practice_progress_problem_idx").on(t.problemId)],
);

export const practiceSkill = pgTable(
  "practice_skill",
  {
    userId: text("user_id")
      .notNull()
      .references(() => user.id, { onDelete: "cascade" }),
    topic: text("topic").notNull(),
    attempts: integer("attempts").notNull().default(0),
    passes: integer("passes").notNull().default(0),
    independentPasses: integer("independent_passes").notNull().default(0),
    failures: integer("failures").notNull().default(0),
    lastAt: ts("last_at").notNull().defaultNow(),
  },
  (t) => [primaryKey({ name: "practice_skill_pk", columns: [t.userId, t.topic] })],
);

export const practiceBookmark = pgTable(
  "practice_bookmark",
  {
    userId: text("user_id")
      .notNull()
      .references(() => user.id, { onDelete: "cascade" }),
    problemId: uuid("problem_id")
      .notNull()
      .references(() => practiceProblem.id, { onDelete: "cascade" }),
    createdAt: ts("created_at").notNull().defaultNow(),
  },
  (t) => [primaryKey({ name: "practice_bookmark_pk", columns: [t.userId, t.problemId] })],
);

export const practiceNote = pgTable(
  "practice_note",
  {
    userId: text("user_id")
      .notNull()
      .references(() => user.id, { onDelete: "cascade" }),
    problemId: uuid("problem_id")
      .notNull()
      .references(() => practiceProblem.id, { onDelete: "cascade" }),
    body: text("body").notNull(),
    updatedAt: ts("updated_at").notNull().defaultNow(),
  },
  (t) => [primaryKey({ name: "practice_note_pk", columns: [t.userId, t.problemId] })],
);

export const practiceAchievement = pgTable(
  "practice_achievement",
  {
    userId: text("user_id")
      .notNull()
      .references(() => user.id, { onDelete: "cascade" }),
    badge: text("badge").notNull(),
    earnedAt: ts("earned_at").notNull().defaultNow(),
    /** The activity event that completed the requirement. */
    eventId: uuid("event_id"),
  },
  (t) => [primaryKey({ name: "practice_achievement_pk", columns: [t.userId, t.badge] })],
);

/** One curated problem per day (Asia/Kolkata calendar day, YYYY-MM-DD). */
export const practiceDailyChallenge = pgTable("practice_daily_challenge", {
  day: text("day").primaryKey(),
  problemId: uuid("problem_id")
    .notNull()
    .references(() => practiceProblem.id, { onDelete: "cascade" }),
  /** auto, or the admin's user id */
  chosenBy: text("chosen_by").notNull().default("auto"),
  createdAt: ts("created_at").notNull().defaultNow(),
});

/** Append-only record of what users did (the source for streaks, achievements, dashboards and exports). */
export const practiceActivityEvent = pgTable(
  "practice_activity_event",
  {
    id: uuid("id").primaryKey().defaultRandom(),
    userId: text("user_id")
      .notNull()
      .references(() => user.id, { onDelete: "cascade" }),
    type: text("type").notNull(),
    problemId: uuid("problem_id"),
    sessionId: uuid("session_id"),
    submissionId: uuid("submission_id"),
    detail: jsonb("detail").$type<Record<string, unknown>>().notNull().default({}),
    createdAt: ts("created_at").notNull().defaultNow(),
  },
  (t) => [index("practice_event_user_idx").on(t.userId, t.createdAt), index("practice_event_type_idx").on(t.type, t.createdAt)],
);

/** AI tutor calls: tokens, cost and outcome (prompts and answers are not stored). */
export const practiceAiUsage = pgTable(
  "practice_ai_usage",
  {
    id: uuid("id").primaryKey().defaultRandom(),
    userId: text("user_id").references(() => user.id, { onDelete: "set null" }),
    feature: text("feature").notNull(),
    provider: text("provider").notNull(),
    model: text("model").notNull(),
    promptVersion: text("prompt_version").notNull(),
    problemId: uuid("problem_id"),
    inputTokens: integer("input_tokens").notNull().default(0),
    outputTokens: integer("output_tokens").notNull().default(0),
    /** Estimated cost in millionths of a US dollar, from the per-million-token prices in the settings. */
    costMicroUsd: bigint("cost_micro_usd", { mode: "number" }).notNull().default(0),
    latencyMs: integer("latency_ms").notNull().default(0),
    /** ok | error | quota | disabled */
    status: text("status").notNull(),
    errorCode: text("error_code"),
    requestId: text("request_id").notNull(),
    createdAt: ts("created_at").notNull().defaultNow(),
  },
  (t) => [index("practice_ai_usage_user_idx").on(t.userId, t.createdAt), index("practice_ai_usage_created_idx").on(t.createdAt)],
);
