import asyncio

from api.adapters.storage.s3 import ensure_bucket

if __name__ == "__main__":
    asyncio.run(ensure_bucket())
