"""
Fixed ModificationTracker with all required methods for the modification engine
"""
from datetime import datetime
from pathlib import Path
import json
import logging

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
        self.current_session = None
        self.variants = {}
        self.current_variant = None
        self.logger = logging.getLogger(self.__class__.__name__)
        
    def start_session(self, session_id=None, building_id=None, base_idf_path=None):
        """Start a new modification session
        
        Args:
            session_id: Session identifier (uses instance session_id if not provided)
            building_id: Building identifier (optional)
            base_idf_path: Path to base IDF (optional)
        """
        # Use provided session_id or fall back to instance session_id
        session_id = session_id or self.session_id
        
        self.current_session = {
            'session_id': session_id,
            'building_id': str(building_id) if building_id else None,
            'base_idf_path': str(base_idf_path) if base_idf_path else None,
            'start_time': datetime.now().isoformat(),
            'variants': []
        }
        self.session_start = datetime.now()
        if building_id and building_id not in self.building_modifications:
            self.building_modifications[building_id] = []
            
    def start_variant(self, variant_id):
        """Start tracking a new variant"""
        self.current_variant = {
            'variant_id': variant_id,
            'start_time': datetime.now().isoformat(),
            'modifications': [],
            'status': 'in_progress'
        }
        self.variants[variant_id] = self.current_variant
        
    def add_modification(self, variant_id, modification):
        """Add a modification to current variant
        
        Args:
            variant_id: Variant identifier
            modification: ModificationResult object
        """
        if variant_id in self.variants:
            mod_data = {
                'category': modification.object_type,
                'object_name': modification.object_name,
                'parameter': modification.parameter,
                'original_value': str(modification.original_value),
                'new_value': str(modification.new_value),
                'change_type': modification.change_type,
                'success': modification.success,
                'validation_status': modification.validation_status
            }
            if modification.message:
                mod_data['message'] = modification.message
                
            self.variants[variant_id]['modifications'].append(mod_data)
            self.modification_count += 1
            
    def complete_variant(self, variant_id, variant_path, modifications):
        """Mark variant as complete
        
        Args:
            variant_id: Variant identifier
            variant_path: Path to saved variant IDF
            modifications: List of ModificationResult objects or dicts
        """
        if variant_id in self.variants:
            self.variants[variant_id]['status'] = 'completed'
            self.variants[variant_id]['path'] = str(variant_path) if variant_path else None
            self.variants[variant_id]['end_time'] = datetime.now().isoformat()
            self.variants[variant_id]['total_modifications'] = len(modifications)
            
            # Count successful modifications - handle both objects and dicts
            if modifications and len(modifications) > 0:
                if hasattr(modifications[0], 'success'):
                    successful = sum(1 for m in modifications if m.success)
                else:
                    successful = sum(1 for m in modifications if m.get('success', False))
            else:
                successful = 0
                
            self.variants[variant_id]['successful_modifications'] = successful
            
            if self.current_session:
                self.current_session['variants'].append(variant_id)
                
    def fail_variant(self, variant_id, error_message):
        """Mark variant as failed
        
        Args:
            variant_id: Variant identifier
            error_message: Error description
        """
        if variant_id in self.variants:
            self.variants[variant_id]['status'] = 'failed'
            self.variants[variant_id]['error'] = str(error_message)
            self.variants[variant_id]['end_time'] = datetime.now().isoformat()
            
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
            
    def track_modifications(self, category, modifications):
        """Track multiple modifications from a category
        
        Args:
            category: Category name
            modifications: List of ModificationResult objects
        """
        for mod in modifications:
            building_id = self.current_session['building_id'] if self.current_session else 'unknown'
            
            mod_desc = f"{mod.parameter}: {mod.original_value} -> {mod.new_value}"
            details = {
                'object_type': mod.object_type,
                'object_name': mod.object_name,
                'success': mod.success,
                'change_type': mod.change_type,
                'validation_status': mod.validation_status
            }
            
            self.track_modification(building_id, category, mod_desc, details)
    
    def log_modification(self, building_id, category, parameter, old_value, new_value, scenario_name):
        """Log a single modification (alias for compatibility)"""
        modification = f"{parameter}: {old_value} -> {new_value}"
        details = {
            'parameter': parameter,
            'old_value': old_value,
            'new_value': new_value,
            'scenario': scenario_name
        }
        self.track_modification(building_id, category, modification, details)
        
    def get_summary(self):
        """Get summary of all modifications"""
        session_duration = (datetime.now() - self.session_start).total_seconds()
        
        return {
            'session_start': self.session_start.isoformat(),
            'session_duration': session_duration,
            'total_modifications': self.modification_count,
            'buildings_modified': len(self.building_modifications),
            'building_ids': list(self.building_modifications.keys()),
            'modifications_by_category': self._get_category_summary(),
            'variants_summary': self._get_variants_summary(),
            'modifications': self.modifications,
            'modifications_by_building': self.building_modifications
        }
    
    def get_all_variants(self):
        """Get all variants information"""
        return self.variants
    
    def get_modifications(self):
        """Get all modifications"""
        return self.modifications
    
    def save_session_summary(self, output_dir):
        """Save session summary to file
        
        Args:
            output_dir: Directory to save summary
        """
        if not self.current_session:
            self.logger.warning("No active session to save")
            return
            
        summary = {
            'session': self.current_session,
            'variants': self.variants,
            'summary': self.get_summary()
        }
        
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        summary_file = output_path / f"modification_summary_{self.current_session['session_id']}.json"
        
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2, default=str)
        
        self.logger.info(f"Saved session summary to: {summary_file}")
        
    def generate_report(self):
        """Generate HTML report of modifications"""
        summary = self.get_summary()
        
        html = f"""
        <html>
        <head>
            <title>Modification Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                table {{ border-collapse: collapse; width: 100%; margin-top: 10px; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
                .success {{ color: green; }}
                .failed {{ color: red; }}
                .summary {{ background-color: #f9f9f9; padding: 15px; margin-bottom: 20px; }}
            </style>
        </head>
        <body>
            <h1>IDF Modification Report</h1>
            
            <div class="summary">
                <h2>Summary</h2>
                <p><strong>Session Start:</strong> {summary['session_start']}</p>
                <p><strong>Duration:</strong> {summary['session_duration']:.1f} seconds</p>
                <p><strong>Total Modifications:</strong> {summary['total_modifications']}</p>
                <p><strong>Buildings Modified:</strong> {summary['buildings_modified']}</p>
                <p><strong>Total Variants:</strong> {len(self.variants)}</p>
            </div>
            
            <h2>Variants</h2>
            <table>
                <tr>
                    <th>Variant ID</th>
                    <th>Status</th>
                    <th>Modifications</th>
                    <th>Duration</th>
                </tr>
        """
        
        for var_id, var_data in self.variants.items():
            status_class = 'success' if var_data['status'] == 'completed' else 'failed'
            duration = 'N/A'
            if 'end_time' in var_data and 'start_time' in var_data:
                start = datetime.fromisoformat(var_data['start_time'])
                end = datetime.fromisoformat(var_data['end_time'])
                duration = f"{(end - start).total_seconds():.1f}s"
                
            html += f"""
                <tr>
                    <td>{var_id}</td>
                    <td class="{status_class}">{var_data['status']}</td>
                    <td>{var_data.get('total_modifications', 0)}</td>
                    <td>{duration}</td>
                </tr>
            """
            
        html += """
            </table>
        </body>
        </html>
        """
        
        return html
    
    def _get_category_summary(self):
        """Get summary by category"""
        category_counts = {}
        for mod in self.modifications:
            cat = mod['category']
            category_counts[cat] = category_counts.get(cat, 0) + 1
        return category_counts
    
    def _get_variants_summary(self):
        """Get summary of variants"""
        completed = sum(1 for v in self.variants.values() if v['status'] == 'completed')
        failed = sum(1 for v in self.variants.values() if v['status'] == 'failed')
        in_progress = sum(1 for v in self.variants.values() if v['status'] == 'in_progress')
        
        return {
            'total': len(self.variants),
            'completed': completed,
            'failed': failed,
            'in_progress': in_progress
        }
    
    def _save_modification_log(self):
        """Save modifications to a log file"""
        if self.output_path:
            log_file = self.output_path / "modification_log.json"
            with open(log_file, 'w') as f:
                json.dump(self.get_summary(), f, indent=2, default=str)
    








    
    def reset(self):
        """Reset the tracker"""
        self.modifications = []
        self.modification_count = 0
        self.building_modifications = {}
        self.session_start = datetime.now()
        self.current_session = None
        self.variants = {}
        self.current_variant = None