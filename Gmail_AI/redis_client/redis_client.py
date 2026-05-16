import os

from redis.asyncio import Redis

from dotenv import load_dotenv
load_dotenv(dotenv_path="../.env")
redis_client  = Redis(
        host="localhost",
        port=os.getenv("REDIS_PORT", 6379),
        password=os.getenv("REDIS_PASSWORD", 123456),
        decode_responses=True)