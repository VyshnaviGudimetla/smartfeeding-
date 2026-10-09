import pytest
import math
from app.services.calculator import (
    calculate_feeding,
    calculate_pond_volume,
    FeedingCalculationInput,
    PondVolumeInput,
)

# =========================================================================
# C. Biomass, Feed, and Cost Calculation Tests (CALC-01 to CALC-16)
# =========================================================================

def test_calc_01_standard_case():
    """CALC-01: 12,000 fish, 80 g, 2.5%, ₹68/kg -> 960 kg biomass; 24 kg feed/day; ₹1,632/day; ₹48,960/30 days."""
    res = calculate_feeding({
        "fish_count": 12000,
        "avg_weight_g": 80,
        "feeding_rate_pct": 2.5,
        "feed_price_per_kg": 68
    })
    assert res.biomass_kg == pytest.approx(960.0, rel=1e-5)
    assert res.daily_feed_kg == pytest.approx(24.0, rel=1e-5)
    assert res.daily_cost == pytest.approx(1632.0, rel=1e-5)
    assert res.cost_30_days == pytest.approx(48960.0, rel=1e-5)

def test_calc_02_micro_quantities():
    """CALC-02: 1 fish, 1 g, 1%, ₹1/kg -> 0.001 kg biomass; 0.00001 kg feed/day before display rounding."""
    res = calculate_feeding({
        "fish_count": 1,
        "avg_weight_g": 1.0,
        "feeding_rate_pct": 1.0,
        "feed_price_per_kg": 1.0
    })
    assert res.biomass_kg == pytest.approx(0.001, rel=1e-6)
    assert res.daily_feed_kg == pytest.approx(0.00001, rel=1e-6)
    assert res.daily_cost == pytest.approx(0.00001, rel=1e-6)

def test_calc_03_zero_fish_count():
    """CALC-03: Fish count = 0 -> Biomass, feed, and cost are zero."""
    res = calculate_feeding({
        "fish_count": 0,
        "avg_weight_g": 80,
        "feeding_rate_pct": 2.5,
        "feed_price_per_kg": 68
    })
    assert res.biomass_kg == 0.0
    assert res.daily_feed_kg == 0.0
    assert res.daily_cost == 0.0
    assert res.cost_30_days == 0.0
    assert any("Fish count is 0" in w for w in res.warnings)

def test_calc_04_zero_average_weight():
    """CALC-04: Average weight = 0 -> Zero biomass and feed; flag unrealistic production inputs if needed."""
    res = calculate_feeding({
        "fish_count": 1000,
        "avg_weight_g": 0.0,
        "feeding_rate_pct": 2.5,
        "feed_price_per_kg": 68
    })
    assert res.biomass_kg == 0.0
    assert res.daily_feed_kg == 0.0
    assert res.daily_cost == 0.0
    assert any("Average fish weight is 0g" in w for w in res.warnings)

def test_calc_05_zero_feeding_rate():
    """CALC-05: Feeding rate = 0% -> Estimated feed and cost are zero."""
    res = calculate_feeding({
        "fish_count": 1000,
        "avg_weight_g": 100.0,
        "feeding_rate_pct": 0.0,
        "feed_price_per_kg": 68
    })
    assert res.biomass_kg == 100.0
    assert res.daily_feed_kg == 0.0
    assert res.daily_cost == 0.0

def test_calc_06_negative_feeding_rate():
    """CALC-06: Negative feeding rate -> Rejected."""
    with pytest.raises(ValueError):
        calculate_feeding({
            "fish_count": 1000,
            "avg_weight_g": 100.0,
            "feeding_rate_pct": -2.5,
            "feed_price_per_kg": 68
        })

def test_calc_07_rate_above_configured_maximum():
    """CALC-07: Feeding rate above configured maximum -> Rejected."""
    with pytest.raises(ValueError, match="maximum biological threshold"):
        calculate_feeding({
            "fish_count": 1000,
            "avg_weight_g": 100.0,
            "feeding_rate_pct": 25.0,  # exceeds 15% max
            "feed_price_per_kg": 68
        })

