# ai-service/app.py: the Python side. A real service would call a model
# here; this stub yields fixed words so the example runs offline.
import asyncio
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

app = FastAPI()


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)


async def generate(message: str) -> AsyncIterator[str]:
    for word in ["Checking", " recent", " latency", " for:", f" {message}"]:
        await asyncio.sleep(0.05)  # stands in for waiting on the model
        yield word


@app.post("/v1/chat")
async def chat(req: ChatRequest) -> StreamingResponse:
    return StreamingResponse(generate(req.message), media_type="text/plain")
