# main_idf_creation.py
import os
import logging
import pandas as pd

from geomeppy import IDF

# Geometry modules
from idf_objects.geomz.building import create_building_with_roof_type
from idf_objects.geomz.geometry_overrides_from_excel import read_geometry_overrides_excel

# Fenestration & Materials
from idf_objects.fenez.fenestration import add_fenestration
from idf_objects.fenez.materials import update_construction_materials, assign_constructions_to_surfaces

from idf_objects.fenez.dict_override_excel import override_dictionaries_from_excel

# Lighting
from idf_objects.Elec.lighting import add_lights_and_parasitics
#from idf_objects.Elec.elec_lookup import elec_lookup as default_elec_lookup
from idf_objects.Elec.lighting_lookup import lighting_lookup
from idf_objects.Elec.lighting_overrides_from_excel import (
    read_lighting_overrides_from_excel, 
    apply_lighting_overrides_to_lookup)
# DHW
from idf_objects.DHW.water_heater import add_dhw_to_idf
from idf_objects.DHW.dhw_lookup import dhw_lookup as default_dhw_lookup
from idf_objects.DHW import dhw_lookup as dhw_lookup_module
from idf_objects.DHW.dhw_overrides_from_excel import override_dhw_lookup_from_excel

# HVAC
from idf_objects.HVAC.custom_hvac import add_HVAC_Ideal_to_all_zones
from idf_objects.HVAC.hvac_lookup import hvac_lookup
from idf_objects.HVAC.hvac_overrides_from_excel import (
    read_hvac_overrides_from_excel, 
    apply_hvac_overrides_to_lookup
)
# Ventilation
from idf_objects.ventilation.add_ventilation import add_ventilation_to_idf
from idf_objects.ventilation.ventilation_lookup import ventilation_lookup
from idf_objects.ventilation.ventilation_overrides_from_excel import (
    read_ventilation_overrides_from_excel,
    apply_ventilation_overrides_to_lookup
)
# Zone Sizing
from idf_objects.setzone.add_outdoor_air_and_zone_sizing_to_all_zones import add_outdoor_air_and_zone_sizing_to_all_zones

# Ground Temps
from idf_objects.tempground.add_ground_temperatures import add_ground_temperatures

# Outputs & Simulations
from idf_objects.outputdef.assign_output_settings import assign_output_settings
from idf_objects.outputdef.add_output_definitions import add_output_definitions

from postproc.merge_results import merge_all_results
from idf_objects.other.zonelist import create_zonelist

# (1) Import your default epw_lookup

from epw.run_epw_sims import simulate_all
from epw.epw_lookup import epw_lookup
from epw.epw_overrides_from_excel import read_epw_overrides_from_excel, apply_epw_overrides_to_lookup



from idf_objects.fenez.data_materials_residential import residential_materials_data
from idf_objects.fenez.data_materials_non_residential import non_residential_materials_data


from idf_objects.shading.shading import add_shading_to_idf  # <-- The new shading integration


#######################################################
# 1) GLOBAL DICTIONARIES: OVERRIDE ONCE, AFTER IMPORTS
#######################################################
override_from_excel = False
excel_path = r"D:\Documents\E_Plus_2027_py\envelop.xlsx"

# Start by referencing the original dictionaries
res_data_dict = residential_materials_data
nonres_data_dict = non_residential_materials_data

# Perform the override if the file exists and the flag is True
if override_from_excel and os.path.isfile(excel_path):
    res_data_dict, nonres_data_dict = override_dictionaries_from_excel(
        excel_path=excel_path,
        default_res_data=res_data_dict,
        default_nonres_data=nonres_data_dict,
        default_roughness="MediumRough",
        fallback_wwr_range=(0.2, 0.3),
    )
    print("[Global] Overrode dictionaries from Excel.")
else:
    print("[Global] Using default dictionaries; no Excel override.")


