"""
Reporting utilities for IDF modifications

This module provides functions to generate:
- Modification reports
- Scenario reports
- Comparison reports
- Validation reports
- Export functionality (CSV, JSON)
"""

import json
import csv
import datetime
from typing import Dict, List, Any, Optional, Union, Tuple  # ADD Tuple herefrom pathlib import Path
import pandas as pd
import logging
from pathlib import Path  # ADD THIS LINE


logger = logging.getLogger(__name__)


def generate_modification_report(modifications: List[Dict[str, Any]], 
                               output_path: Optional[Path] = None,
                               format: str = 'html') -> str:
    """
    Generate a detailed modification report
    
    Args:
        modifications: List of modification dictionaries
        output_path: Optional path to save the report
        format: Report format ('html', 'text', 'markdown')
        
    Returns:
        Report content as string
    """
    report_lines = []
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    if format == 'html':
        report_lines.append("<html><head><title>IDF Modification Report</title>")
        report_lines.append("<style>")
        report_lines.append("body { font-family: Arial, sans-serif; margin: 20px; }")
        report_lines.append("table { border-collapse: collapse; width: 100%; margin: 20px 0; }")
        report_lines.append("th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }")
        report_lines.append("th { background-color: #4CAF50; color: white; }")
        report_lines.append("tr:nth-child(even) { background-color: #f2f2f2; }")
        report_lines.append(".summary { background-color: #e7f3fe; padding: 15px; margin: 20px 0; }")
        report_lines.append("</style></head><body>")
        report_lines.append(f"<h1>IDF Modification Report</h1>")
        report_lines.append(f"<p><strong>Generated:</strong> {timestamp}</p>")
        
        # Summary section
        report_lines.append("<div class='summary'>")
        report_lines.append(f"<h2>Summary</h2>")
        report_lines.append(f"<p>Total modifications: {len(modifications)}</p>")
        
        # Count by object type
        type_counts = {}
        for mod in modifications:
            obj_type = mod.get('object_type', 'Unknown')
            type_counts[obj_type] = type_counts.get(obj_type, 0) + 1
        
        report_lines.append("<p>Modifications by type:</p><ul>")
        for obj_type, count in sorted(type_counts.items()):
            report_lines.append(f"<li>{obj_type}: {count}</li>")
        report_lines.append("</ul></div>")
        
        # Detailed modifications table
        report_lines.append("<h2>Detailed Modifications</h2>")
        report_lines.append("<table>")
        report_lines.append("<tr><th>#</th><th>Object Type</th><th>Object Name</th>")
        report_lines.append("<th>Field</th><th>Old Value</th><th>New Value</th><th>Change %</th></tr>")
        
        for i, mod in enumerate(modifications, 1):
            report_lines.append("<tr>")
            report_lines.append(f"<td>{i}</td>")
            report_lines.append(f"<td>{mod.get('object_type', 'N/A')}</td>")
            report_lines.append(f"<td>{mod.get('object_name', 'N/A')}</td>")
            report_lines.append(f"<td>{mod.get('field', 'N/A')}</td>")
            report_lines.append(f"<td>{mod.get('old_value', 'N/A')}</td>")
            report_lines.append(f"<td>{mod.get('value', 'N/A')}</td>")
            
            # Calculate change percentage for numeric values
            change_pct = "N/A"
            try:
                old_val = float(mod.get('old_value', 0))
                new_val = float(mod.get('value', 0))
                if old_val != 0:
                    change_pct = f"{((new_val - old_val) / old_val * 100):.1f}%"
            except:
                pass
            
            report_lines.append(f"<td>{change_pct}</td>")
            report_lines.append("</tr>")
        
        report_lines.append("</table>")
        report_lines.append("</body></html>")
        
    elif format == 'markdown':
        report_lines.append(f"# IDF Modification Report")
        report_lines.append(f"\n**Generated:** {timestamp}\n")
        report_lines.append(f"## Summary")
        report_lines.append(f"- Total modifications: {len(modifications)}")
        report_lines.append(f"\n### Modifications by type:")
        
        type_counts = {}
        for mod in modifications:
            obj_type = mod.get('object_type', 'Unknown')
            type_counts[obj_type] = type_counts.get(obj_type, 0) + 1
        
        for obj_type, count in sorted(type_counts.items()):
            report_lines.append(f"- {obj_type}: {count}")
        
        report_lines.append(f"\n## Detailed Modifications")
        report_lines.append("| # | Object Type | Object Name | Field | Old Value | New Value | Change % |")
        report_lines.append("|---|-------------|-------------|-------|-----------|-----------|----------|")
        
        for i, mod in enumerate(modifications, 1):
            change_pct = "N/A"
            try:
                old_val = float(mod.get('old_value', 0))
                new_val = float(mod.get('value', 0))
                if old_val != 0:
                    change_pct = f"{((new_val - old_val) / old_val * 100):.1f}%"
            except:
                pass
            
            report_lines.append(
                f"| {i} | {mod.get('object_type', 'N/A')} | "
                f"{mod.get('object_name', 'N/A')} | {mod.get('field', 'N/A')} | "
                f"{mod.get('old_value', 'N/A')} | {mod.get('value', 'N/A')} | {change_pct} |"
            )
    
    else:  # text format
        report_lines.append("IDF MODIFICATION REPORT")
        report_lines.append("=" * 50)
        report_lines.append(f"Generated: {timestamp}")
        report_lines.append("\nSUMMARY")
        report_lines.append("-" * 20)
        report_lines.append(f"Total modifications: {len(modifications)}")
        
        type_counts = {}
        for mod in modifications:
            obj_type = mod.get('object_type', 'Unknown')
            type_counts[obj_type] = type_counts.get(obj_type, 0) + 1
        
        report_lines.append("\nModifications by type:")
        for obj_type, count in sorted(type_counts.items()):
            report_lines.append(f"  - {obj_type}: {count}")
        
        report_lines.append("\nDETAILED MODIFICATIONS")
        report_lines.append("-" * 50)
        
        for i, mod in enumerate(modifications, 1):
            report_lines.append(f"\n{i}. {mod.get('object_type', 'N/A')} - {mod.get('object_name', 'N/A')}")
            report_lines.append(f"   Field: {mod.get('field', 'N/A')}")
            report_lines.append(f"   Old Value: {mod.get('old_value', 'N/A')}")
            report_lines.append(f"   New Value: {mod.get('value', 'N/A')}")
    
    report_content = '\n'.join(report_lines)
    
    # Save to file if path provided
    if output_path:
        try:
            output_path.write_text(report_content)
            logger.info(f"Report saved to {output_path}")
        except Exception as e:
            logger.error(f"Error saving report: {e}")
    
    return report_content


