# ventilation/calc_functions.py

import math

def calc_infiltration(
    infiltration_base,  # e.g. assigned["infiltration_base"] from assign_ventilation_values
    year_factor,        # assigned["year_factor"] from overrides
    flow_exponent,      # typically 0.67 (standard infiltration exponent)
    floor_area_m2       # total building area
):
    """
    Calculate infiltration in m3/s based on an 'infiltration_base' at 10 Pa.

    Steps:
      1) Multiply infiltration_base by year_factor => qv10_lea_ref (represents
         infiltration at 10 Pa for the building, e.g. in dm3/s·m2 or similar).
      2) Convert qv10 => qv1 by applying exponent:
            qv1 = qv10 * (1/10)^n
         (n = flow_exponent, e.g. 0.67 per NTA 8800).
      3) Multiply qv1_lea_ref_per_m2_h by total floor area => infiltration_m3/h.
      4) Convert infiltration_m3/h => infiltration_m3/s by dividing by 3600.

    NTA 8800 basis:
      - Table 11.2 prescribes n=0.67 for leak losses (infiltration).
      - Section 11.2.5 references how infiltration is often reported at 10 Pa
        and needs converting to 1 Pa. This code parallels that approach.

    Returns infiltration in m3/s.
    """

    # 1) infiltration_base * year_factor => infiltration at 10 Pa
    qv10_lea_ref = infiltration_base * year_factor

    # 2) Convert from qv10 to qv1 by (1/10)^exponent
    qv1_lea_ref_per_m2_h = qv10_lea_ref * (1.0 / 10.0)**flow_exponent

    # 3) Multiply by floor area => infiltration in m3/h
    infiltration_m3_h = qv1_lea_ref_per_m2_h * floor_area_m2

    # 4) Convert from m3/h => m3/s
    infiltration_m3_s = infiltration_m3_h / 3600.0
    return infiltration_m3_s


def calc_required_ventilation_flow(
    building_function,
    f_ctrl_val,
    floor_area_m2,
    usage_key=None
):
    """
    Calculate the required ventilation flow (m3/s).

    Approach:
      - If residential: 0.9 dm3/s/m2 is used as base, then multiplied by
        control factor (f_ctrl_val). A minimum of ~126 m3/h is enforced.
        => 126 m3/h = 35 L/s, typical minimal design flow for dwellings.

      - If non-residential: usage_key (office_area_based, childcare, retail, etc.)
        references typical design flows (dm3/s/m2). Then multiplied by f_ctrl_val.

    NTA 8800 basis:
      - In Section 11.2.2.5 or Table 11.8, typical air supply rates are given
        for various functions. This code uses simplified example values.

    Returns flow in m3/s.
    """

    if building_function == "residential":
        # base usage flow in dm3/s
        qv_uspec = 0.9
        # multiply by floor area => dm3/s
        qv_oda_req_des_dm3_s = qv_uspec * floor_area_m2
        # convert to m3/h
        qv_oda_req_des_m3_h = qv_oda_req_des_dm3_s * 3.6

        # apply control factor
        qv_oda_req_m3_h = f_ctrl_val * qv_oda_req_des_m3_h

        # enforce minimum ~126 m3/h
        if qv_oda_req_m3_h < 126:
            qv_oda_req_m3_h = 126

        # return m3/s
        return qv_oda_req_m3_h / 3600.0

    else:
        # non-res => usage_key references typical design rates
        usage_flow_map = {
            "office_area_based": 1.0,  # dm3/s per m2
            "childcare": 4.8,
            "retail": 0.6
        }
        qv_usage = usage_flow_map.get(usage_key, 1.0)  # fallback 1.0 dm3/s/m2
        qv_oda_req_des_dm3_s = qv_usage * floor_area_m2
        qv_oda_req_des_m3_h  = qv_oda_req_des_dm3_s * 3.6

        # apply control factor
        qv_oda_req_m3_h = f_ctrl_val * qv_oda_req_des_m3_h
        return qv_oda_req_m3_h / 3600.0


def calc_fan_power(fan_pressure, fan_efficiency, flow_m3_s):
    """
    Compute fan power in W:
      P_fan = (fan_pressure * flow_m3_s) / fan_efficiency

    NTA 8800 doesn't provide a direct formula for fan power in W in exactly
    these terms, but this approach is standard fluid power:
       Pressure (Pa) * Volumetric Flow (m3/s) = Power in J/s (Watts),
       then / efficiency to account for fan energy losses.

    fan_pressure: Pa
    flow_m3_s: m3/s
    fan_efficiency: fraction (0.0 < eff <= 1.0)
    returns: fan power in Watts
    """
    if fan_efficiency <= 0:
        fan_efficiency = 0.7
    return (fan_pressure * flow_m3_s) / fan_efficiency
