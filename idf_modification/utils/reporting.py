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
from typing import Dict, List, Any, Optional, Union
from pathlib import Path
import pandas as pd
import logging

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