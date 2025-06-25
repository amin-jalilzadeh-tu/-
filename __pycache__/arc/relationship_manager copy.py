"""
c_sensitivity/relationship_manager.py

Manages relationships between equipment, zones, and buildings for multi-level analysis.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import logging
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
import json

@dataclass
class ZoneInfo:
    """Information about a zone"""
    building_id: str
    idf_zone_name: str
    sql_zone_name: str
    zone_type: Optional[str] = None
    multiplier: Optional[float] = 1.0
    area: Optional[float] = None
    volume: Optional[float] = None
    equipment: List[str] = field(default_factory=list)

@dataclass
class EquipmentInfo:
    """Information about equipment"""
    building_id: str
    equipment_name: str
    equipment_type: str
    assigned_zone: str
    schedule: Optional[str] = None
    capacity: Optional[float] = None

class RelationshipManager:
    """Manages hierarchical relationships in building data"""
    
    def __init__(self, parsed_data_path: Path, logger: Optional[logging.Logger] = None):
        self.parsed_data_path = Path(parsed_data_path)
        self.logger = logger or logging.getLogger(__name__)
        
        # Data containers
        self.zone_mappings = {}  # building_id -> {idf_name -> ZoneInfo}
        self.equipment_assignments = {}  # building_id -> {equip_name -> EquipmentInfo}
        self.zone_to_equipment = {}  # building_id -> {zone_name -> [equipment_names]}
        self.building_zones = {}  # building_id -> [zone_names]
        
        # Load relationships
        self._load_relationships()
    
    def _load_relationships(self):
        """Load all relationship data"""
        self.logger.info("Loading relationship data...")
        
        # Load zone mappings
        zone_mapping_path = self.parsed_data_path / "relationships" / "zone_mappings.parquet"
        if zone_mapping_path.exists():
            self._load_zone_mappings(zone_mapping_path)
        else:
            self.logger.warning(f"Zone mappings not found: {zone_mapping_path}")
        
        # Load equipment assignments
        equipment_path = self.parsed_data_path / "relationships" / "equipment_assignments.parquet"
        if equipment_path.exists():
            self._load_equipment_assignments(equipment_path)
        else:
            self.logger.warning(f"Equipment assignments not found: {equipment_path}")
        
        # Load zone geometry if available
        zone_geom_path = self.parsed_data_path / "idf_data" / "by_category" / "geometry_zones.parquet"
        if zone_geom_path.exists():
            self._load_zone_geometry(zone_geom_path)
        
        self.logger.info(f"Loaded relationships for {len(self.zone_mappings)} buildings")
    
    def _load_zone_mappings(self, path: Path):
        """Load zone name mappings between IDF and SQL"""
        df = pd.read_parquet(path)
        
        for _, row in df.iterrows():
            building_id = str(row['building_id'])
            
            if building_id not in self.zone_mappings:
                self.zone_mappings[building_id] = {}
            
            zone_info = ZoneInfo(
                building_id=building_id,
                idf_zone_name=row['idf_zone_name'],
                sql_zone_name=row['sql_zone_name'],
                zone_type=row.get('zone_type'),
                multiplier=row.get('multiplier', 1.0)
            )
            
            self.zone_mappings[building_id][row['idf_zone_name']] = zone_info
            
            # Track building zones
            if building_id not in self.building_zones:
                self.building_zones[building_id] = []
            if row['idf_zone_name'] not in ['ALL_ZONES', 'Environment']:
                self.building_zones[building_id].append(row['idf_zone_name'])
    
    def _load_equipment_assignments(self, path: Path):
        """Load equipment to zone assignments"""
        df = pd.read_parquet(path)
        
        for _, row in df.iterrows():
            building_id = str(row['building_id'])
            
            if building_id not in self.equipment_assignments:
                self.equipment_assignments[building_id] = {}
            
            equip_info = EquipmentInfo(
                building_id=building_id,
                equipment_name=row['equipment_name'],
                equipment_type=row['equipment_type'],
                assigned_zone=row['assigned_zone'],
                schedule=row.get('schedule')
            )
            
            self.equipment_assignments[building_id][row['equipment_name']] = equip_info
            
            # Update zone to equipment mapping
            if building_id not in self.zone_to_equipment:
                self.zone_to_equipment[building_id] = {}
            
            zone = row['assigned_zone']
            if zone not in self.zone_to_equipment[building_id]:
                self.zone_to_equipment[building_id][zone] = []
            
            self.zone_to_equipment[building_id][zone].append(row['equipment_name'])
            
            # Update zone info with equipment
            if building_id in self.zone_mappings and zone in self.zone_mappings[building_id]:
                self.zone_mappings[building_id][zone].equipment.append(row['equipment_name'])
    
    def _load_zone_geometry(self, path: Path):
        """Load zone geometry data for area/volume"""
        df = pd.read_parquet(path)
        
        for _, row in df.iterrows():
            building_id = str(row['building_id'])
            zone_name = row.get('zone_name', row.get('name', ''))
            
            if building_id in self.zone_mappings and zone_name in self.zone_mappings[building_id]:
                zone_info = self.zone_mappings[building_id][zone_name]
                
                # Try to get area and volume, handling 'autocalculate' values
                if 'floor_area' in row:
                    try:
                        # Handle 'autocalculate' or other non-numeric values
                        if str(row['floor_area']).lower() == 'autocalculate':
                            zone_info.area = None  # Will use default later
                        else:
                            zone_info.area = float(row['floor_area'])
                    except (ValueError, TypeError):
                        zone_info.area = None
                        
                elif 'floor_area_numeric' in row:
                    try:
                        zone_info.area = float(row['floor_area_numeric'])
                    except (ValueError, TypeError):
                        zone_info.area = None
                
                if 'volume' in row:
                    try:
                        # Handle 'autocalculate' or other non-numeric values
                        if str(row['volume']).lower() == 'autocalculate':
                            zone_info.volume = None  # Will use default later
                        else:
                            zone_info.volume = float(row['volume'])
                    except (ValueError, TypeError):
                        zone_info.volume = None
                        
                elif 'volume_numeric' in row:
                    try:
                        zone_info.volume = float(row['volume_numeric'])
                    except (ValueError, TypeError):
                        zone_info.volume = None
    
    def get_zone_for_equipment(self, building_id: str, equipment_name: str) -> Optional[str]:
        """Get the zone assignment for a piece of equipment"""
        if building_id in self.equipment_assignments:
            if equipment_name in self.equipment_assignments[building_id]:
                return self.equipment_assignments[building_id][equipment_name].assigned_zone
        return None
    
    def get_sql_zone_name(self, building_id: str, idf_zone_name: str) -> Optional[str]:
        """Get SQL zone name from IDF zone name"""
        if building_id in self.zone_mappings:
            if idf_zone_name in self.zone_mappings[building_id]:
                return self.zone_mappings[building_id][idf_zone_name].sql_zone_name
        
        # Try case-insensitive match
        if building_id in self.zone_mappings:
            for zone_name, zone_info in self.zone_mappings[building_id].items():
                if zone_name.upper() == idf_zone_name.upper():
                    return zone_info.sql_zone_name
        
        # Default: return uppercase version
        return idf_zone_name.upper()
    
    def get_building_zones(self, building_id: str) -> List[str]:
        """Get all zones in a building"""
        return self.building_zones.get(building_id, [])
    
    def get_zone_equipment(self, building_id: str, zone_name: str) -> List[str]:
        """Get all equipment in a zone"""
        if building_id in self.zone_to_equipment:
            return self.zone_to_equipment[building_id].get(zone_name, [])
        return []
    
    def detect_modification_scope(self, 
                                object_name: str, 
                                object_type: str,
                                building_id: str) -> Tuple[str, List[str]]:
        """
        Detect the scope of a modification (building, zone, or equipment level)
        
        Returns:
            Tuple of (scope_type, affected_zones)
            scope_type: 'building', 'zone', or 'equipment'
            affected_zones: List of affected zone names
        """
        # Check for building-wide modifications
        if 'ALL_ZONES' in object_name.upper() or object_name.upper() == building_id:
            return 'building', self.get_building_zones(building_id)
        
        # Check if it's equipment
        if building_id in self.equipment_assignments:
            if object_name in self.equipment_assignments[building_id]:
                zone = self.get_zone_for_equipment(building_id, object_name)
                return 'equipment', [zone] if zone else []
        
        # Check for zone-specific modifications
        building_zones = self.get_building_zones(building_id)
        for zone in building_zones:
            if zone in object_name or zone.upper() in object_name.upper():
                return 'zone', [zone]
        
        # Check object type for clues
        zone_specific_types = ['ZONE', 'PEOPLE', 'LIGHTS', 'ELECTRICEQUIPMENT', 
                              'ZONEINFILTRATION', 'ZONEVENTILATION']
        if any(ztype in object_type.upper() for ztype in zone_specific_types):
            # Try to extract zone from name
            for zone in building_zones:
                if zone.upper() in object_name.upper():
                    return 'zone', [zone]
        
        # Default to building level
        return 'building', self.get_building_zones(building_id)
    
    def get_zone_weights(self, building_id: str, weight_by: str = 'equal') -> Dict[str, float]:
        """
        Get weights for aggregating zone values to building level
        
        Args:
            building_id: Building ID
            weight_by: 'equal', 'area', or 'volume'
            
        Returns:
            Dictionary of zone_name -> weight
        """
        zones = self.get_building_zones(building_id)
        if not zones:
            return {}
        
        if weight_by == 'equal':
            weight = 1.0 / len(zones)
            return {zone: weight for zone in zones}
        
        elif weight_by == 'area':
            zone_areas = {}
            total_area = 0
            
            for zone in zones:
                area = 1.0  # Default if not found
                if building_id in self.zone_mappings and zone in self.zone_mappings[building_id]:
                    zone_area = self.zone_mappings[building_id][zone].area
                    if zone_area is not None and zone_area > 0:
                        area = zone_area
                zone_areas[zone] = area
                total_area += area
            
            return {zone: area / total_area for zone, area in zone_areas.items()}
        
        elif weight_by == 'volume':
            zone_volumes = {}
            total_volume = 0
            
            for zone in zones:
                volume = 1.0  # Default if not found
                if building_id in self.zone_mappings and zone in self.zone_mappings[building_id]:
                    zone_volume = self.zone_mappings[building_id][zone].volume
                    if zone_volume is not None and zone_volume > 0:
                        volume = zone_volume
                zone_volumes[zone] = volume
                total_volume += volume
            
            return {zone: volume / total_volume for zone, volume in zone_volumes.items()}
        
        else:
            # Default to equal weights
            weight = 1.0 / len(zones)
            return {zone: weight for zone in zones}
    
    def create_modification_hierarchy(self, modifications_df: pd.DataFrame) -> Dict[str, Dict]:
        """
        Create a hierarchical view of modifications
        
        Returns:
            Dict with structure:
            {
                'building_level': {building_id: [modifications]},
                'zone_level': {building_id: {zone: [modifications]}},
                'equipment_level': {building_id: {equipment: [modifications]}}
            }
        """
        hierarchy = {
            'building_level': {},
            'zone_level': {},
            'equipment_level': {}
        }
        
        for _, mod in modifications_df.iterrows():
            building_id = str(mod['building_id'])
            object_name = mod.get('object_name', '')
            object_type = mod.get('object_type', '')
            
            scope, affected_zones = self.detect_modification_scope(
                object_name, object_type, building_id
            )
            
            mod_dict = mod.to_dict()
            mod_dict['scope'] = scope
            mod_dict['affected_zones'] = affected_zones
            
            if scope == 'building':
                if building_id not in hierarchy['building_level']:
                    hierarchy['building_level'][building_id] = []
                hierarchy['building_level'][building_id].append(mod_dict)
                
            elif scope == 'zone':
                if building_id not in hierarchy['zone_level']:
                    hierarchy['zone_level'][building_id] = {}
                for zone in affected_zones:
                    if zone not in hierarchy['zone_level'][building_id]:
                        hierarchy['zone_level'][building_id][zone] = []
                    hierarchy['zone_level'][building_id][zone].append(mod_dict)
                    
            elif scope == 'equipment':
                if building_id not in hierarchy['equipment_level']:
                    hierarchy['equipment_level'][building_id] = {}
                if object_name not in hierarchy['equipment_level'][building_id]:
                    hierarchy['equipment_level'][building_id][object_name] = []
                hierarchy['equipment_level'][building_id][object_name].append(mod_dict)
        
        return hierarchy
    
    def save_relationships(self, output_path: Path):
        """Save relationship data for debugging/analysis"""
        output_path = Path(output_path)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Save zone mappings
        zone_data = []
        for building_id, zones in self.zone_mappings.items():
            for zone_name, zone_info in zones.items():
                zone_data.append({
                    'building_id': building_id,
                    'idf_zone_name': zone_info.idf_zone_name,
                    'sql_zone_name': zone_info.sql_zone_name,
                    'area': zone_info.area,
                    'volume': zone_info.volume,
                    'equipment_count': len(zone_info.equipment)
                })
        
        if zone_data:
            pd.DataFrame(zone_data).to_csv(output_path / 'zone_relationships.csv', index=False)
        
        # Save equipment assignments
        equip_data = []
        for building_id, equipment in self.equipment_assignments.items():
            for equip_name, equip_info in equipment.items():
                equip_data.append({
                    'building_id': building_id,
                    'equipment_name': equip_info.equipment_name,
                    'equipment_type': equip_info.equipment_type,
                    'assigned_zone': equip_info.assigned_zone
                })
        
        if equip_data:
            pd.DataFrame(equip_data).to_csv(output_path / 'equipment_relationships.csv', index=False)
        
        self.logger.info(f"Saved relationships to: {output_path}")
