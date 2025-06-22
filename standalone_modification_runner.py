"""
Standalone Modification Runner
Runs only the modification part of the EnergyPlus workflow using existing outputs
"""

import os
import sys
import json
import logging
from pathlib import Path
from datetime import datetime
import pandas as pd
import shutil

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import modification-related modules
from idf_modification.modification_engine import ModificationEngine
from idf_modification.modification_config import ModificationConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class StandaloneModificationRunner:
    """Run modifications independently using existing outputs"""
    
    def __init__(self, job_id: str, base_output_dir: str = None):
        """
        Initialize the runner
        
        Args:
            job_id: The job ID from previous run (e.g., "650e5027-2c43-4a30-b588-5e4d72c0ac23")
            base_output_dir: Base output directory (defaults to environment variable or hardcoded path)
        """
        self.job_id = job_id
        
        # Set up paths
        if base_output_dir:
            self.base_output_dir = Path(base_output_dir)
        else:
            # Try environment variable first, then fallback to hardcoded path
            env_output_dir = os.environ.get("OUTPUT_DIR")
            if env_output_dir:
                self.base_output_dir = Path(env_output_dir)
            else:
                self.base_output_dir = Path(r"D:\Documents\daily\E_Plus_2040_py\output")
        
        self.job_output_dir = self.base_output_dir / job_id
        
        # Verify job directory exists
        if not self.job_output_dir.exists():
            raise ValueError(f"Job output directory not found: {self.job_output_dir}")
        
        # Set up key paths
        self.idf_dir = self.job_output_dir / "output_IDFs"
        self.parsed_data_dir = self.job_output_dir / "parsed_data"
        self.modified_idfs_dir = self.job_output_dir / "modified_idfs"
        
        # Create output directory for modifications
        self.modified_idfs_dir.mkdir(exist_ok=True)
        
        logger.info(f"Initialized standalone runner for job: {job_id}")
        logger.info(f"Job output directory: {self.job_output_dir}")
        
    def load_configuration(self, config_path: str = None):
        """
        Load configuration from file
        
        Args:
            config_path: Path to configuration file (defaults to combined.json in user_configs)
        """
        if config_path:
            config_file = Path(config_path)
        else:
            # Try to find config in typical locations
            possible_paths = [
                Path("user_configs") / self.job_id / "combined.json",
                Path("user_configs") / self.job_id / "main_config.json",
                self.job_output_dir / "combined.json",
                self.job_output_dir / "main_config.json"
            ]
            
            config_file = None
            for path in possible_paths:
                if path.exists():
                    config_file = path
                    break
            
            if not config_file:
                raise FileNotFoundError("Could not find configuration file")
        
        logger.info(f"Loading configuration from: {config_file}")
        
        with open(config_file, 'r') as f:
            config_data = json.load(f)
        
        # Extract modification configuration
        if 'main_config' in config_data:
            self.modification_cfg = config_data['main_config'].get('modification', {})
        else:
            self.modification_cfg = config_data.get('modification', {})
        
        # Also load the categories to modify
        self.categories_to_modify = self.modification_cfg.get('categories_to_modify', {})
        
        logger.info(f"Loaded modification config with {len(self.categories_to_modify)} categories")
        logger.info(f"Categories to modify: {list(self.categories_to_modify.keys())}")
        
        return self.modification_cfg
    
    def get_available_idfs(self):
        """Get list of available IDF files"""
        if not self.idf_dir.exists():
            logger.warning(f"IDF directory not found: {self.idf_dir}")
            return []
        
        idf_files = list(self.idf_dir.glob("*.idf"))
        logger.info(f"Found {len(idf_files)} IDF files")
        
        # Extract building IDs
        building_info = []
        for idf_file in idf_files:
            # Extract building ID from filename (e.g., building_4136733.idf -> 4136733)
            filename = idf_file.stem
            if filename.startswith("building_"):
                building_id = filename.replace("building_", "").split("_")[0]
            else:
                building_id = filename.split("_")[0]
            
            building_info.append({
                'building_id': building_id,
                'idf_path': idf_file,
                'filename': idf_file.name
            })
        
        return building_info
    
    def select_buildings_to_modify(self, building_info):
        """Select buildings based on configuration"""
        base_idf_selection = self.modification_cfg.get('base_idf_selection', {})
        method = base_idf_selection.get('method', 'all')
        
        logger.info(f"Selecting buildings using method: {method}")
        
        selected = []
        
        if method == 'all':
            selected = building_info
        
        elif method == 'specific':
            building_ids = base_idf_selection.get('building_ids', [])
            building_ids = [str(bid) for bid in building_ids]  # Convert to strings
            
            for info in building_info:
                if info['building_id'] in building_ids:
                    selected.append(info)
        
        elif method == 'representative':
            num_buildings = base_idf_selection.get('num_buildings', 5)
            selected = building_info[:num_buildings]
        
        logger.info(f"Selected {len(selected)} buildings for modification")
        return selected
    
    def run_modifications(self):
        """Run the modification process with enhanced reporting"""
        logger.info("="*60)
        logger.info("Starting modification process")
        logger.info("="*60)
        
        # Get modification strategy
        mod_strategy = self.modification_cfg.get('modification_strategy', {})
        strategy_type = mod_strategy.get('type', 'scenarios')
        num_variants = mod_strategy.get('num_variants', 1)
        
        logger.info(f"Modification strategy: {strategy_type}")
        logger.info(f"Number of variants: {num_variants}")
        
        # Get output options
        output_options = self.modification_cfg.get('output_options', {})
        report_formats = output_options.get('report_formats', ['json'])
        
        # Initialize modification engine
        logger.info("Initializing modification engine...")
        
        # Create config for modification engine
        engine_config = {
            'base_idf_selection': self.modification_cfg.get('base_idf_selection', {}),
            'output_options': output_options,
            'categories': self.categories_to_modify
        }
        
        # Initialize engine
        mod_engine = ModificationEngine(
            project_dir=self.job_output_dir,
            config=engine_config
        )
        
        logger.info(f"Loaded {len(mod_engine.modifiers)} modifiers")
        
        # Get available buildings
        building_info = self.get_available_idfs()
        if not building_info:
            logger.error("No IDF files found!")
            return
        
        # Select buildings to modify
        selected_buildings = self.select_buildings_to_modify(building_info)
        
        # Process each building
        all_results = []
        start_time = datetime.now()
        
        for building in selected_buildings:
            building_id = building['building_id']
            idf_path = building['idf_path']
            
            logger.info(f"\nProcessing building {building_id}")
            logger.info(f"IDF path: {idf_path}")
            
            try:
                # Generate variants based on strategy
                for variant_idx in range(num_variants):
                    variant_id = f"variant_{variant_idx}"
                    
                    logger.info(f"Creating {variant_id} for building {building_id}")
                    
                    # Use modification engine's modify_building method
                    result = mod_engine.modify_building(
                        building_id=building_id,
                        idf_path=idf_path,
                        parameter_values=self.categories_to_modify,
                        variant_id=variant_id
                    )
                    
                    # Add timing and building info
                    result['timestamp'] = datetime.now().isoformat()
                    result['building_info'] = building
                    
                    all_results.append(result)
                    
                    if result['success']:
                        logger.info(f"✓ Successfully created variant: {result['output_file']}")
                        logger.info(f"  Applied {len(result['modifications'])} modifications")
                    else:
                        logger.error(f"✗ Failed to create variant: {result['errors']}")
                        
            except Exception as e:
                logger.error(f"Error processing building {building_id}: {e}")
                import traceback
                traceback.print_exc()
                
                # Add failed result
                all_results.append({
                    'building_id': building_id,
                    'variant_id': 'error',
                    'success': False,
                    'errors': [str(e)],
                    'modifications': [],
                    'timestamp': datetime.now().isoformat()
                })
        
        # Calculate total processing time
        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()
        
        # Generate reports based on configured formats
        logger.info("\n" + "="*60)
        logger.info("Generating reports...")
        logger.info("="*60)
        
        generated_reports = []
        
        # Always generate JSON report
        if 'json' in report_formats or True:  # Always generate JSON
            report_path = self.generate_summary_report(all_results)
            generated_reports.append(('JSON', report_path))
        
        # Generate HTML report if requested
        if 'html' in report_formats:
            try:
                report_path = self.generate_html_report(all_results)
                generated_reports.append(('HTML', report_path))
            except Exception as e:
                logger.error(f"Failed to generate HTML report: {e}")
        
        # Generate CSV reports if requested
        if 'csv' in report_formats:
            try:
                self.generate_csv_report(all_results)
                generated_reports.append(('CSV', self.modified_idfs_dir / "modifications_*.csv"))
            except Exception as e:
                logger.error(f"Failed to generate CSV reports: {e}")
        
        # Generate Markdown report if requested
        if 'markdown' in report_formats:
            try:
                report_path = self.generate_markdown_report(all_results)
                generated_reports.append(('Markdown', report_path))
            except Exception as e:
                logger.error(f"Failed to generate Markdown report: {e}")
        
        # Generate Parquet reports if requested
        if 'parquet' in report_formats:
            try:
                success = self.generate_parquet_report(all_results)
                if success:
                    generated_reports.append(('Parquet Database', self.modified_idfs_dir / 'parquet_database'))
                    logger.info("Parquet files generated:")
                    logger.info(f"  - modifications_detail_*.parquet (detailed modifications)")
                    logger.info(f"  - modifications_summary_*.parquet (summary statistics)")
                    logger.info(f"  - parameter_matrix_*.parquet (building × parameter matrix)")
                    logger.info(f"  - parquet_database/index.json (database index)")
            except Exception as e:
                logger.error(f"Failed to generate Parquet reports: {e}")
                import traceback
                traceback.print_exc()

        # Log report generation summary
        logger.info("\nGenerated reports:")
        for report_type, path in generated_reports:
            logger.info(f"  {report_type}: {path}")
        
        # Summary statistics
        logger.info("\n" + "="*60)
        logger.info("MODIFICATION PROCESS COMPLETE")
        logger.info("="*60)
        logger.info(f"Total processing time: {processing_time:.1f} seconds")
        logger.info(f"Average time per variant: {processing_time/len(all_results):.1f} seconds" if all_results else "N/A")
        
        return all_results
    
    def generate_summary_report(self, results):
        """Generate a comprehensive JSON summary report"""
        logger.info("\n" + "="*60)
        logger.info("MODIFICATION SUMMARY")
        logger.info("="*60)
        
        total_attempts = len(results)
        successful = sum(1 for r in results if r['success'])
        total_modifications = sum(len(r['modifications']) for r in results)
        
        logger.info(f"Total variant attempts: {total_attempts}")
        logger.info(f"Successful variants: {successful}")
        logger.info(f"Failed variants: {total_attempts - successful}")
        logger.info(f"Total modifications applied: {total_modifications}")
        
        # Count modifications by category
        mod_by_category = {}
        mod_by_parameter = {}
        
        for result in results:
            for mod in result['modifications']:
                category = mod.get('category', 'unknown')
                mod_by_category[category] = mod_by_category.get(category, 0) + 1
                
                parameter = mod.get('parameter', 'unknown')
                mod_by_parameter[parameter] = mod_by_parameter.get(parameter, 0) + 1
        
        logger.info("\nModifications by category:")
        for category, count in sorted(mod_by_category.items()):
            percentage = (count / total_modifications * 100) if total_modifications > 0 else 0
            logger.info(f"  {category}: {count} ({percentage:.1f}%)")
        
        # Save detailed report
        report_path = self.modified_idfs_dir / f"modification_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        report_data = {
            'metadata': {
                'job_id': self.job_id,
                'timestamp': datetime.now().isoformat(),
                'output_directory': str(self.modified_idfs_dir),
            },
            'configuration': {
                'strategy': self.modification_cfg.get('modification_strategy'),
                'categories_enabled': [cat for cat, cfg in self.categories_to_modify.items() if cfg.get('enabled', False)],
            },
            'summary': {
                'total_attempts': total_attempts,
                'successful': successful,
                'failed': total_attempts - successful,
                'success_rate': (successful / total_attempts * 100) if total_attempts > 0 else 0,
                'total_modifications': total_modifications,
                'modifications_by_category': mod_by_category,
                'modifications_by_parameter': dict(sorted(mod_by_parameter.items(), key=lambda x: x[1], reverse=True)[:10])
            },
            'detailed_results': results
        }
        
        with open(report_path, 'w') as f:
            json.dump(report_data, f, indent=2, default=str)
        
        logger.info(f"\nDetailed JSON report saved to: {report_path}")
        
        return report_path
    
    def generate_html_report(self, results):
        """Generate an HTML report with styling and charts"""
        logger.info("Generating HTML report...")
        
        report_path = self.modified_idfs_dir / f"modification_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        
        # Calculate statistics
        total_attempts = len(results)
        successful = sum(1 for r in results if r['success'])
        total_modifications = sum(len(r['modifications']) for r in results)
        
        # Count modifications by category
        mod_by_category = {}
        mod_by_building = {}
        mod_by_parameter = {}
        
        for result in results:
            building_id = result.get('building_id', 'unknown')
            mod_by_building[building_id] = mod_by_building.get(building_id, 0) + len(result['modifications'])
            
            for mod in result['modifications']:
                # By category
                category = mod.get('category', 'unknown')
                mod_by_category[category] = mod_by_category.get(category, 0) + 1
                
                # By parameter
                param = mod.get('parameter', 'unknown')
                mod_by_parameter[param] = mod_by_parameter.get(param, 0) + 1
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>IDF Modification Report - {self.job_id}</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    margin: 20px;
                    background-color: #f5f5f5;
                }}
                .container {{
                    max-width: 1200px;
                    margin: 0 auto;
                    background-color: white;
                    padding: 30px;
                    border-radius: 10px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                }}
                h1, h2, h3 {{
                    color: #333;
                }}
                .summary-grid {{
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                    gap: 20px;
                    margin: 20px 0;
                }}
                .stat-card {{
                    background-color: #f8f9fa;
                    padding: 20px;
                    border-radius: 8px;
                    border: 1px solid #e9ecef;
                    text-align: center;
                }}
                .stat-value {{
                    font-size: 2.5em;
                    font-weight: bold;
                    color: #28a745;
                    margin: 10px 0;
                }}
                .stat-label {{
                    color: #6c757d;
                    font-size: 0.9em;
                }}
                table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin: 20px 0;
                }}
                th, td {{
                    padding: 12px;
                    text-align: left;
                    border-bottom: 1px solid #e9ecef;
                }}
                th {{
                    background-color: #f8f9fa;
                    font-weight: bold;
                    color: #495057;
                }}
                tr:hover {{
                    background-color: #f8f9fa;
                }}
                .success {{
                    color: #28a745;
                }}
                .failed {{
                    color: #dc3545;
                }}
                .chart-container {{
                    margin: 30px 0;
                    padding: 20px;
                    background-color: #f8f9fa;
                    border-radius: 8px;
                }}
                .progress-bar {{
                    width: 100%;
                    height: 30px;
                    background-color: #e9ecef;
                    border-radius: 15px;
                    overflow: hidden;
                    margin: 10px 0;
                }}
                .progress-fill {{
                    height: 100%;
                    background-color: #28a745;
                    text-align: center;
                    line-height: 30px;
                    color: white;
                    font-weight: bold;
                }}
            </style>
            <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        </head>
        <body>
            <div class="container">
                <h1>IDF Modification Report</h1>
                <p><strong>Job ID:</strong> {self.job_id}</p>
                <p><strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                
                <h2>Summary Statistics</h2>
                <div class="summary-grid">
                    <div class="stat-card">
                        <div class="stat-label">Total Variants</div>
                        <div class="stat-value">{total_attempts}</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-label">Successful</div>
                        <div class="stat-value">{successful}</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-label">Total Modifications</div>
                        <div class="stat-value">{total_modifications}</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-label">Success Rate</div>
                        <div class="stat-value">{(successful/total_attempts*100):.1f}%</div>
                    </div>
                </div>
                
                <div class="progress-bar">
                    <div class="progress-fill" style="width: {(successful/total_attempts*100):.1f}%">
                        {successful}/{total_attempts}
                    </div>
                </div>
                
                <h2>Modifications by Category</h2>
                <div class="chart-container">
                    <canvas id="categoryChart" width="400" height="200"></canvas>
                </div>
                
                <table>
                    <tr>
                        <th>Category</th>
                        <th>Count</th>
                        <th>Percentage</th>
                    </tr>
        """
        
        for category, count in sorted(mod_by_category.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / total_modifications * 100) if total_modifications > 0 else 0
            html_content += f"""
                    <tr>
                        <td>{category}</td>
                        <td>{count}</td>
                        <td>{percentage:.1f}%</td>
                    </tr>
            """
        
        html_content += """
                </table>
                
                <h2>Modifications by Building</h2>
                <table>
                    <tr>
                        <th>Building ID</th>
                        <th>Modifications</th>
                        <th>Average per Variant</th>
                    </tr>
        """
        
        variants_per_building = len(results) // len(mod_by_building) if mod_by_building else 1
        for building_id, count in sorted(mod_by_building.items()):
            avg = count / variants_per_building
            html_content += f"""
                    <tr>
                        <td>{building_id}</td>
                        <td>{count}</td>
                        <td>{avg:.1f}</td>
                    </tr>
            """
        
        html_content += """
                </table>
                
                <h2>Top Modified Parameters</h2>
                <table>
                    <tr>
                        <th>Parameter</th>
                        <th>Times Modified</th>
                    </tr>
        """
        
        # Show top 10 parameters
        for param, count in sorted(mod_by_parameter.items(), key=lambda x: x[1], reverse=True)[:10]:
            html_content += f"""
                    <tr>
                        <td>{param}</td>
                        <td>{count}</td>
                    </tr>
            """
        
        html_content += """
                </table>
            </div>
            
            <script>
                // Category chart
                const ctx = document.getElementById('categoryChart').getContext('2d');
                const categoryChart = new Chart(ctx, {
                    type: 'doughnut',
                    data: {
                        labels: [""" + ', '.join([f'"{cat}"' for cat in mod_by_category.keys()]) + """],
                        datasets: [{
                            data: [""" + ', '.join([str(count) for count in mod_by_category.values()]) + """],
                            backgroundColor: [
                                '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', 
                                '#9966FF', '#FF9F40', '#FF6384', '#C9CBCF',
                                '#4BC0C0', '#FF9F40', '#FF6384', '#36A2EB'
                            ]
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: {
                                position: 'right'
                            }
                        }
                    }
                });
            </script>
        </body>
        </html>
        """
        
        with open(report_path, 'w') as f:
            f.write(html_content)
        
        logger.info(f"HTML report saved to: {report_path}")
        return report_path
    
    def generate_csv_report(self, results):
        """Generate CSV reports for easy analysis in Excel"""
        logger.info("Generating CSV reports...")
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # 1. Modifications detail CSV
        modifications_data = []
        for result in results:
            for mod in result['modifications']:
                modifications_data.append({
                    'timestamp': timestamp,
                    'building_id': result.get('building_id', 'unknown'),
                    'variant_id': result.get('variant_id', 'unknown'),
                    'category': mod.get('category', 'unknown'),
                    'object_type': mod.get('object_type', 'unknown'),
                    'object_name': mod.get('object_name', 'unknown'),
                    'parameter': mod.get('parameter', 'unknown'),
                    'original_value': mod.get('original_value', ''),
                    'new_value': mod.get('new_value', ''),
                    'change_type': mod.get('change_type', 'unknown'),
                    'rule_applied': mod.get('rule_applied', ''),
                    'success': result.get('success', False)
                })
        
        if modifications_data:
            mods_df = pd.DataFrame(modifications_data)
            mods_path = self.modified_idfs_dir / f"modifications_detail_{timestamp}.csv"
            mods_df.to_csv(mods_path, index=False)
            logger.info(f"Modifications detail CSV saved to: {mods_path}")
        
        # 2. Summary statistics CSV
        summary_data = []
        for result in results:
            summary_data.append({
                'building_id': result.get('building_id', 'unknown'),
                'variant_id': result.get('variant_id', 'unknown'),
                'success': result.get('success', False),
                'total_modifications': len(result['modifications']),
                'output_file': result.get('output_file', ''),
                'errors': '; '.join(result.get('errors', []))
            })
        
        if summary_data:
            summary_df = pd.DataFrame(summary_data)
            summary_path = self.modified_idfs_dir / f"modifications_summary_{timestamp}.csv"
            summary_df.to_csv(summary_path, index=False)
            logger.info(f"Summary CSV saved to: {summary_path}")
        
        # 3. Parameter changes matrix (buildings x parameters)
        param_matrix = {}
        for result in results:
            building_variant = f"{result.get('building_id', 'unknown')}_{result.get('variant_id', 'unknown')}"
            param_matrix[building_variant] = {}
            
            for mod in result['modifications']:
                param_key = f"{mod.get('category', 'unknown')}.{mod.get('parameter', 'unknown')}"
                param_matrix[building_variant][param_key] = mod.get('new_value', '')
        
        if param_matrix:
            matrix_df = pd.DataFrame.from_dict(param_matrix, orient='index')
            matrix_df.index.name = 'building_variant'
            matrix_path = self.modified_idfs_dir / f"parameter_matrix_{timestamp}.csv"
            matrix_df.to_csv(matrix_path)
            logger.info(f"Parameter matrix CSV saved to: {matrix_path}")
    
    def generate_markdown_report(self, results):
        """Generate a markdown report for documentation"""
        logger.info("Generating Markdown report...")
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_path = self.modified_idfs_dir / f"modification_report_{timestamp}.md"
        
        # Calculate statistics
        total_attempts = len(results)
        successful = sum(1 for r in results if r['success'])
        total_modifications = sum(len(r['modifications']) for r in results)
        
        # Count by category
        mod_by_category = {}
        for result in results:
            for mod in result['modifications']:
                category = mod.get('category', 'unknown')
                mod_by_category[category] = mod_by_category.get(category, 0) + 1
        
        content = f"""# IDF Modification Report

**Job ID:** {self.job_id}  
**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Summary

| Metric | Value |
|--------|-------|
| Total Variants | {total_attempts} |
| Successful | {successful} |
| Failed | {total_attempts - successful} |
| Total Modifications | {total_modifications} |
| Success Rate | {(successful/total_attempts*100):.1f}% |

## Modifications by Category

| Category | Count | Percentage |
|----------|-------|------------|
"""
        
        for category, count in sorted(mod_by_category.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / total_modifications * 100) if total_modifications > 0 else 0
            content += f"| {category} | {count} | {percentage:.1f}% |\n"
        
        content += """
## Configuration Used

```json
"""
        content += json.dumps(self.modification_cfg, indent=2)
        content += """
```

## Detailed Results

"""
        
        # Group results by building
        by_building = {}
        for result in results:
            building_id = result.get('building_id', 'unknown')
            if building_id not in by_building:
                by_building[building_id] = []
            by_building[building_id].append(result)
        
        for building_id, building_results in by_building.items():
            content += f"### Building {building_id}\n\n"
            
            for result in building_results:
                variant_id = result.get('variant_id', 'unknown')
                status = "✅ Success" if result['success'] else "❌ Failed"
                
                content += f"#### Variant: {variant_id} {status}\n\n"
                
                if result['success']:
                    content += f"- **Output File:** `{result.get('output_file', 'N/A')}`\n"
                    content += f"- **Modifications Applied:** {len(result['modifications'])}\n\n"
                    
                    if result['modifications']:
                        content += "| Parameter | Original | New | Change Type |\n"
                        content += "|-----------|----------|-----|-------------|\n"
                        
                        # Show first 5 modifications
                        for mod in result['modifications'][:5]:
                            content += f"| {mod.get('parameter', 'N/A')} | "
                            content += f"{mod.get('original_value', 'N/A')} | "
                            content += f"{mod.get('new_value', 'N/A')} | "
                            content += f"{mod.get('change_type', 'N/A')} |\n"
                        
                        if len(result['modifications']) > 5:
                            content += f"\n*... and {len(result['modifications']) - 5} more modifications*\n"
                else:
                    content += f"- **Errors:** {', '.join(result.get('errors', ['Unknown error']))}\n"
                
                content += "\n"
        
        content += """
## Notes

This report was generated automatically by the IDF Modification System. 
For more detailed analysis, please refer to the JSON and CSV reports.
"""
        
        with open(report_path, 'w') as f:
            f.write(content)
        
        logger.info(f"Markdown report saved to: {report_path}")
        return report_path
    
    def generate_parquet_report(self, results):
        """Generate Parquet reports for efficient data analysis"""
        logger.info("Generating Parquet reports...")
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        try:
            # 1. Collect all modifications with full context
            all_modifications = []
            for result in results:
                building_id = result.get('building_id', 'unknown')
                variant_id = result.get('variant_id', 'unknown')
                success = result.get('success', False)
                
                for mod in result.get('modifications', []):
                    # Ensure all context is included
                    mod_with_context = mod.copy()
                    mod_with_context['building_id'] = building_id
                    mod_with_context['variant_id'] = variant_id
                    mod_with_context['result_success'] = success
                    mod_with_context['timestamp'] = result.get('timestamp', datetime.now().isoformat())
                    
                    all_modifications.append(mod_with_context)
            
            # 2. Generate detailed modifications Parquet
            mods_parquet_path = self.modified_idfs_dir / f"modifications_detail_{timestamp}.parquet"
            
            # Prepare DataFrame with all modification details
            mod_records = []
            for mod in all_modifications:
                record = {
                    'timestamp': mod.get('timestamp', datetime.now().isoformat()),
                    'building_id': mod.get('building_id', ''),
                    'variant_id': mod.get('variant_id', ''),
                    'category': mod.get('category', ''),
                    'object_type': mod.get('object_type', ''),
                    'object_name': mod.get('object_name', ''),
                    'parameter': mod.get('parameter', ''),
                    'original_value': str(mod.get('original_value', '')),
                    'new_value': str(mod.get('new_value', '')),
                    'original_value_numeric': None,
                    'new_value_numeric': None,
                    'change_percentage': None,
                    'change_type': mod.get('change_type', 'unknown'),
                    'rule_applied': mod.get('rule_applied', ''),
                    'validation_status': mod.get('validation_status', 'unknown'),
                    'success': mod.get('result_success', True),
                    'message': mod.get('message', '')
                }
                
                # Try to extract numeric values
                try:
                    record['original_value_numeric'] = float(mod.get('original_value', 0))
                    record['new_value_numeric'] = float(mod.get('new_value', 0))
                    if record['original_value_numeric'] != 0:
                        record['change_percentage'] = ((record['new_value_numeric'] - record['original_value_numeric']) / 
                                                    record['original_value_numeric']) * 100
                except (ValueError, TypeError):
                    pass
                
                mod_records.append(record)
            
            if mod_records:
                # Create DataFrame
                mods_df = pd.DataFrame(mod_records)
                
                # Optimize data types for Parquet
                for col in ['category', 'object_type', 'change_type', 'validation_status']:
                    if col in mods_df.columns:
                        mods_df[col] = mods_df[col].astype('category')
                
                # Write to Parquet
                mods_df.to_parquet(mods_parquet_path, engine='pyarrow', compression='snappy', index=False)
                logger.info(f"Modifications Parquet saved to: {mods_parquet_path}")
                logger.info(f"File size: {mods_parquet_path.stat().st_size / 1024:.1f} KB")
            
            # 3. Generate summary statistics Parquet
            summary_parquet_path = self.modified_idfs_dir / f"modifications_summary_{timestamp}.parquet"
            
            # Create various aggregations
            summary_records = []
            
            # Building-level summary
            building_summaries = {}
            for result in results:
                building_id = result.get('building_id', 'unknown')
                if building_id not in building_summaries:
                    building_summaries[building_id] = {
                        'total_variants': 0,
                        'successful_variants': 0,
                        'total_modifications': 0,
                        'categories_modified': set(),
                        'parameters_modified': set()
                    }
                
                building_summaries[building_id]['total_variants'] += 1
                if result.get('success', False):
                    building_summaries[building_id]['successful_variants'] += 1
                
                building_summaries[building_id]['total_modifications'] += len(result.get('modifications', []))
                
                for mod in result.get('modifications', []):
                    building_summaries[building_id]['categories_modified'].add(mod.get('category', 'unknown'))
                    building_summaries[building_id]['parameters_modified'].add(mod.get('parameter', 'unknown'))
            
            # Convert to records
            for building_id, stats in building_summaries.items():
                summary_records.append({
                    'summary_type': 'building',
                    'entity_id': building_id,
                    'total_variants': stats['total_variants'],
                    'successful_variants': stats['successful_variants'],
                    'success_rate': stats['successful_variants'] / stats['total_variants'] * 100 if stats['total_variants'] > 0 else 0,
                    'total_modifications': stats['total_modifications'],
                    'avg_modifications_per_variant': stats['total_modifications'] / stats['total_variants'] if stats['total_variants'] > 0 else 0,
                    'unique_categories': len(stats['categories_modified']),
                    'unique_parameters': len(stats['parameters_modified'])
                })
            
            # Category-level summary
            category_stats = {}
            for mod in all_modifications:
                category = mod.get('category', 'unknown')
                if category not in category_stats:
                    category_stats[category] = {
                        'count': 0,
                        'buildings': set(),
                        'parameters': set(),
                        'numeric_changes': []
                    }
                
                category_stats[category]['count'] += 1
                category_stats[category]['buildings'].add(mod.get('building_id', 'unknown'))
                category_stats[category]['parameters'].add(mod.get('parameter', 'unknown'))
                
                # Track numeric changes
                try:
                    old_val = float(mod.get('original_value', 0))
                    new_val = float(mod.get('new_value', 0))
                    if old_val != 0:
                        pct_change = ((new_val - old_val) / old_val) * 100
                        category_stats[category]['numeric_changes'].append(pct_change)
                except:
                    pass
            
            # Convert category stats to records
            for category, stats in category_stats.items():
                numeric_changes = stats['numeric_changes']
                summary_records.append({
                    'summary_type': 'category',
                    'entity_id': category,
                    'total_variants': len(results),
                    'successful_variants': sum(1 for r in results if r.get('success', False)),
                    'success_rate': 100.0,  # Categories don't fail
                    'total_modifications': stats['count'],
                    'avg_modifications_per_variant': stats['count'] / len(results) if results else 0,
                    'unique_categories': 1,
                    'unique_parameters': len(stats['parameters']),
                    'unique_buildings': len(stats['buildings']),
                    'avg_change_percentage': sum(numeric_changes) / len(numeric_changes) if numeric_changes else None,
                    'min_change_percentage': min(numeric_changes) if numeric_changes else None,
                    'max_change_percentage': max(numeric_changes) if numeric_changes else None
                })
            
            # Overall summary
            all_numeric_changes = []
            for mod in all_modifications:
                try:
                    old_val = float(mod.get('original_value', 0))
                    new_val = float(mod.get('new_value', 0))
                    if old_val != 0:
                        pct_change = ((new_val - old_val) / old_val) * 100
                        all_numeric_changes.append(pct_change)
                except:
                    pass
            
            summary_records.append({
                'summary_type': 'overall',
                'entity_id': 'all',
                'total_variants': len(results),
                'successful_variants': sum(1 for r in results if r.get('success', False)),
                'success_rate': sum(1 for r in results if r.get('success', False)) / len(results) * 100 if results else 0,
                'total_modifications': len(all_modifications),
                'avg_modifications_per_variant': len(all_modifications) / len(results) if results else 0,
                'unique_categories': len(category_stats),
                'unique_parameters': len(set(m.get('parameter', 'unknown') for m in all_modifications)),
                'unique_buildings': len(building_summaries),
                'avg_change_percentage': sum(all_numeric_changes) / len(all_numeric_changes) if all_numeric_changes else None,
                'min_change_percentage': min(all_numeric_changes) if all_numeric_changes else None,
                'max_change_percentage': max(all_numeric_changes) if all_numeric_changes else None
            })
            
            if summary_records:
                summary_df = pd.DataFrame(summary_records)
                summary_df.to_parquet(summary_parquet_path, engine='pyarrow', compression='snappy', index=False)
                logger.info(f"Summary Parquet saved to: {summary_parquet_path}")
            
            # 4. Generate parameter matrix Parquet (buildings × parameters)
            matrix_parquet_path = self.modified_idfs_dir / f"parameter_matrix_{timestamp}.parquet"
            
            # Create a pivot table of modifications
            if mod_records:
                # Create a simplified DataFrame for the matrix
                matrix_data = []
                for mod in all_modifications:
                    matrix_data.append({
                        'building_variant': f"{mod.get('building_id', 'unknown')}_{mod.get('variant_id', 'unknown')}",
                        'parameter_key': f"{mod.get('category', 'unknown')}.{mod.get('parameter', 'unknown')}",
                        'new_value': mod.get('new_value', ''),
                        'new_value_numeric': None
                    })
                    
                    # Try to get numeric value
                    try:
                        matrix_data[-1]['new_value_numeric'] = float(mod.get('new_value', 0))
                    except:
                        pass
                
                matrix_df = pd.DataFrame(matrix_data)
                
                # Create pivot table
                if not matrix_df.empty:
                    # Pivot on numeric values where available
                    pivot_numeric = matrix_df.pivot_table(
                        index='building_variant',
                        columns='parameter_key',
                        values='new_value_numeric',
                        aggfunc='first'
                    )
                    
                    # Save to Parquet
                    pivot_numeric.to_parquet(matrix_parquet_path, engine='pyarrow', compression='snappy')
                    logger.info(f"Parameter matrix Parquet saved to: {matrix_parquet_path}")
            
            # 5. Create a comprehensive database directory
            db_dir = self.modified_idfs_dir / 'parquet_database'
            db_dir.mkdir(exist_ok=True)
            
            # Copy all parquet files to the database directory
            for parquet_file in [mods_parquet_path, summary_parquet_path, matrix_parquet_path]:
                if parquet_file.exists():
                    shutil.copy2(parquet_file, db_dir / parquet_file.name)
            
            # Create an index file for the database
            index_data = {
                'database_version': '1.0',
                'creation_timestamp': datetime.now().isoformat(),
                'job_id': self.job_id,
                'total_modifications': len(all_modifications),
                'total_variants': len(results),
                'files': {
                    'modifications_detail': f"modifications_detail_{timestamp}.parquet",
                    'summary_statistics': f"modifications_summary_{timestamp}.parquet",
                    'parameter_matrix': f"parameter_matrix_{timestamp}.parquet"
                },
                'statistics': {
                    'total_buildings': len(building_summaries),
                    'total_categories': len(category_stats),
                    'total_parameters': len(set(m.get('parameter', 'unknown') for m in all_modifications)),
                    'success_rate': sum(1 for r in results if r.get('success', False)) / len(results) * 100 if results else 0
                }
            }
            
            with open(db_dir / 'index.json', 'w') as f:
                json.dump(index_data, f, indent=2)
            
            logger.info(f"Parquet database created in: {db_dir}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to generate Parquet reports: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def test_single_building(self, building_id: str = None):
        """Test modification on a single building"""
        logger.info("Running single building test...")
        
        building_info = self.get_available_idfs()
        
        if building_id:
            # Find specific building
            target = None
            for info in building_info:
                if info['building_id'] == str(building_id):
                    target = info
                    break
            
            if not target:
                logger.error(f"Building {building_id} not found!")
                return
        else:
            # Use first available building
            if building_info:
                target = building_info[0]
            else:
                logger.error("No buildings available!")
                return
        
        logger.info(f"Testing on building: {target['building_id']}")
        
        # Temporarily modify config to process only this building
        original_selection = self.modification_cfg.get('base_idf_selection', {}).copy()
        
        self.modification_cfg['base_idf_selection'] = {
            'method': 'specific',
            'building_ids': [target['building_id']]
        }
        
        # Run modifications
        results = self.run_modifications()
        
        # Restore original config
        self.modification_cfg['base_idf_selection'] = original_selection
        
        return results


def main():
    """Main function for standalone execution"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Run IDF modifications independently',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run with default settings
  python standalone_modification_runner.py 650e5027-2c43-4a30-b588-5e4d72c0ac23
  
  # Run with custom config and all reports
  python standalone_modification_runner.py 650e5027 --config my_config.json --reports all
  
  # Test on specific building with debug output
  python standalone_modification_runner.py 650e5027 --test-building 4136733 --debug
  
  # Generate specific report types
  python standalone_modification_runner.py 650e5027 --reports json,html,parquet
        """
    )
    
    parser.add_argument('job_id', help='Job ID from previous run')
    parser.add_argument('--config', help='Path to configuration file')
    parser.add_argument('--output-dir', help='Base output directory')
    parser.add_argument('--test-building', help='Test on specific building ID')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    parser.add_argument('--reports', 
                       help='Report formats to generate (comma-separated: json,html,csv,markdown,parquet,all)',
                       default=None)
    
    args = parser.parse_args()
    
    # Set logging level
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        # Initialize runner
        runner = StandaloneModificationRunner(
            job_id=args.job_id,
            base_output_dir=args.output_dir
        )
        
        # Load configuration
        runner.load_configuration(args.config)
        
        # Override report formats if specified via command line
        if args.reports:
            if args.reports == 'all':
                report_formats = ['json', 'html', 'csv', 'markdown', 'parquet']
            else:
                report_formats = [fmt.strip() for fmt in args.reports.split(',')]
            
            runner.modification_cfg.setdefault('output_options', {})['report_formats'] = report_formats
        
        # Run modifications
        if args.test_building:
            runner.test_single_building(args.test_building)
        else:
            runner.run_modifications()
        
        logger.info("\nModification process completed!")
        
    except Exception as e:
        logger.error(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    # For direct testing without command line args
    # You can modify these values for quick testing
    TEST_JOB_ID = "650e5027-2c43-4a30-b588-5e4d72c0ac23"
    TEST_OUTPUT_DIR = r"D:\Documents\daily\E_Plus_2040_py\output"
    
    # Check if running with command line args
    if len(sys.argv) > 1:
        main()
    else:
        # Direct execution for testing
        logger.info("Running in test mode...")
        
        runner = StandaloneModificationRunner(
            job_id=TEST_JOB_ID,
            base_output_dir=TEST_OUTPUT_DIR
        )
        
        # Load configuration
        runner.load_configuration()
        
        # Override to generate all reports for testing
        runner.modification_cfg.setdefault('output_options', {})['report_formats'] = ['json', 'html', 'csv', 'markdown', 'parquet']
        
        # Test on a single building first
        # runner.test_single_building("4136733")
        
        # Or run full modifications
        runner.run_modifications()