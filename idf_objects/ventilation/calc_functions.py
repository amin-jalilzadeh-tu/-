# ventilation/calc_functions.py

import math

# Renamed for clarity - calculates the BASE RATE per m2, not the total flow yet.
def calc_infiltration_base_rate_per_m2(
    infiltration_base,  # Base rate per m2 floor area @ 10 Pa (e.g., from lookup)
    year_factor,        # Multiplier based on construction year
    flow_exponent       # Typically 0.67 (standard infiltration exponent)
):
    """
    Calculates the base infiltration rate at 1 Pa per m2 floor area (in m3/h/m2).

    This represents the characteristic leakage rate of the building fabric per unit area,
    adjusted for age, converted to reference pressure conditions (1 Pa).
    This rate can then be multiplied by a specific area (e.g., zone floor area,
    zone exterior area) to estimate the infiltration flow for that component,
    before applying schedule factors or dynamic calculations in EnergyPlus.

    Steps:
      1) Apply year_factor to infiltration_base => qv10_per_m2 (Rate per m2 @ 10 Pa).
      2) Convert qv10 => qv1 using the flow exponent: qv1 = qv10 * (1 Pa / 10 Pa)^n
      3) Return the result in m3/h per m2.

    NTA 8800 basis:
      - Table 11.2 prescribes n=0.67 for leak losses (infiltration).
      - Section 11.2.5 references converting from 10 Pa to 1 Pa.

    Args:
        infiltration_base (float): Base infiltration rate per m2 floor area @ 10 Pa.
        year_factor (float): Multiplier based on age range.
        flow_exponent (float): Flow exponent (typically 0.67).

    Returns:
        float: Base infiltration rate per m2 floor area @ 1 Pa, in m3/h per m2.
               Returns 0.0 if inputs are invalid.
    """
    try:
        # Basic input validation
        if infiltration_base < 0 or year_factor < 0 or flow_exponent <= 0:
            print(f"[WARNING] Invalid inputs to calc_infiltration_base_rate_per_m2. "
                  f"infiltration_base={infiltration_base}, year_factor={year_factor}, flow_exponent={flow_exponent}. Returning 0.")
            return 0.0

        # 1) Apply year factor => Rate per m2 @ 10 Pa
        qv10_lea_ref_per_m2 = infiltration_base * year_factor

        # 2) Convert from qv10 to qv1 using the exponent
        #    The rate units (e.g., dm3/s/m2 or m3/h/m2) don't matter for the conversion factor.
        #    Assuming the input 'infiltration_base' is in units compatible with direct use
        #    as a rate per m2 (the lookup table units need to be consistent).
        #    Let's assume the rate is effectively in m3/h/m2 for this calculation step.
        qv1_lea_ref_per_m2_h = qv10_lea_ref_per_m2 * (1.0 / 10.0)**flow_exponent

        # 3) Return the rate per m2 floor area @ 1 Pa (in m3/h/m2)
        return qv1_lea_ref_per_m2_h

    except Exception as e:
        print(f"[ERROR] Exception in calc_infiltration_base_rate_per_m2: {e}")
        return 0.0