def test_calc_08_feed_price_zero():
    """CALC-08: Feed price = ₹0 -> Zero cost; warning if a zero price is unrealistic."""
    res = calculate_feeding({
        "fish_count": 1000,
        "avg_weight_g": 100.0,
        "feeding_rate_pct": 2.0,
        "feed_price_per_kg": 0.0
    })
    assert res.biomass_kg == 100.0
    assert res.daily_feed_kg == 2.0
    assert res.daily_cost == 0.0
    assert any("Feed price is ₹0/kg" in w for w in res.warnings)

def test_calc_09_missing_required_input():
    """CALC-09: Missing required input -> Validation error."""
    with pytest.raises(ValueError):
        calculate_feeding({
            "fish_count": 1000,
            "avg_weight_g": 100.0
            # missing feeding_rate_pct and feed_price_per_kg
        })

def test_calc_10_change_fish_count_live():
    """CALC-10: Change fish count live -> Biomass, feed, and cost update immediately."""
    res1 = calculate_feeding({"fish_count": 1000, "avg_weight_g": 100, "feeding_rate_pct": 2.0, "feed_price_per_kg": 50})
    res2 = calculate_feeding({"fish_count": 2000, "avg_weight_g": 100, "feeding_rate_pct": 2.0, "feed_price_per_kg": 50})
    assert res2.biomass_kg == res1.biomass_kg * 2
    assert res2.daily_feed_kg == res1.daily_feed_kg * 2
    assert res2.daily_cost == res1.daily_cost * 2

def test_calc_11_change_feeding_rate_live():
    """CALC-11: Change feeding rate live -> Feed and costs update immediately."""
    res1 = calculate_feeding({"fish_count": 1000, "avg_weight_g": 100, "feeding_rate_pct": 2.0, "feed_price_per_kg": 50})
    res2 = calculate_feeding({"fish_count": 1000, "avg_weight_g": 100, "feeding_rate_pct": 4.0, "feed_price_per_kg": 50})
    assert res2.biomass_kg == res1.biomass_kg
    assert res2.daily_feed_kg == res1.daily_feed_kg * 2
    assert res2.daily_cost == res1.daily_cost * 2

def test_calc_12_change_feed_price_live():
    """CALC-12: Change feed price live -> Cost changes while biomass and feed stay unchanged."""
    res1 = calculate_feeding({"fish_count": 1000, "avg_weight_g": 100, "feeding_rate_pct": 2.0, "feed_price_per_kg": 50})
    res2 = calculate_feeding({"fish_count": 1000, "avg_weight_g": 100, "feeding_rate_pct": 2.0, "feed_price_per_kg": 75})
    assert res2.biomass_kg == res1.biomass_kg
    assert res2.daily_feed_kg == res1.daily_feed_kg
    assert res2.daily_cost == res1.daily_cost * 1.5

def test_calc_13_decimal_weight_and_price_precision():
    """CALC-13: Use decimal average weight and price -> Correct precision is maintained."""
    res = calculate_feeding({
        "fish_count": 2500,
        "avg_weight_g": 45.67,
        "feeding_rate_pct": 2.34,
        "feed_price_per_kg": 65.43
    })
    expected_biomass = (2500 * 45.67) / 1000.0
    expected_feed = (expected_biomass * 2.34) / 100.0
    expected_cost = expected_feed * 65.43
    assert res.biomass_kg == pytest.approx(expected_biomass, rel=1e-9)
    assert res.daily_feed_kg == pytest.approx(expected_feed, rel=1e-9)
    assert res.daily_cost == pytest.approx(expected_cost, rel=1e-9)

def test_calc_14_saved_estimate_restoration():
    """CALC-14: Refresh or reopen saved estimate -> Values are restored correctly."""
    data = {"fish_count": 5000, "avg_weight_g": 120.0, "feeding_rate_pct": 3.0, "feed_price_per_kg": 60.0}
    res1 = calculate_feeding(data)
    d = res1.model_dump()
    res2 = FeedingCalculationInput(**d)
    assert res2.fish_count == data["fish_count"]

def test_calc_15_independent_verification():
    """CALC-15: Compare UI result with independent calculation within rounding tolerance."""
    res = calculate_feeding({"fish_count": 8500, "avg_weight_g": 142.5, "feeding_rate_pct": 2.1, "feed_price_per_kg": 72.0})
    hand_biomass = 8500 * 142.5 / 1000.0  # 1211.25 kg
    hand_feed = 1211.25 * 0.021           # 25.43625 kg
    hand_cost = 25.43625 * 72.0           # 1831.41
    assert abs(res.biomass_kg - hand_biomass) < 1e-4
    assert abs(res.daily_feed_kg - hand_feed) < 1e-4
    assert abs(res.daily_cost - hand_cost) < 1e-4

