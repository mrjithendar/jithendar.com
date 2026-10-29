-- Security audit (request IP, user agent and severity on audit entries), remembered human checks for
-- signed-in commenters, featured images on pages and WordPress-style attachment fields on media. Additive.
ALTER TABLE "audit_log" ADD COLUMN IF NOT EXISTS "ip" text;--> statement-breakpoint
ALTER TABLE "audit_log" ADD COLUMN IF NOT EXISTS "user_agent" text;--> statement-breakpoint
ALTER TABLE "audit_log" ADD COLUMN IF NOT EXISTS "severity" text DEFAULT 'info' NOT NULL;--> statement-breakpoint
CREATE INDEX IF NOT EXISTS "audit_action_created_idx" ON "audit_log" USING btree ("action","created_at");--> statement-breakpoint
CREATE INDEX IF NOT EXISTS "audit_ip_created_idx" ON "audit_log" USING btree ("ip","created_at");--> statement-breakpoint
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS "human_verified_at" timestamp with time zone;--> statement-breakpoint
ALTER TABLE "page" ADD COLUMN IF NOT EXISTS "featured_image" jsonb;--> statement-breakpoint
ALTER TABLE "media" ADD COLUMN IF NOT EXISTS "title" text DEFAULT '' NOT NULL;--> statement-breakpoint
ALTER TABLE "media" ADD COLUMN IF NOT EXISTS "caption" text DEFAULT '' NOT NULL;--> statement-breakpoint
ALTER TABLE "media" ADD COLUMN IF NOT EXISTS "description" text DEFAULT '' NOT NULL;
