"""
First-run setup + indexing control.
"""
from pathlib import Path
from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

import config as cfg
import rag

router = APIRouter(prefix="/config", tags=["config"])


class SetupRequest(BaseModel):
    materials_path: str


@router.get("/")
def get_config():
    data = cfg.load_config()
    return {
        "first_run": cfg.is_first_run(),
        "materials_path": data.get("materials_path"),
        "indexed_at": data.get("indexed_at"),
        "file_count": data.get("file_count", 0),
        "chunk_count": data.get("chunk_count", 0),
    }


@router.post("/setup")
def setup(payload: SetupRequest, background: BackgroundTasks):
    """Save the materials path and kick off indexing in the background."""
    path = Path(payload.materials_path).expanduser()
    if not path.exists() or not path.is_dir():
        raise HTTPException(status_code=400, detail=f"Folder not found: {payload.materials_path}")

    cfg.save_config({"materials_path": str(path)})
    background.add_task(_index_and_record, str(path))
    return {"ok": True, "materials_path": str(path), "status": "indexing started"}


@router.post("/reindex")
def reindex(background: BackgroundTasks):
    path = cfg.get_materials_path()
    if not path:
        raise HTTPException(status_code=400, detail="No materials path configured yet")
    background.add_task(_index_and_record, path)
    return {"ok": True, "status": "reindexing started"}


@router.get("/index-status")
def index_status():
    return rag.index_status


def _index_and_record(path: str):
    """Background task: index, then persist the resulting counts to config."""
    from datetime import datetime, timezone

    result = rag.index_materials(path)
    if result:
        cfg.save_config({
            "indexed_at": datetime.now(timezone.utc).isoformat(),
            "file_count": result["file_count"],
            "chunk_count": result["chunk_count"],
        })
