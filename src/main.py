import asyncio
from src.config import BOT_TOKEN, DB_URL, LOG_LEVEL


async def main():
    print(f'BOT_TOKEN={BOT_TOKEN}')
    print(f'DB_URL={DB_URL}')
    print(f'LOG_LEVEL={LOG_LEVEL}')



if __name__ == '__main__':
    asyncio.run(main())
