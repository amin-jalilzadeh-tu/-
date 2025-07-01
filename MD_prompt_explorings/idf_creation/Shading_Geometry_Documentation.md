# Shading (Geometric) Module Documentation

## Overview
The Shading module (distinct from wshading which handles window blinds) creates geometric shading surfaces representing nearby buildings and trees that cast shadows on the simulated building. This affects solar heat gains and daylighting.

## Module Structure

### 1. shading.py (Main Orchestrator)

#### Purpose
Coordinates the addition of external shading objects from building and tree databases.

#### Input Data
- **building_row**: Current building being simulated
- **df_bldg_shading**: Database of nearby building shading objects
  ```csv
  ogc_fid,shade_name,X1,Y1,Z1,X2,Y2,Z2,X3,Y3,Z3,X4,Y4,Z4
  123,Shade_Bldg_1,0,0,0,10,0,0,10,10,0,0,10,0
  ```
- **df_trees_shading**: Database of tree shading objects
  ```csv
  ogc_fid,shade_name,X1,Y1,Z1,X2,Y2,Z2,X3,Y3,Z3,X4,Y4,Z4
  123,Shade_Tree_1,15,5,0,20,5,0,20,10,5,15,10,5
  ```

#### Processing Flow
1. **Filter by Building**: Select shading objects for current ogc_fid
2. **Create Building Shades**: Opaque surfaces from nearby buildings
3. **Create Tree Shades**: Semi-transparent surfaces with seasonal variation
4. **Apply Transmittance**: Trees get seasonal schedules

#### Key Functions
```python
def add_shading_from_databases(
    idf, 
    building_row, 
    df_bldg_shading, 
    df_trees_shading,
    building_prefix="Shade_Bldg_",
    tree_prefix="Shade_Tree_"
):
    # Filter shading objects
    building_shades = df_bldg_shading[
        df_bldg_shading['ogc_fid'] == building_row['ogc_fid']
    ]
    tree_shades = df_trees_shading[
        df_trees_shading['ogc_fid'] == building_row['ogc_fid']
    ]
    
    # Create opaque building shades
    create_shading_surfaces(idf, building_shades, shade_type="Building")
    
    # Create tree shades with transmittance
    tree_schedule = create_tree_transmittance_schedule(idf)
    create_shading_surfaces(
        idf, 
        tree_shades, 
        shade_type="Tree",
        transmittance_schedule=tree_schedule
    )
```

### 2. shading_creator.py

#### Purpose
Low-level creation of individual shading surface objects.

#### Function: create_shading_surfaces()
```python
def create_shading_surfaces(
    idf, 
    df_shades, 
    shade_type="Building",
    transmittance_schedule=None
):
    """
    Create SHADING:BUILDING:DETAILED objects from dataframe.
    
    Parameters:
    - idf: EnergyPlus IDF object
    - df_shades: DataFrame with shade names and vertices
    - shade_type: "Building" or "Tree" 
    - transmittance_schedule: Schedule name for partial shading
    """
```

#### Vertex Processing
```python
# Extract vertices from dataframe columns
vertices = []
for i in range(1, 5):  # Assumes 4 vertices (rectangular)
    x = row[f'X{i}']
    y = row[f'Y{i}']
    z = row[f'Z{i}']
    vertices.append((x, y, z))

# Handle variable vertex counts
if check_for_more_vertices(row):
    # Add additional vertices for complex shapes
    pass
```

#### IDF Object Creation
```python
shade = idf.newidfobject('SHADING:BUILDING:DETAILED')
shade.Name = shade_name
shade.Transmittance_Schedule_Name = transmittance_schedule or ""

# Add vertices
for i, (x, y, z) in enumerate(vertices, 1):
    setattr(shade, f'Vertex_{i}_Xcoordinate', x)
    setattr(shade, f'Vertex_{i}_Ycoordinate', y)
    setattr(shade, f'Vertex_{i}_Zcoordinate', z)
```

### 3. transmittance_schedules.py

#### Purpose
Creates seasonal transmittance schedules for vegetation shading.

#### Function: create_tree_transmittance_schedule()
```python
def create_tree_transmittance_schedule(
    idf,
    schedule_name="TreeTransmittanceSchedule",
    summer_transmittance=0.5,  # Leaf-on (more shading)
    winter_transmittance=0.9   # Leaf-off (less shading)
):
    """
    Create seasonal schedule for tree canopy transmittance.
    
    Summer (May-Sept): Lower transmittance (more leaves)
    Winter (Oct-April): Higher transmittance (fewer leaves)
    """
```

