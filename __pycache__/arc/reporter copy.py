"""
c_sensitivity/reporter.py

Enhanced sensitivity analysis reporter (renamed from sensitivity_reporter.py)
"""

import pandas as pd
import numpy as np
from pathlib import Path
import logging
from typing import Dict, List, Optional, Any, Union
import json
from datetime import datetime

# Try to import visualization libraries
try:
    import matplotlib.pyplot as plt
    import seaborn as sns
    HAVE_MATPLOTLIB = True
except ImportError:
    HAVE_MATPLOTLIB = False

try:
    import plotly.graph_objects as go
    import plotly.express as px
    from plotly.subplots import make_subplots
    HAVE_PLOTLY = True
except ImportError:
    HAVE_PLOTLY = False


class SensitivityReporter:
    """
    Generate reports and visualizations for sensitivity analysis results
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        
        # Check available visualization libraries
        if not HAVE_MATPLOTLIB and not HAVE_PLOTLY:
            self.logger.warning("No visualization libraries available. Install matplotlib or plotly for plots.")
    
    def _format_parameter_name(self, param_name: str, max_length: int = 50) -> str:
        """Format long parameter names for display"""
        if '*' in param_name:
            parts = param_name.split('*')
            if len(parts) >= 4:
                # Show category, object_name, and field_name
                formatted = f"{parts[0]}.{parts[2]}.{parts[3]}"
                if len(formatted) > max_length:
                    # Truncate object_name if needed
                    object_name = parts[2]
                    if len(object_name) > 20:
                        object_name = object_name[:17] + "..."
                    formatted = f"{parts[0]}.{object_name}.{parts[3]}"
                return formatted
        return param_name if len(param_name) <= max_length else param_name[:max_length-3] + "..."


    def generate_html_report(self,
                           results: Dict[str, Any],
                           output_path: Union[str, Path],
                           include_plots: bool = True) -> Path:
        """
        Generate comprehensive HTML report
        
        Args:
            results: Dictionary containing sensitivity analysis results
            output_path: Path to save HTML report
            include_plots: Whether to embed plots in the report
            
        Returns:
            Path to generated HTML report
        """
        output_path = Path(output_path)
        
        html_content = self._create_html_header()
        
        # Add summary section
        html_content += self._create_summary_section(results)
        
        # Add detailed results sections
        if 'traditional' in results:
            html_content += self._create_traditional_section(results['traditional'])
        
        if 'modification' in results:
            html_content += self._create_modification_section(results['modification'])
        
        if 'hybrid' in results:
            html_content += self._create_hybrid_section(results['hybrid'])
        
        # Add visualizations if requested
        if include_plots and (HAVE_PLOTLY or HAVE_MATPLOTLIB):
            html_content += self._create_visualization_section(results)
        
        html_content += self._create_html_footer()
        
        # Save report
        with open(output_path, 'w') as f:
            f.write(html_content)
        
        self.logger.info(f"Generated HTML report: {output_path}")
        return output_path
    
    def _create_html_header(self) -> str:
        """Create HTML header with styling"""
        return """
<!DOCTYPE html>
<html>
<head>
    <title>Sensitivity Analysis Report</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background-color: white;
            padding: 20px;
            box-shadow: 0 0 10px rgba(0,0,0,0.1);
        }
        h1, h2, h3 {
            color: #333;
        }
        table {
            border-collapse: collapse;
            width: 100%;
            margin: 20px 0;
        }
        th, td {
            border: 1px solid #ddd;
            padding: 8px;
            text-align: left;
        }
        th {
            background-color: #4CAF50;
            color: white;
        }
        tr:nth-child(even) {
            background-color: #f2f2f2;
        }
        .metric {
            display: inline-block;
            margin: 10px;
            padding: 10px;
            background-color: #e3f2fd;
            border-radius: 5px;
        }
        .section {
            margin: 30px 0;
            padding: 20px;
            border-left: 4px solid #4CAF50;
            background-color: #fafafa;
        }
        .plot-container {
            margin: 20px 0;
            text-align: center;
        }
    </style>
</head>
<body>
<div class="container">
<h1>Sensitivity Analysis Report</h1>
<p>Generated on: """ + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "</p>"
    
    def _create_html_footer(self) -> str:
        """Create HTML footer"""
        return """
