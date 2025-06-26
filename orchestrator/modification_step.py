"""
orchestrator/modification_step.py

IDF modification logic.
"""

import os
import json
import logging
from datetime import datetime
from pathlib import Path
from collections import defaultdict
import pandas as pd  # ADD THIS LINE
from typing import Dict, Any, Optional, List, Tuple  # Fixed: Added Tuple import

from idf_modification.modification_engine import ModificationEngine
from idf_modification.modification_config import ModificationConfig


def run_modification(
    modification_cfg: dict,
    job_output_dir: str,
    job_idf_dir: str,
    logger: logging.Logger
) -> Optional[Dict[str, Any]]:
    """
    Run IDF modification process.
    
    Returns:
        Dictionary containing modification results or None if failed
    """
    logger.info("[STEP] Starting IDF modification ...")
    
    # Get modification configuration
    mod_strategy = modification_cfg.get("modification_strategy", {})
    categories_to_modify = modification_cfg.get("categories_to_modify", {})
    base_idf_selection = modification_cfg.get("base_idf_selection", {})
    output_options = modification_cfg.get("output_options", {})
    
    # Update configuration for modification engine
    mod_config = {
        "base_idf_selection": base_idf_selection,
        "output_options": output_options,
        "categories": categories_to_modify
    }
    
    # Initialize modification engine
    mod_engine = ModificationEngine(
        project_dir=Path(job_output_dir),
        config=mod_config
    )
    
    logger.info(f"[INFO] Loaded {len(mod_engine.modifiers)} modifiers")
    
    # Select IDFs to modify
    idf_files_to_modify = select_idfs_to_modify(
        base_idf_selection, job_idf_dir, logger
    )
    
    if not idf_files_to_modify:
        logger.warning("[WARN] No IDF files found to modify")
        return None
    
    logger.info(f"[INFO] Found {len(idf_files_to_modify)} IDF files to modify")
    
    # Output directory for modified IDFs
    modified_idfs_dir = Path(job_output_dir) / "modified_idfs"
    modified_idfs_dir.mkdir(exist_ok=True)
    
    # Process each building
    all_modifications = []
    modification_results = []
    modified_building_data = []  # Track modified buildings for simulation
    
    for idf_path, building_id in idf_files_to_modify:
        logger.info(f"[INFO] Modifying building {building_id}")
        
        try:
            # Generate variants based on strategy
            strategy_type = mod_strategy.get("type", "scenarios")
            num_variants = mod_strategy.get("num_variants", 1)
            
            for variant_idx in range(num_variants):
                variant_id = f"variant_{variant_idx}"
                
                # Use modification engine's modify_building method
                result = mod_engine.modify_building(
                    building_id=building_id,
                    idf_path=idf_path,
                    parameter_values=categories_to_modify,
                    variant_id=variant_id
                )
                
                if result['success']:
                    logger.info(f"[INFO] Created variant: {result['output_file']}")
                    all_modifications.extend(result['modifications'])
                    modification_results.append(result)
                    
                    # Track modified building for simulation
                    modified_building_data.append({
                        'building_id': building_id,
                        'variant_id': variant_id,
                        'idf_path': result['output_file'],
                        'original_building_id': building_id  # Keep original ID
                    })
                else:
                    logger.error(f"[ERROR] Failed to create variant {variant_id}: {result['errors']}")
                    
        except Exception as e:
            logger.error(f"[ERROR] Failed to modify building {building_id}: {e}")
            import traceback
            logger.debug(traceback.format_exc())
    
    # Generate modification reports
    if output_options.get("save_report", True):
        generate_modification_reports(
            modification_results, all_modifications, 
            modified_idfs_dir, job_output_dir, 
            output_options, logger
        )
    
    logger.info(f"[INFO] Total modifications applied: {len(all_modifications)}")
    
    return {
        "modification_results": modification_results,
        "all_modifications": all_modifications,
        "modified_building_data": modified_building_data,
        "modified_idfs_dir": str(modified_idfs_dir)
    }