def generate_scenario_report(scenario: Dict[str, Any], 
                           results: Optional[Dict[str, Any]] = None,
                           output_path: Optional[Path] = None) -> str:
    """
    Generate a scenario report with modifications and results
    
    Args:
        scenario: Scenario dictionary
        results: Optional simulation results
        output_path: Optional path to save the report
        
    Returns:
        Report content as string
    """
    report_lines = []
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    report_lines.append(f"SCENARIO REPORT: {scenario.get('name', 'Unnamed')}")
    report_lines.append("=" * 60)
    report_lines.append(f"Generated: {timestamp}")
    report_lines.append(f"\nDescription: {scenario.get('description', 'No description')}")
    
    # Scenario parameters
    if 'parameters' in scenario:
        report_lines.append("\nSCENARIO PARAMETERS")
        report_lines.append("-" * 30)
        for param, value in scenario['parameters'].items():
            report_lines.append(f"  {param}: {value}")
    
    # Modifications summary
    modifications = scenario.get('modifications', [])
    report_lines.append(f"\nMODIFICATIONS ({len(modifications)} total)")
    report_lines.append("-" * 30)
    
    # Group modifications by type
    mod_groups = {}
    for mod in modifications:
        obj_type = mod.get('object_type', 'Unknown')
        if obj_type not in mod_groups:
            mod_groups[obj_type] = []
        mod_groups[obj_type].append(mod)
    
    for obj_type, mods in sorted(mod_groups.items()):
        report_lines.append(f"\n{obj_type} ({len(mods)} modifications):")
        for mod in mods[:5]:  # Show first 5
            report_lines.append(
                f"  - {mod.get('object_name', 'N/A')}: "
                f"{mod.get('field', 'N/A')} = {mod.get('value', 'N/A')}"
            )
        if len(mods) > 5:
            report_lines.append(f"  ... and {len(mods) - 5} more")
    
    # Simulation results if available
    if results:
        report_lines.append("\nSIMULATION RESULTS")
        report_lines.append("-" * 30)
        
        if 'energy' in results:
            report_lines.append("\nEnergy Consumption:")
            for key, value in results['energy'].items():
                report_lines.append(f"  {key}: {value}")
        
        if 'comfort' in results:
            report_lines.append("\nComfort Metrics:")
            for key, value in results['comfort'].items():
                report_lines.append(f"  {key}: {value}")
        
        if 'cost' in results:
            report_lines.append("\nCost Analysis:")
            for key, value in results['cost'].items():
                report_lines.append(f"  {key}: {value}")
    
    report_content = '\n'.join(report_lines)
    
    if output_path:
        try:
            output_path.write_text(report_content)
            logger.info(f"Scenario report saved to {output_path}")
        except Exception as e:
            logger.error(f"Error saving scenario report: {e}")
    
    return report_content


