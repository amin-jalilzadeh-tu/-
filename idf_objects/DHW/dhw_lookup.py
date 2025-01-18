# DHW/dhw_lookup.py

# -------------------------------------------------------------------------------
# NTA 8800 References (Selection):
# -------------------------------------------------------------------------------
# - §§13.1–13.2 of NTA 8800 give an overview of hot tap water energy use,
#   net heat requirement, and occupant-based or area-based usage (esp. 13.2.2, 13.2.3).
# - Table 13.1 (page ~15 in the excerpt) gives typical daily liters at 60 °C per m²
#   for various non-residential functions (like offices, education, sport).
# - For residential, ~40 L/person/day at 60 °C is often cited (NTA 8800 note around p.15).
# - If a circulation loop exists, setpoint often goes to 65 °C (NTA 8800 references in 
#   13.6.2, 13.7.2.2.2).
#
# Below constants are approximate placeholders:
#  - The occupant_density_m2_per_person_range is the approximate range of floor area 
#    per occupant (lower area => higher occupant density).
#  - The liters_per_person_per_day_range is how many liters of 60 °C hot water each occupant uses daily.
#  - default_tank_volume_liters_range, default_heater_capacity_w_range are typical 
#    lumpsum approximations for tank sizing and heater capacity.
#  - setpoint_c_range typically ~60 °C, or 65 °C for certain healthcare/hospital contexts.
#  - usage_split_factor_range, peak_hours_range, sched_*_range are code-specific ways 
#    to shape daily usage.
# 
# You can adjust these numeric ranges as you see fit; they are example placeholders
# reflecting NTA 8800’s typical usage categories, matched to your new naming system.
# -------------------------------------------------------------------------------

