"""
sensitivity_reporter.py - Visualization and reporting for sensitivity analysis

Handles:
- Sensitivity visualizations (tornado, heatmaps, etc.)
- Building clustering based on sensitivity patterns
- Report generation
- Export formatting for downstream modules
"""

import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict, List, Optional, Tuple, Any, Union
import json
from datetime import datetime
from pathlib import Path

# Optional imports for advanced features
try:
    from sklearn.cluster import KMeans
    from sklearn.preprocessing import StandardScaler
    from sklearn.decomposition import PCA
    HAVE_SKLEARN = True
except ImportError:
    HAVE_SKLEARN = False
    print("[WARNING] scikit-learn not available. Clustering features disabled.")

try:
    import plotly.graph_objects as go
    import plotly.express as px
    from plotly.subplots import make_subplots
    HAVE_PLOTLY = True
except ImportError:
    HAVE_PLOTLY = False
    print("[INFO] Plotly not available. Using matplotlib only.")


class SensitivityReporter:
    """Generate reports and visualizations for sensitivity analysis"""
    
    def __init__(self, output_dir: str = "sensitivity_reports"):
        """
        Initialize reporter
        
        Args:
            output_dir: Directory for saving reports and plots
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # Set plotting style
        plt.style.use('seaborn-v0_8-darkgrid')
        sns.set_palette("husl")
    
    def generate_tornado_diagram(self,
                               sensitivity_df: pd.DataFrame,
                               parameter_col: str = "Parameter",
                               sensitivity_col: str = "AbsCorrelation",
                               top_n: int = 20,
                               title: str = "Parameter Sensitivity",
                               save_path: Optional[str] = None,
                               interactive: bool = True) -> Optional[str]:
        """
        Create tornado diagram showing parameter importance
        
        Args:
            sensitivity_df: DataFrame with sensitivity results
            parameter_col: Column name for parameters
            sensitivity_col: Column name for sensitivity values
            top_n: Number of top parameters to show
            title: Plot title
            save_path: Path to save plot
            interactive: Whether to create interactive plot (requires plotly)
            
        Returns:
            Path to saved plot or None
        """
        # Get top parameters
        if sensitivity_col not in sensitivity_df.columns:
            print(f"[WARNING] Column '{sensitivity_col}' not found")
            return None
            
        top_params = sensitivity_df.nlargest(top_n, sensitivity_col)
        
        if interactive and HAVE_PLOTLY:
            # Create interactive tornado diagram
            fig = go.Figure()
            
            fig.add_trace(go.Bar(
                x=top_params[sensitivity_col],
                y=top_params[parameter_col],
                orientation='h',
                marker=dict(
                    color=top_params[sensitivity_col],
                    colorscale='Viridis',
                    showscale=True,
                    colorbar=dict(title="Sensitivity")
                )
            ))
            
            fig.update_layout(
                title=title,
                xaxis_title="Sensitivity Score",
                yaxis_title="Parameter",
                height=max(400, top_n * 25),
                margin=dict(l=200)
            )
            
            if save_path:
                fig.write_html(save_path)
                fig.write_image(save_path.replace('.html', '.png'))
                return save_path
        else:
            # Create static tornado diagram
            plt.figure(figsize=(10, max(6, top_n * 0.3)))
            
            y_pos = np.arange(len(top_params))
            plt.barh(y_pos, top_params[sensitivity_col])
            plt.yticks(y_pos, top_params[parameter_col])
            plt.xlabel('Sensitivity Score')
            plt.title(title)
            plt.tight_layout()
            
            if save_path:
                plt.savefig(save_path, dpi=300, bbox_inches='tight')
                plt.close()
                return save_path
            else:
                plt.show()
        
        return None
    
    def generate_sensitivity_heatmap(self,
                                   building_results: Dict[str, pd.DataFrame],
                                   top_n_params: int = 15,
                                   save_path: Optional[str] = None) -> Optional[str]:
        """
        Create heatmap showing sensitivity across buildings/groups
        
        Args:
            building_results: Dict of building_group -> sensitivity_df
            top_n_params: Number of parameters to include
            save_path: Path to save plot
            
        Returns:
            Path to saved plot or None
        """
        # Collect all parameters and their sensitivities
        all_params = set()
        for df in building_results.values():
            if 'Parameter' in df.columns:
                all_params.update(df['Parameter'].tolist())
        
        # Create matrix
        matrix_data = []
        building_names = []
        
        for building, df in building_results.items():
            building_names.append(building)
            row_data = []
            
            for param in sorted(all_params):
                if 'Parameter' in df.columns and 'AbsCorrelation' in df.columns:
                    param_row = df[df['Parameter'] == param]
                    if not param_row.empty:
                        row_data.append(param_row.iloc[0]['AbsCorrelation'])
                    else:
                        row_data.append(0)
                else:
                    row_data.append(0)
            
            matrix_data.append(row_data)
        
        # Convert to DataFrame
        heatmap_df = pd.DataFrame(
            matrix_data,
            index=building_names,
            columns=sorted(all_params)
        )
        
        # Select top parameters by average sensitivity
        param_avg = heatmap_df.mean(axis=0).nlargest(top_n_params)
        heatmap_df = heatmap_df[param_avg.index]
        
        # Create heatmap
        plt.figure(figsize=(12, max(6, len(building_names) * 0.5)))
        
        sns.heatmap(
            heatmap_df,
            cmap='YlOrRd',
            annot=True,
            fmt='.2f',
            cbar_kws={'label': 'Sensitivity Score'},
            xticklabels=True,
            yticklabels=True
        )
        
        plt.title('Parameter Sensitivity Across Buildings/Groups')
        plt.xlabel('Parameters')
        plt.ylabel('Building/Group')
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            plt.close()
            return save_path
        else:
            plt.show()
        
        return None
    
    def generate_time_series_sensitivity(self,
                                       sensitivity_over_time: pd.DataFrame,
                                       top_n_params: int = 10,
                                       save_path: Optional[str] = None) -> Optional[str]:
        """
        Plot how sensitivity changes over time periods
        
        Args:
            sensitivity_over_time: DataFrame with time-based sensitivity
            top_n_params: Number of parameters to show
            save_path: Path to save plot
            
        Returns:
            Path to saved plot or None
        """
        if HAVE_PLOTLY:
            # Create interactive time series plot
            fig = go.Figure()
            
            # Add traces for top parameters
            for param in sensitivity_over_time.columns[:top_n_params]:
                fig.add_trace(go.Scatter(
                    x=sensitivity_over_time.index,
                    y=sensitivity_over_time[param],
                    mode='lines+markers',
                    name=param
                ))
            
            fig.update_layout(
                title='Parameter Sensitivity Over Time',
                xaxis_title='Time Period',
                yaxis_title='Sensitivity Score',
                hovermode='x unified'
            )
            
            if save_path:
                fig.write_html(save_path)
                return save_path
        else:
            # Static plot
            plt.figure(figsize=(12, 6))
            
            for param in sensitivity_over_time.columns[:top_n_params]:
                plt.plot(sensitivity_over_time.index, sensitivity_over_time[param], 
                        marker='o', label=param)
            
            plt.title('Parameter Sensitivity Over Time')
            plt.xlabel('Time Period')
            plt.ylabel('Sensitivity Score')
            plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
            plt.xticks(rotation=45)
            plt.tight_layout()
            
            if save_path:
                plt.savefig(save_path, dpi=300, bbox_inches='tight')
                plt.close()
                return save_path
            else:
                plt.show()
        
        return None
    
    def cluster_buildings_by_sensitivity(self,
                                       building_results: Dict[str, pd.DataFrame],
                                       n_clusters: int = 3,
                                       save_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Cluster buildings based on their sensitivity patterns
        
        Args:
            building_results: Dict of building -> sensitivity results
            n_clusters: Number of clusters
            save_path: Path to save visualization
            
        Returns:
            Dictionary with cluster assignments and visualization
        """
        if not HAVE_SKLEARN:
            print("[WARNING] scikit-learn required for clustering")
            return {}
        
        # Create feature matrix
        all_params = set()
        for df in building_results.values():
            if 'Parameter' in df.columns:
                all_params.update(df['Parameter'].tolist())
        
        feature_matrix = []
        building_names = []
        
        for building, df in building_results.items():
            building_names.append(building)
            features = []
            
            for param in sorted(all_params):
                if 'Parameter' in df.columns and 'AbsCorrelation' in df.columns:
                    param_row = df[df['Parameter'] == param]
                    if not param_row.empty:
                        features.append(param_row.iloc[0]['AbsCorrelation'])
                    else:
                        features.append(0)
                else:
                    features.append(0)
            
            feature_matrix.append(features)
        
        # Standardize features
        scaler = StandardScaler()
        features_scaled = scaler.fit_transform(feature_matrix)
        
        # Perform clustering
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        clusters = kmeans.fit_predict(features_scaled)
        
        # Reduce dimensions for visualization
        pca = PCA(n_components=2)
        features_2d = pca.fit_transform(features_scaled)
        
        # Create visualization
        plt.figure(figsize=(10, 8))
        
        scatter = plt.scatter(
            features_2d[:, 0],
            features_2d[:, 1],
            c=clusters,
            cmap='viridis',
            s=100,
            alpha=0.6
        )
        
        # Add building labels
        for i, building in enumerate(building_names):
            plt.annotate(
                building,
                (features_2d[i, 0], features_2d[i, 1]),
                xytext=(5, 5),
                textcoords='offset points',
                fontsize=8
            )
        
        plt.colorbar(scatter, label='Cluster')
        plt.xlabel(f'PC1 ({pca.explained_variance_ratio_[0]:.1%} variance)')
        plt.ylabel(f'PC2 ({pca.explained_variance_ratio_[1]:.1%} variance)')
        plt.title('Building Clusters Based on Sensitivity Patterns')
        plt.grid(True, alpha=0.3)
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            plt.close()
        else:
            plt.show()
        
        # Create cluster summary
        cluster_summary = {}
        for cluster_id in range(n_clusters):
            cluster_buildings = [building_names[i] for i, c in enumerate(clusters) if c == cluster_id]
            
            # Find characteristic parameters for this cluster
            cluster_features = [features_scaled[i] for i, c in enumerate(clusters) if c == cluster_id]
            if cluster_features:
                avg_features = np.mean(cluster_features, axis=0)
                top_param_indices = np.argsort(avg_features)[-5:][::-1]
                top_params = [sorted(all_params)[i] for i in top_param_indices]
                
                cluster_summary[f"cluster_{cluster_id}"] = {
                    'buildings': cluster_buildings,
                    'size': len(cluster_buildings),
                    'characteristic_parameters': top_params
                }
        
        return {
            'clusters': dict(zip(building_names, clusters)),
            'summary': cluster_summary,
            'explained_variance': pca.explained_variance_ratio_.tolist()
        }
    
    def generate_multi_objective_plot(self,
                                    multi_obj_results: pd.DataFrame,
                                    objectives: List[str],
                                    save_path: Optional[str] = None) -> Optional[str]:
        """
        Visualize multi-objective sensitivity results
        
        Args:
            multi_obj_results: DataFrame with multi-objective results
            objectives: List of objective names
            save_path: Path to save plot
            
        Returns:
            Path to saved plot or None
        """
        if len(objectives) < 2:
            print("[WARNING] Need at least 2 objectives for multi-objective plot")
            return None
        
        # Create scatter plot of correlations for different objectives
        if len(objectives) == 2:
            # 2D scatter plot
            corr_cols = [f"Corr_{obj}" for obj in objectives]
            
            if all(col in multi_obj_results.columns for col in corr_cols):
                plt.figure(figsize=(10, 8))
                
                # Color by conflict score if available
                if 'ConflictScore' in multi_obj_results.columns:
                    scatter = plt.scatter(
                        multi_obj_results[corr_cols[0]],
                        multi_obj_results[corr_cols[1]],
                        c=multi_obj_results['ConflictScore'],
                        cmap='coolwarm',
                        s=100,
                        alpha=0.6
                    )
                    plt.colorbar(scatter, label='Conflict Score')
                else:
                    plt.scatter(
                        multi_obj_results[corr_cols[0]],
                        multi_obj_results[corr_cols[1]],
                        s=100,
                        alpha=0.6
                    )
                
                # Add diagonal lines
                plt.axhline(y=0, color='k', linestyle='-', alpha=0.3)
                plt.axvline(x=0, color='k', linestyle='-', alpha=0.3)
                
                # Add quadrant labels
                plt.text(0.5, 0.5, 'Win-Win', transform=plt.gca().transAxes,
                        fontsize=12, alpha=0.5, ha='center')
                plt.text(0.05, 0.95, 'Trade-off', transform=plt.gca().transAxes,
                        fontsize=12, alpha=0.5)
                plt.text(0.95, 0.05, 'Trade-off', transform=plt.gca().transAxes,
                        fontsize=12, alpha=0.5)
                
                plt.xlabel(f'Correlation with {objectives[0]}')
                plt.ylabel(f'Correlation with {objectives[1]}')
                plt.title('Multi-Objective Parameter Sensitivity')
                plt.grid(True, alpha=0.3)
                
                # Add parameter labels for conflicting ones
                if 'IsConflicting' in multi_obj_results.columns and 'Parameter' in multi_obj_results.columns:
                    conflicting = multi_obj_results[multi_obj_results['IsConflicting']]
                    for _, row in conflicting.iterrows():
                        plt.annotate(
                            row['Parameter'],
                            (row[corr_cols[0]], row[corr_cols[1]]),
                            xytext=(5, 5),
                            textcoords='offset points',
                            fontsize=8,
                            alpha=0.7
                        )
                
                if save_path:
                    plt.savefig(save_path, dpi=300, bbox_inches='tight')
                    plt.close()
                    return save_path
                else:
                    plt.show()
        
        elif len(objectives) >= 3 and HAVE_PLOTLY:
            # 3D scatter plot for 3+ objectives
            corr_cols = [f"Corr_{obj}" for obj in objectives[:3]]
            
            if all(col in multi_obj_results.columns for col in corr_cols):
                fig = go.Figure(data=[go.Scatter3d(
                    x=multi_obj_results[corr_cols[0]],
                    y=multi_obj_results[corr_cols[1]],
                    z=multi_obj_results[corr_cols[2]],
                    mode='markers',
                    marker=dict(
                        size=8,
                        color=multi_obj_results['ConflictScore'] if 'ConflictScore' in multi_obj_results.columns else 'blue',
                        colorscale='Viridis',
                        showscale=True
                    ),
                    text=multi_obj_results['Parameter'] if 'Parameter' in multi_obj_results.columns else None,
                    hovertemplate='<b>%{text}</b><br>' +
                                  f'{objectives[0]}: %{{x:.3f}}<br>' +
                                  f'{objectives[1]}: %{{y:.3f}}<br>' +
                                  f'{objectives[2]}: %{{z:.3f}}<br>' +
                                  '<extra></extra>'
                )])
                
                fig.update_layout(
                    title='Multi-Objective Parameter Sensitivity (3D)',
                    scene=dict(
                        xaxis_title=f'Correlation with {objectives[0]}',
                        yaxis_title=f'Correlation with {objectives[1]}',
                        zaxis_title=f'Correlation with {objectives[2]}'
                    )
                )
                
                if save_path:
                    fig.write_html(save_path)
                    return save_path
        
        return None
    
    def generate_comprehensive_report(self,
                                    results: Dict[str, Any],
                                    metadata: Dict[str, Any],
                                    output_path: str = "sensitivity_report.html") -> str:
        """
        Generate comprehensive HTML report with all visualizations
        
        Args:
            results: Dictionary containing all analysis results
            metadata: Analysis metadata
            output_path: Path for HTML report
            
        Returns:
            Path to generated report
        """
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Sensitivity Analysis Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h1, h2, h3 {{ color: #333; }}
                .summary-box {{ 
                    background: #f0f0f0; 
                    padding: 15px; 
                    margin: 10px 0;
                    border-radius: 5px;
                }}
                .plot-container {{ 
                    margin: 20px 0; 
                    text-align: center;
                }}
                table {{
                    border-collapse: collapse;
                    width: 100%;
                    margin: 10px 0;
                }}
                th, td {{
                    border: 1px solid #ddd;
                    padding: 8px;
                    text-align: left;
                }}
                th {{
                    background-color: #4CAF50;
                    color: white;
                }}
                tr:nth-child(even) {{
                    background-color: #f2f2f2;
                }}
            </style>
        </head>
        <body>
            <h1>Sensitivity Analysis Report</h1>
            <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            
            <div class="summary-box">
                <h2>Analysis Summary</h2>
                <ul>
                    <li>Number of scenarios: {metadata.get('num_scenarios', 'N/A')}</li>
                    <li>Number of parameters: {metadata.get('num_parameters', 'N/A')}</li>
                    <li>Number of buildings: {metadata.get('num_buildings', 'N/A')}</li>
                    <li>Target variables: {', '.join(metadata.get('target_variables', []))}</li>
                </ul>
            </div>
        """
        
        # Add key findings
        if 'key_findings' in metadata:
            html_content += """
            <div class="summary-box">
                <h2>Key Findings</h2>
            """
            
            if 'top_5_parameters' in metadata['key_findings']:
                html_content += f"""
                <h3>Top 5 Most Sensitive Parameters</h3>
                <ol>
                """
                for param in metadata['key_findings']['top_5_parameters']:
                    html_content += f"<li>{param}</li>"
                html_content += "</ol>"
            
            if 'conflicting_parameters' in metadata['key_findings']:
                html_content += f"""
                <h3>Parameters with Conflicting Effects</h3>
                <ul>
                """
                for param in metadata['key_findings']['conflicting_parameters']:
                    html_content += f"<li>{param}</li>"
                html_content += "</ul>"
            
            html_content += "</div>"
        
        # Add parameter statistics table
        if 'parameter_stats' in metadata:
            html_content += """
            <h2>Parameter Statistics</h2>
            <table>
                <tr>
                    <th>Parameter</th>
                    <th>Min</th>
                    <th>Max</th>
                    <th>Mean</th>
                    <th>Std Dev</th>
                    <th>CV</th>
                </tr>
            """
            
            for param, stats in metadata['parameter_stats'].items():
                html_content += f"""
                <tr>
                    <td>{param}</td>
                    <td>{stats.get('min', 'N/A'):.3f}</td>
                    <td>{stats.get('max', 'N/A'):.3f}</td>
                    <td>{stats.get('mean', 'N/A'):.3f}</td>
                    <td>{stats.get('std', 'N/A'):.3f}</td>
                    <td>{stats.get('cv', 'N/A'):.3f}</td>
                </tr>
                """
            
            html_content += "</table>"
        
        # Add recommendations
        html_content += """
        <h2>Recommendations</h2>
        <div class="summary-box">
            <h3>For Calibration</h3>
            <p>Focus on the top sensitive parameters identified above. These have the most impact on simulation outputs.</p>
            
            <h3>For Surrogate Modeling</h3>
            <p>Include at least the top 10-15 parameters to capture most of the model behavior.</p>
            
            <h3>For Building Modifications</h3>
            <p>Parameters showing high sensitivity in failed validation buildings should be prioritized for adjustment.</p>
        </div>
        
        </body>
        </html>
        """
        
        # Save report
        output_path = Path(self.output_dir) / output_path
        with open(output_path, 'w') as f:
            f.write(html_content)
        
        print(f"[INFO] Comprehensive report saved to: {output_path}")
        return str(output_path)
    
    def create_dashboard(self,
                        results: Dict[str, Any],
                        port: int = 8050) -> None:
        """
        Create interactive dashboard (requires dash)
        
        Args:
            results: Analysis results
            port: Port for dashboard
        """
        try:
            import dash
            from dash import dcc, html
            import plotly.express as px
            
            # Create dash app
            app = dash.Dash(__name__)
            
            # Define layout
            app.layout = html.Div([
                html.H1('Sensitivity Analysis Dashboard'),
                
                dcc.Tabs([
                    dcc.Tab(label='Overview', children=[
                        # Add overview content
                        html.Div([
                            html.H3('Analysis Summary'),
                            # Add summary content
                        ])
                    ]),
                    
                    dcc.Tab(label='Parameter Rankings', children=[
                        # Add parameter ranking visualizations
                        dcc.Graph(id='tornado-diagram')
                    ]),
                    
                    dcc.Tab(label='Building Analysis', children=[
                        # Add building-specific content
                        dcc.Graph(id='building-heatmap')
                    ]),
                    
                    dcc.Tab(label='Multi-Objective', children=[
                        # Add multi-objective visualizations
                        dcc.Graph(id='multi-obj-scatter')
                    ])
                ])
            ])
            
            print(f"[INFO] Dashboard running at http://localhost:{port}")
            app.run_server(port=port, debug=False)
            
        except ImportError:
            print("[WARNING] Dash not installed. Cannot create interactive dashboard.")