def generate_comparison_report(scenarios: List[Dict[str, Any]], 
                             results: Dict[str, Dict[str, Any]],
                             output_path: Optional[Path] = None) -> str:
    """
    Generate a comparison report for multiple scenarios
    
    Args:
        scenarios: List of scenario dictionaries
        results: Dictionary mapping scenario names to results
        output_path: Optional path to save the report
        
    Returns:
        Report content as string
    """
    report_lines = []
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    report_lines.append("SCENARIO COMPARISON REPORT")
    report_lines.append("=" * 60)
    report_lines.append(f"Generated: {timestamp}")
    report_lines.append(f"Scenarios compared: {len(scenarios)}")
    
    # Create comparison table
    report_lines.append("\nENERGY CONSUMPTION COMPARISON")
    report_lines.append("-" * 50)
    
    # Header
    header = "Scenario".ljust(25) + "Total Energy".rjust(15) + "% vs Baseline".rjust(15)
    report_lines.append(header)
    report_lines.append("-" * 55)
    
    # Find baseline
    baseline_energy = None
    for scenario in scenarios:
        name = scenario.get('name', 'Unknown')
        if 'baseline' in name.lower() and name in results:
            baseline_energy = results[name].get('energy', {}).get('total', 0)
            break
    
    # Compare each scenario
    for scenario in scenarios:
        name = scenario.get('name', 'Unknown')
        if name in results:
            total_energy = results[name].get('energy', {}).get('total', 0)
            
            if baseline_energy and baseline_energy > 0:
                pct_diff = ((total_energy - baseline_energy) / baseline_energy) * 100
                pct_str = f"{pct_diff:+.1f}%"
            else:
                pct_str = "N/A"
            
            row = name[:25].ljust(25) + f"{total_energy:,.0f}".rjust(15) + pct_str.rjust(15)
            report_lines.append(row)
    
    # Best performing scenarios
    report_lines.append("\nBEST PERFORMING SCENARIOS")
    report_lines.append("-" * 30)
    
    # Sort by energy consumption
    scenario_energy = []
    for scenario in scenarios:
        name = scenario.get('name', 'Unknown')
        if name in results:
            total = results[name].get('energy', {}).get('total', float('inf'))
            scenario_energy.append((name, total))
    
    scenario_energy.sort(key=lambda x: x[1])
    
    for i, (name, energy) in enumerate(scenario_energy[:5], 1):
        report_lines.append(f"{i}. {name}: {energy:,.0f} kWh")
    
    report_content = '\n'.join(report_lines)
    
    if output_path:
        try:
            output_path.write_text(report_content)
            logger.info(f"Comparison report saved to {output_path}")
        except Exception as e:
            logger.error(f"Error saving comparison report: {e}")
    
    return report_content