# Fix for orchestrator/modification_step.py

def select_idfs_to_modify(
    base_idf_selection: dict, 
    job_idf_dir: str,
    logger: logging.Logger
) -> List[tuple]:
    """
    Select IDF files to modify based on configuration.
    
    Args:
        base_idf_selection: Selection configuration
        job_idf_dir: Directory containing IDF files
        logger: Logger instance
    
    Returns:
        List of tuples (idf_path, building_id)
    """
    idf_files_to_modify = []
    
    if base_idf_selection.get("use_output_idfs", True) and os.path.exists(job_idf_dir):
        # Use generated IDFs
        selection_method = base_idf_selection.get("method", "all")
        
        if selection_method == "all":
            idf_files_to_modify = [
                (idf_file, idf_file.stem.replace("building_", "").split("_")[0])
                for idf_file in Path(job_idf_dir).glob("*.idf")
            ]
        
        elif selection_method == "specific":
            building_ids = base_idf_selection.get("building_ids", [])
            # Convert to strings for consistent comparison
            building_ids = [str(bid) for bid in building_ids]
            
            for building_id in building_ids:
                # Look for exact matches first
                exact_match_found = False
                
                # Try exact filename match first
                exact_patterns = [
                    f"building_{building_id}.idf",
                    f"building_{building_id}_*.idf"
                ]
                
                for pattern in exact_patterns:
                    idf_files = list(Path(job_idf_dir).glob(pattern))
                    if idf_files:
                        # Extract the building ID from the filename
                        for idf_file in idf_files:
                            # Extract building ID more carefully
                            filename = idf_file.stem
                            if filename.startswith(f"building_{building_id}"):
                                # Verify it's an exact match, not a partial match
                                extracted_id = filename.replace("building_", "").split("_")[0]
                                if extracted_id == building_id:
                                    idf_files_to_modify.append((idf_file, building_id))
                                    exact_match_found = True
                                    break
                    if exact_match_found:
                        break
                
                if not exact_match_found:
                    logger.warning(f"No IDF file found for building ID: {building_id}")
        
        else:  # representative
            num_buildings = base_idf_selection.get("num_buildings", 5)
            all_idfs = list(Path(job_idf_dir).glob("*.idf"))[:num_buildings]
            for idf_file in all_idfs:
                building_id = idf_file.stem.replace("building_", "").split("_")[0]
                idf_files_to_modify.append((idf_file, building_id))
    
    logger.info(f"Selected {len(idf_files_to_modify)} IDF files for modification")
    if selection_method == "specific" and idf_files_to_modify:
        logger.info(f"Selected building IDs: {[bid for _, bid in idf_files_to_modify]}")
    
    return idf_files_to_modify


# Also update the modification engine's _select_buildings method
# In idf_modification/modification_engine.py

