import datetime
from sqlalchemy.orm import Session
from app.models.entities import Pond, SensorThreshold, WaterReading, FeedEstimate, AlertRecord, User
from app.core.security import hash_password
from app.services.calculator import calculate_feeding, calculate_pond_volume

def seed_database(db: Session):
    # Check if ponds already exist
    if db.query(Pond).count() > 0:
        return

    print("Seeding initial AquaSmart database records...")

    # 1. Seed Users
    admin = User(username="admin", email="admin@aquasmart.ai", hashed_password=hash_password("admin123"), role="admin")
    sup = User(username="supervisor", email="supervisor@aquasmart.ai", hashed_password=hash_password("aqua2026"), role="supervisor")
    op = User(username="operator", email="operator@aquasmart.ai", hashed_password=hash_password("operator123"), role="operator")
    db.add_all([admin, sup, op])

    # 2. Seed Ponds (from Stitch specification & farm layout)
    ponds_data = [
        {
            "id": "pond-01",
            "name": "Pond Alpha (N-01) - Tilapia Grow-out",
            "species": "Nile Tilapia",
            "fish_count": 12000,
            "avg_weight_g": 80.0,
            "feeding_rate_pct": 2.5,
            "feed_price_per_kg": 68.0,
            "shape": "rectangular",
            "length_m": 40.0,
            "width_m": 25.0,
            "depth_m": 2.0,
            "status": "Optimal"
        },
        {
            "id": "pond-02",
            "name": "Pond Beta (N-02) - Prawns Raceway",
            "species": "Vannamei Shrimp",
            "fish_count": 35000,
            "avg_weight_g": 18.5,
            "feeding_rate_pct": 3.8,
            "feed_price_per_kg": 92.0,
            "shape": "rectangular",
            "length_m": 50.0,
            "width_m": 12.0,
            "depth_m": 1.4,
            "status": "Optimal"
        },
        {
            "id": "pond-03",
            "name": "Pond Delta (S-01) - Critical DO Tank",
            "species": "Nile Tilapia",
            "fish_count": 8500,
            "avg_weight_g": 142.5,
            "feeding_rate_pct": 2.1,
            "feed_price_per_kg": 72.0,
            "shape": "circular",
            "diameter_m": 16.0,
            "depth_m": 2.2,
            "status": "Critical"
        },
        {
            "id": "pond-04",
            "name": "Nursery Pen 04 - Fingerling Hatchery",
            "species": "Nile Tilapia (Fingerlings)",
            "fish_count": 50000,
            "avg_weight_g": 4.5,
            "feeding_rate_pct": 5.0,
            "feed_price_per_kg": 110.0,
            "shape": "rectangular",
            "length_m": 15.0,
            "width_m": 10.0,
            "depth_m": 1.2,
            "status": "Caution"
        },
        {
            "id": "pond-05",
            "name": "Pond Echo (E-02) - Tilapia Broodstock",
            "species": "Nile Tilapia",
            "fish_count": 4200,
            "avg_weight_g": 450.0,
            "feeding_rate_pct": 1.8,
            "feed_price_per_kg": 70.0,
            "shape": "irregular",
            "surface_area_m2": 650.0,
            "depth_m": 1.8,
            "status": "Optimal"
        },
        {
            "id": "pond-06",
            "name": "Pond Foxtrot (W-01) - Vannamei Secondary",
            "species": "Vannamei Shrimp",
            "fish_count": 28000,
            "avg_weight_g": 12.0,
            "feeding_rate_pct": 4.2,
            "feed_price_per_kg": 95.0,
            "shape": "rectangular",
            "length_m": 35.0,
            "width_m": 20.0,
            "depth_m": 1.5,
            "status": "Optimal"
        }
    ]

    for p in ponds_data:
        vol = calculate_pond_volume({
            "shape": p["shape"],
            "length_m": p.get("length_m"),
            "width_m": p.get("width_m"),
            "diameter_m": p.get("diameter_m"),
            "surface_area_m2": p.get("surface_area_m2"),
            "depth_m": p["depth_m"]
        })
        feed = calculate_feeding({
            "fish_count": p["fish_count"],
            "avg_weight_g": p["avg_weight_g"],
            "feeding_rate_pct": p["feeding_rate_pct"],
            "feed_price_per_kg": p["feed_price_per_kg"]
        })

        pond = Pond(
            id=p["id"],
            name=p["name"],
            species=p["species"],
            fish_count=p["fish_count"],
            avg_weight_g=p["avg_weight_g"],
            feeding_rate_pct=p["feeding_rate_pct"],
            feed_price_per_kg=p["feed_price_per_kg"],
            shape=p["shape"],
            length_m=p.get("length_m"),
            width_m=p.get("width_m"),
            diameter_m=p.get("diameter_m"),
            surface_area_m2=p.get("surface_area_m2"),
            depth_m=p["depth_m"],
            volume_m3=vol.volume_m3,
            volume_litres=vol.volume_litres,
            biomass_kg=feed.biomass_kg,
            daily_feed_kg=feed.daily_feed_kg,
            daily_cost=feed.daily_cost,
            cost_30_days=feed.cost_30_days,
            status=p["status"],
            is_demo=True
        )
        db.add(pond)

        # Thresholds
        is_shrimp = "shrimp" in p["species"].lower()
        t = SensorThreshold(
            pond_id=p["id"],
            min_temp=24.0,
            max_temp=32.0,
            min_ph=6.5,
            max_ph=8.5,
            min_do=5.0,
            max_ammonia=0.05,
            min_salinity=12.0 if is_shrimp else 0.0,
            max_salinity=35.0
        )
        db.add(t)

        # Feed Estimate History
        for d in range(10, 0, -1):
            record_date = datetime.datetime.utcnow() - datetime.timedelta(days=d)
            # slight daily growth
            growth_factor = 1.0 - (d * 0.015)
            past_weight = p["avg_weight_g"] * growth_factor
            past_feed = calculate_feeding({
                "fish_count": p["fish_count"],
                "avg_weight_g": past_weight,
                "feeding_rate_pct": p["feeding_rate_pct"],
                "feed_price_per_kg": p["feed_price_per_kg"]
            })
            fe = FeedEstimate(
                pond_id=p["id"],
                fish_count=p["fish_count"],
                avg_weight_g=round(past_weight, 2),
                feeding_rate_pct=p["feeding_rate_pct"],
                feed_price_per_kg=p["feed_price_per_kg"],
                biomass_kg=past_feed.biomass_kg,
                daily_feed_kg=past_feed.daily_feed_kg,
                daily_cost=past_feed.daily_cost,
                cost_30_days=past_feed.cost_30_days,
                notes=f"Recorded daily telemetry batch #{10-d}",
                recorded_at=record_date
            )
            db.add(fe)

        # Water Readings
        if p["id"] == "pond-03":
            # Critical low DO
            do_val = 2.85
            st = "critical"
        elif p["id"] == "pond-04":
            # Slightly elevated ammonia
            do_val = 5.2
            st = "caution"
        else:
            do_val = 6.8
            st = "optimal"

        wr = WaterReading(
            pond_id=p["id"],
            temperature_c=28.4,
            ph=7.65,
            dissolved_oxygen_mg_l=do_val,
            salinity_ppt=18.0 if is_shrimp else 0.2,
            ammonia_mg_l=0.062 if p["id"] == "pond-04" else 0.018,
            source="simulated",
            status=st,
            is_stale=False,
            recorded_at=datetime.datetime.utcnow()
        )
        db.add(wr)

    # 3. Seed Alerts
    alert1 = AlertRecord(
        pond_id="pond-03",
        parameter="Dissolved Oxygen",
        severity="critical",
        message="CRITICAL HYPOXIA: Dissolved oxygen dropped to 2.85 mg/L in Pond Delta. Aerator automatic override triggered.",
        value=2.85,
        threshold=5.0,
        is_acknowledged=False,
        is_resolved=False,
        triggered_at=datetime.datetime.utcnow() - datetime.timedelta(minutes=24)
    )
    alert2 = AlertRecord(
        pond_id="pond-04",
        parameter="Ammonia",
        severity="warning",
        message="Elevated Ammonia NH3: 0.062 mg/L detected in Fingerling Nursery Pen 04. Biofilter backwash suggested.",
        value=0.062,
        threshold=0.05,
        is_acknowledged=True,
        is_resolved=False,
        triggered_at=datetime.datetime.utcnow() - datetime.timedelta(hours=2)
    )
    alert3 = AlertRecord(
        pond_id="pond-01",
        parameter="pH",
        severity="info",
        message="pH stabilized at 7.65 following lime buffer dosing.",
        value=7.65,
        threshold=7.5,
        is_acknowledged=True,
        is_resolved=True,
        triggered_at=datetime.datetime.utcnow() - datetime.timedelta(days=1),
        resolved_at=datetime.datetime.utcnow() - datetime.timedelta(hours=18)
    )
    db.add_all([alert1, alert2, alert3])

    db.commit()
    print("Database seeding completed successfully!")