###############################################
# 1) READ geometry_overrides.xlsx ONCE
###############################################
geom_excel_path = r"D:\Documents\E_Plus_2028_py\geometry_overrides.xlsx"
excel_rules = []
if os.path.isfile(geom_excel_path):
    excel_rules = read_geometry_overrides_excel(geom_excel_path)
    print(f"[main] Loaded {len(excel_rules)} geometry override rules from Excel.")
else:
    print("[main] No geometry_overrides.xlsx found; skipping...")


###############################################
# 1) READ dhw.xlsx ONCE
###############################################

# 1) Decide if we want to override from Excel at startup
override_dhw_from_excel = True
dhw_excel_path = r"D:\Documents\E_Plus_2028_py\dhw_overrides.xlsx"

# 2) If override is True and file exists => update the dictionary once
if override_dhw_from_excel and os.path.isfile(dhw_excel_path):
    updated_lookup = override_dhw_lookup_from_excel(dhw_excel_path, default_dhw_lookup)
    # Monkey-patch the module-level dictionary
    dhw_lookup_module.dhw_lookup = updated_lookup
    print("[Global] DHW lookup has been partially overridden from Excel.")
else:
    print("[Global] Using default DHW lookup with no Excel override.")




#### EPW LOOKUP #########

# Decide if we override from Excel
override_epw_from_excel = False
epw_excel_path = r"D:\Documents\E_Plus_2028_py\epw_overrides.xlsx"

if override_epw_from_excel and os.path.isfile(epw_excel_path):
    overrides = read_epw_overrides_from_excel(epw_excel_path)
    new_epw_lookup = apply_epw_overrides_to_lookup(epw_lookup, overrides)
    epw_lookup[:] = new_epw_lookup  # update in place
    print(f"[Global] Overrode epw_lookup from Excel with {len(overrides)} new or updated entries.")
else:
    print("[Global] Using default epw_lookup (no Excel override).")



###### LIGHTING LOOKUP #########
# 1) Decide if we override from Excel
override_lighting_from_excel = False
lighting_excel_path = r"D:\Documents\E_Plus_2028_py\lighting_overrides.xlsx"

if override_lighting_from_excel and os.path.isfile(lighting_excel_path):
    overrides = read_lighting_overrides_from_excel(lighting_excel_path)
    apply_lighting_overrides_to_lookup(lighting_lookup, overrides)
    print("[Global] Overrode lighting_lookup from Excel.")
else:
    print("[Global] Using default lighting_lookup (no Excel override).")




## HVAC LOOKUP #########
override_hvac_lookup_from_excel = False
hvac_excel_path = r"D:\Documents\E_Plus_2028_py\hvac_overrides.xlsx"

if override_hvac_lookup_from_excel and os.path.isfile(hvac_excel_path):
    hvac_overrides = read_hvac_overrides_from_excel(hvac_excel_path)
    apply_hvac_overrides_to_lookup(hvac_lookup, hvac_overrides)
    print("[Global] Overrode hvac_lookup from Excel.")
else:
    print("[Global] Using default hvac_lookup (no Excel override).")


## VENTILATION LOOKUP #########
# Decide if we override
override_vent_lookup_from_excel = False
vent_excel_path = r"D:\Documents\E_Plus_2028_py\ventilation_overrides.xlsx"

if override_vent_lookup_from_excel and os.path.isfile(vent_excel_path):
    override_data = read_ventilation_overrides_from_excel(vent_excel_path)
    apply_ventilation_overrides_to_lookup(ventilation_lookup, override_data)
    print("[Global] Overrode ventilation_lookup from Excel.")
else:
    print("[Global] Using default ventilation_lookup (no Excel override).")







#######################################################
# USER CONFIGS (override rules)
#######################################################
# 1) Geometry override rules
user_config_geom = [
    {
        "building_id": 4136730,
        "param_name": "perimeter_depth",
        "min_val": 3.5,
        "max_val": 4.0,
        "fixed_value": True
    },
    {
        "building_type": "Meeting Function",
        "param_name": "has_core",
        "fixed_value": True
    },
]