def _select_buildings(self, building_ids: Optional[List[str]] = None) -> List[Tuple[str, Path]]:
    """Select buildings to modify based on configuration"""
    buildings = []
    
    # Get IDF directory
    idf_dir = self.project_dir / "output_IDFs"
    if not idf_dir.exists():
        idf_dir = self.project_dir
    
    # Get selection method from config
    selection = self.config.get('base_idf_selection', {})
    method = selection.get('method', 'all')
    
    if building_ids:
        # Use provided building IDs - ensure they're strings
        building_ids = [str(bid) for bid in building_ids]
        
        for bid in building_ids:
            # Look for exact matches only
            exact_patterns = [
                f"building_{bid}.idf",
                f"building_{bid}_*.idf"
            ]
            
            found = False
            for pattern in exact_patterns:
                files = list(idf_dir.glob(pattern))
                for file in files:
                    # Verify exact match
                    filename = file.stem
                    if filename.startswith(f"building_{bid}"):
                        extracted_id = filename.replace("building_", "").split("_")[0]
                        if extracted_id == bid:
                            buildings.append((bid, file))
                            found = True
                            break
                if found:
                    break
            
            if not found:
                self.logger.warning(f"No IDF file found for building ID: {bid}")
    
    elif method == 'specific':
        # Use specific building IDs from config
        config_building_ids = [str(bid) for bid in selection.get('building_ids', [])]
        
        for bid in config_building_ids:
            # Same exact matching logic as above
            exact_patterns = [
                f"building_{bid}.idf",
                f"building_{bid}_*.idf"
            ]
            
            found = False
            for pattern in exact_patterns:
                files = list(idf_dir.glob(pattern))
                for file in files:
                    filename = file.stem
                    if filename.startswith(f"building_{bid}"):
                        extracted_id = filename.replace("building_", "").split("_")[0]
                        if extracted_id == bid:
                            buildings.append((bid, file))
                            found = True
                            break
                if found:
                    break
            
            if not found:
                self.logger.warning(f"No IDF file found for building ID: {bid}")
    
    elif method == 'representative':
        # Select representative buildings
        num_buildings = selection.get('num_buildings', 5)
        all_idfs = list(idf_dir.glob("*.idf"))[:num_buildings]
        for idf_file in all_idfs:
            bid = idf_file.stem.replace("building_", "").split("_")[0]
            buildings.append((bid, idf_file))
    
    else:  # method == 'all'
        # Select all buildings
        for idf_file in idf_dir.glob("*.idf"):
            bid = idf_file.stem.replace("building_", "").split("_")[0]
            buildings.append((bid, idf_file))
    
    self.logger.info(f"Selected {len(buildings)} buildings for modification")
    if method == 'specific' and buildings:
        self.logger.info(f"Selected building IDs: {[bid for bid, _ in buildings]}")
    
    return buildings


