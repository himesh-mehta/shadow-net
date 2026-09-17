"""
Decision and Risk Engine for SHADOW-NET.
Evaluates window-level model predictions against configurable thresholds
to classify audio as REAL, DEEPFAKE, or UNCERTAIN, and assigns threat levels.
"""

from typing import List, Dict, Any, Tuple
from app.models.incident import PredictionType, ThreatLevel, ResponseAction


class DecisionEngine:
    """
    Evaluates classifier outputs and applies threshold-based risk policies.
    Provides three-state classification: REAL, DEEPFAKE, or UNCERTAIN.
    """

    def __init__(self, default_threshold: float = 0.75):
        self.default_threshold = default_threshold

    def evaluate_window(
        self,
        fake_probability: float,
        threshold: float = None,
    ) -> Tuple[PredictionType, ThreatLevel, float]:
        """
        Classifies a single window based on fake probability and threshold.

        Rules:
        - fake_probability >= threshold -> DEEPFAKE
        - fake_probability <= (1.0 - threshold) -> REAL
        - Otherwise -> UNCERTAIN
        """
        th = threshold if threshold is not None else self.default_threshold
        lower_bound = round(1.0 - th, 4)

        if fake_probability >= th:
            prediction = PredictionType.DEEPFAKE
            confidence = fake_probability
            threat_level = ThreatLevel.CRITICAL if fake_probability >= 0.90 else ThreatLevel.HIGH
        elif fake_probability <= lower_bound:
            prediction = PredictionType.REAL
            confidence = round(1.0 - fake_probability, 4)
            threat_level = ThreatLevel.LOW
        else:
            prediction = PredictionType.UNCERTAIN
            # Uncertainty confidence measures distance from ambiguity (0.5)
            confidence = round(1.0 - abs(fake_probability - 0.5) * 2.0, 4)
            threat_level = ThreatLevel.MEDIUM

        return prediction, threat_level, confidence

    def evaluate_session(
        self,
        window_predictions: List[Dict[str, Any]],
        threshold: float = None,
    ) -> Dict[str, Any]:
        """
        Aggregates window-level inferences across an audio stream to derive
        an overall session-level risk verdict.
        """
        if not window_predictions:
            return {
                "prediction": PredictionType.UNCERTAIN,
                "confidence": 0.0,
                "threat_level": ThreatLevel.LOW,
                "response_action": ResponseAction.NONE,
                "average_fake_prob": 0.0,
                "max_fake_prob": 0.0,
                "deepfake_window_count": 0,
                "total_windows": 0,
            }

        fake_probs = [w["fake_probability"] for w in window_predictions]
        avg_fake = float(np.mean(fake_probs)) if "np" in globals() else sum(fake_probs) / len(fake_probs)
        max_fake = max(fake_probs)

        # Use combined metric: 60% max spike + 40% average to catch intermittent deepfake segments
        aggregated_metric = 0.60 * max_fake + 0.40 * avg_fake

        overall_pred, overall_threat, overall_conf = self.evaluate_window(
            aggregated_metric, threshold=threshold
        )

        # Determine automated mitigation response action
        if overall_pred == PredictionType.DEEPFAKE:
            response_action = (
                ResponseAction.RESTRICT_SESSION
                if overall_threat == ThreatLevel.CRITICAL
                else ResponseAction.ALERT
            )
        elif overall_pred == PredictionType.UNCERTAIN:
            response_action = ResponseAction.ALERT
        else:
            response_action = ResponseAction.NONE

        deepfake_windows = sum(
            1 for w in window_predictions if w["fake_probability"] >= (threshold or self.default_threshold)
        )

        return {
            "prediction": overall_pred,
            "confidence": round(overall_conf, 4),
            "threat_level": overall_threat,
            "response_action": response_action,
            "average_fake_prob": round(avg_fake, 4),
            "max_fake_prob": round(max_fake, 4),
            "deepfake_window_count": deepfake_windows,
            "total_windows": len(window_predictions),
        }


default_decision_engine = DecisionEngine()
