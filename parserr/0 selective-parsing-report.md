 here's the updated plan to support selective content parsing:

## 1. **Enhanced Configuration Structure in `combined.json`**

The `parsing` section needs to be expanded to include:

### File Selection:

* **Parse types selection** : Choose between IDF files, SQL files, or both
* **Parse mode** : Parse all files or only specific ones
* **Building selection** : Specify which buildings to parse
* **File selection** : Directly specify file paths to parse

### Content Selection for IDF:

* **Category level** : Parse only specific categories (e.g., only "hvac", "geometry")
* **Object type level** : Parse only specific object types (e.g., only "ZONE", "LIGHTS")
* **Exclude categories/objects** : Blacklist approach to skip certain types

### Content Selection for SQL:

* **Variable categories** : Parse only specific variable types (e.g., only "energy", "comfort")
* **Specific variables** : List exact variable names to extract
* **Frequency filter** : Only parse variables with specific reporting frequencies
* **Time range** : Parse only data within specific date ranges
* **Skip types** : Skip schedules, skip summary metrics, etc.

## 2. **Updates to `orchestrator.py`**

* Add logic to parse the detailed content selection configuration
* Pass content filters to the analyzer
* Support partial parsing workflows
* Add pre-validation to check if requested content exists

## 3. **Updates to `energyplus_analyzer_main.py`**

* Modify parsing methods to respect content filters:
  * Filter IDF categories/objects before processing
  * Filter SQL variables before extraction
  * Skip entire processing sections if not requested
* Add methods to validate requested content against available content
* Support "dry run" mode to show what would be parsed without doing it

## 4. **Updates to `idf_parser.py`**

* Add filtering in `_organize_objects` to skip unwanted object types
* Add category-level filtering to skip entire categories
* Support wildcard patterns for object selection
* Add option to parse only object headers without parameters

## 5. **Updates to `sql_analyzer.py`**

* Filter variables in `extract_timeseries` based on configuration
* Skip schedule extraction if not requested
* Skip summary metrics creation if not requested
* Add variable name pattern matching support

## 6. **New Configuration Examples to Support**

### Example configurations:

* Parse only geometry and zones from IDF files
* Parse only energy variables from SQL files
* Parse HVAC objects from IDF but only temperature variables from SQL
* Parse everything except schedules
* Parse only OUTPUT:VARIABLE definitions from IDF
* Parse only daily frequency variables from SQL
* Parse only specific months of data
* Quick parse mode (minimal essential data only)

## 7. **Performance Benefits**

* Faster parsing when only subset needed
* Reduced memory usage
* Smaller output files
* Ability to iteratively parse (e.g., parse geometry first, then HVAC later)

## 8. **Additional Features**

* **Parse Profiles** : Pre-defined parsing profiles (e.g., "geometry_only", "energy_analysis", "debug_outputs")
* **Content Discovery Mode** : List what's available without parsing
* **Merge Mode** : Parse new content and merge with existing parsed data
* **Validation Mode** : Check if requested content exists before parsing

This granular control will allow you to:

* Debug specific aspects without parsing everything
* Create focused datasets for specific analyses
* Speed up iterative development
* Handle large projects by parsing in stages

# Selective Parsing Feature Report

## Overview

The EnergyPlus parsing system has been enhanced with selective parsing capabilities, allowing fine-grained control over what data is extracted from IDF and SQL files. This feature significantly improves performance and flexibility by parsing only the required data.

## Key Features

### 1. **File Selection**

- Parse all files or specific buildings only
- Support for building ID patterns (e.g., "4136*")
- Direct file path specification
- Separate control for IDF and SQL parsing

### 2. **Content Filtering for IDF Files**

- **Category-based**: Parse only specific categories (geometry, HVAC, etc.)
- **Object-based**: Parse only specific object types (ZONE, LIGHTS, etc.)
- **Exclusion**: Skip unwanted categories or objects
- **Parameter control**: Option to parse only object headers without parameters