# 2) Lighting override rules
user_config_lighting = []
 #   {
 #       "building_id": 4136730,
 #       "param_name": "lights_wm2",
 #       "min_val": 8.0,
 ##       "max_val": 10.0
  #  },
  #  {
  #      "building_type": "residential",
  #      "param_name": "tN",
  #      "min_val": 100,
  ##      "max_val": 200
  #  },
  #  {
   #     "building_id": 4136731,
   #     "building_type": "non_residential",
   #     "param_name": "parasitic_wm2",
   ##     "min_val": 0.28,
    #    "max_val": 0.30
   # },
#]

# 3) DHW override rules
user_config_dhw = []
##    {
 #       "building_id": 4136730,
 #       "param_name": "occupant_density_m2_per_person",
 #       "fixed_value": None
 #   },
 #   {
 #       "dhw_key": "Office",
 #       "param_name": "setpoint_c",
 ##       "min_val": 58.0,
  ##      "max_val": 60.0
  #  }
#]

# 4) Fenestration / Materials override rules
#user_config_fenez = [
#    {
#        "building_id": 4136730,
#        "building_function": "residential",
#        "age_range": "1992 - 2005",
#        "scenario": "scenario1",
#        "param_name": "wwr",
#        "min_val": 0.25,
#        "max_val": 0.30
#    },
 #   {
 #       "building_function": "non_residential",
 #       "age_range": "2015 and later",
 #       "scenario": "scenario1",
 #       "param_name": "roof_R_value",
 #       "fixed_value": 3.0
 #   },
    # ...
#]

user_config_fenez = {}
    # Overwrite top-level WWR:
 #   "wwr": 0.32,

    # Overwrite top-level opaque material:
 #   "material_opaque_lookup": "Concrete_200mm",

    # Overwrite top-level window material:
 #   "material_window_lookup": "Glazing_Clear_3mm_Post",

    # Override sub-elements
 #   "elements": {
 #       "exterior_wall": {
 #           "R_value": 2.7,
 #           "U_value": 0.37,
 #           "material_opaque_lookup": "DoorPanel_Range"
 #       },
 #       "doors": {
 #           "U_value": 3.2,
 #           "material_opaque_lookup": "DoorPanel_Range"
 #       },
 #       "windows": {
 #           "area_m2": 36.0,
 #           "material_window_lookup": "Glazing_Clear_3mm"
 #       },
 #       "flat_roof": {
  #          "R_value": 3.5,
   #         "material_opaque_lookup": "Roof_Insulation_R5"
   #     }
   # }
#}















# 5) HVAC override rules
user_config_hvac = []
#    {
#        "building_id": 4136730,
#        "param_name": "heating_day_setpoint",
#        "min_val": 20.0,
#        "max_val": 21.0
#    },
#    {
#        "building_function": "residential",
#        "param_name": "cooling_day_setpoint",
#        "fixed_value": 25.0
#   },
#    {
#        "scenario": "scenario1",
#        "age_range": "2015 and later",
 #       "param_name": "max_heating_supply_air_temp",
  #      "min_val": 48.0,
 ##       "max_val": 50.0
#    },
#]

# 6) Ventilation override rules
user_config_vent = []
#    {"building_id": 4136730, "param_name": "infiltration_base", "min_val": 1.3, "max_val": 1.4},
#    {"building_function": "residential", "age_range": "1992 - 2005", "param_name": "year_factor", "min_val": 1.4, "max_val": 1.5},
#    {"building_id": 4136731, "param_name": "system_type", "fixed_value": "D"},
#    {"building_id": 4136731, "param_name": "fan_pressure", "min_val": 100, "max_val": 120},
#    # ...
#]

# 7) EPW override rules
#user_config_epw = [
#    {"building_id": 4136730, "fixed_epw_path": "C:/MyCustom.epw"},
#    {"desired_year": 2050, "override_year_to": 2018},
    # ...]



