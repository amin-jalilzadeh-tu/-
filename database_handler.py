# database_handler.py

import os
import pandas as pd
from sqlalchemy import create_engine, text

def load_buildings_from_db(filter_criteria=None, filter_by=None):
    """
    Load buildings from DB using SQL 'DISTINCT ON (pand_id)' so that
    each pand_id appears only once in the result.

    :param filter_criteria: dict containing filter values; e.g.
        {
          "meestvoorkomendepostcode": ["1011AB"],
          "pand_id": ["0383100000001369"],
          "pand_ids": ["XYZ123", "XYZ999"],
          "bbox_xy": [minx, miny, maxx, maxy],
          "bbox_latlon": [min_lat, min_lon, max_lat, max_lon]
        }

    :param filter_by: str, one of:
        "meestvoorkomendepostcode", "pand_id", "pand_ids",
        "bbox_xy", or "bbox_latlon"

    :return: A pandas DataFrame with unique pand_ids (using DISTINCT ON).
    """

    # 1) Read DB credentials from environment
    db_user = os.getenv("DB_USER", "postgres")
    db_password = os.getenv("DB_PASSWORD"#, #"")
    db_host = os.getenv("DB_HOST", "db")
    db_port = os.getenv("DB_PORT", "5432")
    db_name = os.getenv("DB_NAME"#, #"")

    # 2) Create the connection string
    connection_string = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

    # 3) Use DISTINCT ON (pand_id) to fetch only one row per pand_id
    #    We'll pick the row with the *lowest* ogc_fid for each pand_id
    #    by ordering on (pand_id, ogc_fid).
    base_sql = """
SELECT DISTINCT ON (b.pand_id)
    b.ogc_fid,
    b.pand_id,
    b.meestvoorkomendelabel,
    b.gem_hoogte,
    b.gem_bouwlagen,
    b.b3_dak_type,
    b.b3_opp_dak_plat,
    b.b3_opp_dak_schuin,
    b.x,
    b.y,
    b.lon,
    b.lat,
    b.postcode,
    b.area,
    b.perimeter,
    b.height,
    b.bouwjaar,
    b.age_range,
    b.average_wwr,
    b.building_function,
    b.residential_type,
    b.non_residential_type,
    b.north_side,
    b.east_side,
    b.south_side,
    b.west_side,
    b.building_orientation,
    b.building_orientation_cardinal
FROM amin.buildings_1_deducted b
"""

    order_clause = "ORDER BY b.pand_id, b.ogc_fid"

    where_clauses = []
    params = {}

    # 4) Build WHERE clauses if filter_by is provided
    if filter_criteria and filter_by:
        if filter_by == "meestvoorkomendepostcode":
            where_clauses.append("b.meestvoorkomendepostcode = ANY(:mpostcodes)")
            params["mpostcodes"] = filter_criteria.get("meestvoorkomendepostcode", [])

        elif filter_by == "pand_id":
            where_clauses.append("b.pand_id = ANY(:pid)")
            params["pid"] = filter_criteria.get("pand_id", [])

        elif filter_by == "pand_ids":
            where_clauses.append("b.pand_id = ANY(:pids)")
            params["pids"] = filter_criteria.get("pand_ids", [])

        elif filter_by == "bbox_xy":
            minx, miny, maxx, maxy = filter_criteria.get("bbox_xy", [0, 0, 0, 0])
            where_clauses.append("b.x BETWEEN :minx AND :maxx AND b.y BETWEEN :miny AND :maxy")
            params.update({"minx": minx, "maxx": maxx, "miny": miny, "maxy": maxy})

        elif filter_by == "bbox_latlon":
            min_lat, min_lon, max_lat, max_lon = filter_criteria.get("bbox_latlon", [0, 0, 0, 0])
            where_clauses.append("b.lat BETWEEN :min_lat AND :max_lat AND b.lon BETWEEN :min_lon AND :max_lon")
            params.update({"min_lat": min_lat, "max_lat": max_lat, "min_lon": min_lon, "max_lon": max_lon})

    # 5) Build the final SQL string with WHERE (if needed) + ORDER BY
    if where_clauses:
        final_query_str = f"""
{base_sql}
WHERE {' AND '.join(where_clauses)}
{order_clause}
"""
    else:
        final_query_str = f"{base_sql}\n{order_clause}"

    # 6) Connect and fetch data into a DataFrame
    engine = create_engine(connection_string)
    with engine.connect() as conn:
        df = pd.read_sql(text(final_query_str), conn, params=params)

    # df now contains exactly one row per pand_id
    return df
