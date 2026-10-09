import os
import io
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.ai_vision import evaluate_held_out_dataset
import numpy as np
import cv2

client = TestClient(app)

# =========================================================================
# A. Dashboard & Navigation Endpoints
# =========================================================================

def test_ui_01_dashboard_summary():
    """UI-01 & UI-05: Open dashboard -> loads without errors, returns farm summary."""
    response = client.get("/api/reports/dashboard-summary")
    assert response.status_code == 200
    data = response.json()
    assert "active_ponds_count" in data
    assert data["active_ponds_count"] >= 6
    assert data["demo_mode"] is True

def test_ui_06_reset_demo_data():
    """UI-06: Reset demo data restores initial values."""
    res = client.post("/api/reset-demo-data")
    assert res.status_code == 200
    assert res.json()["status"] == "success"

def test_health_and_readiness():
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json()["status"] == "healthy"

    res_ready = client.get("/api/ready")
    assert res_ready.status_code == 200
    assert res_ready.json()["status"] == "ready"


# =========================================================================
# B. Pond Management Tests (POND-01 to POND-14)
# =========================================================================

def test_pond_01_add_valid_pond():
    """POND-01: Add a pond with valid details."""
    payload = {
        "name": "Pond Test Gamma (G-01)",
        "species": "Nile Tilapia",
        "fish_count": 5000,
        "avg_weight_g": 90.0,
        "feeding_rate_pct": 2.5,
        "feed_price_per_kg": 65.0,
        "shape": "rectangular",
        "length_m": 20.0,
        "width_m": 10.0,
        "depth_m": 1.5
    }
    res = client.post("/api/ponds", json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["name"] == payload["name"]
    assert data["biomass_kg"] == 450.0  # 5000 * 90 / 1000
    assert data["daily_feed_kg"] == 11.25 # 450 * 0.025
    assert data["volume_m3"] == 300.0  # 20 * 10 * 1.5

def test_pond_02_name_missing():
    """POND-02: Submit with pond name missing -> validation message appears."""
    res = client.post("/api/ponds", json={
        "name": "",
        "fish_count": 1000,
        "avg_weight_g": 50.0,
        "feeding_rate_pct": 2.0,
        "feed_price_per_kg": 50.0,
        "depth_m": 1.0
    })
    assert res.status_code == 422

def test_pond_03_zero_fish_count():
    """POND-03: Enter fish count as zero -> accepted; calculations remain zero."""
    res = client.post("/api/ponds", json={
        "name": "Empty Test Pond Z",
        "fish_count": 0,
        "avg_weight_g": 0.0,
        "feeding_rate_pct": 2.0,
        "feed_price_per_kg": 50.0,
        "depth_m": 1.0,
        "shape": "rectangular",
        "length_m": 10.0,
        "width_m": 5.0
    })
    assert res.status_code == 201
    assert res.json()["biomass_kg"] == 0.0
    assert res.json()["daily_feed_kg"] == 0.0

def test_pond_04_negative_fish_count():
    """POND-04: Enter negative fish count -> Rejected."""
    res = client.post("/api/ponds", json={
        "name": "Pond Neg Count",
        "fish_count": -50,
        "avg_weight_g": 50.0,
        "feeding_rate_pct": 2.0,
        "feed_price_per_kg": 50.0,
        "depth_m": 1.0
    })
    assert res.status_code == 422

def test_pond_05_decimal_fish_count():
    """POND-05: Enter decimal fish count -> Rejected."""
    res = client.post("/api/ponds", json={
        "name": "Pond Decimal Count",
        "fish_count": 50.5,
        "avg_weight_g": 50.0,
        "feeding_rate_pct": 2.0,
        "feed_price_per_kg": 50.0,
        "depth_m": 1.0
    })
    assert res.status_code == 422

def test_pond_06_negative_avg_weight():
    """POND-06: Enter negative average weight -> Rejected."""
    res = client.post("/api/ponds", json={
        "name": "Pond Neg Weight",
        "fish_count": 100,
        "avg_weight_g": -5.0,
        "feeding_rate_pct": 2.0,
        "feed_price_per_kg": 50.0,
        "depth_m": 1.0
    })
    assert res.status_code == 422

def test_pond_07_negative_feed_price():
    """POND-07: Enter negative feed price -> Rejected."""
    res = client.post("/api/ponds", json={
        "name": "Pond Neg Price",
        "fish_count": 100,
        "avg_weight_g": 50.0,
        "feeding_rate_pct": 2.0,
        "feed_price_per_kg": -10.0,
        "depth_m": 1.0
    })
    assert res.status_code == 422

def test_pond_08_text_in_numeric_fields():
    """POND-08: Enter text in numeric fields -> Rejected with 422."""
    res = client.post("/api/ponds", json={
        "name": "Pond Text Numeric",
        "fish_count": "invalid_count",
        "avg_weight_g": 50.0,
        "feeding_rate_pct": 2.0,
        "feed_price_per_kg": 50.0,
        "depth_m": 1.0
    })
    assert res.status_code == 422

def test_pond_09_very_large_values():
    """POND-09: Enter extremely large values -> Safe limits enforced."""
    res = client.post("/api/ponds", json={
        "name": "Pond Huge Value",
        "fish_count": 9999999999999,
        "avg_weight_g": 50.0,
        "feeding_rate_pct": 2.0,
        "feed_price_per_kg": 50.0,
        "depth_m": 1.0
    })
    assert res.status_code == 422

def test_pond_10_duplicate_pond_name():
    """POND-10: Add two ponds with the same name -> Rejected with 409 Conflict."""
    name = "Unique Basin Delta 9"
    res1 = client.post("/api/ponds", json={
        "name": name,
        "fish_count": 100,
        "avg_weight_g": 50.0,
        "feeding_rate_pct": 2.0,
        "feed_price_per_kg": 50.0,
        "depth_m": 1.0,
        "shape": "rectangular",
        "length_m": 5.0,
        "width_m": 5.0
    })
    assert res1.status_code == 201

    res2 = client.post("/api/ponds", json={
        "name": name,
        "fish_count": 200,
        "avg_weight_g": 60.0,
        "feeding_rate_pct": 2.0,
        "feed_price_per_kg": 50.0,
        "depth_m": 1.0,
        "shape": "rectangular",
        "length_m": 5.0,
        "width_m": 5.0
    })
    assert res2.status_code == 409

def test_pond_11_edit_pond():
    """POND-11: Edit a pond -> Updated values appear."""
    # List ponds to get one
    ponds = client.get("/api/ponds").json()
    first_id = ponds[0]["id"]
    res = client.put(f"/api/ponds/{first_id}", json={
        "fish_count": 15000,
        "avg_weight_g": 85.0
    })
    assert res.status_code == 200
    assert res.json()["fish_count"] == 15000
    assert res.json()["avg_weight_g"] == 85.0
    assert res.json()["biomass_kg"] == 1275.0  # 15000 * 85 / 1000

def test_pond_12_delete_pond():
    """POND-12: Delete a pond."""
    # Create pond then delete
    res = client.post("/api/ponds", json={
        "name": "Temporary Delete Pond",
        "fish_count": 100,
        "avg_weight_g": 20.0,
        "feeding_rate_pct": 2.0,
        "feed_price_per_kg": 50.0,
        "depth_m": 1.0,
        "shape": "rectangular",
        "length_m": 5.0,
        "width_m": 5.0
    })
    pid = res.json()["id"]
    del_res = client.delete(f"/api/ponds/{pid}")
    assert del_res.status_code == 204

    # Verify deleted
    get_res = client.get(f"/api/ponds/{pid}")
    assert get_res.status_code == 404

def test_pond_13_search_and_filter():
    """POND-13: Search and filter ponds."""
    res = client.get("/api/ponds?search=Tilapia")
    assert res.status_code == 200
    for p in res.json():
        assert "tilapia" in p["species"].lower() or "tilapia" in p["name"].lower()


# =========================================================================
# F. Water-Quality Tests (WQ-01 to WQ-14)
# =========================================================================

def test_wq_01_and_02_valid_readings():
    """WQ-01 & WQ-02: Enter valid temperature and pH."""
    res = client.post("/api/sensors/readings", json={
        "pond_id": "pond-01",
        "temperature_c": 28.5,
        "ph": 7.4,
        "dissolved_oxygen_mg_l": 6.8,
        "source": "live"
    })
    assert res.status_code == 201
    d = res.json()
    assert d["temperature_c"] == 28.5
    assert d["ph"] == 7.4
    assert d["status"] == "optimal"

def test_wq_04_impossible_numeric_value():
    """WQ-04: Enter impossible numeric value (e.g., pH 18.0) -> Rejected."""
    res = client.post("/api/sensors/readings", json={
        "pond_id": "pond-01",
        "ph": 18.0
    })
    assert res.status_code == 422

def test_wq_08_and_09_alert_trigger_and_recovery():
    """WQ-08 & WQ-09: Low DO triggers critical alert, normal DO recovers."""
    # Critical low DO trigger
    res = client.post("/api/sensors/readings", json={
        "pond_id": "pond-01",
        "dissolved_oxygen_mg_l": 2.5
    })
    assert res.status_code == 201
    assert res.json()["status"] == "critical"

    # Verify alert was created
    alerts = client.get("/api/alerts?pond_id=pond-01&unresolved_only=true").json()
    assert any(a["parameter"] == "Dissolved Oxygen" for a in alerts)

    # Recovery reading
    res_rec = client.post("/api/sensors/readings", json={
        "pond_id": "pond-01",
        "dissolved_oxygen_mg_l": 7.2,
        "ph": 7.5,
        "temperature_c": 27.0
    })
    assert res_rec.status_code == 201
    assert res_rec.json()["status"] == "optimal"

def test_wq_12_sensor_calibration():
    """WQ-12: Compare sensor with reference instrument and apply calibration offset."""
    res = client.post("/api/sensors/calibrate", json={
        "sensor_type": "ph",
        "reference_value": 7.00,
        "measured_raw_value": 7.15,
        "notes": "NIST standard 7.00 buffer test"
    })
    assert res.status_code == 200
    d = res.json()
    assert d["offset_applied"] == -0.15
    assert d["calibrated_value"] == 7.00


# =========================================================================
# E. Fish Counting AI Tests (AI-01 to AI-14)
# =========================================================================

def test_ai_01_and_07_valid_fish_image_analysis():
    """AI-01 & AI-07: Upload valid fish image -> Returns detected count and annotation."""
    # Create synthetic test image with 3 simulated fish blobs
    img = np.zeros((300, 400, 3), dtype=np.uint8)
    img[:] = (120, 80, 20)  # dark blue-green water background
    # Draw 3 bright fish shapes
    cv2.ellipse(img, (100, 100), (35, 12), 30, 0, 360, (230, 240, 240), -1)
    cv2.ellipse(img, (250, 150), (40, 14), -20, 0, 360, (220, 235, 235), -1)
    cv2.ellipse(img, (180, 240), (30, 10), 10, 0, 360, (240, 245, 245), -1)

    _, buf = cv2.imencode(".jpg", img)
    file_bytes = io.BytesIO(buf.tobytes())

    res = client.post(
        "/api/ai/detect",
        files={"file": ("pond_sample.jpg", file_bytes, "image/jpeg")},
        data={"pond_id": "pond-01"}
    )
    assert res.status_code == 200
    d = res.json()
    assert d["detected_count"] >= 3
    assert len(d["bounding_boxes"]) >= 3
    assert "annotated_url" in d
    assert "disclaimer" in d

def test_ai_02_unsupported_file_type():
    """AI-02: Upload unsupported file type -> 415 rejection."""
    fake_txt = io.BytesIO(b"hello world this is text")
    res = client.post(
        "/api/ai/detect",
        files={"file": ("readme.txt", fake_txt, "text/plain")}
    )
    assert res.status_code == 415

def test_ai_04_corrupt_image():
    """AI-04: Upload corrupt image -> error shown safely."""
    corrupt = io.BytesIO(b"GIF89a\x00\x00\x00\x00NOT_A_VALID_IMAGE_DATA")
    res = client.post(
        "/api/ai/detect",
        files={"file": ("corrupt.jpg", corrupt, "image/jpeg")}
    )
    assert res.status_code in [400, 422]

def test_ai_09_manual_count_correction():
    """AI-09: User manual correction -> saved as confirmed count."""
    # First analyze an image
    img = np.zeros((200, 200, 3), dtype=np.uint8)
    cv2.ellipse(img, (100, 100), (30, 10), 0, 0, 360, (255, 255, 255), -1)
    _, buf = cv2.imencode(".jpg", img)
    upload_res = client.post(
        "/api/ai/detect",
        files={"file": ("test.jpg", io.BytesIO(buf.tobytes()), "image/jpeg")},
        data={"pond_id": "pond-01"}
    )
    det_id = upload_res.json()["id"]

    # Now confirm with manual override
    confirm_res = client.post(
        f"/api/ai/confirm/{det_id}",
        json={"confirmed_count": 12, "apply_to_pond_id": "pond-01"}
    )
    assert confirm_res.status_code == 200
    assert confirm_res.json()["confirmed_count"] == 12
    assert confirm_res.json()["status"] == "confirmed"

def test_ai_11_held_out_evaluation():
    """AI-11: Held-out dataset precision, recall, and counting error."""
    metrics = evaluate_held_out_dataset()
    assert "precision" in metrics
    assert "recall" in metrics
    assert "mean_absolute_error_mae" in metrics
    assert metrics["precision"] > 0.8
    assert metrics["recall"] > 0.8


# =========================================================================
# G. Reports, Trends and CSV Tests (REP-01 to REP-09)
# =========================================================================

def test_rep_01_and_02_feeding_trends():
    """REP-01 & REP-02: Open feeding trends chart."""
    res = client.get("/api/reports/feeding-trends?days=14")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert "biomass_kg" in data[0]
    assert "daily_feed_kg" in data[0]

def test_rep_07_and_08_csv_export():
    """REP-07 & REP-08: Export CSV with RFC-4180 escaping."""
    res = client.get("/api/reports/export-feeding-csv")
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("text/csv")
    csv_text = res.text
    assert "Record ID" in csv_text
    assert "Total Biomass (kg)" in csv_text
    assert "Daily Feed Cost (INR)" in csv_text
