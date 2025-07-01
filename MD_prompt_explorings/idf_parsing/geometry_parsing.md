# Geometry and Envelope Parsing Documentation

## Overview
The geometry parsing module extracts building geometry and envelope data from IDF files and SQL simulation results. This includes zones, surfaces (walls, floors, roofs), windows, doors, and their thermal properties.

## IDF Objects Parsed

### 1. ZONE
Thermal zone definitions.

**Parameters Extracted:**
- Zone Name
- `floor_area`: Floor Area (m²) - if specified
- `volume`: Volume (m³) - if specified
- `ceiling_height`: Ceiling Height (m) - if specified
- `zone_multiplier`: Multiplier
- X,Y,Z Origin coordinates
- Type (default: 1)
- Part of Total Floor Area (Yes/No)

### 2. BUILDINGSURFACE:DETAILED
Detailed surface geometry (walls, floors, roofs).

**Parameters Extracted:**
- Surface Name
- Surface Type (Wall, Floor, Roof, Ceiling)
- Construction Name
- Zone Name
- Outside Boundary Condition
- Outside Boundary Condition Object
- Sun Exposure
- Wind Exposure
- View Factor to Ground
- `vertices`: Number of Vertices
- Vertex coordinates (X,Y,Z for each vertex)
- `area`: Calculated Surface Area (m²)
- `azimuth`: Azimuth angle (degrees)
- `tilt`: Tilt angle (degrees)

### 3. FENESTRATIONSURFACE:DETAILED
Window and door surfaces.

**Parameters Extracted:**
- Surface Name
- Surface Type (Window, Door, GlassDoor)
- Construction Name
- Building Surface Name (host surface)
- Outside Boundary Condition Object
- View Factor to Ground
- Shading Control Name
- Frame and Divider Name
- Multiplier
- Number of Vertices
- Vertex coordinates
- `area`: Surface Area (m²)

### 4. Simple Geometry Objects

#### FLOOR:DETAILED, WALL:DETAILED, ROOFCEILING:DETAILED
Simplified surface input methods.

**Parameters Extracted:**
- Similar to BUILDINGSURFACE:DETAILED but with simplified input

#### WINDOW, DOOR, GLAZEDDOOR
Simplified fenestration input.

**Parameters Extracted:**
- Similar to FENESTRATIONSURFACE:DETAILED but with simplified input

### 5. GLOBALGEOMETRYRULES
Rules for interpreting geometry.

**Parameters Extracted:**
- Starting Vertex Position
- Vertex Entry Direction
- Coordinate System
- Daylighting Reference Point Coordinate System
- Rectangular Surface Coordinate System

### 6. Other Geometry Objects
- INTERIORSTARTINGPOINT: Starting point for interior zone
- DAYLIGHTINGDEVICE:TUBULAR: Tubular daylighting devices
- ZONELIST: Groups of zones

## SQL Variables Extracted

1. **Zone Mean Air Temperature** (°C)
2. **Zone Air Temperature** (°C)
3. **Zone Thermal Comfort Mean Radiant Temperature** (°C)
4. **Zone Total Internal Total Heat Gain Rate** (W)
5. **Zone Total Internal Total Heat Gain Energy** (J)
6. **Surface Inside Face Temperature** (°C)
7. **Surface Outside Face Temperature** (°C)
8. **Surface Inside Face Conduction Heat Transfer Rate** (W)
9. **Surface Outside Face Conduction Heat Transfer Rate** (W)

## Key Metrics Calculated

1. **Total Floor Area**
   - Sum of all zone floor areas (considering multipliers)
   - Units: m²

2. **Total Volume**
   - Sum of all zone volumes
   - Units: m³

3. **Window-Wall Ratio (WWR)**
   - Ratio of window area to gross wall area
   - Calculated per orientation and total
   - Units: fraction (0-1)

4. **Envelope Area**
   - Total area of exterior surfaces
   - Broken down by surface type

5. **Average Ceiling Height**
   - Volume divided by floor area
   - Units: m

## Output Structure

### IDF Data Output
```
parsed_data/
└── idf_data/
    └── building_{id}/
        ├── geometry_zones.parquet
        └── geometry_surfaces.parquet
```

**geometry_zones.parquet columns:**
- building_id
- zone_name
- floor_area
- volume
- ceiling_height
- multiplier
- origin_x, origin_y, origin_z
- part_of_total_floor_area

**geometry_surfaces.parquet columns:**
- building_id
- zone_name
- surface_name
- surface_type
- construction_name
- area
- azimuth
- tilt
- outside_boundary_condition
- sun_exposure
- wind_exposure
- vertex_count
- vertex_coordinates (as JSON)

### SQL Timeseries Output
```
parsed_data/
└── timeseries/
    └── base_all_daily.parquet (for base buildings)
    └── comparisons/
        └── comparison_{building_id}.parquet (for variants)
```

## Data Processing Notes

1. **Coordinate Systems**: EnergyPlus supports multiple coordinate systems - the parser handles conversions.

2. **Surface Matching**: Interior surfaces are matched between zones for proper heat transfer.

3. **Area Calculations**: Surface areas are calculated from vertex coordinates.

4. **Orientation Analysis**: Azimuth angles determine surface orientation for solar analysis.

5. **Multipliers**: Zone multipliers affect total floor area and volume calculations.

## Geometry Calculations

### Surface Area
Calculated using the Shoelace formula for polygons defined by vertices.

### Azimuth
Calculated from surface normal vector:
- North = 0°
- East = 90°
- South = 180°
- West = 270°

### Tilt
Calculated from surface normal vector:
- Horizontal (floor/roof) = 0° or 180°
- Vertical (wall) = 90°

### Window-Wall Ratio
```
WWR = Total Window Area / Gross Wall Area
```
Calculated per orientation and building total.

## Special Considerations

1. **Subsurfaces**: Windows and doors must be contained within their host surfaces.

2. **Ground Contact**: Surfaces with ground contact have special heat transfer considerations.

3. **Shading Surfaces**: External shading surfaces affect solar gains but aren't part of thermal zones.

4. **Curved Surfaces**: Approximated as faceted surfaces with multiple vertices.

5. **Zone Air Volume**: Can be auto-calculated from geometry or explicitly specified.

## Quality Checks

1. **Surface Enclosure**: All zones must be fully enclosed by surfaces.

2. **Surface Matching**: Interior surfaces must match between adjacent zones.

3. **Vertex Order**: Vertices must be in correct order (counterclockwise when viewed from outside).

4. **Convexity**: Non-convex zones require special handling for solar distribution.

5. **Subsurface Containment**: Windows/doors must be fully contained within host surfaces.