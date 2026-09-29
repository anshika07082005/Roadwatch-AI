from app.services.risk_engine import MotionState, classify_pair_risk

def test_close_converging_objects_have_nonzero_risk():
    a = MotionState(1, "car", (100, 100), (5, 0))
    b = MotionState(2, "car", (150, 100), (-5, 0))
    result = classify_pair_risk(a, b, 1280, 720)
    assert result["risk_score"] > 0
    assert result["risk_level"] in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
