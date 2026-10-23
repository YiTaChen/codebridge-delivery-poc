"""Loopback-only local proof of concept; never expose the Codex route publicly."""

import asyncio
from io import BytesIO
import os
from pathlib import Path
import shutil
import time
from typing import Annotated, Literal

import fitz
import httpx
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image, UnidentifiedImageError
from pydantic import ValidationError

from .providers import call_codex, call_openai, inference_cost
from .reconcile import reconcile, validate_sources

app = FastAPI(title="ParcelProof", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
                   allow_methods=["GET", "POST"], allow_headers=["Content-Type"])
MAX_FILE_BYTES = 10 * 1024 * 1024
ANALYSIS_LOCK = asyncio.Lock()


@app.middleware("http")
async def local_only(request: Request, call_next):
    """A local authenticated CLI must never become a remotely callable service."""
    if request.url.path.startswith("/api/"):
        if request.url.hostname not in {"localhost", "127.0.0.1", "::1"}:
            return JSONResponse(status_code=403, content={"detail": "Use this PoC on localhost only."})
        if request.client and request.client.host not in {"127.0.0.1", "::1", "testclient"}:
            return JSONResponse(status_code=403, content={"detail": "Only local requests are supported."})
        origin = request.headers.get("origin")
        if origin and origin not in {"http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:8000", "http://127.0.0.1:8000"}:
            return JSONResponse(status_code=403, content={"detail": "This origin is not allowed to invoke local analysis."})
        try:
            if int(request.headers.get("content-length", "0")) > 40 * 1024 * 1024:
                return JSONResponse(status_code=413, content={"detail": "Upload is too large."})
        except ValueError:
            return JSONResponse(status_code=400, content={"detail": "Invalid request size."})
    return await call_next(request)


def extract_pdf(data: bytes) -> list[dict]:
    if not data.startswith(b"%PDF-"):
        raise ValueError("The packing list must be a valid PDF.")
    try:
        with fitz.open(stream=data, filetype="pdf") as document:
            if document.is_encrypted:
                raise ValueError("Password-protected PDFs are unsupported.")
            if len(document) != 1:
                raise ValueError("Use exactly one PDF page.")
            page = document[0]
            # Group words sharing the same visual text row, preserving table references.
            words = page.get_text("words", sort=True)
            grouped = []
            for word in words:
                baseline = (word[1] + word[3]) / 2
                row = next((r for r in grouped if abs(r["y"] - baseline) < 3), None)
                if row is None:
                    row = {"y": baseline, "words": []}
                    grouped.append(row)
                row["words"].append(word)
            raw = [" ".join(w[4] for w in sorted(r["words"], key=lambda x: x[0])) for r in sorted(grouped, key=lambda r: r["y"])]
    except ValueError:
        raise
    except Exception:
        raise ValueError("The PDF could not be opened. Upload a valid, unencrypted text PDF.") from None
    if not raw or sum(len(line) for line in raw) < 10:
        raise ValueError("No usable PDF text was found. Scanned/image PDFs need OCR and are unsupported.")
    if len(raw) > 200 or sum(map(len, raw)) > 20000:
        raise ValueError("PDF text is too large for this limited PoC.")
    return [{"line": index + 1, "text": text} for index, text in enumerate(raw)]


def validate_photo(data: bytes, content_type: str) -> dict:
    if content_type not in {"image/jpeg", "image/png", "image/webp"}:
        raise ValueError("Photos must be JPEG, PNG, or WebP.")
    try:
        with Image.open(BytesIO(data)) as image:
            if image.format not in {"JPEG", "PNG", "WEBP"}:
                raise ValueError("Photo bytes do not contain a supported image.")
            if image.width * image.height > 20_000_000:
                raise ValueError("Photos must be at most 20 megapixels.")
            image.verify()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
        raise ValueError("Photo data is invalid or too large.") from None
    return {"data": data, "mime": content_type}


async def read_limited(file: UploadFile) -> bytes:
    data = await file.read(MAX_FILE_BYTES + 1)
    await file.close()
    if not data or len(data) > MAX_FILE_BYTES:
        raise ValueError("Each file must contain data and be at most 10 MiB.")
    return data


@app.get("/api/health")
async def health():
    executable = os.environ.get("CODEX_BIN") or shutil.which("codex")
    authenticated = False
    if executable:
        try:
            process = await asyncio.create_subprocess_exec(executable, "login", "status", stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
            await asyncio.wait_for(process.wait(), 5)
            authenticated = process.returncode == 0
        except (OSError, asyncio.TimeoutError):
            pass
    return {"status": "ok", "codex_available": bool(executable), "codex_authenticated": authenticated, "default_provider": "codex"}


@app.post("/api/analyze")
async def analyze(
    packing_list: Annotated[UploadFile, File()],
    photos: Annotated[list[UploadFile], File()],
    provider: Annotated[Literal["codex", "openai"], Form()] = "codex",
    api_key: Annotated[str, Form()] = "",
):
    started = time.perf_counter()
    if not 1 <= len(photos) <= 3:
        raise HTTPException(400, "Upload between one and three photos.")
    if packing_list.content_type != "application/pdf":
        raise HTTPException(400, "The packing list must be a PDF.")
    if provider == "openai" and (not api_key.strip() or len(api_key) > 300):
        raise HTTPException(400, "Enter a valid OpenAI API key in the masked field.")
    try:
        pdf_lines = extract_pdf(await read_limited(packing_list))
        validated_photos = []
        for index, file in enumerate(photos):
            content_type = file.content_type
            validated_photos.append({**validate_photo(await read_limited(file), content_type), "photo_id": f"photo_{index + 1}"})
    except ValueError as error:
        raise HTTPException(400, str(error)) from None
    if ANALYSIS_LOCK.locked():
        raise HTTPException(409, "An analysis is already running. Wait for it to finish before retrying.")
    async with ANALYSIS_LOCK:
        try:
            if provider == "codex":
                reading, usage, model = await call_codex(pdf_lines, validated_photos)
            else:
                reading, usage, model = await call_openai(pdf_lines, validated_photos, api_key.strip())
            validate_sources(reading, pdf_lines, {p["photo_id"] for p in validated_photos})
            result = reconcile(reading)
        except (ValidationError, ValueError):
            raise HTTPException(502, "The model returned invalid structured data or unsupported source references. No conclusion was accepted. Try clearer labels or a simpler one-page packing list.") from None
        except RuntimeError as error:
            raise HTTPException(502, str(error)) from None
        except httpx.TimeoutException:
            raise HTTPException(504, "The model request timed out. No conclusion was accepted.") from None
        except Exception:
            raise HTTPException(502, "Analysis could not complete. Check your selected provider and try again. No credentials are included in this error.") from None
    result["pdf_lines"] = pdf_lines
    result["metrics"] = {"elapsed_seconds": round(time.perf_counter() - started, 3), "elapsed_measured": True,
                         "provider": provider, "model": model, "usage": usage, "cost": inference_cost(provider, usage)}
    result["warnings"].append("Evidence regions are model descriptions, not independently verified bounding boxes. Synthetic samples are not real-world accuracy validation.")
    return result


# Public sample assets and recorded results contain no account credentials.
repo_root = Path(__file__).resolve().parents[1]
if (repo_root / "sample-data").exists():
    app.mount("/sample-data", StaticFiles(directory=repo_root / "sample-data"), name="samples")
if (repo_root / "frontend" / "dist").exists():
    app.mount("/", StaticFiles(directory=repo_root / "frontend" / "dist", html=True), name="frontend")