def generate_validation_report(validation_results: List[Tuple[str, bool, List[str]]],
                             output_path: Optional[Path] = None) -> str:
    """
    Generate a validation report
    
    Args:
        validation_results: List of (item_name, is_valid, errors) tuples
        output_path: Optional path to save the report
        
    Returns:
        Report content as string
    """
    report_lines = []
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    report_lines.append("VALIDATION REPORT")
    report_lines.append("=" * 50)
    report_lines.append(f"Generated: {timestamp}")
    
    # Summary
    total_items = len(validation_results)
    valid_items = sum(1 for _, is_valid, _ in validation_results if is_valid)
    invalid_items = total_items - valid_items
    
    report_lines.append(f"\nSUMMARY")
    report_lines.append(f"Total items validated: {total_items}")
    report_lines.append(f"Valid items: {valid_items}")
    report_lines.append(f"Invalid items: {invalid_items}")
    report_lines.append(f"Success rate: {(valid_items / total_items * 100):.1f}%")
    
    # Errors by category
    if invalid_items > 0:
        report_lines.append("\nVALIDATION ERRORS")
        report_lines.append("-" * 30)
        
        error_count = {}
        for item_name, is_valid, errors in validation_results:
            if not is_valid:
                report_lines.append(f"\n{item_name}:")
                for error in errors:
                    report_lines.append(f"  - {error}")
                    
                    # Count error types
                    error_type = error.split(':')[0] if ':' in error else 'General'
                    error_count[error_type] = error_count.get(error_type, 0) + 1
        
        report_lines.append("\nERROR SUMMARY BY TYPE")
        report_lines.append("-" * 20)
        for error_type, count in sorted(error_count.items(), key=lambda x: x[1], reverse=True):
            report_lines.append(f"  {error_type}: {count}")
    
    report_content = '\n'.join(report_lines)
    
    if output_path:
        try:
            output_path.write_text(report_content)
            logger.info(f"Validation report saved to {output_path}")
        except Exception as e:
            logger.error(f"Error saving validation report: {e}")
    
    return report_content


def export_modifications_to_csv(modifications: List[Dict[str, Any]], 
                              output_path: Path) -> bool:
    """
    Export modifications to CSV file
    
    Args:
        modifications: List of modification dictionaries
        output_path: Path for the CSV file
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Prepare data for CSV
        rows = []
        for mod in modifications:
            row = {
                'timestamp': mod.get('timestamp', datetime.datetime.now().isoformat()),
                'object_type': mod.get('object_type', ''),
                'object_name': mod.get('object_name', ''),
                'field': mod.get('field', ''),
                'old_value': mod.get('old_value', ''),
                'new_value': mod.get('value', ''),
                'action': mod.get('action', 'modify'),
                'scenario': mod.get('scenario', ''),
                'modifier': mod.get('modifier', '')
            }
            rows.append(row)
        
        # Write to CSV
        df = pd.DataFrame(rows)
        df.to_csv(output_path, index=False)
        
        logger.info(f"Exported {len(modifications)} modifications to {output_path}")
        return True
        
    except Exception as e:
        logger.error(f"Error exporting to CSV: {e}")
        return False


def export_modifications_to_json(modifications: List[Dict[str, Any]], 
                               output_path: Path,
                               include_metadata: bool = True) -> bool:
    """
    Export modifications to JSON file
    
    Args:
        modifications: List of modification dictionaries
        output_path: Path for the JSON file
        include_metadata: Whether to include metadata
        
    Returns:
        True if successful, False otherwise
    """
    try:
        data = {
            'modifications': modifications
        }
        
        if include_metadata:
            data['metadata'] = {
                'version': '1.0',
                'timestamp': datetime.datetime.now().isoformat(),
                'total_modifications': len(modifications),
                'object_types': list(set(m.get('object_type', 'Unknown') for m in modifications))
            }
        
        # Write to JSON
        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Exported {len(modifications)} modifications to {output_path}")
        return True
        
    except Exception as e:
        logger.error(f"Error exporting to JSON: {e}")
        return False


def create_modification_summary(modifications: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Create a summary of modifications
    
    Args:
        modifications: List of modification dictionaries
        
    Returns:
        Summary dictionary
    """
    summary = {
        'total_modifications': len(modifications),
        'by_object_type': {},
        'by_field': {},
        'by_action': {},
        'numeric_changes': []
    }
    
    for mod in modifications:
        # Count by object type
        obj_type = mod.get('object_type', 'Unknown')
        summary['by_object_type'][obj_type] = summary['by_object_type'].get(obj_type, 0) + 1
        
        # Count by field
        field = mod.get('field', 'Unknown')
        summary['by_field'][field] = summary['by_field'].get(field, 0) + 1
        
        # Count by action
        action = mod.get('action', 'modify')
        summary['by_action'][action] = summary['by_action'].get(action, 0) + 1
        
        # Track numeric changes
        try:
            old_val = float(mod.get('old_value', 0))
            new_val = float(mod.get('value', 0))
            if old_val != 0:
                pct_change = ((new_val - old_val) / old_val) * 100
                summary['numeric_changes'].append({
                    'object': f"{obj_type}.{mod.get('object_name', 'Unknown')}",
                    'field': field,
                    'old_value': old_val,
                    'new_value': new_val,
                    'change_percent': pct_change
                })
        except:
            pass
    
    # Sort numeric changes by impact
    summary['numeric_changes'].sort(key=lambda x: abs(x['change_percent']), reverse=True)
    
    return summary





