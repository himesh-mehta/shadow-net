"""
Decision and Risk Engine for SHADOW-NET.
Evaluates window-level model predictions against calibrated thresholds
to classify audio as REAL, AI_SUSPECTED / DEEPFAKE, or UNCERTAIN, and assigns threat levels.

Supports multi-window temporal aggregation:
- Identifies sustained threat clusters (> K consecutive windows exceeding AI threshold)
- Speaker attribution placeholder labeling
- Explicit handling of UNTRAINED / EXPERIMENTAL model status (never faking certainty)
"""

from typing import List, Dict, Any, Tuple, Optional
from app.models.incident import PredictionType, ThreatLevel, ResponseAction

DEFAULT_REAL_THRESHOLD: float = 0.35
DEFAULT_AI_THRESHOLD: float = 0.65


class DecisionEngine:
    """
    Multi-window temporal decision and risk evaluation engine.
    """

    def __init__(
        self,
        real_threshold: float = DEFAULT_REAL_THRESHOLD,
        deepfake_threshold: float = DEFAULT_AI_THRESHOLD,
        consecutive_sustained_k: int = 2,
        default_threshold: Optional[float] = None,
    ):
        if default_threshold is not None:
            self.real_threshold = round(1.0 - default_threshold, 4)
            self.deepfake_threshold = default_threshold
        else:
            self.real_threshold = real_threshold
            self.deepfake_threshold = deepfake_threshold

        self.consecutive_sustained_k = consecutive_sustained_k

        if self.real_threshold >= self.deepfake_threshold:
            raise ValueError(
                f"real_threshold ({self.real_threshold}) must be strictly less than "
                f"deepfake_threshold ({self.deepfake_threshold})"
            )

    def evaluate_window(
        self,
        fake_probability: float,
        threshold: Optional[float] = None,
    ) -> Tuple[PredictionType, ThreatLevel, float]:
        """
        Classifies a single window based on AI/fake probability.
        """
        if threshold is not None:
            real_th = round(1.0 - threshold, 4)
            deepfake_th = threshold
        else:
            real_th = self.real_threshold
            deepfake_th = self.deepfake_threshold

        if fake_probability >= deepfake_th:
            prediction = PredictionType.AI_SUSPECTED
            confidence = round(fake_probability, 4)
            threat_level = (
                ThreatLevel.CRITICAL if fake_probability >= 0.90 else ThreatLevel.HIGH
            )

        elif fake_probability < real_th:
            prediction = PredictionType.REAL
            confidence = round(min(1.0, (real_th - fake_probability) / real_th + 0.5), 4)
            threat_level = ThreatLevel.LOW

        else:
            prediction = PredictionType.UNCERTAIN
            confidence = 0.50
            threat_level = ThreatLevel.MEDIUM

        return prediction, threat_level, confidence

    def evaluate_session(
        self,
        window_predictions: List[Dict[str, Any]],
        threshold: Optional[float] = None,
        model_status: str = "NOT_TRAINED",
    ) -> Dict[str, Any]:
        """
        Aggregates window-level inferences across an audio stream.
        Applies multi-window temporal logic:
        - Detects sustained runs of AI-suspected windows
        - Provides transparent display verdict when model is untrained
        """
        if not window_predictions:
            return {
                "prediction": PredictionType.UNCERTAIN,
                "display_verdict": "UNCERTAIN (MODEL NOT TRAINED)" if model_status == "NOT_TRAINED" else "UNCERTAIN",
                "confidence": 0.0,
                "threat_level": ThreatLevel.LOW,
                "response_action": ResponseAction.NONE,
                "average_fake_prob": 0.0,
                "max_fake_prob": 0.0,
                "deepfake_window_count": 0,
                "sustained_threat_detected": False,
                "total_windows": 0,
            }

        fake_probs = [
            w.get("ai_probability", w.get("fake_probability", 0.5))
            for w in window_predictions
        ]
        avg_fake = sum(fake_probs) / len(fake_probs)
        max_fake = max(fake_probs)

        # Multi-window temporal sustained detection:
        # Check for K consecutive windows exceeding deepfake_threshold
        deepfake_th = threshold if threshold is not None else self.deepfake_threshold
        sustained_run = 0
        sustained_threat = False
        consecutive_k = self.consecutive_sustained_k

        for p in fake_probs:
            if p >= deepfake_th:
                sustained_run += 1
                if sustained_run >= consecutive_k:
                    sustained_threat = True
            else:
                sustained_run = 0

        # Weighted aggregate: 60% max spike + 40% average
        aggregated_metric = 0.60 * max_fake + 0.40 * avg_fake
        if sustained_threat:
            # Sustained spoofing presence elevates risk metric
            aggregated_metric = max(aggregated_metric, deepfake_th)

        overall_pred, overall_threat, overall_conf = self.evaluate_window(
            aggregated_metric, threshold=threshold
        )

        deepfake_windows = sum(1 for p in fake_probs if p >= deepfake_th)

        # Untrained model safety handling:
        # If model is NOT_TRAINED, verdict must clearly be UNCERTAIN (MODEL NOT TRAINED)
        is_untrained = (model_status == "NOT_TRAINED")
        if is_untrained:
            display_verdict = "UNCERTAIN (MODEL NOT TRAINED)"
            # Keep overall_threat moderate in untrained mode
            if overall_threat in [ThreatLevel.CRITICAL, ThreatLevel.HIGH]:
                overall_threat = ThreatLevel.MEDIUM
            response_action = ResponseAction.NONE
        else:
            display_verdict = overall_pred.value
            if overall_pred in [PredictionType.AI_SUSPECTED, PredictionType.DEEPFAKE]:
                response_action = (
                    ResponseAction.RESTRICT_SESSION
                    if overall_threat == ThreatLevel.CRITICAL
                    else ResponseAction.ALERT
                )
            elif overall_pred == PredictionType.UNCERTAIN:
                response_action = ResponseAction.ALERT
            else:
                response_action = ResponseAction.NONE

        return {
            "prediction": PredictionType.UNCERTAIN if is_untrained else overall_pred,
            "raw_prediction": overall_pred,
            "display_verdict": display_verdict,
            "confidence": round(overall_conf, 4),
            "threat_level": overall_threat,
            "response_action": response_action,
            "average_fake_prob": round(avg_fake, 4),
            "ai_probability": round(avg_fake, 4),
            "real_probability": round(1.0 - avg_fake, 4),
            "max_fake_prob": round(max_fake, 4),
            "deepfake_window_count": deepfake_windows,
            "sustained_threat_detected": sustained_threat,
            "total_windows": len(window_predictions),
            "model_status": model_status,
        }


default_decision_engine = DecisionEngine()