</div>
</body>
</html>
"""
    
    def _create_summary_section(self, results: Dict[str, Any]) -> str:
        """Create summary section of the report"""
        html = '<div class="section">\n<h2>Executive Summary</h2>\n'
        
        # Extract key metrics
        if 'metadata' in results:
            meta = results['metadata']
            html += f'<div class="metric"><strong>Analysis Type:</strong> {meta.get("analysis_type", "Unknown")}</div>\n'
            html += f'<div class="metric"><strong>Parameters Analyzed:</strong> {meta.get("n_parameters", 0)}</div>\n'
            html += f'<div class="metric"><strong>Outputs Analyzed:</strong> {meta.get("n_outputs", 0)}</div>\n'
        
        # Top parameters summary
        if 'summary' in results and 'top_parameters' in results['summary']:
            html += '<h3>Top Sensitive Parameters</h3>\n'
            html += '<table>\n<tr><th>Rank</th><th>Parameter</th><th>Sensitivity Score</th></tr>\n'
            
            for i, param in enumerate(results['summary']['top_parameters'][:10], 1):
                param_name = param.get("parameter", "")
                formatted_name = self._format_parameter_name(param_name)
                html += f'<tr><td>{i}</td><td title="{param_name}">{formatted_name}</td>'
                html += f'<td>{param.get("avg_sensitivity_score", 0):.4f}</td></tr>\n'
            
            html += '</table>\n'
        
        html += '</div>\n'
        return html
    
    def create_sensitivity_heatmap(self,
                                 sensitivity_df: pd.DataFrame,
                                 top_n_params: int = 20,
                                 save_path: Optional[str] = None) -> Optional[str]:
        """
        Create heatmap visualization of sensitivity scores
        
        Args:
            sensitivity_df: DataFrame with sensitivity results
            top_n_params: Number of top parameters to show
            save_path: Path to save plot
            
        Returns:
            Path to saved plot or None
        """
        if not HAVE_MATPLOTLIB:
            self.logger.warning("Matplotlib not available for heatmap generation")
            return None
        
        # Prepare data for heatmap
        if 'parameter' in sensitivity_df.columns and 'output_variable' in sensitivity_df.columns:
            # Pivot data
            heatmap_data = sensitivity_df.pivot_table(
                index='parameter',
                columns='output_variable',
                values='sensitivity_score',
                aggfunc='mean'
            )
            
            # Select top parameters
            top_params = sensitivity_df.groupby('parameter')['sensitivity_score'].mean().nlargest(top_n_params).index
            heatmap_data = heatmap_data.loc[top_params]
            
            # Create plot
            plt.figure(figsize=(12, 8))
            sns.heatmap(
                heatmap_data,
                cmap='YlOrRd',
                annot=True,
                fmt='.3f',
                cbar_kws={'label': 'Sensitivity Score'}
            )
            plt.title('Parameter Sensitivity Heatmap')
            plt.xlabel('Output Variables')
            plt.ylabel('Parameters')
            plt.xticks(rotation=45, ha='right')
            plt.yticks(rotation=0)
            plt.tight_layout()
            
            if save_path:
                plt.savefig(save_path, dpi=300, bbox_inches='tight')
                plt.close()
                return save_path
            else:
                plt.show()
        
        return None
    
    def create_level_comparison_plot(self,
                                   sensitivity_df: pd.DataFrame,
                                   save_path: Optional[str] = None) -> Optional[str]:
        """
        Create comparison plot for multi-level sensitivity analysis
        
        Args:
            sensitivity_df: DataFrame with level column
            save_path: Path to save plot
            
        Returns:
            Path to saved plot or None
        """
        if 'level' not in sensitivity_df.columns:
            return None
        
        if HAVE_PLOTLY:
            # Create interactive plot with plotly
            fig = px.box(
                sensitivity_df,
                x='level',
                y='sensitivity_score',
                color='category' if 'category' in sensitivity_df.columns else None,
                title='Sensitivity Distribution by Analysis Level',
                labels={
                    'sensitivity_score': 'Sensitivity Score',
                    'level': 'Analysis Level',
                    'category': 'Parameter Category'
                }
            )
            
            fig.update_layout(
                showlegend=True,
                height=600,
                template='plotly_white'
            )
            
            if save_path:
                fig.write_html(save_path)
                return save_path
            else:
                fig.show()
                
        elif HAVE_MATPLOTLIB:
            # Fallback to matplotlib
            fig, ax = plt.subplots(figsize=(10, 6))
            
            levels = sensitivity_df['level'].unique()
            data_by_level = [
                sensitivity_df[sensitivity_df['level'] == level]['sensitivity_score'].values 
                for level in levels
            ]
            
            bp = ax.boxplot(data_by_level, labels=levels, patch_artist=True)
            
            # Color boxes
            colors = plt.cm.Set3(np.linspace(0, 1, len(levels)))
            for patch, color in zip(bp['boxes'], colors):
                patch.set_facecolor(color)
            
            ax.set_xlabel('Analysis Level')
            ax.set_ylabel('Sensitivity Score')
            ax.set_title('Sensitivity Distribution by Analysis Level')
            ax.grid(True, alpha=0.3)
            
            plt.tight_layout()
            
            if save_path:
                plt.savefig(save_path, dpi=300, bbox_inches='tight')
                plt.close()
                return save_path
            else:
                plt.show()
        
        return None
    
    def create_parameter_ranking_plot(self,
                                    sensitivity_df: pd.DataFrame,
                                    top_n: int = 15,
                                    group_by: Optional[str] = None,
                                    save_path: Optional[str] = None) -> Optional[str]:
        """
        Create horizontal bar plot of parameter rankings
        
        Args:
            sensitivity_df: DataFrame with sensitivity results
            top_n: Number of top parameters to show
            group_by: Column to group by (e.g., 'category', 'level')
            save_path: Path to save plot
            
        Returns:
            Path to saved plot or None
        """
        if not HAVE_MATPLOTLIB:
            return None
        
        # Aggregate scores
        if group_by and group_by in sensitivity_df.columns:
            grouped = sensitivity_df.groupby(['parameter', group_by])['sensitivity_score'].mean().reset_index()
            top_params = grouped.groupby('parameter')['sensitivity_score'].sum().nlargest(top_n).index
            plot_data = grouped[grouped['parameter'].isin(top_params)]
            
            # Create grouped bar plot
            fig, ax = plt.subplots(figsize=(10, max(6, top_n * 0.5)))
            
            # Pivot for plotting
            pivot_data = plot_data.pivot(index='parameter', columns=group_by, values='sensitivity_score')
            pivot_data.plot(kind='barh', stacked=True, ax=ax)
            
            ax.set_xlabel('Sensitivity Score')
            ax.set_ylabel('Parameter')
            ax.set_title(f'Top {top_n} Parameters by Sensitivity (Grouped by {group_by})')
            ax.legend(title=group_by, bbox_to_anchor=(1.05, 1), loc='upper left')
            
        else:
            # Simple ranking
            top_params = sensitivity_df.groupby('parameter')['sensitivity_score'].mean().nlargest(top_n)
            
            fig, ax = plt.subplots(figsize=(10, max(6, top_n * 0.4)))
            
            positions = np.arange(len(top_params))
            ax.barh(positions, top_params.values)
            ax.set_yticks(positions)
            ax.set_yticklabels([self._format_parameter_name(p, max_length=40) for p in top_params.index])
            ax.set_xlabel('Sensitivity Score')
            ax.set_title(f'Top {top_n} Parameters by Sensitivity')
            ax.invert_yaxis()
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            plt.close()
            return save_path
        else:
            plt.show()
        
        return None
    
    def generate_latex_tables(self,
                            results: Dict[str, pd.DataFrame],
                            output_dir: Path,
                            table_format: str = 'latex') -> List[Path]:
        """
        Generate LaTeX tables for inclusion in reports
        
        Args:
            results: Dictionary of DataFrames to convert
            output_dir: Directory to save tables
            table_format: 'latex' or 'latex_booktabs'
            
        Returns:
            List of paths to generated tables
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(exist_ok=True)
        
        generated_files = []
        
        for name, df in results.items():
            if isinstance(df, pd.DataFrame) and not df.empty:
                # Select relevant columns and limit rows
                if 'sensitivity_score' in df.columns:
                    table_df = df.nlargest(20, 'sensitivity_score')[
                        ['parameter', 'output_variable', 'sensitivity_score', 'p_value']
                    ].round(4)
                else:
                    table_df = df.head(20)
                
                # Generate LaTeX
                latex_content = table_df.to_latex(
                    index=False,
                    caption=f"Sensitivity Analysis Results - {name}",
                    label=f"tab:sensitivity_{name}",
                    column_format='l' * len(table_df.columns),
                    escape=True
                )
                
                # Save to file
                file_path = output_dir / f"sensitivity_table_{name}.tex"
                with open(file_path, 'w') as f:
                    f.write(latex_content)
                
                generated_files.append(file_path)
                self.logger.info(f"Generated LaTeX table: {file_path}")
        
        return generated_files
    
    def create_interactive_dashboard(self,
                                   results: Dict[str, Any],
                                   output_path: Union[str, Path]) -> Optional[Path]:
        """
        Create interactive dashboard using Plotly
        
        Args:
            results: Complete sensitivity analysis results
            output_path: Path to save HTML dashboard
            
        Returns:
            Path to saved dashboard or None
        """
        if not HAVE_PLOTLY:
            self.logger.warning("Plotly not available for dashboard creation")
            return None
        
        # Implementation of interactive dashboard
        # This would create a comprehensive interactive visualization
        # For now, returning None as placeholder
        
        self.logger.info("Interactive dashboard generation not fully implemented yet")
        return None
