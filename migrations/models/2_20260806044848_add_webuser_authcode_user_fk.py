from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "auth_codes" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "telegram_id" BIGINT NOT NULL,
    "code" VARCHAR(6) NOT NULL,
    "expires_at" TIMESTAMPTZ NOT NULL,
    "is_used" BOOL NOT NULL,
    "created_at" TIMESTAMPTZ NOT NULL
);
COMMENT ON TABLE "auth_codes" IS 'Одноразовый код для входа в веб-интерфейс.';
        CREATE TABLE IF NOT EXISTS "web_users" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "telegram_id" BIGINT NOT NULL UNIQUE,
    "username" VARCHAR(100),
    "chat_id" BIGINT,
    "is_admin" BOOL NOT NULL,
    "created_at" TIMESTAMPTZ NOT NULL
);
COMMENT ON TABLE "web_users" IS 'Пользователь веб-интерфейса, привязанный к Telegram-аккаунту.';
        ALTER TABLE "channels" ADD "user_id" INT;
        ALTER TABLE "search_requests" ADD "user_id" INT;
        ALTER TABLE "telegram_accounts" ADD "user_id" INT;
        ALTER TABLE "channels" ADD CONSTRAINT "fk_channels_web_user_43cd80db" FOREIGN KEY ("user_id") REFERENCES "web_users" ("id") ON DELETE CASCADE;
        ALTER TABLE "search_requests" ADD CONSTRAINT "fk_search_r_web_user_3fed80a1" FOREIGN KEY ("user_id") REFERENCES "web_users" ("id") ON DELETE CASCADE;
        ALTER TABLE "telegram_accounts" ADD CONSTRAINT "fk_telegram_web_user_5d9b1e5f" FOREIGN KEY ("user_id") REFERENCES "web_users" ("id") ON DELETE CASCADE;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "telegram_accounts" DROP CONSTRAINT IF EXISTS "fk_telegram_web_user_5d9b1e5f";
        ALTER TABLE "search_requests" DROP CONSTRAINT IF EXISTS "fk_search_r_web_user_3fed80a1";
        ALTER TABLE "channels" DROP CONSTRAINT IF EXISTS "fk_channels_web_user_43cd80db";
        ALTER TABLE "channels" DROP COLUMN "user_id";
        ALTER TABLE "search_requests" DROP COLUMN "user_id";
        ALTER TABLE "telegram_accounts" DROP COLUMN "user_id";
        DROP TABLE IF EXISTS "auth_codes";
        DROP TABLE IF EXISTS "web_users";"""


MODELS_STATE = (
    "eJztXV1v2zYU/SuCnlIg7WRbSdwAe3DSdM3WxEXibsPWQaAl2hYqU65EJTG6/PeBH7KuJM"
    "qRHMezXb44DslLUocf4rmHpL+b09DDQfyml9DJeehh89T4bhI0ZV9KcYeGiWazLIYFUDQM"
    "eGKU0Injhh7mwWgY0wi51Dw1RiiI8aFhejh2I39G/ZCw9F8Sy25h9tmx+afHP3mIbfHv4v"
    "MkC++0eeyQf39r8D8IRNsGyI+nskcGMDyCaUURMhqk6ohUrdf8Tzermw2iRQ1tGxi85SGt"
    "N+zxvdCNaeST8V4/6RfCH60DoryiochWZgJSiiLsFqz6CJoZn/q3A+OnIBz75NAAiLVLac"
    "VnG2KxvKC2McABHkdoCgqWaIkMXHWDiKIgPDI9PhRg5OoFDSGWo+Yw3OHIH81530qI/y3B"
    "Dg3HmE5wZJ4af/9zaJg+8fADjtN/Z1+dkY8DLzegfY9lwMMdOp/xsEtC3/OErNsOHTcMki"
    "nJEs/mdBKSRWqfUBY6xgRHiGKWPY0SNrxJEgRyLkhHvKhplkRUEdh4eISSgE0SzFpUIAsz"
    "Hee6P3BuLwaOY5YmkNQCjDQZ5IaETT4+oQyN7+aYVeF1u2Wf2N3Osd09NExezUXIyaMoOg"
    "NGGHJ4rgfmI49HFIkUHOMMVCq7kqNC98wfVwJcMHwa6RTXZVCnARnW2fy7ObDfttudzknb"
    "6hx3j+yTk6OutUC9HLUM/rPLX1gLHBpmGCFXvGnSJsmagL12ytifT1CkRj5NX4A8ptEuQj"
    "5FD06AyZhOzFPjeAmYv/duzj/0bg6OX+UBvZYRbRaTRxY/zPwIxw6iZXzfIYqpP8VqjPOW"
    "BaQ9afom/bKDuC8BenB5dXE76F19YtlP4/hbwPHqDS5YTJuHzguhpVZZZGL8cTn4YLB/jb"
    "/61xcczjCm44iXmKUb/GWyOqGEhg4J7x3kQUzS4DQo18x+7CQxVs1fYRhgRCreEJlVoX2H"
    "YRi8VJMuQjbbpmf9/sdcc55dFual689XZxc3By3ejvG3wKdV01WEGSYrDKq85R4OKjPCyO"
    "uTYC4XCTsyyOR6pjTG2EpsJFdii6XZELlf71HkOaWYsB1WpS1HTdvTYggiaMzbjIHLqikZ"
    "3PkEEYIDFblLo5ZyO1ckasLsBFmxACkQ34eFpbeCwYjlsVgqW9nyGBKUjmASVgXZ2lDhkv"
    "/k1uuAg40Ah5B1kURubaxDQeYA2bNPSmxMJDoxkhhHju8ZB6ynGD8bgIXAIq0yC7UAci6E"
    "5pVmJ5qd7ADUG+YmbKTx7w34CbRZiaNIWLeTorQsqwZJaVlWJU3hcXmYqU+DRhgvDPaQBL"
    "aPjmog3D46qkSYx+UR9mMHudS/w81ZQma3QZ6QTi07SxPkO7rBSxFYrDRfb9u0sYZ3Y2kF"
    "nse3DO77MML+mPyG5xzjSxJTRFxV55Ur6D/w8LPMabfgldhloVkVI3S/WKDBXhUSx8MBFj"
    "32vHd73nt3YT5Wk5oMbEamYsXMIc3e/3aDA8SfoBLoT2G8iy7RKpgfn8n4MmxjjCJ34kT4"
    "W4KVKF8hMh+E7LNmn77lOd6IDHduobekY/PncwocuPS0EeuL2Fukg/x3FEa8eb7iuQJ7OU"
    "4WjShTyQxkLJ1EYTKeqMxhScrBdmiYTpHfPC4l/3zYKJh/Opyqaf9izNbk/IDQplzS+JK0"
    "rZZQK/MUFAiCgPzm2Gd7Xf6ALaiY9BVIfVQh9NVxHEBfBjCWBqKeHegZWKunIcOrpa6s7T"
    "7ldsiNNAM8uHAxdA3pjqpyJfyd0dJpPJbDSY4Z8x/taNgGR0PWMCs4GzJjLYeu7HKg+EGh"
    "LAzwQyX6Iv0+uBqWCQYXfw5y1CyluwdXvT9f5fSCj/3rX9LkgLmdf+yfFbCeYs9Hjk9GYR"
    "nxX2/712rE81ZFHcd3qfGvEfi1ll67gz+DYzn+RagLIgzLoIj/nY/vFSveyplmkV4T5PLE"
    "Ide2TfCEJhrSMqQRngU+boIosNCAlgGdoSheSTvPGWrpfNul81ybh/Fq+yVyhmto8y0bW/"
    "u0BYm5HBm5aLKMgjZ6EbX6IirGhDo0ZN4n2lDdKZrqjWBNNoLl3II11wd5o32iyWtbI+S9"
    "qs3gVdrqhdiTalrqhXu+oAa2pO1YP66rqOWHsFpUq+7Pa4C4qb6zZV25Ls7KsdxUw3zJjZ"
    "n5dlCINKWGqlZrFCpgTd0GKg3ysBjw41uNxY5TeF7NAt+7UP2o3KQp9hyKM192qyovDEqU"
    "ageMBgZSzIEn26x6ucstj/C8FlRr4PG6LkAMnu8DeyqlkIQrRCrdCptthea7d2FD6D28Wl"
    "rblLTWdPvos7aO/oA7G7/i+X2odHtXa2bQRutmzXUzn1Ac3aHAibHbZMoomG2O/nYsa6un"
    "jwzawJ/61JnhyIkS0gDbkt3mwD3aFWxjimgSN5mMM4vNTcdmTMPZTJzM3MCcXGc7f7t6Nz"
    "+LKvRgFFPWCVfw+BdMtc9/m33+JKT+aM59x423DJVt98hJt+n7E/SB5B9QVUWuGyakoXs8"
    "b6TVB31uZ+NKg+yCa3CDp6fBe1mOO9Z363rC88P2acVBn43ay7NRO4Ly+o5G5U7uPO9M1D"
    "NkyZ06DQWes3gOSnXQLH8cKq9sFo9BqQ9LrfM4lFjlLNXcipO+QnVTvBeqdbfF2QU5xzZR"
    "3mppJYtLS1RyCbwTEd4oqRBmlmtHbi09qEK72r3n0He3aN1n23Wf2SQkjYSfhcF6XI3/L7"
    "gv7GNEM78h810YaNarYL0MngmKJ036K7TZQ7Hy2K5zGaddfRunXey0MY5jPySORKeuWFkw"
    "03rlCnqlvv1GX5K5JX1/j33S2neq7zzaG7/ek/fyNPHwPftKnj319S319aT9VOHjAV242r"
    "dzj4fsiutoxVtwVnQNuOv7jQ5Rjvz9jKZbXT3Fb5AsnDivm232tTtP382j4YJwSQ8VdGQd"
    "Z/6bfDlrBrFb2lItbjyC/rlcOdKHV7odSCbtwuuWqyA7yvnk1vAwdstgq29v6pOfB1GCjY"
    "NanrLeu6vLa+f8Q2/gXL571QAW2LjHcI/9E88tErVyPj5Q6rDkuss9Kv88BtdfaS/ednnx"
    "9A3M+gbmH+EG5pV28ente2vo4OlbbgXXVGqmj+1r15R2TT3n91vq7DlpwvfrbzfZsjmwku"
    "hXn2jfsGtkFwFT7jJZHbLmOx93BbSXdCf1cOS7E+Vv5IqY5b+Qm6V5ypNUDYNmd9vF7u5w"
    "xKTVJtwCmOyh6P0iJ3TZoGq0r2C2p+i+DHMLCcWqDfXVN68Bk2ddvLZtaD9Wg7u2m9f+1x"
    "8FfPwPbACI0g=="
)
