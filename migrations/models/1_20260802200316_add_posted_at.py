from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "posts" ADD "posted_at" TIMESTAMPTZ;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "posts" DROP COLUMN "posted_at";"""


MODELS_STATE = (
    "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"
)
