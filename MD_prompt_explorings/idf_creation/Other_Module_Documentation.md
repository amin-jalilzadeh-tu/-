# Other Module Documentation

## Overview
The "other" module contains utility functions that don't fit into specific IDF object categories. Currently, it primarily contains the zonelist creation functionality.

## Module: zonelist.py

### Purpose
Creates a ZONELIST object in EnergyPlus that groups multiple thermal zones together. This enables applying settings (like equipment, lighting, or HVAC controls) to multiple zones simultaneously using a single reference.

### Function: create_zonelist()

#### Input Parameters
```python
def create_zonelist(idf, zonelist_name="ALL_ZONES"):
    """
    Create a ZONELIST object containing all zones in the IDF.
    
    Parameters:
    - idf: The EnergyPlus IDF object
    - zonelist_name: Name for the zonelist (default: "ALL_ZONES")
    """
```

#### Processing Logic

1. **Duplicate Check**:
   ```python
   # Check if zonelist already exists
   existing_zonelists = idf.idfobjects.get("ZONELIST", [])
   for zl in existing_zonelists:
       if zl.Name == zonelist_name:
           return zl  # Return existing zonelist
   ```

2. **Zone Collection**:
   ```python
   # Get all zone objects
   zones = idf.idfobjects.get("ZONE", [])
   if not zones:
       return None  # No zones to add
   ```

3. **Zonelist Creation**:
   ```python
   # Create new zonelist object
   zonelist = idf.newidfobject("ZONELIST")
   zonelist.Name = zonelist_name
   
   # Add zones dynamically
   for i, zone in enumerate(zones, 1):
       field_name = f"Zone_{i}_Name"
       setattr(zonelist, field_name, zone.Name)
   ```

### IDF Object Created

**ZONELIST**:
```
ZoneList,
    ALL_ZONES,              ! Name
    Thermal Zone 1,         ! Zone 1 Name
    Thermal Zone 2,         ! Zone 2 Name
    Thermal Zone 3,         ! Zone 3 Name
    Core_Zone,              ! Zone 4 Name
    Perimeter_North,        ! Zone 5 Name
    Perimeter_South;        ! Zone 6 Name
```

### Usage in Other Modules

The created zonelist is referenced by:

1. **Lighting Module**:
   ```
   Lights,
       Lights_ALL_ZONES,
       ALL_ZONES,          ! Zone or ZoneList Name
       LightsSchedule,
       Watts/Area,
       ,
       10.0;
   ```

2. **Equipment Module**:
   ```
   ElectricEquipment,
       Equip_ALL_ZONES,
       ALL_ZONES,          ! Zone or ZoneList Name
       EquipSchedule,
       Watts/Area,
       ,
       5.0;
   ```

3. **DHW Module** (indirectly through zone references)

4. **HVAC Controls** (when applying to multiple zones)

### Benefits of Using Zonelists

1. **Simplified Application**: Apply settings to all zones with one object
2. **Consistency**: Ensures uniform settings across zones
3. **Maintenance**: Easy to update - changes apply to all zones
4. **Flexibility**: Can create multiple zonelists for different zone groups

### Advanced Usage Examples

#### Creating Perimeter-Only Zonelist
```python
def create_perimeter_zonelist(idf):
    zones = idf.idfobjects.get("ZONE", [])
    perimeter_zones = [z for z in zones if "Perimeter" in z.Name]
    
    zonelist = idf.newidfobject("ZONELIST")
    zonelist.Name = "PERIMETER_ZONES"
    
    for i, zone in enumerate(perimeter_zones, 1):
        setattr(zonelist, f"Zone_{i}_Name", zone.Name)
    
    return zonelist
```

#### Creating Floor-Specific Zonelists
```python
def create_floor_zonelists(idf):
    zones = idf.idfobjects.get("ZONE", [])
    floors = {}
    
    # Group zones by floor
    for zone in zones:
        floor_num = extract_floor_number(zone.Name)
        if floor_num not in floors:
            floors[floor_num] = []
        floors[floor_num].append(zone)
    
    # Create zonelist for each floor
    for floor_num, floor_zones in floors.items():
        zonelist = idf.newidfobject("ZONELIST")
        zonelist.Name = f"FLOOR_{floor_num}_ZONES"
        
        for i, zone in enumerate(floor_zones, 1):
            setattr(zonelist, f"Zone_{i}_Name", zone.Name)
```

### Error Handling

1. **No Zones**: Returns None if no zones exist
2. **Duplicate Names**: Checks for existing zonelist before creating
3. **Field Limits**: EnergyPlus has maximum field counts - handled by IDF object

### Integration Notes

- Called after all zones are created in geometry module
- Must be called before equipment/lighting modules that reference it
- Name "ALL_ZONES" is hardcoded in several modules - maintain consistency

### Future Enhancements

Potential additions to the "other" module:
1. **Schedule utilities**: Common schedule creation functions
2. **Material utilities**: Shared material property functions
3. **Validation utilities**: IDF consistency checks
4. **Naming utilities**: Standardized object naming functions
5. **Unit conversion**: Helper functions for unit conversions