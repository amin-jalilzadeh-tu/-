"""
Extract simulation results from variant SQL files for calibration
Combines parameter values with corresponding simulation outputs
"""

import pandas as pd
import numpy as np
import sqlite3
from pathlib import Path
import json
import logging
from typing import List, Dict, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class VariantResultsExtractor:
    """Extract and organize simulation results from variants for calibration"""
    
    def __init__(self, output_dir: str):
        self.output_dir = Path(output_dir)
        self.modifications_data = None
        self.variant_results = {}
        
    def load_modifications(self):
        """Load modifications data to understand variants"""
        mod_files = list((self.output_dir / "modified_idfs").glob("modifications_detail_wide_*.parquet"))
        if not mod_files:
            raise FileNotFoundError("No modifications parquet file found")
            
        self.modifications_data = pd.read_parquet(mod_files[0])
        logger.info(f"Loaded modifications data with {len(self.modifications_data)} parameters")
        
        # Get variant columns
        self.variant_cols = [col for col in self.modifications_data.columns if col.startswith('variant_')]
        logger.info(f"Found {len(self.variant_cols)} variants")
        
    def extract_from_sql(self, sql_file: Path, variables: List[str], 
                        time_freq: str = 'Monthly') -> pd.DataFrame:
        """
        Extract specified variables from SQL file
        
        Args:
            sql_file: Path to SQL file
            variables: List of variable names to extract
            time_freq: Time frequency (Hourly, Daily, Monthly)
            
        Returns:
            DataFrame with extracted data
        """
        try:
            conn = sqlite3.connect(str(sql_file))
            
            # Build query for ReportData table
            var_conditions = " OR ".join([f"Name = '{var}'" for var in variables])
            
            query = f"""
            SELECT 
                rd.TimeIndex,
                rd.Value,
                rdd.Name as VariableName,
                rdd.ReportingFrequency,
                rdd.Units,
                t.Month,
                t.Day,
                t.Hour,
                t.Minute
            FROM ReportData rd
            JOIN ReportDataDictionary rdd ON rd.ReportDataDictionaryIndex = rdd.ReportDataDictionaryIndex
            JOIN Time t ON rd.TimeIndex = t.TimeIndex
            WHERE ({var_conditions})
            AND rdd.ReportingFrequency = '{time_freq}'
            ORDER BY rd.TimeIndex
            """
            
            df = pd.read_sql_query(query, conn)
            conn.close()
            
            # Pivot to wide format
            if not df.empty:
                pivot_df = df.pivot_table(
                    index=['TimeIndex', 'Month', 'Day', 'Hour'],
                    columns='VariableName',
                    values='Value',
                    aggfunc='first'
                ).reset_index()
                
                return pivot_df
            else:
                logger.warning(f"No data found for variables in {sql_file.name}")
                return pd.DataFrame()
                
        except Exception as e:
            logger.error(f"Error reading SQL file {sql_file}: {e}")
            return pd.DataFrame()
    
    def extract_variant_results(self, target_variables: List[str], 
                              time_freq: str = 'Monthly',
                              building_id: Optional[str] = None):
        """
        Extract results for all variants
        
        Args:
            target_variables: Variables to extract
            time_freq: Time frequency
            building_id: Specific building ID or None for first found
        """
        results_dir = self.output_dir / "Modified_Sim_Results"
        if not results_dir.exists():
            raise FileNotFoundError(f"Modified results directory not found at {results_dir}")
        
        # Find year directories
        year_dirs = [d for d in results_dir.iterdir() if d.is_dir() and d.name.isdigit()]
        if not year_dirs:
            raise FileNotFoundError("No year directories found in Modified_Sim_Results")
        
        year_dir = year_dirs[0]  # Use first year
        logger.info(f"Processing results from {year_dir}")
        
        # Extract building ID from file names if not specified
        if building_id is None:
            sql_files = list(year_dir.glob("*.sql"))
            if sql_files:
                # Extract building ID from filename like simulation_bldg0_4136733.sql
                filename = sql_files[0].stem
                parts = filename.split('_')
                if len(parts) >= 3:
                    building_id = parts[-1]
                    logger.info(f"Detected building ID: {building_id}")
        
        # Process each variant
        all_results = []
        
        for variant_idx, variant_col in enumerate(self.variant_cols):
            variant_num = int(variant_col.split('_')[1])
            
            # Find corresponding SQL file
            sql_pattern = f"simulation_bldg{variant_num}_{building_id}.sql"
            sql_file = year_dir / sql_pattern
            
            if not sql_file.exists():
                logger.warning(f"SQL file not found: {sql_file}")
                continue
            
            # Extract data
            logger.info(f"Extracting data from variant {variant_num}")
            variant_data = self.extract_from_sql(sql_file, target_variables, time_freq)
            
            if not variant_data.empty:
                # Add variant identifier
                variant_data['variant_id'] = variant_num
                variant_data['variant_name'] = variant_col
                
                # Add parameter values for this variant
                for _, param_row in self.modifications_data.iterrows():
                    param_name = f"{param_row['category']}*{param_row['object_type']}*{param_row['object_name']}*{param_row['field']}"
                    variant_data[param_name] = param_row[variant_col]
                
                all_results.append(variant_data)
                self.variant_results[variant_num] = variant_data
        
        # Combine all results
        if all_results:
            combined_df = pd.concat(all_results, ignore_index=True)
            logger.info(f"Extracted results for {len(all_results)} variants")
            return combined_df
        else:
            logger.error("No results extracted from any variant")
            return pd.DataFrame()
    
    def aggregate_results(self, results_df: pd.DataFrame, 
                         agg_method: str = 'sum',
                         group_by: str = 'monthly') -> pd.DataFrame:
        """
        Aggregate results to desired time scale
        
        Args:
            results_df: Raw results DataFrame
            agg_method: Aggregation method (sum, mean, max, min)
            group_by: Grouping level (monthly, yearly, total)
            
        Returns:
            Aggregated DataFrame
        """
        if results_df.empty:
            return results_df
        
        # Get variable columns (not metadata columns)
        meta_cols = ['TimeIndex', 'Month', 'Day', 'Hour', 'variant_id', 'variant_name']
        param_cols = [col for col in results_df.columns if '*' in col]
        var_cols = [col for col in results_df.columns if col not in meta_cols + param_cols]
        
        if group_by == 'monthly':
            # Group by variant and month
            grouped = results_df.groupby(['variant_id', 'variant_name', 'Month'])
            
        elif group_by == 'yearly':
            # Group by variant only
            grouped = results_df.groupby(['variant_id', 'variant_name'])
            
        else:  # total
            grouped = results_df.groupby(['variant_id', 'variant_name'])
        
        # Aggregate variables
        agg_dict = {col: agg_method for col in var_cols}
        
        # Keep first value of parameters (they're constant per variant)
        for param_col in param_cols:
            agg_dict[param_col] = 'first'
        
        aggregated = grouped.agg(agg_dict).reset_index()
        
        return aggregated
    
    def save_calibration_data(self, results_df: pd.DataFrame, 
                            output_name: str = "calibration_data"):
        """
        Save extracted data in calibration-ready format
        
        Args:
            results_df: Results DataFrame
            output_name: Output directory name
        """
        output_dir = self.output_dir / output_name
        output_dir.mkdir(exist_ok=True)
        
        # Save full results
        results_df.to_parquet(output_dir / "variant_results_full.parquet")
        results_df.to_csv(output_dir / "variant_results_full.csv", index=False)
        
        # Create parameter matrix (variants x parameters)
        param_cols = [col for col in results_df.columns if '*' in col]
        if param_cols:
            param_matrix = results_df[['variant_id'] + param_cols].drop_duplicates()
            param_matrix.to_csv(output_dir / "parameter_matrix.csv", index=False)
        
        # Create output matrix (variants x outputs x time)
        meta_cols = ['variant_id', 'variant_name', 'Month']
        var_cols = [col for col in results_df.columns 
                   if col not in meta_cols + param_cols and col != 'TimeIndex']
        
        if var_cols:
            output_matrix = results_df[meta_cols + var_cols]
            output_matrix.to_csv(output_dir / "output_matrix.csv", index=False)
        
        # Create summary
        summary = {
            'n_variants': len(results_df['variant_id'].unique()),
            'n_parameters': len(param_cols),
            'n_outputs': len(var_cols),
            'parameters': param_cols,
            'outputs': var_cols,
            'time_points': len(results_df['Month'].unique()) if 'Month' in results_df else 1
        }
        
        with open(output_dir / "calibration_data_summary.json", 'w') as f:
            json.dump(summary, f, indent=2)
        
        logger.info(f"Saved calibration data to {output_dir}")
        logger.info(f"Summary: {summary}")


