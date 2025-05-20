# ventilation/calc_functions.py

import math

# Updated function name and docstring for clarity on units
def calc_infiltration_rate_at_1Pa_per_m2(
    infiltration_base_at_10Pa_per_m2,  # Base rate per m2 floor area @ 10 Pa (e.g., in L/s/m2 or m3/h/m2)
    year_factor,                       # Multiplier based on construction year
    flow_exponent                      # Typically 0.67 (standard infiltration exponent)
):
    """
    Calculates the infiltration rate at 1 Pa per m2 floor area.

    The output rate will be in the same volumetric units as the input
    'infiltration_base_at_10Pa_per_m2' (e.g., if input is L/s/m2, output is L/s/m2).
    This function adjusts for the construction year and converts the pressure basis from 10 Pa to 1 Pa.
    The final conversion to m3/s for EnergyPlus is handled in the calling script (e.g., add_ventilation.py).

    Steps:
      1) Apply year_factor to infiltration_base_at_10Pa_per_m2 => qv10_per_m2 (Rate per m2 @ 10 Pa).
      2) Convert qv10 => qv1 using the flow exponent: qv1 = qv10 * (1 Pa / 10 Pa)^n
      3) Return the result (e.g., in L/s per m2 @ 1Pa or m3/h per m2 @ 1Pa).

    NTA 8800 basis:
      - Table 11.2 prescribes n=0.67 for leak losses (infiltration).
      - Section 11.2.5 references converting from 10 Pa to 1 Pa.

    Args:
        infiltration_base_at_10Pa_per_m2 (float): Base infiltration rate per m2 floor area
                                                  at 10 Pa (e.g., in L/s/m2 or m3/h/m2).
        year_factor (float): Multiplier based on age range.
        flow_exponent (float): Flow exponent (typically 0.67).

    Returns:
        float: Infiltration rate per m2 floor area @ 1 Pa, in the same volumetric units
               as 'infiltration_base_at_10Pa_per_m2'.
               Returns 0.0 if inputs are invalid.
    """
    try:
        # Basic input validation
        if infiltration_base_at_10Pa_per_m2 < 0 or year_factor < 0 or flow_exponent <= 0:
            print(f"[WARNING] Invalid inputs to calc_infiltration_rate_at_1Pa_per_m2. "
                  f"base_rate={infiltration_base_at_10Pa_per_m2}, year_factor={year_factor}, exponent={flow_exponent}. Returning 0.")
            return 0.0

        # 1) Apply year factor => Rate per m2 @ 10 Pa, in original volumetric units
        qv10_effective_per_m2 = infiltration_base_at_10Pa_per_m2 * year_factor

        # 2) Convert from qv10 to qv1 using the exponent
        # The volumetric unit (e.g., L/s or m3/h) is preserved during this conversion.
        qv1_effective_per_m2 = qv10_effective_per_m2 * (1.0 / 10.0)**flow_exponent

        # 3) Return the rate per m2 floor area @ 1 Pa (in original volumetric units per m2)
        return qv1_effective_per_m2

    except Exception as e:
        print(f"[ERROR] Exception in calc_infiltration_rate_at_1Pa_per_m2: {e}")
        return 0.0