### 3. **Content Filtering for SQL Files**

- **Variable selection**: By category, specific names, or patterns
- **Time filtering**: Date ranges, specific months, or hours
- **Frequency filtering**: Only specific reporting frequencies
- **Zone filtering**: Include/exclude specific zones
- **Component selection**: Control over timeseries, schedules, metrics

### 4. **Parsing Profiles**

Pre-defined configurations for common use cases:

- `minimal`: Essential data only
- `geometry_only`: Just geometric data
- `energy_analysis`: Energy-related data
- `outputs_only`: Output definitions
- `debug_mode`: Everything with metadata

## Performance Benefits

1. **Reduced parsing time**: Parse only what's needed
2. **Lower memory usage**: Smaller datasets in memory
3. **Smaller output files**: Only requested data is saved
4. **Iterative parsing**: Parse in stages as needed

## Configuration Structure

```json
{
  "parsing": {
    "perform_parsing": true,
    "parse_mode": "selective",
    "parse_types": {
      "idf": true,
      "sql": true
    },
    "building_selection": {
      "mode": "specific",
      "building_ids": [...]
    },
    "idf_content": {
      "mode": "selective",
      "categories": [...]
    },
    "sql_content": {
      "mode": "selective",
      "variables": {...}
    }
  }
}
```

## Use Cases

### 1. **Debugging**

Parse only specific buildings or components to quickly identify issues.

### 2. **Incremental Analysis**

Parse geometry first, then add HVAC data later without re-parsing everything.

### 3. **Performance Optimization**

Parse only hourly energy data instead of timestep data for faster analysis.

### 4. **Targeted Studies**

Parse only relevant data for specific analyses (e.g., only comfort variables for comfort studies).

## Implementation Details

### File Selection Logic

The system supports three modes of file selection:

- **all**: Parse all available files
- **selective**: Parse based on building criteria
- **specific_files**: Parse exact file paths

### Content Filtering Process

1. **IDF Filtering**: Objects are filtered during parsing based on category or type
2. **SQL Filtering**: Variables are filtered before extraction using SQL queries
3. **Time Filtering**: Applied directly in SQL queries for efficiency

### Error Handling

- Validation before parsing to catch configuration errors
- Option to continue on errors or stop immediately
- Detailed error reporting for each building

## Configuration Examples

### Minimal Configuration

```json
{
  "parsing": {
    "perform_parsing": true
  }
}
```

### Parse Single Building

```json
{
  "parsing": {
    "perform_parsing": true,
    "parse_mode": "selective",
    "building_selection": {
      "mode": "specific",
      "building_ids": [413673000]
    }
  }
}
```

### Parse with Time Filter

```json
{
  "parsing": {
    "perform_parsing": true,
    "sql_content": {
      "time_filter": {
        "start_date": "2020-01-01",
        "end_date": "2020-03-31",
        "hours": [8, 9, 10, 11, 12, 13, 14, 15, 16, 17]
      }
    }
  }
}
```

## Best Practices

1. **Start Simple**: Begin with minimal configuration and add filters as needed
2. **Use Profiles**: Leverage pre-defined profiles for common scenarios
3. **Validate First**: Enable validation to catch issues before parsing
4. **Monitor Performance**: Check parsing times and adjust batch sizes
5. **Incremental Approach**: Parse in stages for large datasets

## Troubleshooting

### Common Issues

1. **No files found**: Check building IDs and file paths
2. **Empty results**: Verify variable names and patterns
3. **Memory errors**: Reduce batch size or parse fewer buildings
4. **Slow parsing**: Use time filters or frequency filters

### Debug Tips

1. Enable validation reporting
2. Parse single building first
3. Check parsed data summary
4. Review error logs in metadata

## Future Enhancements

1. **Parallel parsing**: Multi-threaded parsing for large datasets
2. **Streaming mode**: Process large files without loading all data
3. **Smart caching**: Cache parsed data for faster re-parsing
4. **Auto-detection**: Automatically detect optimal parsing configuration
