"""
Fixed ModificationTracker with get_summary method
"""
from datetime import datetime
from pathlib import Path
import json

class ModificationTracker:
    """Track modifications made to IDF files"""
    
    def __init__(self, output_path=None):
        """Initialize the modification tracker
        
        Args:
            output_path: Path to output directory (optional)
        """
        self.output_path = Path(output_path) if output_path else None
        self.modifications = []
        self.modification_count = 0
        self.building_modifications = {}
        self.session_start = datetime.now()
        
    def track_modification(self, building_id, category, modification, details=None):
        """Track a modification
        
        Args:
            building_id: Building identifier
            category: Category of modification (e.g., 'hvac', 'lighting')
            modification: Description of the modification
            details: Additional details (optional)
        """
        mod_entry = {
            'building_id': str(building_id),
            'category': category,
            'modification': modification,
            'timestamp': datetime.now().isoformat(),
            'details': details or {}
        }
        
        self.modifications.append(mod_entry)
        self.modification_count += 1
        
        if building_id not in self.building_modifications:
            self.building_modifications[building_id] = []
        self.building_modifications[building_id].append((category, modification))
        
        # Save to file if output path is set
        if self.output_path:
            self._save_modification_log()
    

    def start_session(self, session_id, building_id, base_idf_path):
        """Start a new modification session."""
        from datetime import datetime
        
        self.session_start = {
            'session_id': session_id,
            'building_id': building_id,
            'base_idf_path': base_idf_path,
            'start_time': datetime.now().isoformat()
        }
        if not hasattr(self, 'building_modifications'):
            self.building_modifications = {}
        self.building_modifications[building_id] = []
        
    def log_modification(self, building_id, category, parameter, old_value, new_value, scenario_name):
        """Log a single modification (alias for track_modification)."""
        self.track_modification(
            building_id=building_id,
            category=category,
            parameter=parameter,
            old_value=old_value,
            new_value=new_value,
            scenario=scenario_name
        )










    def get_summary(self):
        """Get summary of all modifications"""
        return {
            'session_start': self.session_start.isoformat(),
            'session_duration': (datetime.now() - self.session_start).total_seconds(),
            'total_modifications': self.modification_count,
            'buildings_modified': len(self.building_modifications),
            'building_ids': list(self.building_modifications.keys()),
            'modifications_by_category': self._get_category_summary(),
            'modifications': self.modifications,
            'modifications_by_building': self.building_modifications
        }
    
    def get_modifications(self):
        """Get all modifications"""
        return self.modifications
    
    def _get_category_summary(self):
        """Get summary by category"""
        category_counts = {}
        for mod in self.modifications:
            cat = mod['category']
            category_counts[cat] = category_counts.get(cat, 0) + 1
        return category_counts
    
    def _save_modification_log(self):
        """Save modifications to a log file"""
        if self.output_path:
            log_file = self.output_path / "modification_log.json"
            with open(log_file, 'w') as f:
                json.dump(self.get_summary(), f, indent=2)
    
    def reset(self):
        """Reset the tracker"""
        self.modifications = []
        self.modification_count = 0
        self.building_modifications = {}
        self.session_start = datetime.now()