def generate_modification_reports(
    modification_results: list,
    all_modifications: list,
    modified_idfs_dir: Path,
    job_output_dir: str,
    output_options: dict,
    logger: logging.Logger
) -> None:
    """
    Generate modification reports in multiple formats including parquet.
    """
    report_formats = output_options.get("report_formats", ["json"])
    logger.info(f"[INFO] Generating modification reports: {report_formats}")
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Prepare base report data
    report_data = {
        'metadata': {
            'job_id': os.path.basename(job_output_dir),
            'timestamp': datetime.now().isoformat(),
            'output_directory': str(modified_idfs_dir),
        },
        'summary': {
            'total_variants': len(modification_results),
            'successful': sum(1 for r in modification_results if r['success']),
            'total_modifications': len(all_modifications),
        },
        'results': modification_results
    }
    
    # 1. JSON report (always generate as it's the default)
    if "json" in report_formats or True:  # Always save JSON
        report_path = modified_idfs_dir / f"modification_report_{timestamp}.json"
        with open(report_path, 'w') as f:
            json.dump(report_data, f, indent=2, default=str)
        logger.info(f"[INFO] JSON report saved to: {report_path}")
    
    # 2. Parquet reports
    if "parquet" in report_formats:
        try:
            # Create modifications DataFrame
            modifications_data = []
            for mod in all_modifications:
                modifications_data.append({
                    'building_id': mod.get('building_id', ''),
                    'variant_id': mod.get('variant_id', ''),
                    'category': mod.get('category', ''),
                    'object_type': mod.get('object_type', ''),
                    'object_name': mod.get('object_name', ''),
                    'field_name': mod.get('parameter', ''), 
                    'original_value': str(mod.get('original_value', '')),
                    'new_value': str(mod.get('new_value', '')),
                    'change_type': mod.get('change_type', ''),
                    'timestamp': mod.get('timestamp', datetime.now().isoformat())
                })
            
            if modifications_data:
                modifications_df = pd.DataFrame(modifications_data)
                modifications_parquet = modified_idfs_dir / f"modifications_detail_{timestamp}.parquet"
                modifications_df.to_parquet(modifications_parquet, index=False)
                logger.info(f"[INFO] Modifications parquet saved to: {modifications_parquet}")
            
            # Create summary DataFrame
            summary_data = []
            for result in modification_results:
                summary_data.append({
                    'building_id': result.get('building_id', ''),
                    'variant_id': result.get('variant_id', ''),
                    'success': result.get('success', False),
                    'output_file': result.get('output_file', ''),
                    'num_modifications': len(result.get('modifications', [])),
                    'categories_modified': list(set(m['category'] for m in result.get('modifications', []))),
                    'timestamp': datetime.now().isoformat()
                })
            
            if summary_data:
                summary_df = pd.DataFrame(summary_data)
                summary_parquet = modified_idfs_dir / f"modifications_summary_{timestamp}.parquet"
                summary_df.to_parquet(summary_parquet, index=False)
                logger.info(f"[INFO] Summary parquet saved to: {summary_parquet}")
            
            # Create parameter changes DataFrame (useful for analysis)
            param_changes = []
            for mod in all_modifications:
                if mod.get('field_name') and mod.get('original_value') is not None:
                    try:
                        # Try to convert to numeric for analysis
                        orig_val = float(mod['original_value']) if mod['original_value'] != '' else None
                        new_val = float(mod['new_value']) if mod['new_value'] != '' else None
                        if orig_val is not None and new_val is not None:
                            change_percent = ((new_val - orig_val) / orig_val * 100) if orig_val != 0 else 0
                        else:
                            change_percent = None
                    except (ValueError, TypeError):
                        orig_val = None
                        new_val = None
                        change_percent = None
                    
                    param_changes.append({
                        'building_id': mod.get('building_id', ''),
                        'variant_id': mod.get('variant_id', ''),
                        'parameter': f"{mod.get('category', '')}_{mod.get('field_name', '')}",
                        'original_value_numeric': orig_val,
                        'new_value_numeric': new_val,
                        'change_percent': change_percent,
                        'original_value_str': str(mod.get('original_value', '')),
                        'new_value_str': str(mod.get('new_value', ''))
                    })
            
            if param_changes:
                param_df = pd.DataFrame(param_changes)
                param_parquet = modified_idfs_dir / f"parameter_changes_{timestamp}.parquet"
                param_df.to_parquet(param_parquet, index=False)
                logger.info(f"[INFO] Parameter changes parquet saved to: {param_parquet}")
                
        except Exception as e:
            logger.error(f"[ERROR] Failed to generate parquet reports: {e}")
            import traceback
            logger.debug(traceback.format_exc())
    
    # 3. CSV reports
    if "csv" in report_formats:
        try:
            # Save modifications as CSV
            if 'modifications_df' in locals():
                modifications_csv = modified_idfs_dir / f"modifications_detail_{timestamp}.csv"
                modifications_df.to_csv(modifications_csv, index=False)
                logger.info(f"[INFO] Modifications CSV saved to: {modifications_csv}")
            
            # Save summary as CSV
            if 'summary_df' in locals():
                summary_csv = modified_idfs_dir / f"modifications_summary_{timestamp}.csv"
                summary_df.to_csv(summary_csv, index=False)
                logger.info(f"[INFO] Summary CSV saved to: {summary_csv}")
                
        except Exception as e:
            logger.error(f"[ERROR] Failed to generate CSV reports: {e}")
    
    # 4. HTML report
    if "html" in report_formats:
        try:
            html_content = generate_html_report(report_data, all_modifications)
            html_path = modified_idfs_dir / f"modification_report_{timestamp}.html"
            with open(html_path, 'w') as f:
                f.write(html_content)
            logger.info(f"[INFO] HTML report saved to: {html_path}")
        except Exception as e:
            logger.error(f"[ERROR] Failed to generate HTML report: {e}")
    
    # 5. Markdown report
    if "markdown" in report_formats:
        try:
            md_content = generate_markdown_report(report_data, all_modifications)
            md_path = modified_idfs_dir / f"modification_report_{timestamp}.md"
            with open(md_path, 'w') as f:
                f.write(md_content)
            logger.info(f"[INFO] Markdown report saved to: {md_path}")
        except Exception as e:
            logger.error(f"[ERROR] Failed to generate Markdown report: {e}")
    
    logger.info(f"[INFO] Modification reports generation complete")


