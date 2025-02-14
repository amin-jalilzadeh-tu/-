import os
import pandas as pd
from sqlalchemy import create_engine, text

def load_buildings_from_db(filter_criteria=None):
    """
    Connect to the PostgreSQL database (credentials from environment variables),
    build a SQL query for building data, apply optional filters, and return a
    pandas DataFrame.

    filter_criteria (dict) may include:
    ------------------------------------------------------
    {
      "postcodes": ["1011AB", "1053PJ", ...],   # list of multiple postcodes
      "ids": [1001, 1002, 1003],               # list of ogc_fid
      "pand_ids": ["XYZ123", "XYZ456"],        # list of pand_id if needed
      "bbox_xy": [min_x, min_y, max_x, max_y], # bounding box in X/Y
      "bbox_latlon": [min_lat, min_lon, max_lat, max_lon] # bounding box in lat/lon
    }
    ------------------------------------------------------

    For example:
      "bbox_xy": [120000.0, 487000.0, 121000.0, 488000.0]
      "bbox_latlon": [52.35, 4.85, 52.37, 4.92]

    Returns
    -------
    pd.DataFrame
    """

    # 1) Read DB credentials from environment
    db_user = os.getenv("DB_USER", "postgres")
    db_password = os.getenv("DB_PASSWORD", "mysecret")
    db_host = os.getenv("DB_HOST", "localhost")
    db_port = os.getenv("DB_PORT", "5432")
    db_name = os.getenv("DB_NAME", "research")

    # 2) Create connection string
    connection_string = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

    # 3) Base query: adjust schema/table and columns to match your DB
    base_query = """
    SELECT 
        ogc_fid,
        pand_id,
        meestvoorkomendelabel,
        gem_hoogte,
        gem_bouwlagen,
        b3_dak_type,
        b3_opp_dak_plat,
        b3_opp_dak_schuin,
        x,
        y,
        lon,
        lat,
        postcode,
        area,
        perimeter,
        height,
        bouwjaar,
        age_range,
        average_wwr,
        building_function,
        residential_type,
        non_residential_type,
        north_side,
        east_side,
        south_side,
        west_side,
        building_orientation,
        building_orientation_cardinal
    FROM 
        amin.buildings_1
    """

    # 4) Prepare WHERE clauses and params for parameterized query
    where_clauses = []
    params = {}

    if filter_criteria is not None:
        # Multiple or single postcodes
        if "postcodes" in filter_criteria:
            # Using "IN" or "ANY" for a list of possible postcodes
            where_clauses.append("postcode = ANY(:postcodes_list)")
            params["postcodes_list"] = filter_criteria["postcodes"]

        # Building IDs (ogc_fid)
        if "ids" in filter_criteria:
            # "ANY" approach for integer array of ogc_fid
            where_clauses.append("ogc_fid = ANY(:ids_list)")
            params["ids_list"] = filter_criteria["ids"]

        # pand_ids (if your DB has separate ID references)
        if "pand_ids" in filter_criteria:
            # If these are strings, similarly
            where_clauses.append("pand_id = ANY(:pand_ids_list)")
            params["pand_ids_list"] = filter_criteria["pand_ids"]

        # Bounding box in X/Y
        if "bbox_xy" in filter_criteria:
            minx, miny, maxx, maxy = filter_criteria["bbox_xy"]
            where_clauses.append("x BETWEEN :minx AND :maxx")
            where_clauses.append("y BETWEEN :miny AND :maxy")
            params["minx"] = minx
            params["maxx"] = maxx
            params["miny"] = miny
            params["maxy"] = maxy

        # Bounding box in Lat/Lon
        if "bbox_latlon" in filter_criteria:
            min_lat, min_lon, max_lat, max_lon = filter_criteria["bbox_latlon"]
            where_clauses.append("lat BETWEEN :min_lat AND :max_lat")
            where_clauses.append("lon BETWEEN :min_lon AND :max_lon")
            params["min_lat"] = min_lat
            params["max_lat"] = max_lat
            params["min_lon"] = min_lon
            params["max_lon"] = max_lon

    # 5) Combine WHERE clauses
    if where_clauses:
        base_query += "\nWHERE " + " AND ".join(where_clauses)

    # 6) Execute query and return dataframe
    engine = create_engine(connection_string)
    with engine.connect() as conn:
        df = pd.read_sql(text(base_query), conn, params=params)
    return df