# Shading user config: can define strategy here or in each row
user_config_shading = [
    {
        "building_id": 4136730,
        "param_name": "top_n_buildings",
        "fixed_value": 5
    },
    {
        "building_function": "residential",
        "param_name": "summer_value",
        "min_val": 0.4,
        "max_val": 0.6
    },
    {
        "param_name": "top_n_trees",
        "fixed_value": 3
    },
    # etc...
]
assigned_shading_log = {}




#######################################################
# LOG DICTIONARIES FOR EACH COMPONENT
#######################################################
assigned_epw_log = {}
assigned_vent_log = {}
assigned_hvac_log = {}
assigned_fenez_log = {}
assigned_groundtemp_log = {}
assigned_setzone_log = {}

# geometry, lighting, dhw logs
assigned_geom_log = {}
assigned_lighting_log = {}
assigned_dhw_log = {}
assigned_shading_log = {}


#######################################################
# IDF CONFIG & GLOBALS
#######################################################
idf_config = {
    "iddfile": "D:/EnergyPlus/Energy+.idd",
    "idf_file_path": "D:/Minimal.idf",
    "output_dir": "output/output_IDFs"
}

CALIBRATION_STAGE = "pre_calibration"
STRATEGY = "B"
RANDOM_SEED = 42


df_bldg_shading = pd.read_csv("df_focus.csv")
df_trees_shading = pd.read_csv("df_trees.csv")


