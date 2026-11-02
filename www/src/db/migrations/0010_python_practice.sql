-- Python practice (/python-practice): roles, topics, versioned problems and test cases, sessions, submissions,
-- progress, skills, bookmarks, notes, achievements, daily challenges, activity events and AI usage. Additive.
-- Users are the existing Better Auth "user" rows; deleting a user deletes their practice data (cascade).
CREATE TABLE IF NOT EXISTS "practice_role" (
	"slug" text PRIMARY KEY NOT NULL,
	"name" text NOT NULL,
	"description" text NOT NULL,
	"icon" text DEFAULT 'code' NOT NULL,
	"competencies" jsonb DEFAULT '[]'::jsonb NOT NULL,
	"learning_path" jsonb DEFAULT '[]'::jsonb NOT NULL,
	"topics" text[] DEFAULT '{}'::text[] NOT NULL,
	"difficulty_mix" jsonb DEFAULT '{}'::jsonb NOT NULL,
	"scenarios" jsonb DEFAULT '[]'::jsonb NOT NULL,
	"libraries" jsonb DEFAULT '[]'::jsonb NOT NULL,
	"sort" integer DEFAULT 100 NOT NULL,
	"status" text DEFAULT 'active' NOT NULL,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL
);--> statement-breakpoint
CREATE TABLE IF NOT EXISTS "practice_topic" (
	"slug" text PRIMARY KEY NOT NULL,
	"name" text NOT NULL,
	"area" text NOT NULL,
	"description" text DEFAULT '' NOT NULL,
	"sort" integer DEFAULT 100 NOT NULL
);--> statement-breakpoint
CREATE TABLE IF NOT EXISTS "practice_problem" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"slug" text NOT NULL UNIQUE,
	"title" text NOT NULL,
	"difficulty" text NOT NULL,
	"roles" text[] DEFAULT '{}'::text[] NOT NULL,
	"topics" text[] DEFAULT '{}'::text[] NOT NULL,
	"status" text DEFAULT 'draft' NOT NULL,
	"current_version" integer DEFAULT 1 NOT NULL,
	"estimated_minutes" integer DEFAULT 15 NOT NULL,
	"source" text DEFAULT 'admin' NOT NULL,
	"seed_hash" text,
	"daily_eligible" boolean DEFAULT true NOT NULL,
	"created_by" text,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL,
	"published_at" timestamp with time zone
);--> statement-breakpoint
CREATE INDEX IF NOT EXISTS "practice_problem_status_idx" ON "practice_problem" USING btree ("status","difficulty");--> statement-breakpoint
CREATE INDEX IF NOT EXISTS "practice_problem_roles_idx" ON "practice_problem" USING gin ("roles");--> statement-breakpoint
CREATE INDEX IF NOT EXISTS "practice_problem_topics_idx" ON "practice_problem" USING gin ("topics");--> statement-breakpoint
CREATE TABLE IF NOT EXISTS "practice_problem_version" (
	"problem_id" uuid NOT NULL REFERENCES "practice_problem"("id") ON DELETE cascade,
	"version" integer NOT NULL,
	"title" text NOT NULL,
	"description" text NOT NULL,
	"entrypoint" text NOT NULL,
	"starter_code" text NOT NULL,
	"prelude" text DEFAULT '' NOT NULL,
	"comparator" text DEFAULT 'exact' NOT NULL,
	"tolerance" jsonb DEFAULT '0.000001'::jsonb NOT NULL,
	"constraints" jsonb DEFAULT '[]'::jsonb NOT NULL,
	"io" jsonb DEFAULT '{}'::jsonb NOT NULL,
	"hints" jsonb DEFAULT '[]'::jsonb NOT NULL,
	"solution" jsonb NOT NULL,
	"limits" jsonb NOT NULL,
	"content_hash" text NOT NULL,
	"note" text DEFAULT '' NOT NULL,
	"created_by" text,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	CONSTRAINT "practice_problem_version_pk" PRIMARY KEY ("problem_id","version")
);--> statement-breakpoint
CREATE TABLE IF NOT EXISTS "practice_test_case" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"problem_id" uuid NOT NULL,
	"version" integer NOT NULL,
	"ordinal" integer NOT NULL,
	"visibility" text NOT NULL,
	"is_example" boolean DEFAULT false NOT NULL,
	"label" text DEFAULT '' NOT NULL,
	"explanation" text DEFAULT '' NOT NULL,
	"args" jsonb DEFAULT '[]'::jsonb NOT NULL,
	"kwargs" jsonb DEFAULT '{}'::jsonb NOT NULL,
	"expected" jsonb,
	CONSTRAINT "practice_test_case_version_fk" FOREIGN KEY ("problem_id","version") REFERENCES "practice_problem_version"("problem_id","version") ON DELETE cascade
);--> statement-breakpoint
CREATE INDEX IF NOT EXISTS "practice_test_case_problem_idx" ON "practice_test_case" USING btree ("problem_id","version","ordinal");--> statement-breakpoint
CREATE TABLE IF NOT EXISTS "practice_profile" (
	"user_id" text PRIMARY KEY NOT NULL REFERENCES "user"("id") ON DELETE cascade,
	"roles" text[] DEFAULT '{}'::text[] NOT NULL,
	"leaderboard_opt_in" boolean DEFAULT false NOT NULL,
	"public_name" text,
	"xp" integer DEFAULT 0 NOT NULL,
	"current_streak" integer DEFAULT 0 NOT NULL,
	"longest_streak" integer DEFAULT 0 NOT NULL,
	"last_active_day" text,
	"preferences" jsonb DEFAULT '{}'::jsonb NOT NULL,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL
);--> statement-breakpoint
CREATE INDEX IF NOT EXISTS "practice_profile_leaderboard_idx" ON "practice_profile" USING btree ("xp") WHERE "leaderboard_opt_in";--> statement-breakpoint
CREATE TABLE IF NOT EXISTS "practice_session" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"user_id" text NOT NULL REFERENCES "user"("id") ON DELETE cascade,
	"mode" text NOT NULL,
	"config" jsonb NOT NULL,
	"status" text DEFAULT 'active' NOT NULL,
	"current_index" integer DEFAULT 0 NOT NULL,
	"started_at" timestamp with time zone DEFAULT now() NOT NULL,
	"deadline_at" timestamp with time zone,
	"completed_at" timestamp with time zone,
	"score" jsonb,
	"rationale" jsonb DEFAULT '[]'::jsonb NOT NULL
);--> statement-breakpoint
CREATE INDEX IF NOT EXISTS "practice_session_user_idx" ON "practice_session" USING btree ("user_id","started_at");--> statement-breakpoint
CREATE INDEX IF NOT EXISTS "practice_session_status_idx" ON "practice_session" USING btree ("status","deadline_at");--> statement-breakpoint
CREATE TABLE IF NOT EXISTS "practice_session_item" (
	"session_id" uuid NOT NULL REFERENCES "practice_session"("id") ON DELETE cascade,
	"position" integer NOT NULL,
	"problem_id" uuid NOT NULL REFERENCES "practice_problem"("id") ON DELETE cascade,
	"version" integer NOT NULL,
	"status" text DEFAULT 'pending' NOT NULL,
	"hints_used" integer DEFAULT 0 NOT NULL,
	"solution_revealed" boolean DEFAULT false NOT NULL,
	"best_submission_id" uuid,
	"passed" integer DEFAULT 0 NOT NULL,
	"total" integer DEFAULT 0 NOT NULL,
	"score" integer DEFAULT 0 NOT NULL,
	"feedback" jsonb,
	CONSTRAINT "practice_session_item_pk" PRIMARY KEY ("session_id","position")
);--> statement-breakpoint
CREATE TABLE IF NOT EXISTS "practice_submission" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"user_id" text NOT NULL REFERENCES "user"("id") ON DELETE cascade,
	"problem_id" uuid NOT NULL REFERENCES "practice_problem"("id") ON DELETE cascade,
	"problem_version" integer NOT NULL,
	"session_id" uuid REFERENCES "practice_session"("id") ON DELETE set null,
	"kind" text NOT NULL,
	"idempotency_key" text NOT NULL,
	"code" text NOT NULL,
	"code_sha256" text NOT NULL,
	"runtime" text NOT NULL,
	"status" text DEFAULT 'queued' NOT NULL,
	"verdict" text,
	"passed" integer DEFAULT 0 NOT NULL,
	"total" integer DEFAULT 0 NOT NULL,
	"results" jsonb DEFAULT '[]'::jsonb NOT NULL,
	"load_error" jsonb,
	"max_ms" jsonb,
	"max_memory_kb" integer,
	"python_version" text,
	"hints_used" integer DEFAULT 0 NOT NULL,
	"solution_revealed" boolean DEFAULT false NOT NULL,
	"independent" boolean DEFAULT false NOT NULL,
	"score" integer,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	"finished_at" timestamp with time zone
);--> statement-breakpoint
CREATE UNIQUE INDEX IF NOT EXISTS "practice_submission_idem_idx" ON "practice_submission" USING btree ("user_id","idempotency_key");--> statement-breakpoint
CREATE INDEX IF NOT EXISTS "practice_submission_user_idx" ON "practice_submission" USING btree ("user_id","created_at");--> statement-breakpoint
CREATE INDEX IF NOT EXISTS "practice_submission_problem_idx" ON "practice_submission" USING btree ("problem_id","created_at");--> statement-breakpoint
CREATE INDEX IF NOT EXISTS "practice_submission_session_idx" ON "practice_submission" USING btree ("session_id");--> statement-breakpoint
CREATE INDEX IF NOT EXISTS "practice_submission_pending_idx" ON "practice_submission" USING btree ("status","created_at") WHERE "status" in ('queued', 'running');--> statement-breakpoint
CREATE TABLE IF NOT EXISTS "practice_execution_job" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"submission_id" uuid NOT NULL UNIQUE REFERENCES "practice_submission"("id") ON DELETE cascade,
	"executor_job_id" text,
	"status" text DEFAULT 'queued' NOT NULL,
	"error" text,
	"queued_at" timestamp with time zone DEFAULT now() NOT NULL,
	"finished_at" timestamp with time zone
);--> statement-breakpoint
CREATE INDEX IF NOT EXISTS "practice_execution_job_status_idx" ON "practice_execution_job" USING btree ("status","queued_at");--> statement-breakpoint
CREATE TABLE IF NOT EXISTS "practice_progress" (
	"user_id" text NOT NULL REFERENCES "user"("id") ON DELETE cascade,
	"problem_id" uuid NOT NULL REFERENCES "practice_problem"("id") ON DELETE cascade,
	"status" text DEFAULT 'attempted' NOT NULL,
	"runs" integer DEFAULT 0 NOT NULL,
	"submits" integer DEFAULT 0 NOT NULL,
	"hints_used" integer DEFAULT 0 NOT NULL,
	"solution_revealed_at" timestamp with time zone,
	"first_attempt_at" timestamp with time zone DEFAULT now() NOT NULL,
	"solved_at" timestamp with time zone,
	"independent_solved_at" timestamp with time zone,
	"solve_ms" bigint,
	"best_ms" jsonb,
	"last_submission_id" uuid,
	"draft_code" text,
	"draft_saved_at" timestamp with time zone,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL,
	CONSTRAINT "practice_progress_pk" PRIMARY KEY ("user_id","problem_id")
);--> statement-breakpoint
CREATE INDEX IF NOT EXISTS "practice_progress_problem_idx" ON "practice_progress" USING btree ("problem_id");--> statement-breakpoint
CREATE TABLE IF NOT EXISTS "practice_skill" (
	"user_id" text NOT NULL REFERENCES "user"("id") ON DELETE cascade,
	"topic" text NOT NULL,
	"attempts" integer DEFAULT 0 NOT NULL,
	"passes" integer DEFAULT 0 NOT NULL,
	"independent_passes" integer DEFAULT 0 NOT NULL,
	"failures" integer DEFAULT 0 NOT NULL,
	"last_at" timestamp with time zone DEFAULT now() NOT NULL,
	CONSTRAINT "practice_skill_pk" PRIMARY KEY ("user_id","topic")
);--> statement-breakpoint
CREATE TABLE IF NOT EXISTS "practice_bookmark" (
	"user_id" text NOT NULL REFERENCES "user"("id") ON DELETE cascade,
	"problem_id" uuid NOT NULL REFERENCES "practice_problem"("id") ON DELETE cascade,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	CONSTRAINT "practice_bookmark_pk" PRIMARY KEY ("user_id","problem_id")
);--> statement-breakpoint
CREATE TABLE IF NOT EXISTS "practice_note" (
	"user_id" text NOT NULL REFERENCES "user"("id") ON DELETE cascade,
	"problem_id" uuid NOT NULL REFERENCES "practice_problem"("id") ON DELETE cascade,
	"body" text NOT NULL,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL,
	CONSTRAINT "practice_note_pk" PRIMARY KEY ("user_id","problem_id")
);--> statement-breakpoint
CREATE TABLE IF NOT EXISTS "practice_achievement" (
	"user_id" text NOT NULL REFERENCES "user"("id") ON DELETE cascade,
	"badge" text NOT NULL,
	"earned_at" timestamp with time zone DEFAULT now() NOT NULL,
	"event_id" uuid,
	CONSTRAINT "practice_achievement_pk" PRIMARY KEY ("user_id","badge")
);--> statement-breakpoint
CREATE TABLE IF NOT EXISTS "practice_daily_challenge" (
	"day" text PRIMARY KEY NOT NULL,
	"problem_id" uuid NOT NULL REFERENCES "practice_problem"("id") ON DELETE cascade,
	"chosen_by" text DEFAULT 'auto' NOT NULL,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL
);--> statement-breakpoint
CREATE TABLE IF NOT EXISTS "practice_activity_event" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"user_id" text NOT NULL REFERENCES "user"("id") ON DELETE cascade,
	"type" text NOT NULL,
	"problem_id" uuid,
	"session_id" uuid,
	"submission_id" uuid,
	"detail" jsonb DEFAULT '{}'::jsonb NOT NULL,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL
);--> statement-breakpoint
CREATE INDEX IF NOT EXISTS "practice_event_user_idx" ON "practice_activity_event" USING btree ("user_id","created_at");--> statement-breakpoint
CREATE INDEX IF NOT EXISTS "practice_event_type_idx" ON "practice_activity_event" USING btree ("type","created_at");--> statement-breakpoint
CREATE TABLE IF NOT EXISTS "practice_ai_usage" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"user_id" text REFERENCES "user"("id") ON DELETE set null,
	"feature" text NOT NULL,
	"provider" text NOT NULL,
	"model" text NOT NULL,
	"prompt_version" text NOT NULL,
	"problem_id" uuid,
	"input_tokens" integer DEFAULT 0 NOT NULL,
	"output_tokens" integer DEFAULT 0 NOT NULL,
	"cost_micro_usd" bigint DEFAULT 0 NOT NULL,
	"latency_ms" integer DEFAULT 0 NOT NULL,
	"status" text NOT NULL,
	"error_code" text,
	"request_id" text NOT NULL,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL
);--> statement-breakpoint
CREATE INDEX IF NOT EXISTS "practice_ai_usage_user_idx" ON "practice_ai_usage" USING btree ("user_id","created_at");--> statement-breakpoint
CREATE INDEX IF NOT EXISTS "practice_ai_usage_created_idx" ON "practice_ai_usage" USING btree ("created_at");