def generate_html_report(report_data: dict, all_modifications: list) -> str:
    """Generate HTML report content"""
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Modification Report</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            h1, h2 {{ color: #333; }}
            table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
            th {{ background-color: #f2f2f2; }}
            .summary {{ background-color: #f9f9f9; padding: 15px; border-radius: 5px; }}
        </style>
    </head>
    <body>
        <h1>IDF Modification Report</h1>
        <div class="summary">
            <h2>Summary</h2>
            <p>Job ID: {report_data['metadata']['job_id']}</p>
            <p>Timestamp: {report_data['metadata']['timestamp']}</p>
            <p>Total Variants: {report_data['summary']['total_variants']}</p>
            <p>Successful: {report_data['summary']['successful']}</p>
            <p>Total Modifications: {report_data['summary']['total_modifications']}</p>
        </div>
        
        <h2>Modifications by Category</h2>
        <table>
            <tr>
                <th>Category</th>
                <th>Count</th>
                <th>Parameters Modified</th>
            </tr>
    """
    
    # Group modifications by category
    from collections import defaultdict
    category_stats = defaultdict(lambda: {'count': 0, 'params': set()})
    
    for mod in all_modifications:
        cat = mod.get('category', 'unknown')
        category_stats[cat]['count'] += 1
        if mod.get('field_name'):
            category_stats[cat]['params'].add(mod['field_name'])
    
    for category, stats in sorted(category_stats.items()):
        html += f"""
            <tr>
                <td>{category}</td>
                <td>{stats['count']}</td>
                <td>{', '.join(sorted(stats['params']))}</td>
            </tr>
        """
    
    html += """
        </table>
    </body>
    </html>
    """
    
    return html


def generate_markdown_report(report_data: dict, all_modifications: list) -> str:
    """Generate Markdown report content"""
    md = f"""# IDF Modification Report

## Summary

- **Job ID**: {report_data['metadata']['job_id']}
- **Timestamp**: {report_data['metadata']['timestamp']}
- **Total Variants**: {report_data['summary']['total_variants']}
- **Successful**: {report_data['summary']['successful']}
- **Total Modifications**: {report_data['summary']['total_modifications']}

## Modifications by Category

| Category | Count | Parameters Modified |
|----------|-------|-------------------|
"""
    
    # Group modifications by category
    from collections import defaultdict
    category_stats = defaultdict(lambda: {'count': 0, 'params': set()})
    
    for mod in all_modifications:
        cat = mod.get('category', 'unknown')
        category_stats[cat]['count'] += 1
        if mod.get('field_name'):
            category_stats[cat]['params'].add(mod['field_name'])
    
    for category, stats in sorted(category_stats.items()):
        params_str = ', '.join(sorted(stats['params']))
        md += f"| {category} | {stats['count']} | {params_str} |\n"
    
    # Add modification details section
    md += "\n## Modification Details\n\n"
    
    # Group by building and variant
    from collections import defaultdict
    by_building = defaultdict(lambda: defaultdict(list))
    
    for mod in all_modifications[:50]:  # Limit to first 50 for readability
        building = mod.get('building_id', 'unknown')
        variant = mod.get('variant_id', 'unknown')
        by_building[building][variant].append(mod)
    
    for building_id in sorted(by_building.keys()):
        md += f"\n### Building {building_id}\n\n"
        for variant_id in sorted(by_building[building_id].keys()):
            md += f"#### Variant {variant_id}\n\n"
            mods = by_building[building_id][variant_id]
            
            for mod in mods[:10]:  # Limit per variant
                md += f"- **{mod.get('category', 'unknown')}** - {mod.get('object_type', '')} "
                md += f"`{mod.get('field_name', '')}`: "
                md += f"{mod.get('original_value', '')} → {mod.get('new_value', '')}\n"
            
            if len(mods) > 10:
                md += f"- ... and {len(mods) - 10} more modifications\n"
    
    return md