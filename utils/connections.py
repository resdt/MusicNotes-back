import os
import re
import asyncpg
from fastapi import HTTPException


DB_LINK = os.getenv("DB_LINK")
PARAMETER_LIST = re.split(r"[:/\@\?]+", DB_LINK)
DB_PARAMS = {"user": PARAMETER_LIST[1],
             "password": PARAMETER_LIST[2],
             "host": PARAMETER_LIST[3],
             "database": PARAMETER_LIST[4],
             "port": "5432"}


async def execute_query(query, *parameters):
    connection = await asyncpg.connect(**DB_PARAMS)
    try:
        results = await connection.fetch(query, *parameters)
        return [dict(row) for row in results]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
    finally:
        await connection.close()
