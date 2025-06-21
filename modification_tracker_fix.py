# ModificationTracker Fix
# Add this to your modification_tracker.py file

from datetime import datetime

def get_summary(self):
    """Return a summary of all modifications made"""
    summary = {
        'total_modifications': len(self.modifications) if hasattr(self, 'modifications') else 0,
        'modifications_by_type': {},
        'modifications_by_building': {},
        'modifications_by_category': {},
        'parameters_modified': set(),
        'timestamp': datetime.now().isoformat(),
        'status': 'completed'
    }
    
    if hasattr(self, 'modifications') and self.modifications:
        for mod in self.modifications:
            # Count by type
            mod_type = mod.get('type', 'unknown')
            summary['modifications_by_type'][mod_type] = \
                summary['modifications_by_type'].get(mod_type, 0) + 1
            
            # Count by building
            building_id = mod.get('building_id', 'unknown')
            summary['modifications_by_building'][building_id] = \
                summary['modifications_by_building'].get(building_id, 0) + 1
            
            # Count by category
            category = mod.get('category', 'unknown')
            summary['modifications_by_category'][category] = \
                summary['modifications_by_category'].get(category, 0) + 1
            
            # Track parameters
            if 'parameter' in mod:
                summary['parameters_modified'].add(mod['parameter'])
    
    # Convert set to list for JSON serialization
    summary['parameters_modified'] = list(summary['parameters_modified'])
    
    # If no modifications were made, add a note
    if summary['total_modifications'] == 0:
        summary['note'] = 'No modifications were tracked'
        summary['status'] = 'no_changes'
    
    return summary

# Add this method to your ModificationTracker class
