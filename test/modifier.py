# test/modifier.py - Standalone Modification Module

import sys
import os
import logging
from pathlib import Path
from datetime import datetime
import json

# Add parent directories to path
current_dir = Path(__file__).parent
project_root = current_dir.parent
sys.path.insert(0, str(project_root))

try:
    # Import required modules
    from idf_modification.modification_engine import ModificationEngine
    from parserr.idf_parser import EnhancedIDFParser
except ImportError as e:
    print(f"Error importing required modules: {e}")
    print("\nMake sure you have the following directory structure:")
    print(f"  {project_root}/idf_modification/")
    print(f"  {project_root}/parserr/")
    print("\nAnd that these directories contain the required modules.")
    sys.exit(1)

class StandaloneModifier:
    """Standalone modifier for testing IDF modifications"""
    
    def __init__(self, config_path=None):
        """Initialize the standalone modifier
        
        Args:
            config_path: Path to configuration file
        """
        self.logger = self._setup_logger()
        self.config = self._load_config(config_path)
        self.parser = EnhancedIDFParser()
        self.output_dir = Path(self.config.get('output_dir', './output'))
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def _setup_logger(self):
        """Setup logging"""
        logger = logging.getLogger('StandaloneModifier')
        logger.setLevel(logging.INFO)
        
        # Console handler
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        ch.setFormatter(formatter)
        logger.addHandler(ch)
        
        # File handler
        log_dir = Path('./logs')
        log_dir.mkdir(exist_ok=True)
        fh = logging.FileHandler(log_dir / f'modifier_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(formatter)
        logger.addHandler(fh)
        
        return logger
        
    def _load_config(self, config_path):
        """Load configuration"""
        if config_path and Path(config_path).exists():
            with open(config_path, 'r') as f:
                return json.load(f)
        else:
            # Default configuration
            return {
                "output_dir": "./output",
                "modification": {
                    "categories_to_modify": {
                        "hvac": {
                            "enabled": True,
                            "strategy": "high_efficiency",
                            "parameters": {
                                "cooling_cop": {
                                    "method": "percentage",
                                    "change": 30,
                                    "comment": "Increase cooling COP by 30%"
                                },
                                "heating_efficiency": {
                                    "method": "absolute",
                                    "value": 0.95,
                                    "comment": "Set heating efficiency to 95%"
                                }
                            }
                        },
                        "lighting": {
                            "enabled": True,
                            "strategy": "led_retrofit",
                            "parameters": {
                                "watts_per_area": {
                                    "method": "percentage",
                                    "change": -50,
                                    "comment": "LED retrofit reduces power by 50%"
                                }
                            }
                        },
                        "infiltration": {
                            "enabled": True,
                            "strategy": "air_sealing",
                            "parameters": {
                                "air_changes_per_hour": {
                                    "method": "percentage",
                                    "change": -40,
                                    "comment": "Reduce infiltration by 40%"
                                }
                            }
                        }
                    },
                    "output_options": {
                        "save_modified_idfs": True,
                        "generate_report": True
                    }
                }
            }
    
    def modify_idf(self, idf_path, building_id=None, variant_id="test_variant"):
        """Modify a single IDF file
        
        Args:
            idf_path: Path to IDF file
            building_id: Building identifier (optional)
            variant_id: Variant identifier
            
        Returns:
            Dict with modification results
        """
        idf_path = Path(idf_path)
        if not idf_path.exists():
            raise FileNotFoundError(f"IDF file not found: {idf_path}")
        
        if not building_id:
            building_id = idf_path.stem
        
        self.logger.info(f"Modifying IDF: {idf_path}")
        self.logger.info(f"Building ID: {building_id}, Variant ID: {variant_id}")
        
        try:
            # Create a temporary project structure for the modification engine
            temp_project = self.output_dir / "temp_project"
            temp_project.mkdir(exist_ok=True)
            
            # Parse the IDF first to create required structure
            self.logger.info("Parsing IDF file...")
            building_data = self.parser.parse_file(idf_path)
            
            # Create parsed data directory structure
            parsed_dir = temp_project / "parsed_data"
            parsed_dir.mkdir(exist_ok=True)
            
            # Initialize modification engine
            self.logger.info("Initializing modification engine...")
            mod_engine = ModificationEngine(
                project_dir=temp_project,
                config=self.config.get('modification', {}),
                output_path=self.output_dir
            )
            
            # Apply modifications
            self.logger.info("Applying modifications...")
            results = mod_engine.modify_building(
                building_id=building_id,
                idf_path=idf_path,
                parameter_values=self.config['modification'].get('categories_to_modify', {}),
                variant_id=variant_id
            )
            
            # Generate report
            if results['success']:
                self.logger.info(f"Successfully modified {len(results['modifications'])} parameters")
                self._generate_report(results, building_id, variant_id)
            else:
                self.logger.error(f"Modification failed: {results['errors']}")
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error during modification: {e}")
            import traceback
            self.logger.debug(traceback.format_exc())
            return {
                'success': False,
                'errors': [str(e)],
                'modifications': []
            }
    
    def _generate_report(self, results, building_id, variant_id):
        """Generate modification report"""
        report_path = self.output_dir / f"modification_report_{building_id}_{variant_id}.json"
        
        report_data = {
            'timestamp': datetime.now().isoformat(),
            'building_id': building_id,
            'variant_id': variant_id,
            'success': results['success'],
            'total_modifications': len(results['modifications']),
            'output_file': results.get('output_file'),
            'modifications': results['modifications'],
            'errors': results.get('errors', [])
        }
        
        with open(report_path, 'w') as f:
            json.dump(report_data, f, indent=2)
        
        self.logger.info(f"Report saved to: {report_path}")
        
        # Also create a summary
        summary_path = self.output_dir / f"modification_summary_{building_id}_{variant_id}.txt"
        with open(summary_path, 'w') as f:
            f.write(f"Modification Summary\n")
            f.write(f"===================\n")
            f.write(f"Building ID: {building_id}\n")
            f.write(f"Variant ID: {variant_id}\n")
            f.write(f"Timestamp: {report_data['timestamp']}\n")
            f.write(f"Success: {report_data['success']}\n")
            f.write(f"Total Modifications: {report_data['total_modifications']}\n")
            f.write(f"Output File: {report_data['output_file']}\n\n")
            
            f.write("Modifications by Category:\n")
            f.write("--------------------------\n")
            
            # Group by category
            by_category = {}
            for mod in results['modifications']:
                cat = mod.get('category', 'unknown')
                if cat not in by_category:
                    by_category[cat] = []
                by_category[cat].append(mod)
            
            for cat, mods in by_category.items():
                f.write(f"\n{cat.upper()} ({len(mods)} modifications):\n")
                for mod in mods:
                    f.write(f"  - {mod['object_type']}.{mod['parameter']}: ")
                    f.write(f"{mod['original_value']} -> {mod['new_value']}\n")
                    
        self.logger.info(f"Summary saved to: {summary_path}")


if __name__ == "__main__":
    # Test the modifier
    modifier = StandaloneModifier()
    
    # Example usage
    test_idf = r"D:\Documents\daily\E_Plus_2040_py\output\b0fb6596-3303-4494-bc5f-5741a4db5e11\output_IDFs\building_4136733.idf"
    
    if Path(test_idf).exists():
        results = modifier.modify_idf(test_idf)
        print(f"Modification results: {results['success']}")
        print(f"Total modifications: {len(results['modifications'])}")
    else:
        print(f"Test IDF not found: {test_idf}")