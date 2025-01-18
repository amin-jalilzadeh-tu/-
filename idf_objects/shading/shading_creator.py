# shading/shading_creator.py

import ast

def create_shading_detailed(
    idf, 
    df_shades,
    shading_type="SHADING:BUILDING:DETAILED",
    trans_schedule_name=None
):
    """
    Creates polygon-based shading surfaces in the given IDF, from each row in df_shades.
    Each row must have:
      - "Name"
      - "vertices_local" => a list of [x, y, z] coords
    """
    for idx, row in df_shades.iterrows():
        shade_name = row.get("Name", f"Shade_{idx}")

        vertices_local = row.get("vertices_local", [])
        # If it's stored as a string, parse it
        if isinstance(vertices_local, str):
            vertices_local = ast.literal_eval(vertices_local)

        # Skip if fewer than 3 points
        if len(vertices_local) < 3:
            continue

        shading_obj = idf.newidfobject(shading_type)
        shading_obj.Name = shade_name
        shading_obj.Number_of_Vertices = len(vertices_local)

        if trans_schedule_name is not None:
            shading_obj.Transmittance_Schedule_Name = trans_schedule_name

        # setcoords expects a list of (x, y, z) tuples
        shading_obj.setcoords(vertices_local)
