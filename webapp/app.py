from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from webapp.auth_service import get_auth_service
from webapp.service import get_service
from webapp.storage import OUTPUT_ROOT


PROJECT_ROOT = Path(__file__).resolve().parents[1]
STATIC_DIR = PROJECT_ROOT / "webapp" / "static"
VUE_INDEX_PATH = STATIC_DIR / "vue" / "index.html"
LEGACY_INDEX_PATH = STATIC_DIR / "index.html"


class CredentialsPayload(BaseModel):
    username: str = Field(..., min_length=3, max_length=32)
    password: str = Field(..., min_length=6, max_length=128)


class ChangePasswordPayload(BaseModel):
    old_password: str = Field(..., min_length=6, max_length=128)
    new_password: str = Field(..., min_length=6, max_length=128)


app = FastAPI(
    title="Steel Defect Detection Web API",
    description="A lightweight web wrapper around the existing YOLOv8 defect detector.",
    version="0.4.0",
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


def _extract_bearer_token(authorization: Optional[str]) -> str:
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header is required.")

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise HTTPException(status_code=401, detail="Authorization header must use Bearer token.")

    return token.strip()


def get_current_user(
    authorization: Optional[str] = Header(None),
) -> Dict[str, Any]:
    token = _extract_bearer_token(authorization)
    auth_service = get_auth_service()
    user = auth_service.authenticate_token(token)
    if user is None:
        raise HTTPException(status_code=401, detail="Token is invalid or expired.")
    return user


def _client_meta(request: Request) -> Dict[str, Optional[str]]:
    client_host = request.client.host if request.client else None
    return {
        "ip_address": client_host,
        "user_agent": request.headers.get("user-agent"),
    }


def _record_inference_activity(user: Dict[str, Any], payload: Dict[str, Any]) -> None:
    try:
        get_auth_service().log_inference_activity(user_id=int(user["id"]), response_payload=payload)
    except Exception:
        # Inference should not fail because activity logging failed.
        return


@app.get("/", response_class=FileResponse)
def index() -> FileResponse:
    if VUE_INDEX_PATH.exists():
        return FileResponse(VUE_INDEX_PATH)
    return FileResponse(LEGACY_INDEX_PATH)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/auth/bootstrap-status")
def auth_bootstrap_status() -> dict:
    return get_auth_service().bootstrap_status()


@app.post("/api/auth/register")
def register(payload: CredentialsPayload, request: Request) -> dict:
    meta = _client_meta(request)
    auth_service = get_auth_service()
    try:
        return auth_service.register(
            username=payload.username,
            password=payload.password,
            ip_address=meta["ip_address"],
            user_agent=meta["user_agent"],
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/auth/login")
def login(payload: CredentialsPayload, request: Request) -> dict:
    meta = _client_meta(request)
    auth_service = get_auth_service()
    try:
        auth_service.cleanup_sessions()
        return auth_service.login(
            username=payload.username,
            password=payload.password,
            ip_address=meta["ip_address"],
            user_agent=meta["user_agent"],
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/auth/me")
def me(current_user: Dict[str, Any] = Depends(get_current_user)) -> dict:
    return {"user": current_user}


@app.post("/api/auth/logout")
def logout(
    current_user: Dict[str, Any] = Depends(get_current_user),
    authorization: Optional[str] = Header(None),
) -> dict:
    _ = current_user
    token = _extract_bearer_token(authorization)
    get_auth_service().logout(token)
    return {"ok": True}


@app.post("/api/auth/change-password")
def change_password(
    payload: ChangePasswordPayload,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> dict:
    auth_service = get_auth_service()
    try:
        auth_service.change_password(
            user_id=int(current_user["id"]),
            old_password=payload.old_password,
            new_password=payload.new_password,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "ok": True,
        "message": "Password changed successfully. Please login again.",
    }


@app.get("/api/auth/activity")
def my_activity(
    limit: int = Query(50, ge=1, le=2000),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> dict:
    records = get_auth_service().list_my_activity(user_id=int(current_user["id"]), limit=limit)
    return {
        "count": len(records),
        "records": records,
    }


@app.get("/api/auth/model-performance")
def model_performance(
    limit: int = Query(500, ge=1, le=2000),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> dict:
    records = get_auth_service().model_performance_summary(user_id=int(current_user["id"]), limit=limit)
    return {
        "count": len(records),
        "records": records,
    }


@app.get("/api/info")
def info(current_user: Dict[str, Any] = Depends(get_current_user)) -> dict:
    service = get_service()
    return {
        "app_name": app.title,
        "version": app.version,
        "service": service.app_info(),
        "user": current_user,
    }


@app.get("/api/models")
def models(current_user: Dict[str, Any] = Depends(get_current_user)) -> dict:
    _ = current_user
    service = get_service()
    return {"models": service.list_models()}


@app.get("/api/history")
def history(
    limit: int = Query(50, ge=1, le=200),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> dict:
    _ = current_user
    service = get_service()
    return {
        "count": service.storage.count(),
        "records": service.history_records(limit=limit),
    }


@app.get("/api/history/export")
def export_history(
    export_format: str = Query("csv", alias="format"),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    _ = current_user
    service = get_service()
    try:
        export_path = service.export_history(export_format.lower())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return FileResponse(export_path, filename=export_path.name)


@app.get("/api/history/{record_id}")
def history_detail(
    record_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> dict:
    _ = current_user
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
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> dict:
    return await _handle_image_request(
        file=file,
        model_id=model_id,
        confidence=confidence,
        image_size=image_size,
        task_kind="image",
        current_user=current_user,
    )


@app.post("/api/predict/images-batch")
async def predict_images_batch(
    files: List[UploadFile] = File(...),
    model_id: Optional[str] = Form(None),
    confidence: Optional[float] = Form(None),
    image_size: Optional[int] = Form(None),
    current_user: Dict[str, Any] = Depends(get_current_user),
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
        result = service.process_image_batch(
            files=payloads,
            model_id=model_id,
            confidence=confidence,
            image_size=image_size,
        )
        _record_inference_activity(current_user, result)
        return result
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
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> dict:
    return await _handle_image_request(
        file=file,
        model_id=model_id,
        confidence=confidence,
        image_size=image_size,
        task_kind="camera",
        current_user=current_user,
    )


@app.post("/api/predict/video")
async def predict_video(
    file: UploadFile = File(...),
    model_id: Optional[str] = Form(None),
    confidence: Optional[float] = Form(None),
    image_size: Optional[int] = Form(None),
    current_user: Dict[str, Any] = Depends(get_current_user),
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
        _record_inference_activity(current_user, result)
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
    current_user: Dict[str, Any],
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
        _record_inference_activity(current_user, result)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Inference failed: {exc}") from exc

    return result
