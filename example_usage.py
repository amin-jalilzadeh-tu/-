"""
Example usage of IDF Modification Module
"""

from pathlib import Path
from eppy.modeleditor import IDF

# Import from our module
from idf_modification import (
    ModificationConfig,
    ModificationTracker,
    ParameterRegistry
)
from idf_modification.utils import (
    validate_modification,
    generate_modification_report
)

# Configuration
IDD_PATH = "path/to/Energy+.idd"
IDF_PATH = "path/to/building.idf"
OUTPUT_DIR = "output"

# Initialize
IDF.setiddname(IDD_PATH)

def main():
    # Load IDF
    idf = IDF(IDF_PATH)
    
    # Create configuration
    config = {
        "modifications": {
            "lighting": {
                "enabled": True,
                "reduction_factor": 0.5
            }
        }
    }
    
    # Initialize components
    mod_config = ModificationConfig(config)
    tracker = ModificationTracker()
    registry = ParameterRegistry()
    
    # Track modifications
    modifications = []
    
    # Apply lighting modifications
    for light in idf.idfobjects.get('LIGHTS', []):
        if light.Watts_per_Zone_Floor_Area:
            old_val = float(light.Watts_per_Zone_Floor_Area)
            new_val = old_val * 0.5
            light.Watts_per_Zone_Floor_Area = new_val
            
            mod = {
                'object_type': 'LIGHTS',
                'object_name': light.Name,
                'field': 'Watts_per_Zone_Floor_Area',
                'old_value': old_val,
                'value': new_val
            }
            
            # Validate
            is_valid, errors = validate_modification(mod)
            if is_valid:
                modifications.append(mod)
                tracker.track_modification(mod)
    
    # Generate report
    report = generate_modification_report(modifications, format='html')
    
    # Save modified IDF
    output_path = Path(OUTPUT_DIR) / "modified.idf"
    idf.save(str(output_path))
    
    print(f"Modified {len(modifications)} objects")
    print(f"Saved to: {output_path}")

if __name__ == "__main__":
    main()