def calc_required_ventilation_flow(
    building_function,
    f_ctrl_val,         # Control factor (e.g., from lookup based on system type)
    floor_area_m2,      # TOTAL building floor area
    usage_key=None      # Specific usage type for non-residential (e.g., office, retail)
):
    """
    Calculate the TOTAL required mechanical ventilation flow (m3/s) for the building.

    Applies standard rates per m2 based on building function/usage, applies
    a control factor, and enforces a minimum for residential buildings.

    NTA 8800 basis:
      - Section 11.2.2.5 / Table 11.8 provide typical supply rates. This uses simplified examples.
      - Residential minimum often relates to dwelling size/occupancy (~35 L/s or 126 m3/h).

    Args:
        building_function (str): 'residential' or 'non_residential'.
        f_ctrl_val (float): Control factor multiplier.
        floor_area_m2 (float): Total building floor area.
        usage_key (str, optional): Key for non-residential usage type.

    Returns:
        float: Total required ventilation flow rate for the building in m3/s.
    """
    try:
        # Basic input validation
        if floor_area_m2 <= 0:
             print(f"[WARNING] Invalid floor_area_m2 ({floor_area_m2}) in calc_required_ventilation_flow. Returning 0.")
             return 0.0
        if f_ctrl_val < 0:
             print(f"[WARNING] Negative f_ctrl_val ({f_ctrl_val}) in calc_required_ventilation_flow. Using 0.")
             f_ctrl_val = 0.0

        qv_oda_req_des_m3_h = 0.0 # Design required flow in m3/h

        if building_function == "residential":
            # Base rate from NTA 8800 example for dwellings (0.9 dm3/s per m2)
            qv_uspec_dm3_s_m2 = 0.9
            # Total design required flow in dm3/s
            qv_oda_req_des_dm3_s = qv_uspec_dm3_s_m2 * floor_area_m2
            # Convert total design flow to m3/h
            qv_oda_req_des_m3_h = qv_oda_req_des_dm3_s * 3.6

            # Apply control factor
            qv_oda_req_m3_h = f_ctrl_val * qv_oda_req_des_m3_h

            # Enforce minimum ventilation rate for a dwelling (~126 m3/h = 35 L/s)
            # This minimum applies AFTER the control factor potentially reduces the calculated rate.
            residential_min_m3_h = 126.0
            if qv_oda_req_m3_h < residential_min_m3_h:
                # print(f"[VENT INFO] Residential calculated vent {qv_oda_req_m3_h:.1f} m3/h below minimum. Using {residential_min_m3_h} m3/h.")
                qv_oda_req_m3_h = residential_min_m3_h

        else: # Non-residential
            # Base rates per m2 based on usage_key (examples, adjust as needed)
            # Rates in dm3/s per m2
            usage_flow_map = {
                "office_area_based": 1.0,
                "childcare": 4.8,          # Example - high rate for childcare
                "retail": 0.6,
                # Add other keys from mappings.py if they need different rates
                "meeting_function": 1.0, # Example mapping
                "healthcare_function": 1.2, # Example mapping
                "sport_function": 1.5,    # Example mapping
                "cell_function": 0.8,     # Example mapping
                "industrial_function": 0.5, # Example mapping
                "accommodation_function": 0.9, # Example mapping
                "education_function": 1.1,  # Example mapping
                "other_use_function": 0.6 # Example mapping
            }
            # Use usage_key, fallback to a default non-res rate if key not found
            qv_usage_dm3_s_m2 = usage_flow_map.get(usage_key, 1.0)

            # Total design required flow in dm3/s
            qv_oda_req_des_dm3_s = qv_usage_dm3_s_m2 * floor_area_m2
            # Convert total design flow to m3/h
            qv_oda_req_des_m3_h = qv_oda_req_des_dm3_s * 3.6

            # Apply control factor
            qv_oda_req_m3_h = f_ctrl_val * qv_oda_req_des_m3_h
            # Minimums for non-res are typically implicit in the design rates,
            # but could be added here if needed per category.

        # Final conversion from calculated m3/h to m3/s
        total_vent_flow_m3_s = qv_oda_req_m3_h / 3600.0
        return total_vent_flow_m3_s

    except Exception as e:
        print(f"[ERROR] Exception in calc_required_ventilation_flow: {e}")
        return 0.0


def calc_fan_power(fan_pressure, fan_efficiency, flow_m3_s):
    """
    Compute fan power in Watts based on pressure rise, efficiency, and flow rate.

    Formula: P_fan = (fan_pressure * flow_m3_s) / fan_efficiency

    Args:
        fan_pressure (float): Fan pressure rise in Pascals (Pa).
        fan_efficiency (float): Overall fan efficiency (0.0 < eff <= 1.0).
        flow_m3_s (float): Air volume flow rate in m3/s.

    Returns:
        float: Fan power in Watts (W). Returns 0 if efficiency is invalid.
    """
    try:
        if fan_efficiency <= 0 or fan_efficiency > 1.0:
            print(f"[WARNING] Invalid fan_efficiency ({fan_efficiency}) in calc_fan_power. Using 0.7 default for calculation if needed, but returning 0 W.")
            # Or maybe raise an error? For now, return 0 power if efficiency is bad.
            return 0.0
            # fan_efficiency = 0.7 # Or apply a default if you prefer non-zero output

        if fan_pressure < 0 or flow_m3_s < 0:
             print(f"[WARNING] Negative pressure or flow in calc_fan_power. Result may be invalid.")
             # Calculation proceeds, result might be negative or zero.

        # Ensure inputs are numbers
        pressure = float(fan_pressure)
        flow = float(flow_m3_s)
        efficiency = float(fan_efficiency)

        fan_power_watts = (pressure * flow) / efficiency
        return fan_power_watts

    except Exception as e:
        print(f"[ERROR] Exception in calc_fan_power: {e}")
        return 0.0