def calc_required_ventilation_flow(
    building_function,
    f_ctrl_val,          # Control factor (e.g., from lookup based on system type)
    floor_area_m2,       # TOTAL building floor area
    usage_key=None       # Specific usage type for non-residential (e.g., office, retail)
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
        if f_ctrl_val < 0: # Allow f_ctrl_val == 0 (e.g. to turn off mech vent based on control)
            print(f"[WARNING] Negative f_ctrl_val ({f_ctrl_val}) in calc_required_ventilation_flow. Using 0.")
            f_ctrl_val = 0.0

        qv_oda_req_des_m3_h = 0.0 # Design required flow in m3/h, before control factor

        if building_function == "residential":
            # Base rate from NTA 8800 example for dwellings (0.9 dm3/s per m2 = 0.9 L/s per m2)
            qv_uspec_L_s_m2 = 0.9 # dm3/s is L/s
            # Total design required flow in L/s
            qv_oda_req_des_L_s = qv_uspec_L_s_m2 * floor_area_m2
            # Convert total design flow from L/s to m3/h (1 L/s = 3.6 m3/h)
            qv_oda_req_des_m3_h = qv_oda_req_des_L_s * 3.6

            # Apply control factor
            qv_oda_req_actual_m3_h = f_ctrl_val * qv_oda_req_des_m3_h

            # Enforce minimum ventilation rate for a dwelling (~126 m3/h = 35 L/s)
            # This minimum applies AFTER the control factor potentially reduces the calculated rate.
            residential_min_m3_h = 126.0
            if qv_oda_req_actual_m3_h < residential_min_m3_h and f_ctrl_val > 0: # Only apply minimum if control factor didn't intend to shut it off
                # print(f"[VENT INFO] Residential calculated vent {qv_oda_req_actual_m3_h:.1f} m3/h below minimum. Using {residential_min_m3_h} m3/h.")
                qv_oda_req_actual_m3_h = residential_min_m3_h
            elif f_ctrl_val == 0: # If control factor is zero, required flow is zero
                 qv_oda_req_actual_m3_h = 0.0


        else: # Non-residential
            # Base rates per m2 based on usage_key (examples, adjust as needed)
            # Rates in dm3/s per m2 (which is L/s per m2)
            usage_flow_map_L_s_m2 = {
                "office_area_based": 1.0,
                "childcare": 4.8,         # Example - high rate for childcare
                "retail": 0.6,
                # Add other keys from mappings.py if they need different rates
                # Ensure these keys match those produced by map_usage_key
                "meeting_function": 1.0,      # Example mapping (should match map_usage_key output)
                "healthcare_function": 1.2, # Example mapping
                "sport_function": 1.5,      # Example mapping
                "cell_function": 0.8,       # Example mapping
                "industrial_function": 0.5, # Example mapping
                "accommodation_function": 0.9,# Example mapping
                "education_function": 1.1,    # Example mapping
                "other_use_function": 0.6   # Example mapping (should match map_usage_key output)
            }
            # Use usage_key, fallback to a default non-res rate if key not found
            # A common default might be "office_area_based" or a generic "default_nonres"
            qv_usage_L_s_m2 = usage_flow_map_L_s_m2.get(usage_key, 1.0) # Default to 1.0 L/s/m2 if key unknown

            # Total design required flow in L/s
            qv_oda_req_des_L_s = qv_usage_L_s_m2 * floor_area_m2
            # Convert total design flow from L/s to m3/h
            qv_oda_req_des_m3_h = qv_oda_req_des_L_s * 3.6

            # Apply control factor
            qv_oda_req_actual_m3_h = f_ctrl_val * qv_oda_req_des_m3_h
            # Minimums for non-res are typically implicit in the design rates or specific to regulations,
            # but could be added here if needed per category.

        # Final conversion from calculated m3/h to m3/s
        total_vent_flow_m3_s = qv_oda_req_actual_m3_h / 3600.0
        return total_vent_flow_m3_s

    except Exception as e:
        print(f"[ERROR] Exception in calc_required_ventilation_flow: {e}")
        return 0.0


def calc_fan_power(fan_pressure_Pa, fan_total_efficiency, flow_rate_m3_s):
    """
    Compute fan power in Watts based on pressure rise, efficiency, and flow rate.

    Formula: P_fan = (fan_pressure_Pa * flow_rate_m3_s) / fan_total_efficiency

    Args:
        fan_pressure_Pa (float): Fan pressure rise in Pascals (Pa).
        fan_total_efficiency (float): Overall fan efficiency (0.0 < eff <= 1.0).
        flow_rate_m3_s (float): Air volume flow rate in m3/s.

    Returns:
        float: Fan power in Watts (W). Returns 0 if efficiency is invalid or flow is zero.
    """
    try:
        # Ensure inputs are numbers
        pressure = float(fan_pressure_Pa)
        flow = float(flow_rate_m3_s)
        efficiency = float(fan_total_efficiency)

        if efficiency <= 0 or efficiency > 1.0: # Efficiency must be a valid fraction
            print(f"[WARNING] Invalid fan_total_efficiency ({efficiency}) in calc_fan_power. Must be > 0 and <= 1.0. Returning 0 W.")
            return 0.0
        
        if flow == 0: # No flow, no power
            return 0.0
            
        if pressure < 0: # Negative pressure might imply energy recovery or error
             print(f"[WARNING] Negative fan_pressure_Pa ({pressure}) in calc_fan_power. Result may be unconventional.")
        if flow < 0: # Negative flow is physically problematic here
             print(f"[WARNING] Negative flow_rate_m3_s ({flow}) in calc_fan_power. Returning 0 W.")
             return 0.0

        fan_power_watts = (pressure * flow) / efficiency
        return fan_power_watts

    except Exception as e:
        print(f"[ERROR] Exception in calc_fan_power: {e}")
        return 0.0