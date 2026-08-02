from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "channels" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "telegram_id" BIGINT NOT NULL UNIQUE,
    "username" VARCHAR(100),
    "title" VARCHAR(255) NOT NULL,
    "is_active" BOOL NOT NULL
);
CREATE TABLE IF NOT EXISTS "telegram_accounts" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "phone" VARCHAR(20) NOT NULL UNIQUE,
    "api_id" INT NOT NULL,
    "api_hash" VARCHAR(64) NOT NULL,
    "session_str" TEXT,
    "is_active" BOOL NOT NULL,
    "created_at" TIMESTAMPTZ NOT NULL
);
CREATE TABLE IF NOT EXISTS "search_requests" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "name" VARCHAR(255) NOT NULL,
    "keywords" TEXT,
    "interval_sec" INT NOT NULL,
    "limit_per_run" INT NOT NULL,
    "status" VARCHAR(20) NOT NULL,
    "last_run_at" TIMESTAMPTZ,
    "notify_chat_id" BIGINT,
    "created_at" TIMESTAMPTZ NOT NULL,
    "account_id" INT NOT NULL REFERENCES "telegram_accounts" ("id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "posts" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "telegram_msg_id" BIGINT NOT NULL,
    "text" TEXT,
    "media_info" JSONB,
    "views" INT,
    "forwards" INT,
    "replies" INT,
    "parsed_at" TIMESTAMPTZ NOT NULL,
    "raw_data" JSONB,
    "sent_to_chat" BOOL NOT NULL,
    "channel_id" INT NOT NULL REFERENCES "channels" ("id") ON DELETE CASCADE,
    "search_request_id" INT REFERENCES "search_requests" ("id") ON DELETE CASCADE,
    CONSTRAINT "uid_posts_telegra_9a2696" UNIQUE ("telegram_msg_id", "channel_id")
);
CREATE TABLE IF NOT EXISTS "aerich" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "version" VARCHAR(255) NOT NULL,
    "app" VARCHAR(100) NOT NULL,
    "content" JSONB NOT NULL
);
CREATE TABLE IF NOT EXISTS "search_requests_channels" (
    "search_requests_id" INT NOT NULL REFERENCES "search_requests" ("id") ON DELETE CASCADE,
    "channel_id" INT NOT NULL REFERENCES "channels" ("id") ON DELETE CASCADE
);
CREATE UNIQUE INDEX IF NOT EXISTS "uidx_search_requ_search__f671c1" ON "search_requests_channels" ("search_requests_id", "channel_id");"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        """


MODELS_STATE = (
    "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"
    "yuRFlfabRvu5HO7SSu1rBP/lB7Pn/wGQeH+8"
)
