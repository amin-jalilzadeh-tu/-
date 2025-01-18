# other/zonelist.py
def create_zonelist(idf, zonelist_name="ALL_ZONES"):
    # Check if a ZoneList with zonelist_name already exists
    zone_lists = idf.idfobjects["ZONELIST"]
    for zl in zone_lists:
        if zl.Name.upper() == zonelist_name.upper():
            print(f"ZoneList '{zonelist_name}' already exists.")
            return zl
    
    # Get all the Zone objects from the IDF
    zones = idf.idfobjects["ZONE"]
    if not zones:
        print("No zones found in the IDF file.")
        return None
    
    # Create a new ZONELIST object
    zonelist_obj = idf.newidfobject("ZONELIST")
    zonelist_obj.Name = zonelist_name
    
    # Loop through the zones and assign them to Zone_1_Name, Zone_2_Name, etc.
    for i, zone in enumerate(zones):
        field_name = f"Zone_{i+1}_Name"  # Use underscores
        zonelist_obj[field_name] = zone.Name
    
    print(f"ZoneList '{zonelist_name}' created with zones: {[z.Name for z in zones]}")
    return zonelist_obj