def create_idf_for_building(
    building_row,
    building_index,
    scenario,
    calibration_stage,
    strategy,
    # geometry & lighting overrides + logs
    user_config_geom=None,
    assigned_geom_log=None,
    user_config_lighting=None,
    assigned_lighting_log=None,
    # DHW overrides + logs
    user_config_dhw=None,
    assigned_dhw_log=None,
    # Fenez overrides + logs
    user_config_fenez=None,
    assigned_fenez_log=None,
    # HVAC overrides + logs
    user_config_hvac=None,
    assigned_hvac_log=None,
    # Ventilation overrides + logs
    user_config_vent=None,
    assigned_vent_log=None,
    # Zone sizing
    assigned_setzone_log=None,
    # Ground temps
    assigned_groundtemp_log=None,
    df_bldg_shading = df_bldg_shading,
    df_trees_shading = df_trees_shading,
    assigned_shading_log = None
    
):
    """
    Builds an IDF for a single building row, applying override+log for geometry, fenestration,
    lighting, DHW, HVAC, ventilation, zone sizing, ground temps.
    Saves the IDF to disk and returns the file name.
    """
    # 1) Setup IDF
    IDF.setiddname(idf_config["iddfile"])
    idf = IDF(idf_config["idf_file_path"])

    building_obj = idf.newidfobject("BUILDING")
    building_obj.Name = f"Sample_Building_{building_index}"

    orientation = building_row.get("building_orientation", 0.0)
    if not pd.isna(orientation):
        building_obj.North_Axis = orientation

    # 2) Geometry
    edge_types = []
    for side_col in ["north_side", "east_side", "south_side", "west_side"]:
        edge_types.append(building_row.get(side_col, "facade"))

    create_building_with_roof_type(
        idf=idf,
        area=building_row["area"],
        perimeter=building_row["perimeter"],
        orientation=orientation,
        building_row=building_row,
        edge_types=edge_types,
        calibration_stage=calibration_stage,
        strategy=strategy,
        random_seed=RANDOM_SEED,
        user_config=user_config_geom,
        assigned_geom_log=assigned_geom_log
    )

    # 3) Materials & Constructions (Fenez)
    # update_construction_materials(
       

    construction_map = update_construction_materials(
        idf=idf,
        building_row=building_row,
        building_index=building_index,  # pass the loop index
        scenario=scenario,
        calibration_stage=calibration_stage,
        strategy=strategy,
        random_seed=RANDOM_SEED,
        user_config_fenez=user_config_fenez,
        assigned_fenez_log=assigned_fenez_log
    )


    assign_constructions_to_surfaces(idf, construction_map)

    # 4) Fenestration
    add_fenestration(
        idf=idf,
        building_row=building_row,
        scenario=scenario,
        calibration_stage=calibration_stage,
        strategy=strategy,
        random_seed=RANDOM_SEED,
        user_config_fenez=user_config_fenez,
        assigned_fenez_log=assigned_fenez_log
        # e.g. use_computed_wwr=True, include_doors_in_wwr=False, ...
    )

    # Create a zone list
    create_zonelist(idf, zonelist_name="ALL_ZONES")

    # 5) Lighting
    add_lights_and_parasitics(
        idf=idf,
        building_row=building_row,
        calibration_stage=calibration_stage,
        strategy=strategy,
        random_seed=RANDOM_SEED,
        user_config=user_config_lighting,
        assigned_values_log=assigned_lighting_log
    )

    # 6) DHW

    # use_nta_flag = False
    #if building_row.get("building_function", "") in ["residential", "non_residential"]:
    #use_nta_flag = True

    add_dhw_to_idf(
        idf=idf,
        building_row=building_row,
        calibration_stage=calibration_stage,
        strategy=strategy,
        random_seed=RANDOM_SEED,
        name_suffix=f"MyDHW_{building_index}",
        user_config_dhw=user_config_dhw,
        assigned_dhw_log=assigned_dhw_log,
        use_nta=True    # <--- enable occupant usage from NTA   # use_nta_flag
    )

    # 7) HVAC
    add_HVAC_Ideal_to_all_zones(
        idf=idf,
        building_row=building_row,
        calibration_stage=calibration_stage,
        strategy=strategy,
        random_seed=RANDOM_SEED,
        user_config_hvac=user_config_hvac,
        assigned_hvac_log=assigned_hvac_log
    )

    # 8) Ventilation
    add_ventilation_to_idf(
        idf=idf,
        building_row=building_row,
        calibration_stage=calibration_stage,
        strategy=strategy,
        random_seed=RANDOM_SEED,
        user_config_vent=user_config_vent,
        assigned_vent_log=assigned_vent_log
    )

    # 9) Zone Sizing
    add_outdoor_air_and_zone_sizing_to_all_zones(
        idf=idf,
        building_row=building_row,
        calibration_stage=calibration_stage,
        strategy=strategy,
        random_seed=RANDOM_SEED,
        assigned_setzone_log=assigned_setzone_log
    )

    # 10) Ground Temps
    add_ground_temperatures(
        idf=idf,
        calibration_stage=calibration_stage,
        strategy=strategy,
        random_seed=RANDOM_SEED,
        assigned_groundtemp_log=assigned_groundtemp_log
    )








    # 11) Output definitions
    desired_vars = ["Facility Total Electric Demand Power", "Zone Air Temperature Maximum"]
    desired_meters = ["Electricity:Facility"]

    out_settings = assign_output_settings(
        desired_variables=desired_vars,
        desired_meters=desired_meters,
        override_variable_frequency="Hourly",
        override_meter_frequency="Hourly",
        include_tables=True,
        include_summary=True
    )
    add_output_definitions(idf, out_settings)

    # 12) Save IDF
    os.makedirs(idf_config["output_dir"], exist_ok=True)
    idf_filename = f"building_{building_index}.idf"
    out_path = os.path.join(idf_config["output_dir"], idf_filename)
    idf.save(out_path)
    print(f"[create_idf_for_building] IDF saved at: {out_path}")

    return idf_filename


