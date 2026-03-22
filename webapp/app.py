from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from webapp.service import get_service
from webapp.storage import OUTPUT_ROOT


PROJECT_ROOT = Path(__file__).resolve().parents[1]
STATIC_DIR = PROJECT_ROOT / "webapp" / "static"

app = FastAPI(
    title="Steel Defect Detection Web API",
    description="A lightweight web wrapper around the existing YOLOv8 defect detector.",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
app.mount("/media", StaticFiles(directory=str(OUTPUT_ROOT)), name="media")


@app.get("/", response_class=FileResponse)
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/info")
def info() -> dict:
    service = get_service()
    return {
        "app_name": app.title,
        "version": app.version,
        "service": service.app_info(),
    }


@app.get("/api/models")
def models() -> dict:
    service = get_service()
    return {"models": service.list_models()}


@app.get("/api/history")
def history(limit: int = Query(50, ge=1, le=200)) -> dict:
    service = get_service()
    return {
        "count": service.storage.count(),
        "records": service.history_records(limit=limit),
    }


@app.get("/api/history/export")
def export_history(export_format: str = Query("csv", alias="format")):
    service = get_service()
    try:
        export_path = service.export_history(export_format.lower())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return FileResponse(export_path, filename=export_path.name)


@app.get("/api/history/{record_id}")
def history_detail(record_id: str) -> dict:
    service = get_service()
    try:
        return service.history_record_detail(record_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/predict/image")
async def predict_image(
    file: UploadFile = File(...),
    model_id: Optional[str] = Form(None),
    confidence: Optional[float] = Form(None),
    image_size: Optional[int] = Form(None),
) -> dict:
    return await _handle_image_request(
        file=file,
        model_id=model_id,
        confidence=confidence,
        image_size=image_size,
        task_kind="image",
    )


@app.post("/api/predict/images-batch")
async def predict_images_batch(
    files: List[UploadFile] = File(...),
    model_id: Optional[str] = Form(None),
    confidence: Optional[float] = Form(None),
    image_size: Optional[int] = Form(None),
) -> dict:
    if not files:
        raise HTTPException(status_code=400, detail="Please choose image files.")

    payloads = []
    for file in files:
        if not file.filename:
            raise HTTPException(status_code=400, detail="One of the uploaded files has no filename.")
        if file.content_type and not file.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="Batch mode only supports images.")
        payloads.append((await file.read(), file.filename))

    service = get_service()
    try:
        return service.process_image_batch(
            files=payloads,
            model_id=model_id,
            confidence=confidence,
            image_size=image_size,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Batch inference failed: {exc}") from exc


@app.post("/api/predict/camera-frame")
async def predict_camera_frame(
    file: UploadFile = File(...),
    model_id: Optional[str] = Form(None),
    confidence: Optional[float] = Form(None),
    image_size: Optional[int] = Form(None),
) -> dict:
    return await _handle_image_request(
        file=file,
        model_id=model_id,
        confidence=confidence,
        image_size=image_size,
        task_kind="camera",
    )


@app.post("/api/predict/video")
async def predict_video(
    file: UploadFile = File(...),
    model_id: Optional[str] = Form(None),
    confidence: Optional[float] = Form(None),
    image_size: Optional[int] = Form(None),
) -> dict:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Please choose a video file.")

    payload = await file.read()
    service = get_service()

    try:
        result = service.process_video_upload(
            video_bytes=payload,
            filename=file.filename,
            model_id=model_id,
            confidence=confidence,
            image_size=image_size,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Video inference failed: {exc}") from exc

    return result


async def _handle_image_request(
    file: UploadFile,
    model_id: Optional[str],
    confidence: Optional[float],
    image_size: Optional[int],
    task_kind: str,
) -> dict:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Please choose an image file.")
    if file.content_type and not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image uploads are supported here.")

    payload = await file.read()
    service = get_service()

    try:
        if task_kind == "camera":
            result = service.process_camera_frame(
                image_bytes=payload,
                filename=file.filename,
                model_id=model_id,
                confidence=confidence,
                image_size=image_size,
            )
        else:
            result = service.process_image_upload(
                image_bytes=payload,
                filename=file.filename,
                model_id=model_id,
                confidence=confidence,
                image_size=image_size,
            )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Inference failed: {exc}") from exc

    return result
