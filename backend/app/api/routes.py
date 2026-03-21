import json
import asyncio
from pathlib import Path
from typing import AsyncGenerator
from uuid import uuid4

import aiofiles
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse, FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_settings
from app.schemas import RunCreate, RunResult, FileUploadResponse
from app.workflows.graph import run_workflow, app as graph_app
from app.db.session import get_session
from app.models import FileArtifact, Run
from app.config import settings

router = APIRouter()
RUN_STORE: dict[str, RunResult] = {}

async def stream_workflow_generator(prompt: str, file_refs: list[str]) -> AsyncGenerator[str, None]:
    run_id = str(uuid4())
    initial_state = {
        "run_id": run_id,
        "prompt": prompt,
        "file_refs": file_refs,
        "status": "pending",
        "plan": [],
        "cursor": 0,
        "tool_results": [],
        "message": None,
        "summary": None,
    }
    
    # Yield initial state
    yield f"data: {json.dumps({'node': 'start', 'state': initial_state})}\n\n"

    # graph_app.stream is synchronous — run it in a thread to avoid blocking the event loop
    loop = asyncio.get_event_loop()
    queue: asyncio.Queue = asyncio.Queue()

    def run_graph():
        try:
            for output in graph_app.stream(initial_state):
                node_name = list(output.keys())[0]
                state_update = output[node_name]
                loop.call_soon_threadsafe(queue.put_nowait, (node_name, state_update))
        finally:
            loop.call_soon_threadsafe(queue.put_nowait, None)  # sentinel

    loop.run_in_executor(None, run_graph)

    while True:
        item = await queue.get()
        if item is None:
            break
        node_name, state_update = item
        yield f"data: {json.dumps({'node': node_name, 'state': state_update})}\n\n"
        await asyncio.sleep(0)  # yield control

    yield "data: [DONE]\n\n"

@router.post("/runs/stream", tags=["runs"])
async def create_run_stream(payload: RunCreate) -> StreamingResponse:
    return StreamingResponse(
        stream_workflow_generator(prompt=payload.prompt, file_refs=payload.file_refs or []),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
    )



@router.get("/status", tags=["system"])
async def status(settings=Depends(get_settings)) -> dict[str, str]:
    return {"status": "ready", "env": settings.env}


@router.post("/runs", response_model=RunResult, tags=["runs"])
async def create_run(payload: RunCreate, session: AsyncSession = Depends(get_session)) -> RunResult:
    state = run_workflow(prompt=payload.prompt, file_refs=payload.file_refs or [])
    result = RunResult.model_validate(state)
    RUN_STORE[result.run_id] = result

    run_row = Run(
        id=result.run_id,
        prompt=payload.prompt,
        status=result.status,
        message=result.message,
        plan=result.plan,
        cursor=result.cursor,
        tool_results=result.tool_results,
    )
    session.add(run_row)
    await session.commit()
    return result


@router.get("/runs/{run_id}", response_model=RunResult, tags=["runs"])
async def get_run(run_id: str) -> RunResult:
    if run_id not in RUN_STORE:
        raise HTTPException(status_code=404, detail="run_not_found")
    return RUN_STORE[run_id]


@router.post("/files", response_model=FileUploadResponse, tags=["files"])
async def upload_file(
    upload: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
    settings_dep=Depends(get_settings),
) -> FileUploadResponse:
    storage_dir = Path(settings_dep.storage_dir)
    storage_dir.mkdir(parents=True, exist_ok=True)

    file_id = str(uuid4())
    safe_name = f"{file_id}_{upload.filename}"
    dest_path = storage_dir / safe_name

    size = 0
    async with aiofiles.open(dest_path, "wb") as out_file:
        while True:
            chunk = await upload.read(1024 * 1024)
            if not chunk:
                break
            size += len(chunk)
            await out_file.write(chunk)

    artifact = FileArtifact(
        id=file_id,
        filename=upload.filename,
        content_type=upload.content_type,
        path=str(dest_path),
        size=size,
    )
    session.add(artifact)
    await session.commit()

    return FileUploadResponse(
        file_id=file_id,
        filename=upload.filename,
        content_type=upload.content_type,
        path=str(dest_path),
        size=size,
    )


@router.get("/reports/{filename}", tags=["reports"])
async def download_report(filename: str) -> FileResponse:
    """Download a generated markdown report by filename."""
    reports_dir = Path(settings.storage_dir).parent / "reports"
    file_path = reports_dir / filename

    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="report_not_found")

    # Basic path traversal guard
    if not file_path.resolve().is_relative_to(reports_dir.resolve()):
        raise HTTPException(status_code=403, detail="forbidden")

    return FileResponse(
        path=str(file_path),
        media_type="text/markdown",
        filename=filename,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