def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logging.info("Starting main...")

    # 1) Load building data
    df_buildings = pd.read_csv("df_buildings.csv")








    # 2) Suppose we define or set 'desired_climate_year'
    desired_years = [2020] #, 2050]
    for i in range(len(df_buildings)):
        df_buildings.loc[i, "desired_climate_year"] = desired_years[i % len(desired_years)]

    scenario = "scenario1"
    calibration_stage = CALIBRATION_STAGE
    strategy = STRATEGY

    # 3) Create dictionaries to store final picks
    assigned_geom_log = {}
    assigned_lighting_log = {}
    assigned_dhw_log = {}
    assigned_fenez_log = {}
    assigned_hvac_log = {}
    assigned_vent_log = {}
    assigned_epw_log = {}
    assigned_groundtemp_log = {}
    assigned_setzone_log = {}

    # 4) Create IDFs for each building
    for idx, row in df_buildings.iterrows():
        print(f"--- Creating IDF for building index {idx} ---")
        idf_filename = create_idf_for_building(
            building_row=row,
            building_index=idx,
            scenario=scenario,
            calibration_stage=calibration_stage,
            strategy=strategy,
            # geometry
            user_config_geom=user_config_geom,
            assigned_geom_log=assigned_geom_log,
            # lighting
            user_config_lighting=user_config_lighting,
            assigned_lighting_log=assigned_lighting_log,
            # DHW
            user_config_dhw=user_config_dhw,
            assigned_dhw_log=assigned_dhw_log,
            
            # Fenez
            user_config_fenez=user_config_fenez,
            assigned_fenez_log=assigned_fenez_log,
            # HVAC
            user_config_hvac=user_config_hvac,
            assigned_hvac_log=assigned_hvac_log,
            # Vent
            user_config_vent=user_config_vent,
            assigned_vent_log=assigned_vent_log,
            # zone sizing
            assigned_setzone_log=assigned_setzone_log,
            # ground temps
            assigned_groundtemp_log=assigned_groundtemp_log
        )
        df_buildings.loc[idx, "idf_name"] = idf_filename

    # 5) EPW & Simulation
    idf_directory = idf_config["output_dir"]
    iddfile = idf_config["iddfile"]
    base_output_dir = "output/Sim_Results"
    num_workers = 4

    simulate_all(
        df_buildings=df_buildings,
        idf_directory=idf_directory,
        iddfile=iddfile,
        base_output_dir=base_output_dir,
        #user_config_epw=user_config_epw,   # pass EPW overrides
        assigned_epw_log=assigned_epw_log, # store final EPW picks
        num_workers=num_workers
    )

    # 6) Post-processing merges
    out_csv_as_is = "output/results/merged_as_is.csv"
    merge_all_results(
        base_output_dir=base_output_dir,
        output_csv=out_csv_as_is,
        convert_to_daily=False,
        convert_to_monthly=False
    )

    # Another example => daily mean
    out_csv_daily_mean = "output/results/merged_daily_mean.csv"
    merge_all_results(
        base_output_dir=base_output_dir,
        output_csv=out_csv_daily_mean,
        convert_to_daily=True,
        daily_aggregator="mean",
        convert_to_monthly=False
    )

    # 7) Write geometry picks to CSV
    geom_rows = []
    for bldg_id, param_dict in assigned_geom_log.items():
        for param_name, param_val in param_dict.items():
            geom_rows.append({
                "ogc_fid": bldg_id,
                "param_name": param_name,
                "assigned_value": param_val
            })
    df_geom = pd.DataFrame(geom_rows)
    df_geom.to_csv("output/assigned/assigned_geometry.csv", index=False)

    # 8) Lighting picks -> flatten sub-dicts (including fraction params)
    light_rows = []
    for bldg_id, param_dict in assigned_lighting_log.items():
        # param_dict e.g. {
        #   "lights_wm2": {
        #       "assigned_value": 15.2, "min_val":15.0, "max_val":17.0, "object_name":"LIGHTS"
        #    },
        #   "parasitic_wm2": {...},
        #   "lights_fraction_radiant": {...}, etc.
        # }
        for param_name, subdict in param_dict.items():
            assigned_val = subdict.get("assigned_value")
            min_v = subdict.get("min_val")
            max_v = subdict.get("max_val")
            obj_name = subdict.get("object_name", "")

            light_rows.append({
                "ogc_fid": bldg_id,
                "object_name": obj_name,
                "param_name": param_name,
                "assigned_value": assigned_val,
                "min_val": min_v,
                "max_val": max_v
            })

    df_lights = pd.DataFrame(light_rows)
    df_lights.to_csv("output/assigned/assigned_lighting.csv", index=False)
    print(df_lights)






















    # 10) Fenez picks
    # 10) Fenez picks
    fenez_rows = []
    for bldg_id, param_dict in assigned_fenez_log.items():
        for p_name, p_val in param_dict.items():
            fenez_rows.append({
                "ogc_fid": bldg_id,
                "param_name": p_name,
                "assigned_value": p_val
            })
    df_fenez = pd.DataFrame(fenez_rows)
    csv_path = "output/assigned/assigned_fenez_params.csv"
    df_fenez.to_csv(csv_path, index=False)
    print(f"[main] Wrote final fenestration/material picks to {csv_path}")































    # 11b) HVAC picks
    hvac_rows = []
    for bldg_id, param_dict in assigned_hvac_log.items():
        # param_dict might contain e.g.:
        # {
        #   "heating_day_setpoint": 20.2,
        #   "heating_day_setpoint_range": (19.0, 21.0),
        #   "heating_night_setpoint": 15.5,
        #   "heating_night_setpoint_range": (15.0, 16.0),
        #   ...
        # }

        # Approach #1: We just store them as separate entries,
        # param_name => param_value
        for bldg_id, param_dict in assigned_hvac_log.items():
            for param_name, param_val in param_dict.items():
                hvac_rows.append({
                    "ogc_fid": bldg_id,
                    "param_name": param_name,        # e.g. "schedule_day_start"
                    "assigned_value": param_val      # e.g. "07:00"
                })

    df_hvac = pd.DataFrame(hvac_rows)
    df_hvac.to_csv("output/assigned/assigned_hvac_params.csv", index=False)
    print("[main] Wrote final HVAC picks to assigned_hvac_params.csv")




    # 9) DHW picks
    dhw_rows = []
    for bldg_id, param_dict in assigned_dhw_log.items():
        for param_name, param_val in param_dict.items():
            dhw_rows.append({
                "ogc_fid": bldg_id,
                "param_name": param_name,   # e.g. "liters_per_person_per_day_range"
                "assigned_value": param_val
            })

    df_dhw = pd.DataFrame(dhw_rows)
    df_dhw.to_csv("output/assigned/assigned_dhw_params.csv", index=False)











    # 12) Vent picks
    vent_rows = []
    for bldg_id, param_dict in assigned_vent_log.items():
        for param_name, param_val in param_dict.items():
            vent_rows.append({
                "ogc_fid": bldg_id,
                "param_name": param_name,
                "assigned_value": param_val
            })
    df_vent = pd.DataFrame(vent_rows)
    df_vent.to_csv("output/assigned/assigned_ventilation.csv", index=False)


    # 13) EPW picks
    epw_rows = []
    for bldg_id, epw_path in assigned_epw_log.items():
        epw_rows.append({
            "ogc_fid": bldg_id,
            "epw_path": epw_path
        })
    df_epw_assigned = pd.DataFrame(epw_rows)
    df_epw_assigned.to_csv("output/assigned/assigned_epw_paths.csv", index=False)
    print(df_epw_assigned)

    # 14) Ground temps
    rows = []
    ground_temps = assigned_groundtemp_log.get("ground_temperatures", {})
    for month_name, temp_val in ground_temps.items():
        rows.append({
            "month": month_name,
            "temp_value": temp_val
        })
    df_ground = pd.DataFrame(rows)
    df_ground.to_csv("output/assigned/assigned_ground_temps.csv", index=False)
    print(df_ground)

    # 15) Zone Sizing
    setzone_rows = []
    for bldg_id, param_dict in assigned_setzone_log.items():
        for p_name, p_val in param_dict.items():
            setzone_rows.append({
                "ogc_fid": bldg_id,
                "param_name": p_name,
                "assigned_value": p_val
            })
    df_setzone = pd.DataFrame(setzone_rows)
    df_setzone.to_csv("output/assigned/assigned_setzone_params.csv", index=False)
    print(df_setzone)














    logging.info("All done with main.")


if __name__ == "__main__":
    main()