# Add these functions to your reporting.py file

def export_modifications_to_parquet(modifications: List[Dict[str, Any]], 
                                  output_path: Path,
                                  include_metadata: bool = True,
                                  format: str = 'wide') -> bool:
    """
    Export modifications to Parquet file in wide format
    
    Args:
        modifications: List of modification dictionaries
        output_path: Path for the Parquet file
        include_metadata: Whether to include metadata in file metadata
        format: 'wide' (new default) or 'long' (legacy)
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # First create long format as before
        rows = []
        for mod in modifications:
            # Add parameter_scope classification
            object_type = mod.get('object_type', '').upper()
            parameter_scope = _classify_parameter_scope(object_type)
            
            # Extract zone_name
            zone_name = _extract_zone_name(mod, parameter_scope)
            
            row = {
                'timestamp': mod.get('timestamp', datetime.datetime.now().isoformat()),
                'building_id': mod.get('building_id', ''),
                'variant_id': mod.get('variant_id', ''),
                'parameter_scope': parameter_scope,  # NEW FIELD
                'zone_name': zone_name,              # NEW FIELD
                'category': mod.get('category', ''),
                'object_type': mod.get('object_type', ''),
                'object_name': mod.get('object_name', ''),
                'parameter': mod.get('parameter', ''),
                'field': mod.get('parameter', mod.get('field', '')),  # <-- USE 'parameter' if 'field' is empty
                'original_value': str(mod.get('original_value', '')),
                'new_value': str(mod.get('new_value', mod.get('value', ''))),
                'original_value_numeric': None,
                'new_value_numeric': None,
                'change_type': mod.get('change_type', 'unknown'),
                'change_percentage': None,
                'rule_applied': mod.get('rule_applied', ''),
                'action': mod.get('action', 'modify'),
                'scenario': mod.get('scenario', ''),
                'modifier': mod.get('modifier', ''),
                'validation_status': mod.get('validation_status', 'unknown'),
                'success': mod.get('success', True),
                'message': mod.get('message', '')
            }
            
            # Try to extract numeric values
            try:
                row['original_value_numeric'] = float(mod.get('original_value', 0))
                row['new_value_numeric'] = float(mod.get('new_value', mod.get('value', 0)))
                if row['original_value_numeric'] != 0:
                    row['change_percentage'] = ((row['new_value_numeric'] - row['original_value_numeric']) / 
                                               row['original_value_numeric']) * 100
            except (ValueError, TypeError):
                pass
            
            
            rows.append(row)
        
        # Create long format DataFrame
        df_long = pd.DataFrame(rows)
        
        if format == 'wide':
            # Convert to wide format
            df = _convert_to_wide_format(df_long)
        else:
            df = df_long
        
        # Define optimal dtypes for Parquet
        dtype_mapping = {
            'timestamp': 'string',
            'building_id': 'string',
            'variant_id': 'string',
            'category': 'category',
            'object_type': 'category',
            'object_name': 'string',
            'parameter': 'string',
            'field': 'string',
            'original_value': 'string',
            'new_value': 'string',
            'original_value_numeric': 'float64',
            'new_value_numeric': 'float64',
            'change_percentage': 'float64',
            'change_type': 'category',
            'rule_applied': 'string',
            'action': 'category',
            'scenario': 'string',
            'modifier': 'category',
            'validation_status': 'category',
            'success': 'bool',
            'message': 'string'
        }
        
        # Apply dtypes
        for col, dtype in dtype_mapping.items():
            if col in df.columns:
                try:
                    if dtype == 'category':
                        df[col] = df[col].astype('category')
                    elif dtype == 'bool':
                        df[col] = df[col].astype('bool')
                    elif dtype == 'float64':
                        df[col] = pd.to_numeric(df[col], errors='coerce')
                    else:
                        df[col] = df[col].astype(dtype)
                except Exception as e:
                    logger.debug(f"Could not convert column {col} to {dtype}: {e}")
        
        # Write to Parquet with metadata
        if include_metadata:
            metadata = {
                'version': '1.0',
                'creation_timestamp': datetime.datetime.now().isoformat(),
                'total_modifications': len(modifications),
                'unique_buildings': df['building_id'].nunique(),
                'unique_categories': df['category'].nunique(),
                'unique_object_types': df['object_type'].nunique(),
            }
            
            # Convert metadata to bytes for Parquet
            import pyarrow as pa
            import pyarrow.parquet as pq
            
            table = pa.Table.from_pandas(df)
            # Add metadata to schema
            existing_metadata = table.schema.metadata or {}
            combined_metadata = {**existing_metadata, 
                               **{k.encode(): str(v).encode() for k, v in metadata.items()}}
            table = table.replace_schema_metadata(combined_metadata)
            pq.write_table(table, output_path, compression='snappy')
        else:
            df.to_parquet(output_path, engine='pyarrow', compression='snappy', index=False)
        
        logger.info(f"Exported {len(modifications)} modifications to Parquet: {output_path}")
        logger.info(f"File size: {output_path.stat().st_size / 1024:.1f} KB")
        return True
        
    except Exception as e:
        logger.error(f"Error exporting to Parquet: {e}")
        import traceback
        traceback.print_exc()
        return False




def _classify_parameter_scope(object_type: str) -> str:
    """
    Classify the parameter scope based on object type
    
    Returns: 'building', 'zone', or 'surface'
    """
    object_type = object_type.upper()
    
    # Building-level objects
    building_level = {
        'TIMESTEP', 'SIMULATIONCONTROL', 'BUILDING', 'SHADOWCALCULATION',
        'HEATBALANCEALGORITHM', 'SURFACECONVECTIONALGORITHM:INSIDE',
        'SURFACECONVECTIONALGORITHM:OUTSIDE', 'SITE:LOCATION', 
        'SITE:GROUNDTEMPERATURE:BUILDINGSURFACE', 'RUNPERIOD',
        'RUNPERIODCONTROL:SPECIALDAYS', 'RUNPERIODCONTROL:DAYLIGHTSAVINGTIME',
        'GLOBALGEOMETRYRULES', 'OUTPUT:VARIABLE', 'OUTPUT:METER',
        'OUTPUT:TABLE:SUMMARYREPORTS', 'OUTPUT:SQLITE', 'OUTPUTCONTROL:TABLE:STYLE',
        'MATERIAL', 'MATERIAL:NOMASS', 'WINDOWMATERIAL:SIMPLEGLAZINGSYSTEM',
        'CONSTRUCTION', 'VERSION'
    }
    
    # Surface-level objects
    surface_level = {
        'BUILDINGSURFACE:DETAILED', 'FENESTRATIONSURFACE:DETAILED',
        'FLOOR:DETAILED', 'WALL:DETAILED', 'ROOFCEILING:DETAILED',
        'WINDOW', 'DOOR', 'GLAZEDDOOR', 'SHADING:SITE', 'SHADING:BUILDING',
        'SHADING:ZONE', 'SHADING:SITE:DETAILED', 'SHADING:BUILDING:DETAILED',
        'SHADING:ZONE:DETAILED'
    }
    
    # Check classification
    if object_type in building_level:
        return 'building'
    elif object_type in surface_level:
        return 'surface'
    else:
        # Default to zone for everything else
        return 'zone'


def _extract_zone_name(mod: Dict[str, Any], parameter_scope: str) -> str:
    """
    Extract the appropriate zone name based on parameter scope
    """
    if parameter_scope == 'building':
        return 'BUILDING'
    
    # For zone and surface objects, check if zone_name is in the modification
    # This would need to be passed from the modifier
    zone_name = mod.get('zone_name', '')
    
    if zone_name == 'ALL_ZONES' or zone_name == '*':
        return 'ALL_ZONES'
    elif zone_name:
        return zone_name
    else:
        # Try to extract from object_name if it contains zone info
        # This is a fallback - ideally zone_name should be passed in mod
        return 'UNKNOWN'


def _convert_to_wide_format(df_long: pd.DataFrame) -> pd.DataFrame:
    """
    Convert long format modifications to wide format
    """
    # Group by all identifier columns
    group_cols = ['building_id', 'parameter_scope', 'zone_name', 
                  'category', 'object_type', 'object_name', 'field']
    
    # Get unique variant IDs
    variants = sorted(df_long['variant_id'].unique())
    
    # Create a pivot table
    # First, get original values AND change_type (from the first variant or base)
    original_df = df_long[df_long['variant_id'] == variants[0]][
        group_cols + ['original_value', 'change_type']  # ADD change_type here
    ].drop_duplicates()
    
    # Rename original_value to 'original'
    original_df = original_df.rename(columns={'original_value': 'original'})
    
    # Now pivot the new values for each variant
    pivot_df = df_long.pivot_table(
        index=group_cols,
        columns='variant_id',
        values='new_value',
        aggfunc='first'
    ).reset_index()
    
    # Rename variant columns
    variant_mapping = {v: f'variant_{i}' for i, v in enumerate(variants)}
    pivot_df = pivot_df.rename(columns=variant_mapping)
    
    # Merge with original values AND change_type
    wide_df = pd.merge(original_df, pivot_df, on=group_cols, how='outer')
    
    # Reorder columns - INCLUDE change_type after field
    col_order = group_cols + ['change_type', 'original'] + [f'variant_{i}' for i in range(len(variants))]
    wide_df = wide_df[col_order]
    
    return wide_df







def export_summary_statistics_to_parquet(modifications: List[Dict[str, Any]], 
                                       output_path: Path) -> bool:
    """
    Export summary statistics to a separate Parquet file
    
    Args:
        modifications: List of modification dictionaries
        output_path: Path for the summary Parquet file
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Create summary statistics by various dimensions
        summary_data = []
        
        # Group modifications for analysis
        from collections import defaultdict
        
        # By building and category
        building_category_stats = defaultdict(lambda: defaultdict(int))
        
        # By parameter
        parameter_stats = defaultdict(lambda: {
            'count': 0,
            'numeric_changes': [],
            'categories': set(),
            'buildings': set()
        })
        
        # Process each modification
        for mod in modifications:
            building_id = mod.get('building_id', 'unknown')
            category = mod.get('category', 'unknown')
            parameter = mod.get('parameter', 'unknown')
            
            # Count by building and category
            building_category_stats[building_id][category] += 1
            
            # Track parameter statistics
            param_stat = parameter_stats[parameter]
            param_stat['count'] += 1
            param_stat['categories'].add(category)
            param_stat['buildings'].add(building_id)
            
            # Track numeric changes
            try:
                old_val = float(mod.get('original_value', 0))
                new_val = float(mod.get('new_value', mod.get('value', 0)))
                if old_val != 0:
                    pct_change = ((new_val - old_val) / old_val) * 100
                    param_stat['numeric_changes'].append(pct_change)
            except:
                pass
        
        # Create summary rows
        # 1. Building-Category Summary
        for building_id, categories in building_category_stats.items():
            for category, count in categories.items():
                summary_data.append({
                    'summary_type': 'building_category',
                    'building_id': building_id,
                    'category': category,
                    'parameter': '',
                    'modification_count': count,
                    'avg_change_percentage': None,
                    'min_change_percentage': None,
                    'max_change_percentage': None,
                    'unique_parameters': 0,
                    'unique_buildings': 1
                })
        
        # 2. Parameter Summary
        for parameter, stats in parameter_stats.items():
            numeric_changes = stats['numeric_changes']
            
            summary_data.append({
                'summary_type': 'parameter',
                'building_id': '',
                'category': ','.join(sorted(stats['categories'])),
                'parameter': parameter,
                'modification_count': stats['count'],
                'avg_change_percentage': sum(numeric_changes) / len(numeric_changes) if numeric_changes else None,
                'min_change_percentage': min(numeric_changes) if numeric_changes else None,
                'max_change_percentage': max(numeric_changes) if numeric_changes else None,
                'unique_parameters': 1,
                'unique_buildings': len(stats['buildings'])
            })
        
        # 3. Overall Summary
        all_numeric_changes = []
        for mod in modifications:
            try:
                old_val = float(mod.get('original_value', 0))
                new_val = float(mod.get('new_value', mod.get('value', 0)))
                if old_val != 0:
                    pct_change = ((new_val - old_val) / old_val) * 100
                    all_numeric_changes.append(pct_change)
            except:
                pass
        
        summary_data.append({
            'summary_type': 'overall',
            'building_id': 'all',
            'category': 'all',
            'parameter': 'all',
            'modification_count': len(modifications),
            'avg_change_percentage': sum(all_numeric_changes) / len(all_numeric_changes) if all_numeric_changes else None,
            'min_change_percentage': min(all_numeric_changes) if all_numeric_changes else None,
            'max_change_percentage': max(all_numeric_changes) if all_numeric_changes else None,
            'unique_parameters': len(parameter_stats),
            'unique_buildings': len(building_category_stats)
        })
        
        # Create DataFrame
        df = pd.DataFrame(summary_data)
        
        # Write to Parquet
        df.to_parquet(output_path, engine='pyarrow', compression='snappy', index=False)
        
        logger.info(f"Exported summary statistics to Parquet: {output_path}")
        return True
        
    except Exception as e:
        logger.error(f"Error exporting summary to Parquet: {e}")
        import traceback
        traceback.print_exc()
        return False