#### Schedule Creation
```python
schedule = idf.newidfobject('SCHEDULE:COMPACT')
schedule.Name = schedule_name
schedule.Schedule_Type_Limits_Name = "Fraction"

# Define seasonal periods
schedule.Field_1 = "Through: 04/30"
schedule.Field_2 = "For: AllDays"
schedule.Field_3 = "Until: 24:00"
schedule.Field_4 = winter_transmittance

schedule.Field_5 = "Through: 09/30"
schedule.Field_6 = "For: AllDays"
schedule.Field_7 = "Until: 24:00"
schedule.Field_8 = summer_transmittance

schedule.Field_9 = "Through: 12/31"
schedule.Field_10 = "For: AllDays"
schedule.Field_11 = "Until: 24:00"
schedule.Field_12 = winter_transmittance
```

## IDF Objects Created

### SHADING:BUILDING:DETAILED (Opaque)
For nearby buildings:
```
Shading:Building:Detailed,
    Shade_Bldg_1,           ! Name
    ,                       ! Transmittance Schedule Name (blank=opaque)
    4,                      ! Number of Vertices
    0.0, 0.0, 0.0,         ! X,Y,Z Vertex 1
    10.0, 0.0, 0.0,        ! X,Y,Z Vertex 2
    10.0, 10.0, 0.0,       ! X,Y,Z Vertex 3
    0.0, 10.0, 0.0;        ! X,Y,Z Vertex 4
```

### SHADING:BUILDING:DETAILED (Trees)
With seasonal transmittance:
```
Shading:Building:Detailed,
    Shade_Tree_1,                    ! Name
    TreeTransmittanceSchedule,       ! Transmittance Schedule Name
    4,                               ! Number of Vertices
    15.0, 5.0, 0.0,                 ! X,Y,Z Vertex 1
    20.0, 5.0, 0.0,                 ! X,Y,Z Vertex 2
    20.0, 10.0, 5.0,                ! X,Y,Z Vertex 3
    15.0, 10.0, 5.0;                ! X,Y,Z Vertex 4
```

### SCHEDULE:COMPACT (Tree Transmittance)
```
Schedule:Compact,
    TreeTransmittanceSchedule,       ! Name
    Fraction,                        ! Schedule Type Limits Name
    Through: 04/30,                  ! Field 1
    For: AllDays,                    ! Field 2
    Until: 24:00, 0.9,              ! Field 3-4 (Winter - less shade)
    Through: 09/30,                  ! Field 5
    For: AllDays,                    ! Field 6
    Until: 24:00, 0.5,              ! Field 7-8 (Summer - more shade)
    Through: 12/31,                  ! Field 9
    For: AllDays,                    ! Field 10
    Until: 24:00, 0.9;              ! Field 11-12 (Winter again)
```

## Key Features

### 1. Building Shading
- Fully opaque surfaces
- Represents neighboring buildings
- Static throughout year
- Affects both direct and diffuse solar

### 2. Tree Shading
- Partially transparent
- Seasonal variation (leaf-on/leaf-off)
- Can model deciduous trees realistically
- Allows some diffuse light through

### 3. Coordinate System
- Uses building-relative coordinates
- X: East-West (East positive)
- Y: North-South (North positive)
- Z: Vertical (Up positive)

### 4. Performance Considerations
- Too many shading surfaces slow simulation
- Group small shades when possible
- Consider distance cutoffs
- Use simplified geometry for distant objects

## Input Data Requirements

### Building Shading Database
- Building ID (ogc_fid)
- Shade surface name
- Vertex coordinates (minimum 3, typically 4)
- Heights representing actual building geometry

### Tree Shading Database
- Building ID (ogc_fid)
- Tree shade name
- Vertex coordinates representing canopy
- Heights at canopy level

## Integration Notes

1. **Preprocessing**: Shading databases created from GIS analysis
2. **Coordinate Transform**: Must be in building-local coordinates
3. **Timing**: Added after building geometry but before simulation
4. **Validation**: Check for self-shading and invalid surfaces

## Best Practices

1. **Simplification**: Use rectangular approximations when possible
2. **Distance Filtering**: Only include shades within reasonable distance
3. **Height Accuracy**: Ensure shade heights match actual obstructions
4. **Tree Modeling**: Use appropriate transmittance values for tree species
5. **Seasonal Variation**: Adjust schedule dates for local climate

## Future Enhancements

1. **Dynamic Shading**: Time-varying positions (e.g., moveable awnings)
2. **Complex Transmittance**: Wavelength-dependent properties
3. **Shading Groups**: Aggregate similar shades for performance
4. **Automated Generation**: From 3D city models or LIDAR data
5. **Reflection Modeling**: Account for reflected radiation from shades