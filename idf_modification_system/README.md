# IDF Modification System

A comprehensive system for modifying EnergyPlus IDF files with various strategies and rules.

## Directory Structure

```
idf_modification_system/
├── modifiers/          # Specific modifier implementations
├── rules/              # Rule engines (efficiency, comfort, dependencies)
├── tests/              # Test scripts
├── config/             # Configuration files
├── examples/           # Example scripts and data
├── base_modifier.py    # Abstract base class for modifiers
├── modification_engine.py  # Main orchestrator
├── modification_tracker.py # Tracks all modifications
├── parameter_registry.py   # Central parameter registry
├── scenario_generator.py   # Generates modification scenarios
├── validation.py          # Validation utilities
├── reporting.py           # Reporting utilities
└── idf_helpers.py         # IDF manipulation helpers
```

## Usage

1. Set up your configuration in a JSON file
2. Initialize the ModificationEngine with your project path and config
3. Generate modifications using various strategies
4. Review the generated reports and modified IDF files

See tests/unified_test.py for a complete example.