def create_modification_database(job_output_dir: Path, 
                               include_parsed_data: bool = True) -> bool:
    """
    Create a comprehensive Parquet database of all modifications and related data
    
    Args:
        job_output_dir: The job output directory containing all data
        include_parsed_data: Whether to include parsed IDF data
        
    Returns:
        True if successful, False otherwise
    """
    try:
        db_dir = job_output_dir / 'modification_database'
        db_dir.mkdir(exist_ok=True)
        
        logger.info(f"Creating modification database in: {db_dir}")
        
        # 1. Find all modification reports
        mod_reports = list(job_output_dir.glob('**/modification_report_*.json'))
        
        all_modifications = []
        all_results = []
        
        for report_path in mod_reports:
            with open(report_path, 'r') as f:
                data = json.load(f)
                
            # Extract modifications
            if 'detailed_results' in data:
                for result in data['detailed_results']:
                    all_results.append(result)
                    for mod in result.get('modifications', []):
                        # Add context from result
                        mod['building_id'] = result.get('building_id', '')
                        mod['variant_id'] = result.get('variant_id', '')
                        mod['success'] = result.get('success', True)
                        all_modifications.append(mod)
        
        # 2. Export modifications to Parquet
        if all_modifications:
            # Export in wide format by default
            mods_parquet = db_dir / 'modifications_detail_wide.parquet'
            export_modifications_to_parquet(all_modifications, mods_parquet, format='wide')
            
            # Optionally also export in long format for compatibility
            mods_long_parquet = db_dir / 'modifications_detail_long.parquet'
            export_modifications_to_parquet(all_modifications, mods_long_parquet, format='long')
            
            # Export summary statistics
            summary_parquet = db_dir / 'modification_summary.parquet'
            export_summary_statistics_to_parquet(all_modifications, summary_parquet)
        
        # 3. Create results summary Parquet
        if all_results:
            results_df = pd.DataFrame([{
                'building_id': r.get('building_id', ''),
                'variant_id': r.get('variant_id', ''),
                'success': r.get('success', False),
                'modification_count': len(r.get('modifications', [])),
                'output_file': r.get('output_file', ''),
                'timestamp': r.get('timestamp', ''),
                'errors': '; '.join(r.get('errors', []))
            } for r in all_results])
            
            results_parquet = db_dir / 'results_summary.parquet'
            results_df.to_parquet(results_parquet, engine='pyarrow', compression='snappy', index=False)
            logger.info(f"Exported results summary to: {results_parquet}")
        
        # 4. Include parsed data if requested
        if include_parsed_data:
            parsed_dir = job_output_dir / 'parsed_data'
            if parsed_dir.exists():
                # Copy relevant parquet files
                import shutil
                for parquet_file in parsed_dir.glob('**/*.parquet'):
                    if 'parameter_matrix' in parquet_file.name:
                        dest = db_dir / f'parsed_{parquet_file.name}'
                        shutil.copy2(parquet_file, dest)
                        logger.info(f"Included parsed data: {parquet_file.name}")
        
        # 5. Create index file
        index_data = {
            'database_version': '1.0',
            'creation_timestamp': datetime.datetime.now().isoformat(),
            'job_id': job_output_dir.name,
            'total_modifications': len(all_modifications),
            'total_results': len(all_results),
            'files': {
                'modifications': 'modifications.parquet',
                'summary': 'modification_summary.parquet',
                'results': 'results_summary.parquet'
            }
        }
        
        index_path = db_dir / 'index.json'
        with open(index_path, 'w') as f:
            json.dump(index_data, f, indent=2)
        
        logger.info(f"Modification database created successfully in: {db_dir}")
        return True
        
    except Exception as e:
        logger.error(f"Error creating modification database: {e}")
        import traceback
        traceback.print_exc()
        return False