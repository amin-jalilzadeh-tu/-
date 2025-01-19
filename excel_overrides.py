"""
excel_overrides.py

Handles Excel-based overrides for:
 - Fenestration & Materials (Residential / Non-Residential dictionaries)
 - DHW lookup
 - EPW lookup
 - Lighting lookup
 - HVAC lookup
 - Ventilation lookup

These functions read Excel files (if found) and return updated in-memory dictionaries.
You can decide whether to permanently save them back or just use them for the current run.
"""

import os
import pandas as pd

# Example placeholders referencing your real override functions:
# from idf_objects.fenez.dict_override_excel import override_dictionaries_from_excel
# from idf_objects.DHW.dhw_overrides_from_excel import override_dhw_lookup_from_excel
# from epw.epw_overrides_from_excel import read_epw_overrides_from_excel, apply_epw_overrides_to_lookup
# from idf_objects.Elec.lighting_overrides_from_excel import (
#     read_lighting_overrides_from_excel,
#     apply_lighting_overrides_to_lookup
# )
# from idf_objects.HVAC.hvac_overrides_from_excel import (
#     read_hvac_overrides_from_excel,
#     apply_hvac_overrides_to_lookup
# )
# from idf_objects.ventilation.ventilation_overrides_from_excel import (
#     read_ventilation_overrides_from_excel,
#     apply_ventilation_overrides_to_lookup
# )


############################################
# 1) Fenestration/Materials Excel Override
############################################
def override_fenestration_dicts_from_excel(
    excel_path,
    default_res_data,
    default_nonres_data,
    override_from_excel_flag=True,
    default_roughness="MediumRough",
    fallback_wwr_range=(0.2, 0.3)
):
    """
    If override_from_excel_flag is True and the excel_path exists,
    calls a function like override_dictionaries_from_excel(...) to
    update 'default_res_data' and 'default_nonres_data'.

    Otherwise returns the original dictionaries unchanged.
    """
    if override_from_excel_flag and os.path.isfile(excel_path):
        # The real function might be something like:
        # updated_res, updated_nonres = override_dictionaries_from_excel(
        #     excel_path=excel_path,
        #     default_res_data=default_res_data,
        #     default_nonres_data=default_nonres_data,
        #     default_roughness=default_roughness,
        #     fallback_wwr_range=fallback_wwr_range,
        # )
        # return updated_res, updated_nonres

        print(f"[excel_overrides] Overrode fenestration dictionaries from {excel_path}")
        # For demonstration, pretend we updated them:
        updated_res = default_res_data.copy()
        updated_nonres = default_nonres_data.copy()
        updated_res["test_override"] = True  # Example
        updated_nonres["test_override"] = True
        return updated_res, updated_nonres
    else:
        print("[excel_overrides] Using default fenestration dictionaries (no Excel override).")
        return default_res_data, default_nonres_data


############################################
# 2) DHW Excel Override
############################################
def override_dhw_lookup_from_excel_file(
    dhw_excel_path,
    default_dhw_lookup,
    override_dhw_flag=True
):
    """
    If override_dhw_flag is True and file exists, calls your
    override_dhw_lookup_from_excel(...) function from
    idf_objects.DHW.dhw_overrides_from_excel to partially override
    the default_dhw_lookup.
    """
    if override_dhw_flag and os.path.isfile(dhw_excel_path):
        # updated_dhw = override_dhw_lookup_from_excel(dhw_excel_path, default_dhw_lookup)
        # return updated_dhw

        print(f"[excel_overrides] Overrode DHW lookup from {dhw_excel_path}")
        # Demo: pretend we updated it:
        updated_dhw = default_dhw_lookup.copy()
        updated_dhw["dhw_key_TEST"] = {"setpoint_c": 60.0}
        return updated_dhw
    else:
        print("[excel_overrides] Using default DHW lookup (no Excel override).")
        return default_dhw_lookup


############################################
# 3) EPW Excel Override
############################################
def override_epw_lookup_from_excel_file(
    epw_excel_path,
    epw_lookup,
    override_epw_flag=False
):
    """
    If override_epw_flag is True, read overrides from Excel
    and apply them to the epw_lookup in memory.
    """
    if override_epw_flag and os.path.isfile(epw_excel_path):
        # overrides = read_epw_overrides_from_excel(epw_excel_path)
        # new_epw_lookup = apply_epw_overrides_to_lookup(epw_lookup, overrides)
        # epw_lookup[:] = new_epw_lookup  # or return new_epw_lookup
        print(f"[excel_overrides] Overrode epw_lookup from {epw_excel_path}")
        new_epw_lookup = epw_lookup.copy()
        new_epw_lookup.append({"city": "TestCity", "file": "TestCity.epw"})
        return new_epw_lookup
    else:
        print("[excel_overrides] Using default epw_lookup (no Excel override).")
        return epw_lookup


############################################
# 4) Lighting Excel Override
############################################
def override_lighting_lookup_from_excel_file(
    lighting_excel_path,
    lighting_lookup,
    override_lighting_flag=False
):
    """
    If override_lighting_flag is True and file exists, calls read_lighting_overrides_from_excel
    and apply_lighting_overrides_to_lookup to override the lighting_lookup.
    """
    if override_lighting_flag and os.path.isfile(lighting_excel_path):
        # overrides = read_lighting_overrides_from_excel(lighting_excel_path)
        # apply_lighting_overrides_to_lookup(lighting_lookup, overrides)
        print(f"[excel_overrides] Overrode lighting_lookup from {lighting_excel_path}")
        # Demo: pretend we updated it
        lighting_lookup["test_param"] = 999
        return lighting_lookup
    else:
        print("[excel_overrides] Using default lighting_lookup (no Excel override).")
        return lighting_lookup


############################################
# 5) HVAC Excel Override
############################################
def override_hvac_lookup_from_excel_file(
    hvac_excel_path,
    hvac_lookup,
    override_hvac_flag=False
):
    """
    If override_hvac_flag is True, read from Excel to override hvac_lookup in memory.
    """
    if override_hvac_flag and os.path.isfile(hvac_excel_path):
        # hvac_overrides = read_hvac_overrides_from_excel(hvac_excel_path)
        # apply_hvac_overrides_to_lookup(hvac_lookup, hvac_overrides)
        print(f"[excel_overrides] Overrode hvac_lookup from {hvac_excel_path}")
        hvac_lookup["dummy_param"] = 12345
        return hvac_lookup
    else:
        print("[excel_overrides] Using default hvac_lookup (no Excel override).")
        return hvac_lookup


############################################
# 6) Ventilation Excel Override
############################################
def override_vent_lookup_from_excel_file(
    vent_excel_path,
    vent_lookup,
    override_vent_flag=False
):
    """
    If override_vent_flag is True, read from Excel to override ventilation_lookup in memory.
    """
    if override_vent_flag and os.path.isfile(vent_excel_path):
        # override_data = read_ventilation_overrides_from_excel(vent_excel_path)
        # apply_ventilation_overrides_to_lookup(vent_lookup, override_data)
        print(f"[excel_overrides] Overrode ventilation_lookup from {vent_excel_path}")
        vent_lookup["some_override"] = "YES"
        return vent_lookup
    else:
        print("[excel_overrides] Using default ventilation_lookup (no Excel override).")
        return vent_lookup