dhw_lookup = {

    # -------------------------------------------------------------
    # TABLE_13_1_KWH_PER_M2 for area-based approach
    # (Renamed to match your new Non-Residential Type naming system)
    # -------------------------------------------------------------
    "TABLE_13_1_KWH_PER_M2": {
        "Meeting Function":       2.8,   # e.g. 2.8 kWh/m²/year
        "Office Function":        1.4,   # ~1.4 kWh/m²/year
        "Retail Function":        1.4,   # ~1.4 kWh/m²/year
        "Healthcare Function":   15.3,   # e.g. large hospital or care facility
        "Education Function":     1.4,   # ~1.4 kWh/m²/year
        "Sport Function":         12.5,   # placeholder for sports
        "Cell Function":          4.2,   # placeholder for penal/detention usage
        "Industrial Function":    1.2,   # placeholder for industrial usage
        "Accommodation Function": 12.5,  # typical hotel factor
        "Other Use Function":     2.4    # fallback
    },


    # ---------------------------------------------------------------------
    #  "pre_calibration" => broad ranges, approximate
    # ---------------------------------------------------------------------
    "pre_calibration": {

        # ==========================
        # Residential Types
        # ==========================

        # 1) Corner House
        #    Approx. occupant usage ~45–55 L/p/d. 
        #    occupant_density = None => code may do area-based occupant formula instead.
        "Corner House": {
            "occupant_density_m2_per_person_range": (None, None),
            "liters_per_person_per_day_range": (45.0, 55.0),
            "default_tank_volume_liters_range": (180.0, 220.0),
            "default_heater_capacity_w_range": (3500.0, 4500.0),
            "setpoint_c_range": (58.0, 60.0),
            "usage_split_factor_range": (0.5, 0.7),
            "peak_hours_range": (1.5, 2.5),
            "sched_morning_range": (0.6, 0.8),
            "sched_peak_range": (0.9, 1.1),
            "sched_afternoon_range": (0.1, 0.3),
            "sched_evening_range": (0.5, 0.9)
        },

        # 2) Apartment
        #    Could mirror 'multifamily' logic => occupant_density ~25–35 m²/p
        #    daily usage ~45–55 L/p/d
        "Apartment": {
            "occupant_density_m2_per_person_range": (25.0, 35.0),
            "liters_per_person_per_day_range": (45.0, 55.0),
            "default_tank_volume_liters_range": (900.0, 1100.0),
            "default_heater_capacity_w_range": (18000.0, 22000.0),
            "setpoint_c_range": (58.0, 60.0),
            "usage_split_factor_range": (0.5, 0.7),
            "peak_hours_range": (2.0, 3.0),
            "sched_morning_range": (0.5, 0.7),
            "sched_peak_range": (0.9, 1.1),
            "sched_afternoon_range": (0.2, 0.4),
            "sched_evening_range": (0.5, 0.8)
        },

        # 3) Terrace or Semi-detached House
        #    Similar usage to smaller single-family => ~45–55 L/p/d
        "Terrace or Semi-detached House": {
            "occupant_density_m2_per_person_range": (None, None),
            "liters_per_person_per_day_range": (45.0, 55.0),
            "default_tank_volume_liters_range": (180.0, 250.0),
            "default_heater_capacity_w_range": (3500.0, 5000.0),
            "setpoint_c_range": (58.0, 60.0),
            "usage_split_factor_range": (0.5, 0.7),
            "peak_hours_range": (2.0, 3.0),
            "sched_morning_range": (0.6, 0.8),
            "sched_peak_range": (0.9, 1.1),
            "sched_afternoon_range": (0.2, 0.4),
            "sched_evening_range": (0.5, 0.9)
        },

        # 4) Detached House
        #    Possibly higher daily usage => ~55–65 L/p/d
        "Detached House": {
            "occupant_density_m2_per_person_range": (None, None),
            "liters_per_person_per_day_range": (55.0, 65.0),
            "default_tank_volume_liters_range": (250.0, 350.0),
            "default_heater_capacity_w_range": (4000.0, 5000.0),
            "setpoint_c_range": (58.0, 60.0),
            "usage_split_factor_range": (0.5, 0.7),
            "peak_hours_range": (2.0, 3.0),
            "sched_morning_range": (0.6, 0.8),
            "sched_peak_range": (0.9, 1.1),
            "sched_afternoon_range": (0.2, 0.3),
            "sched_evening_range": (0.6, 1.0)
        },

        # 5) Two-and-a-half-story House
        #    Another single-family variant => placeholder usage ~50–60 L/p/d
        "Two-and-a-half-story House": {
            "occupant_density_m2_per_person_range": (None, None),
            "liters_per_person_per_day_range": (50.0, 60.0),
            "default_tank_volume_liters_range": (220.0, 320.0),
            "default_heater_capacity_w_range": (4000.0, 5000.0),
            "setpoint_c_range": (58.0, 60.0),
            "usage_split_factor_range": (0.5, 0.7),
            "peak_hours_range": (1.5, 2.5),
            "sched_morning_range": (0.6, 0.8),
            "sched_peak_range": (0.9, 1.1),
            "sched_afternoon_range": (0.2, 0.4),
            "sched_evening_range": (0.5, 0.9)
        },

        # ==========================
        # Non-Residential Types
        # ==========================

        # 1) Meeting Function
        #    Like "Assembly" => occupant_density ~1 m²/p, daily usage ~4–6 L/p/d
        "Meeting Function": {
            "occupant_density_m2_per_person_range": (0.8, 1.2),
            "liters_per_person_per_day_range": (4.0, 6.0),
            "default_tank_volume_liters_range": (400.0, 600.0),
            "default_heater_capacity_w_range": (13000.0, 17000.0),
            "setpoint_c_range": (58.0, 60.0),
            "usage_split_factor_range": (0.6, 0.8),
            "peak_hours_range": (2.0, 3.0),
            "sched_morning_range": (0.1, 0.2),
            "sched_peak_range": (0.6, 0.8),
            "sched_afternoon_range": (0.1, 0.3),
            "sched_evening_range": (0.2, 0.5)
        },

        # 2) Healthcare Function
        #    Could be outpatient or hospital => occupant_density (8–30), usage (18–70) 
        #    is a wide range. Feel free to split into "clinic" vs "hospital" if you prefer.
        "Healthcare Function": {
            "occupant_density_m2_per_person_range": (8.0, 30.0),
            "liters_per_person_per_day_range": (18.0, 70.0),
            "default_tank_volume_liters_range": (1000.0, 5000.0),
            "default_heater_capacity_w_range": (20000.0, 50000.0),
            "setpoint_c_range": (58.0, 65.0),  # might go higher in hospital contexts
            "usage_split_factor_range": (0.6, 0.8),
            "peak_hours_range": (2.0, 3.0),
            "sched_morning_range": (0.2, 0.4),
            "sched_peak_range": (0.6, 0.8),
            "sched_afternoon_range": (0.2, 0.4),
            "sched_evening_range": (0.1, 0.3)
        },

        # 3) Sport Function
        #    Similar to "Sports_Facility" => occupant_density ~8–12, usage ~25–35 L/p/d
        "Sport Function": {
            "occupant_density_m2_per_person_range": (8.0, 12.0),
            "liters_per_person_per_day_range": (25.0, 35.0),
            "default_tank_volume_liters_range": (2800.0, 3200.0),
            "default_heater_capacity_w_range": (38000.0, 42000.0),
            "setpoint_c_range": (58.0, 60.0),
            "usage_split_factor_range": (0.6, 0.8),
            "peak_hours_range": (2.0, 3.0),
            "sched_morning_range": (0.2, 0.4),
            "sched_peak_range": (0.6, 0.8),
            "sched_afternoon_range": (0.2, 0.4),
            "sched_evening_range": (0.3, 0.6)
        },

        # 4) Cell Function
        #    Placeholder for a detention/penal facility => occupant_density could vary widely.
        #    For demonstration: occupant_density ~10–20, usage ~30–40 L/p/d
        "Cell Function": {
            "occupant_density_m2_per_person_range": (10.0, 20.0),
            "liters_per_person_per_day_range": (30.0, 40.0),
            "default_tank_volume_liters_range": (1000.0, 3000.0),
            "default_heater_capacity_w_range": (20000.0, 40000.0),
            "setpoint_c_range": (58.0, 60.0),
            "usage_split_factor_range": (0.6, 0.8),
            "peak_hours_range": (2.0, 3.0),
            "sched_morning_range": (0.2, 0.4),
            "sched_peak_range": (0.7, 0.8),
            "sched_afternoon_range": (0.2, 0.4),
            "sched_evening_range": (0.4, 0.7)
        },

        # 5) Retail Function
        #    occupant_density ~4–6, usage ~4–6 L/p/d
        "Retail Function": {
            "occupant_density_m2_per_person_range": (4.0, 6.0),
            "liters_per_person_per_day_range": (4.0, 6.0),
            "default_tank_volume_liters_range": (250.0, 350.0),
            "default_heater_capacity_w_range": (9000.0, 11000.0),
            "setpoint_c_range": (58.0, 60.0),
            "usage_split_factor_range": (0.6, 0.8),
            "peak_hours_range": (2.0, 3.0),
            "sched_morning_range": (0.1, 0.3),
            "sched_peak_range": (0.5, 0.7),
            "sched_afternoon_range": (0.2, 0.4),
            "sched_evening_range": (0.1, 0.2)
        },

        # 6) Industrial Function
        #    occupant_density can be quite low or varied => (12.0, 30.0)
        #    usage might be moderate => (10–20 L/p/d), placeholders only
        "Industrial Function": {
            "occupant_density_m2_per_person_range": (12.0, 30.0),
            "liters_per_person_per_day_range": (10.0, 20.0),
            "default_tank_volume_liters_range": (500.0, 2000.0),
            "default_heater_capacity_w_range": (10000.0, 30000.0),
            "setpoint_c_range": (58.0, 60.0),
            "usage_split_factor_range": (0.6, 0.8),
            "peak_hours_range": (2.0, 3.0),
            "sched_morning_range": (0.2, 0.3),
            "sched_peak_range": (0.6, 0.7),
            "sched_afternoon_range": (0.2, 0.4),
            "sched_evening_range": (0.2, 0.3)
        },

        # 7) Accommodation Function
        #    Like hotels => occupant_density ~15–25, usage ~50–70 L/p/d
        "Accommodation Function": {
            "occupant_density_m2_per_person_range": (15.0, 25.0),
            "liters_per_person_per_day_range": (50.0, 70.0),
            "default_tank_volume_liters_range": (1800.0, 2200.0),
            "default_heater_capacity_w_range": (28000.0, 32000.0),
            "setpoint_c_range": (58.0, 60.0),
            "usage_split_factor_range": (0.6, 0.8),
            "peak_hours_range": (2.0, 3.0),
            "sched_morning_range": (0.2, 0.4),
            "sched_peak_range": (0.8, 1.0),
            "sched_afternoon_range": (0.2, 0.4),
            "sched_evening_range": (0.4, 0.7)
        },

        # 8) Office Function
        #    occupant_density ~12–18, usage ~8–12 L/p/d
        "Office Function": {
            "occupant_density_m2_per_person_range": (12.0, 18.0),
            "liters_per_person_per_day_range": (8.0, 12.0),
            "default_tank_volume_liters_range": (250.0, 350.0),
            "default_heater_capacity_w_range": (7000.0, 9000.0),
            "setpoint_c_range": (58.0, 62.0),
            "usage_split_factor_range": (0.6, 0.8),
            "peak_hours_range": (2.0, 3.0),
            "sched_morning_range": (0.1, 0.2),
            "sched_peak_range": (0.5, 0.7),
            "sched_afternoon_range": (0.2, 0.4),
            "sched_evening_range": (0.05, 0.2)
        },

        # 9) Education Function
        #    occupant_density ~6–10, usage ~8–12 L/p/d
        "Education Function": {
            "occupant_density_m2_per_person_range": (6.0, 10.0),
            "liters_per_person_per_day_range": (8.0, 12.0),
            "default_tank_volume_liters_range": (400.0, 600.0),
            "default_heater_capacity_w_range": (9000.0, 11000.0),
            "setpoint_c_range": (58.0, 60.0),
            "usage_split_factor_range": (0.6, 0.8),
            "peak_hours_range": (2.0, 3.0),
            "sched_morning_range": (0.1, 0.3),
            "sched_peak_range": (0.5, 0.7),
            "sched_afternoon_range": (0.2, 0.4),
            "sched_evening_range": (0.1, 0.2)
        },

        # 10) Other Use Function
        #     Fallback => occupant_density ~5–15, usage ~5–15 L/p/d
        "Other Use Function": {
            "occupant_density_m2_per_person_range": (5.0, 15.0),
            "liters_per_person_per_day_range": (5.0, 15.0),
            "default_tank_volume_liters_range": (300.0, 600.0),
            "default_heater_capacity_w_range": (9000.0, 15000.0),
            "setpoint_c_range": (58.0, 60.0),
            "usage_split_factor_range": (0.5, 0.7),
            "peak_hours_range": (2.0, 2.5),
            "sched_morning_range": (0.1, 0.2),
            "sched_peak_range": (0.5, 0.7),
            "sched_afternoon_range": (0.2, 0.4),
            "sched_evening_range": (0.2, 0.3)
        },
    },

    # ---------------------------------------------------------------------
    #  "post_calibration" => narrower or fixed values, reflecting final 
    #  calibrated parameters. You can further refine or unify them.
    # ---------------------------------------------------------------------
    "post_calibration": {

        # ==========================
        # Residential
        # ==========================
        "Corner House": {
            "occupant_density_m2_per_person_range": (None, None),
            "liters_per_person_per_day_range": (50.0, 50.0),
            "default_tank_volume_liters_range": (200.0, 200.0),
            "default_heater_capacity_w_range": (4000.0, 4000.0),
            "setpoint_c_range": (60.0, 60.0),
            "usage_split_factor_range": (0.6, 0.6),
            "peak_hours_range": (2.0, 2.0),
            "sched_morning_range": (0.7, 0.7),
            "sched_peak_range": (1.0, 1.0),
            "sched_afternoon_range": (0.2, 0.2),
            "sched_evening_range": (0.8, 0.8)
        },

        "Apartment": {
            "occupant_density_m2_per_person_range": (30.0, 30.0),
            "liters_per_person_per_day_range": (50.0, 50.0),
            "default_tank_volume_liters_range": (1000.0, 1000.0),
            "default_heater_capacity_w_range": (20000.0, 20000.0),
            "setpoint_c_range": (60.0, 60.0),
            "usage_split_factor_range": (0.6, 0.6),
            "peak_hours_range": (2.0, 2.0),
            "sched_morning_range": (0.7, 0.7),
            "sched_peak_range": (1.0, 1.0),
            "sched_afternoon_range": (0.2, 0.2),
            "sched_evening_range": (0.8, 0.8)
        },

        "Terrace or Semi-detached House": {
            "occupant_density_m2_per_person_range": (None, None),
            "liters_per_person_per_day_range": (50.0, 50.0),
            "default_tank_volume_liters_range": (200.0, 200.0),
            "default_heater_capacity_w_range": (4000.0, 4000.0),
            "setpoint_c_range": (60.0, 60.0),
            "usage_split_factor_range": (0.6, 0.6),
            "peak_hours_range": (2.0, 2.0),
            "sched_morning_range": (0.7, 0.7),
            "sched_peak_range": (1.0, 1.0),
            "sched_afternoon_range": (0.2, 0.2),
            "sched_evening_range": (0.8, 0.8)
        },

        "Detached House": {
            "occupant_density_m2_per_person_range": (None, None),
            "liters_per_person_per_day_range": (60.0, 60.0),
            "default_tank_volume_liters_range": (300.0, 300.0),
            "default_heater_capacity_w_range": (5000.0, 5000.0),
            "setpoint_c_range": (60.0, 60.0),
            "usage_split_factor_range": (0.6, 0.6),
            "peak_hours_range": (2.5, 2.5),
            "sched_morning_range": (0.7, 0.7),
            "sched_peak_range": (1.0, 1.0),
            "sched_afternoon_range": (0.2, 0.2),
            "sched_evening_range": (0.8, 0.8)
        },

        "Two-and-a-half-story House": {
            "occupant_density_m2_per_person_range": (None, None),
            "liters_per_person_per_day_range": (55.0, 55.0),
            "default_tank_volume_liters_range": (250.0, 250.0),
            "default_heater_capacity_w_range": (4500.0, 4500.0),
            "setpoint_c_range": (60.0, 60.0),
            "usage_split_factor_range": (0.6, 0.6),
            "peak_hours_range": (2.0, 2.0),
            "sched_morning_range": (0.7, 0.7),
            "sched_peak_range": (1.0, 1.0),
            "sched_afternoon_range": (0.2, 0.2),
            "sched_evening_range": (0.8, 0.8)
        },

        # ==========================
        # Non-Residential
        # ==========================
        "Meeting Function": {
            "occupant_density_m2_per_person_range": (1.0, 1.0),
            "liters_per_person_per_day_range": (5.0, 5.0),
            "default_tank_volume_liters_range": (500.0, 500.0),
            "default_heater_capacity_w_range": (15000.0, 15000.0),
            "setpoint_c_range": (60.0, 60.0),
            "usage_split_factor_range": (0.6, 0.6),
            "peak_hours_range": (2.0, 2.0),
            "sched_morning_range": (0.2, 0.2),
            "sched_peak_range": (0.6, 0.6),
            "sched_afternoon_range": (0.2, 0.2),
            "sched_evening_range": (0.5, 0.5)
        },

        "Healthcare Function": {
            "occupant_density_m2_per_person_range": (20.0, 20.0),
            "liters_per_person_per_day_range": (60.0, 60.0),
            "default_tank_volume_liters_range": (3000.0, 3000.0),
            "default_heater_capacity_w_range": (40000.0, 40000.0),
            "setpoint_c_range": (65.0, 65.0),
            "usage_split_factor_range": (0.7, 0.7),
            "peak_hours_range": (3.0, 3.0),
            "sched_morning_range": (0.3, 0.3),
            "sched_peak_range": (0.7, 0.7),
            "sched_afternoon_range": (0.3, 0.3),
            "sched_evening_range": (0.5, 0.5)
        },

        "Sport Function": {
            "occupant_density_m2_per_person_range": (10.0, 10.0),
            "liters_per_person_per_day_range": (30.0, 30.0),
            "default_tank_volume_liters_range": (3000.0, 3000.0),
            "default_heater_capacity_w_range": (40000.0, 40000.0),
            "setpoint_c_range": (60.0, 60.0),
            "usage_split_factor_range": (0.6, 0.6),
            "peak_hours_range": (2.0, 2.0),
            "sched_morning_range": (0.3, 0.3),
            "sched_peak_range": (0.7, 0.7),
            "sched_afternoon_range": (0.3, 0.3),
            "sched_evening_range": (0.6, 0.6)
        },

        "Cell Function": {
            "occupant_density_m2_per_person_range": (15.0, 15.0),
            "liters_per_person_per_day_range": (35.0, 35.0),
            "default_tank_volume_liters_range": (2000.0, 2000.0),
            "default_heater_capacity_w_range": (30000.0, 30000.0),
            "setpoint_c_range": (60.0, 60.0),
            "usage_split_factor_range": (0.6, 0.6),
            "peak_hours_range": (2.5, 2.5),
            "sched_morning_range": (0.3, 0.3),
            "sched_peak_range": (0.7, 0.7),
            "sched_afternoon_range": (0.3, 0.3),
            "sched_evening_range": (0.5, 0.5)
        },

        "Retail Function": {
            "occupant_density_m2_per_person_range": (5.0, 5.0),
            "liters_per_person_per_day_range": (5.0, 5.0),
            "default_tank_volume_liters_range": (300.0, 300.0),
            "default_heater_capacity_w_range": (10000.0, 10000.0),
            "setpoint_c_range": (60.0, 60.0),
            "usage_split_factor_range": (0.6, 0.6),
            "peak_hours_range": (2.0, 2.0),
            "sched_morning_range": (0.1, 0.1),
            "sched_peak_range": (0.7, 0.7),
            "sched_afternoon_range": (0.2, 0.2),
            "sched_evening_range": (0.1, 0.1)
        },

        "Industrial Function": {
            "occupant_density_m2_per_person_range": (20.0, 20.0),
            "liters_per_person_per_day_range": (15.0, 15.0),
            "default_tank_volume_liters_range": (1000.0, 1000.0),
            "default_heater_capacity_w_range": (20000.0, 20000.0),
            "setpoint_c_range": (60.0, 60.0),
            "usage_split_factor_range": (0.6, 0.6),
            "peak_hours_range": (2.0, 2.0),
            "sched_morning_range": (0.2, 0.2),
            "sched_peak_range": (0.6, 0.6),
            "sched_afternoon_range": (0.2, 0.2),
            "sched_evening_range": (0.3, 0.3)
        },

        "Accommodation Function": {
            "occupant_density_m2_per_person_range": (20.0, 20.0),
            "liters_per_person_per_day_range": (60.0, 60.0),
            "default_tank_volume_liters_range": (2000.0, 2000.0),
            "default_heater_capacity_w_range": (30000.0, 30000.0),
            "setpoint_c_range": (60.0, 60.0),
            "usage_split_factor_range": (0.6, 0.6),
            "peak_hours_range": (2.0, 2.0),
            "sched_morning_range": (0.3, 0.3),
            "sched_peak_range": (0.8, 0.8),
            "sched_afternoon_range": (0.3, 0.3),
            "sched_evening_range": (0.6, 0.6)
        },

        "Office Function": {
            "occupant_density_m2_per_person_range": (15.0, 15.0),
            "liters_per_person_per_day_range": (10.0, 10.0),
            "default_tank_volume_liters_range": (300.0, 300.0),
            "default_heater_capacity_w_range": (8000.0, 8000.0),
            "setpoint_c_range": (60.0, 60.0),
            "usage_split_factor_range": (0.7, 0.7),
            "peak_hours_range": (2.5, 2.5),
            "sched_morning_range": (0.15, 0.15),
            "sched_peak_range": (0.6, 0.6),
            "sched_afternoon_range": (0.3, 0.3),
            "sched_evening_range": (0.1, 0.1)
        },

        "Education Function": {
            "occupant_density_m2_per_person_range": (8.0, 8.0),
            "liters_per_person_per_day_range": (10.0, 10.0),
            "default_tank_volume_liters_range": (500.0, 500.0),
            "default_heater_capacity_w_range": (10000.0, 10000.0),
            "setpoint_c_range": (60.0, 60.0),
            "usage_split_factor_range": (0.6, 0.6),
            "peak_hours_range": (2.0, 2.0),
            "sched_morning_range": (0.2, 0.2),
            "sched_peak_range": (0.6, 0.6),
            "sched_afternoon_range": (0.2, 0.2),
            "sched_evening_range": (0.1, 0.1)
        },

        "Other Use Function": {
            "occupant_density_m2_per_person_range": (10.0, 10.0),
            "liters_per_person_per_day_range": (10.0, 10.0),
            "default_tank_volume_liters_range": (400.0, 400.0),
            "default_heater_capacity_w_range": (10000.0, 10000.0),
            "setpoint_c_range": (60.0, 60.0),
            "usage_split_factor_range": (0.6, 0.6),
            "peak_hours_range": (2.0, 2.0),
            "sched_morning_range": (0.2, 0.2),
            "sched_peak_range": (0.6, 0.6),
            "sched_afternoon_range": (0.2, 0.2),
            "sched_evening_range": (0.3, 0.3)
        }
    }
}


"""
Provides a single dictionary `dhw_lookup` with detailed parameter ranges
for your new usage types. Each is labeled exactly as you specified:

- Residential: 
   "Corner House", "Apartment", "Terrace or Semi-detached House",
   "Detached House", "Two-and-a-half-story House"

- Non-Residential:
   "Meeting Function", "Healthcare Function", "Sport Function", 
   "Cell Function", "Retail Function", "Industrial Function",
   "Accommodation Function", "Office Function", "Education Function",
   "Other Use Function"

The numeric ranges are example placeholders reflecting typical NTA 8800
values; you can edit them to match local data. For usage patterns with
circulation loops (e.g. hospitals), you might see higher setpoints (~65 °C).

We also updated the "TABLE_13_1_KWH_PER_M2" keys to match the new 
non-res naming (e.g. "Meeting Function", "Healthcare Function", etc.).
Adjust or extend these as needed.
"""
