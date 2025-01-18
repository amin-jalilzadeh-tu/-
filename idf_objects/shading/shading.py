# shading/shading.py

import json
import pandas as pd

from .shading_creator import create_shading_detailed
from .transmittance_schedules import create_tree_trans_schedule

def add_shading_to_idf(
    idf,
    building_row,
    df_bldg_shading,
    df_trees_shading,
    assigned_shading_log=None
):
    """
    Reads shading data from the two DataFrames (df_bldg_shading and df_trees_shading),
    which must already be top-N objects in local coords.
    
    Steps:
      1) Filter building-based shading objects for this building's ogc_fid
      2) Filter tree-based shading objects for this building
      3) Create a single "TreeTransSchedule" for all trees
      4) Create building shading surfaces (opaque)
      5) Create tree shading surfaces (partial transmittance)
      6) Log assigned shading info (optional)
    """
    focus_id = building_row.get("ogc_fid", 0)

    # 1) Subset the rows for this building
    df_bldg_sub = df_bldg_shading[df_bldg_shading["focus_ogc_fid"] == focus_id]
    df_trees_sub = df_trees_shading[df_trees_shading["focus_ogc_fid"] == focus_id]

    # 2) Create or update partial trans schedule for trees
    tree_schedule_name = "TreeTransSchedule"
    create_tree_trans_schedule(
        idf=idf,
        schedule_name=tree_schedule_name,
        summer_value=0.5,
        winter_value=0.9
    )

    # 3) For building-based shading objects: fully opaque => no schedule
    bldg_shade_rows = []
    for idx, row in df_bldg_sub.iterrows():
        shade_name = f"Shade_Bldg_{focus_id}_{row['edge_label']}_{row['object_id']}"
        # We pass "Name" and "vertices_local" to create_shading_detailed
        bldg_shade_rows.append({
            "Name": shade_name,
            "vertices_local": row["vertices_local"]
        })
    if bldg_shade_rows:
        df_bldg_shade = pd.DataFrame(bldg_shade_rows)
        create_shading_detailed(
            idf=idf,
            df_shades=df_bldg_shade,
            shading_type="SHADING:BUILDING:DETAILED",
            trans_schedule_name=None
        )

    # 4) For tree-based shading objects: partial trans => use tree schedule
    tree_shade_rows = []
    for idx, row in df_trees_sub.iterrows():
        shade_name = f"Shade_Tree_{focus_id}_{row['edge_label']}_{row['object_id']}"
        tree_shade_rows.append({
            "Name": shade_name,
            "vertices_local": row["vertices_local"]
        })
    if tree_shade_rows:
        df_tree_shade = pd.DataFrame(tree_shade_rows)
        create_shading_detailed(
            idf=idf,
            df_shades=df_tree_shade,
            shading_type="SHADING:BUILDING:DETAILED",
            trans_schedule_name=tree_schedule_name
        )

    # 5) Log assigned shading objects
    if assigned_shading_log is not None:
        assigned_shading_log[focus_id] = {
            "num_bldg_shades": len(bldg_shade_rows),
            "num_tree_shades": len(tree_shade_rows)
        }
