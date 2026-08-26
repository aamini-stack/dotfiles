CREATE TABLE "items" (
	"id" text PRIMARY KEY,
	"name" text NOT NULL,
	"userId" text NOT NULL,
	"createdAt" timestamp with time zone NOT NULL
);
--> statement-breakpoint
CREATE TABLE "account" (
	"id" text PRIMARY KEY,
	"user_id" text NOT NULL,
	"account_id" text NOT NULL,
	"provider_id" text NOT NULL,
	"access_token" text,
	"refresh_token" text,
	"access_token_expires_at" timestamp with time zone,
	"refresh_token_expires_at" timestamp with time zone,
	"scope" text,
	"id_token" text,
	"password" text,
	"created_at" timestamp with time zone NOT NULL,
	"updated_at" timestamp with time zone NOT NULL
);
--> statement-breakpoint
CREATE TABLE "session" (
	"id" text PRIMARY KEY,
	"user_id" text NOT NULL,
	"token" text NOT NULL,
	"expires_at" timestamp with time zone NOT NULL,
	"ip_address" text,
	"user_agent" text,
	"impersonated_by" text,
	"created_at" timestamp with time zone NOT NULL,
	"updated_at" timestamp with time zone NOT NULL
);
--> statement-breakpoint
CREATE TABLE "user" (
	"id" text PRIMARY KEY,
	"name" text NOT NULL,
	"email" text NOT NULL,
	"email_verified" boolean DEFAULT false NOT NULL,
	"image" text,
	"created_at" timestamp with time zone NOT NULL,
	"updated_at" timestamp with time zone NOT NULL
);
--> statement-breakpoint
CREATE TABLE "verification" (
	"id" text PRIMARY KEY,
	"identifier" text NOT NULL,
	"value" text NOT NULL,
	"expires_at" timestamp with time zone NOT NULL,
	"created_at" timestamp with time zone NOT NULL,
	"updated_at" timestamp with time zone NOT NULL
);
--> statement-breakpoint
CREATE INDEX "items_user_id_index" ON "items" ("userId");--> statement-breakpoint
CREATE INDEX "account_user_id_index" ON "account" ("user_id");--> statement-breakpoint
CREATE UNIQUE INDEX "account_provider_account_index" ON "account" ("provider_id","account_id");--> statement-breakpoint
CREATE UNIQUE INDEX "session_token_index" ON "session" ("token");--> statement-breakpoint
CREATE INDEX "session_user_id_index" ON "session" ("user_id");--> statement-breakpoint
CREATE UNIQUE INDEX "user_email_index" ON "user" ("email");--> statement-breakpoint
CREATE INDEX "verification_identifier_index" ON "verification" ("identifier");--> statement-breakpoint
ALTER TABLE "items" ADD CONSTRAINT "items_user_id_fk" FOREIGN KEY ("userId") REFERENCES "user"("id") ON DELETE CASCADE;--> statement-breakpoint
ALTER TABLE "account" ADD CONSTRAINT "account_user_id_fk" FOREIGN KEY ("user_id") REFERENCES "user"("id") ON DELETE CASCADE;--> statement-breakpoint
ALTER TABLE "session" ADD CONSTRAINT "session_user_id_fk" FOREIGN KEY ("user_id") REFERENCES "user"("id") ON DELETE CASCADE;