def test_calc_16_estimate_identification():
    """CALC-16: Change feeding rate -> Output updates; user-selected rate remains clearly identified as an estimate."""
    res = calculate_feeding({"fish_count": 1000, "avg_weight_g": 50, "feeding_rate_pct": 3.0, "feed_price_per_kg": 50})
    assert res.is_user_selected_estimate is True
    assert "estimate" in res.disclaimer.lower()


# =========================================================================
# D. Pond Water-Volume Tests (VOL-01 to VOL-10)
# =========================================================================

def test_vol_01_rectangular():
    """VOL-01: Rectangular pond: 10 m × 5 m × 2 m -> 100 m³, or 100,000 litres."""
    res = calculate_pond_volume({"shape": "rectangular", "length_m": 10, "width_m": 5, "depth_m": 2})
    assert res.volume_m3 == pytest.approx(100.0, rel=1e-5)
    assert res.volume_litres == pytest.approx(100_000.0, rel=1e-5)

def test_vol_02_circular():
    """VOL-02: Circular pond: diameter 4 m, depth 2 m -> Approximately 25.133 m³, or 25,133 litres."""
    res = calculate_pond_volume({"shape": "circular", "diameter_m": 4, "depth_m": 2})
    expected_m3 = math.pi * (2.0 ** 2) * 2.0  # 8 * pi = 25.132741...
    assert res.volume_m3 == pytest.approx(expected_m3, rel=1e-4)
    assert res.volume_litres == pytest.approx(25132.74, rel=1e-3)
    assert "25.133" in res.display_volume_m3

def test_vol_03_irregular():
    """VOL-03: Irregular pond: area 100 m², depth 1.5 m -> 150 m³, or 150,000 litres."""
    res = calculate_pond_volume({"shape": "irregular", "surface_area_m2": 100, "depth_m": 1.5})
    assert res.volume_m3 == pytest.approx(150.0, rel=1e-5)
    assert res.volume_litres == pytest.approx(150_000.0, rel=1e-5)

def test_vol_04_missing_dimensions():
    """VOL-04: Missing dimensions -> Validation error."""
    with pytest.raises(ValueError):
        calculate_pond_volume({"shape": "rectangular", "length_m": 10, "depth_m": 2})

def test_vol_05_negative_dimensions():
    """VOL-05: Negative dimensions -> Rejected."""
    with pytest.raises(ValueError):
        calculate_pond_volume({"shape": "rectangular", "length_m": -10, "width_m": 5, "depth_m": 2})

def test_vol_06_zero_depth():
    """VOL-06: Zero depth -> Zero volume with a warning."""
    res = calculate_pond_volume({"shape": "rectangular", "length_m": 10, "width_m": 5, "depth_m": 0})
    assert res.volume_m3 == 0.0
    assert res.volume_litres == 0.0
    assert any("Pond depth is 0m" in w for w in res.warnings)

def test_vol_07_unsupported_shape():
    """VOL-07: Unsupported pond shape -> Rejected."""
    with pytest.raises(ValueError, match="Unsupported pond shape"):
        calculate_pond_volume({"shape": "triangular", "length_m": 10, "depth_m": 2})

def test_vol_08_unit_conversions():
    """VOL-08: Change units -> Correct conversion and clearly displayed units."""
    res = calculate_pond_volume({"shape": "rectangular", "length_m": 10, "width_m": 5, "depth_m": 2})
    assert res.volume_gallons == pytest.approx(26417.2, rel=1e-3)
    assert "gal" in res.display_volume_gallons

def test_vol_09_very_large_dimensions():
    """VOL-09: Very large dimensions -> Limits and numeric safety checks work."""
    with pytest.raises(ValueError):
        calculate_pond_volume({"shape": "rectangular", "length_m": 99999999, "width_m": 5, "depth_m": 2})

def test_vol_10_reference_comparison():
    """VOL-10: Compare displayed volume with reference calculation."""
    res = calculate_pond_volume({"shape": "circular", "diameter_m": 10, "depth_m": 3})
    ref = math.pi * (5.0 ** 2) * 3.0
    assert res.volume_m3 == pytest.approx(ref, rel=1e-5)
