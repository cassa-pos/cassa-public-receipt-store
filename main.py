import asyncio
import os
import shutil
from typing import Annotated
from datetime import date, timedelta

import aiofiles
import aiofiles.os
from fastapi import FastAPI, Path, UploadFile, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles

app = FastAPI()

date_regex = "^\\d{4}-\\d{2}-\\d{2}$"
uuid_regex = "^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"

upload_path = os.environ.get("UPLOAD_PATH") or "./"


async def authorize(credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())):
    if credentials.credentials != os.environ["AUTH_TOKEN"]:
        raise HTTPException(status_code=401)


@app.post("/upload/{date}/{uuid}", status_code=201)
async def upload(date: Annotated[str, Path(regex=date_regex)], uuid: Annotated[str, Path(regex=uuid_regex)],
                 auth: Annotated[None, Depends(authorize)], file: UploadFile):
    try:
        await aiofiles.os.mkdir(upload_path + "/" + date)
    except FileExistsError:
        pass
    async with aiofiles.open(f"{upload_path}/{date}/{uuid}.pdf", mode="xb") as destination_file:
        buffer_size = 4096
        while True:
            buffer = await file.read(buffer_size)
            await destination_file.write(buffer)
            if len(buffer) < buffer_size:
                break
    await file.close()
    return


app.mount("/", StaticFiles(directory=upload_path), name="download")


async def cleanup():
    while True:
        date_limit = date.today() - timedelta(days=10)
        try:
            for entry in await aiofiles.os.listdir(upload_path):
                try:
                    entry_date = date.fromisoformat(entry)
                    if entry_date < date_limit:
                        try:
                            await aiofiles.os.wrap(shutil.rmtree)(f"{upload_path}/{entry}")
                        except Exception:
                            pass
                except ValueError:
                    continue
        except Exception:
            pass
        await asyncio.sleep(12 * 60)


asyncio.get_running_loop().create_task(cleanup())
