"""
SHADOW-NET Evaluation API Router (Phase 3)
=========================================
Endpoints for triggering test-bench evaluation runs and retrieving
the latest validation metrics report.
"""

import json
import logging
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, status, Depends
from starlette.concurrency import run_in_threadpool
from app.db import get_db
from app.config import get_settings
from app.ml.factory import get_detector

from app.ml.evaluator import run_evaluation

logger = logging.getLogger("shadow_net.evaluation_api")

router = APIRouter(prefix="/evaluation", tags=["Evaluation"])

REPORT_PATH = Path(__file__).resolve().parent.parent.parent.parent / "scripts" / "evaluation_report.json"
DEFAULT_AUDIO_DIR = Path(__file__).resolve().parent.parent.parent.parent / "datasets" / "sample"


class EvaluationRunRequest(BaseModel):
    audio_dir: Optional[str] = Field(
        default=None,
        description="Path to dataset directory. Defaults to sample audio directory.",
    )
    real_threshold: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Optional override for REAL threshold.",
    )
    deepfake_threshold: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Optional override for DEEPFAKE threshold.",
    )


@router.get("/latest")
async def get_latest_evaluation_report():
    """
    Retrieve the most recent evaluation report.
    If no report file exists yet, runs an evaluation automatically.
    """
    if REPORT_PATH.is_file():
        try:
            with open(REPORT_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning("Could not read existing evaluation report: %s", e)

    raise HTTPException(status_code=404, detail="No evaluation report yet. Run an evaluation explicitly.")


@router.post("/run")
async def execute_evaluation(req: EvaluationRunRequest = EvaluationRunRequest(), db=Depends(get_db)):
    """
    Trigger a model evaluation across the specified or sample audio dataset.
    Computes aggregate metrics, confusion matrix, per-file verdicts,
    and updates the persistent evaluation report.
    """
    target_dir = Path(req.audio_dir) if req.audio_dir else DEFAULT_AUDIO_DIR

    if not target_dir.exists() or not target_dir.is_dir():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Audio directory does not exist: {target_dir}",
        )

    try:
        doc = await db.settings.find_one({"scope": "global"}) if db is not None else None
        demo = doc.get("demo_mode", get_settings().DEMO_MODE) if doc else get_settings().DEMO_MODE
        detector = await run_in_threadpool(get_detector, demo_mode=demo)
        report = await run_in_threadpool(run_evaluation,
            detector=detector,
            audio_dir=target_dir,
            real_threshold=req.real_threshold,
            deepfake_threshold=req.deepfake_threshold,
        )
        # Persist report to file
        REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(REPORT_PATH, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)

        return report
    except Exception as e:
        logger.error("Evaluation run failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Evaluation failed: {str(e)}",
        )