def main():
    """Extract variant results for calibration"""
    
    output_dir = "/mnt/d/Documents/daily/E_Plus_2040_py/output/e0e23b56-96a2-44b9-9936-76c15af196fb"
    
    extractor = VariantResultsExtractor(output_dir)
    
    # Load modifications
    extractor.load_modifications()
    
    # Define target variables for calibration
    target_variables = [
        "Electricity:Facility",
        "Heating:EnergyTransfer",
        "Cooling:EnergyTransfer",
        "InteriorLights:Electricity",
        "InteriorEquipment:Electricity"
    ]
    
    # Extract results
    logger.info(f"Extracting variables: {target_variables}")
    results = extractor.extract_variant_results(
        target_variables=target_variables,
        time_freq='Monthly'
    )
    
    if not results.empty:
        # Aggregate to monthly totals
        monthly_results = extractor.aggregate_results(
            results, 
            agg_method='sum',
            group_by='monthly'
        )
        
        # Save for calibration
        extractor.save_calibration_data(monthly_results)
        
        print(f"\nExtraction complete!")
        print(f"Variants processed: {len(monthly_results['variant_id'].unique())}")
        print(f"Parameters included: {len([c for c in monthly_results.columns if '*' in c])}")
        print(f"Output variables: {[c for c in monthly_results.columns if c in target_variables]}")
    else:
        print("\nNo results extracted. Check if SQL files exist and contain the specified variables.")


if __name__ == "__main__":
    main()