"""
validation_data_loader.py - Updated with configuration support and better alignment
Handles loading of real and simulated data from various formats with automatic conversion
"""
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Union, Tuple, Optional
import logging

from validation.validation_config import ValidationConfig
from validation.data_alignment import DataAligner

logger = logging.getLogger(__name__)


class ValidationDataLoader:
    """Enhanced data loader with configuration support"""
    
    def __init__(self, job_output_dir: str, config: Optional[ValidationConfig] = None):
        self.job_output_dir = Path(job_output_dir)
        self.parsed_data_dir = self.job_output_dir / "parsed_data"
        self.config = config or ValidationConfig()
        self.aligner = DataAligner(self.config)
        
        # Check if parsed data directory exists
        if not self.parsed_data_dir.exists():
            logger.warning(f"Parsed data directory not found: {self.parsed_data_dir}")
    
    def load_real_data(self, real_data_path: str, id_column: str = "BuildingID") -> pd.DataFrame:
        """
        Load real/measured data from CSV or Parquet with automatic format detection
        
        Args:
            real_data_path: Path to real data file
            id_column: Column name containing building IDs
            
        Returns:
            DataFrame with standardized structure
        """
        path = Path(real_data_path)
        
        if not path.exists():
            raise FileNotFoundError(f"Real data file not found: {real_data_path}")
        
        # Load based on file extension
        logger.info(f"Loading real data from: {path}")
        
        if path.suffix.lower() == '.csv':
            df = pd.read_csv(path, encoding=self.config.config['real_data']['encoding'])
        elif path.suffix.lower() == '.parquet':
            df = pd.read_parquet(path)
        else:
            raise ValueError(f"Unsupported file format: {path.suffix}")
        
        logger.info(f"Loaded {len(df)} rows from {path.name}")
        
        # Detect format
        data_format = self.aligner.detect_format(df)
        logger.info(f"Detected data format: {data_format}")
        
        # Standardize structure
        df = self._standardize_real_data_structure(df, id_column)
        
        # Apply variable name mappings
        df = self.aligner.standardize_variable_names(df)
        
        # Log summary
        if 'VariableName' in df.columns:
            variables = df['VariableName'].unique()
            logger.info(f"Variables found: {', '.join(variables[:5])}" + 
                       (" ..." if len(variables) > 5 else ""))
        
        if 'BuildingID' in df.columns:
            buildings = df['BuildingID'].unique()
            logger.info(f"Buildings found: {', '.join(map(str, buildings[:5]))}" + 
                       (" ..." if len(buildings) > 5 else ""))
        
        return df
    
    def _standardize_real_data_structure(self, df: pd.DataFrame, id_column: str) -> pd.DataFrame:
        """
        Standardize real data to match expected structure with better error handling
        """
        # Rename ID column if needed
        if id_column in df.columns and id_column != 'BuildingID':
            df = df.rename(columns={id_column: 'BuildingID'})
        
        # Ensure BuildingID exists
        if 'BuildingID' not in df.columns:
            raise ValueError("BuildingID column not found in data")
        
        # Convert BuildingID to string for consistent handling
        df['BuildingID'] = df['BuildingID'].astype(str)
        
        # Detect if data is in wide or long format
        data_format = self.aligner.detect_format(df)
        
        if data_format == 'wide':
            # Wide format: dates as columns
            # Ensure VariableName column exists
            if 'VariableName' not in df.columns and 'Variable' not in df.columns:
                # Check if variables are in rows (need to transpose)
                if len(df) < 20 and len(df.columns) > 50:
                    logger.info("Data appears to be transposed, fixing...")
                    df = self._transpose_data(df)
                else:
                    raise ValueError("VariableName column not found in wide format data")
            
            # Rename Variable to VariableName if needed
            if 'Variable' in df.columns:
                df = df.rename(columns={'Variable': 'VariableName'})
            
            # Ensure date columns are properly formatted
            date_cols = [col for col in df.columns if col not in ['BuildingID', 'VariableName', 'Zone', 'Units']]
            
            # Try to standardize date column names
            new_col_names = {}
            for col in date_cols:
                try:
                    # Parse the date
                    parsed = self._parse_date_string(col)
                    if parsed:
                        # Use consistent format
                        new_name = parsed.strftime('%m/%d')
                        new_col_names[col] = new_name
                except:
                    # Keep original if can't parse
                    pass
            
            if new_col_names:
                df = df.rename(columns=new_col_names)
                logger.info(f"Standardized {len(new_col_names)} date column names")
            
            # Ensure numeric values in date columns
            date_cols = [col for col in df.columns if col not in ['BuildingID', 'VariableName', 'Zone', 'Units']]
            for col in date_cols:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        else:
            # Long format
            # Ensure required columns
            if 'VariableName' not in df.columns and 'Variable' in df.columns:
                df = df.rename(columns={'Variable': 'VariableName'})
            
            if 'DateTime' not in df.columns:
                if 'Date' in df.columns:
                    df = df.rename(columns={'Date': 'DateTime'})
                elif 'Timestamp' in df.columns:
                    df = df.rename(columns={'Timestamp': 'DateTime'})
                else:
                    raise ValueError("DateTime column not found in long format data")
            
            # Ensure DateTime is datetime type
            df['DateTime'] = pd.to_datetime(df['DateTime'], 
                                           infer_datetime_format=self.config.config['real_data']['date_parsing']['infer_datetime_format'])
            
            # Ensure Value column exists and is numeric
            if 'Value' in df.columns:
                df['Value'] = pd.to_numeric(df['Value'], errors='coerce')
            else:
                raise ValueError("Value column not found in long format data")
        
        return df
    
    def _parse_date_string(self, date_str: str) -> Optional[pd.Timestamp]:
        """Parse date string using configured formats"""
        for date_format in self.config.get_date_formats():
            try:
                return pd.to_datetime(date_str, format=date_format)
            except:
                continue
        
        # Try pandas automatic parsing
        try:
            return pd.to_datetime(date_str)
        except:
            return None
    
    def _transpose_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Transpose data if variables are in columns instead of rows"""
        # This is a complex operation that needs careful handling
        # For now, raise an error with helpful message
        raise ValueError(
            "Data appears to be transposed (variables in columns). "
            "Please restructure data to have BuildingID and VariableName columns "
            "with dates as additional columns or use long format."
        )
    
    def load_simulated_data_from_parsed(self, building_ids: List[Union[str, int]], 
                                      variables: List[str],
                                      frequency: str = "daily") -> pd.DataFrame:
        """
        Load simulated data from parsed Parquet files with improved error handling
        """
        all_data = []
        
        # Convert building IDs to strings for consistent matching
        building_ids_str = [str(b) for b in building_ids]
        
        logger.info(f"Loading simulated data for buildings: {building_ids_str}")
        logger.info(f"Requested variables: {variables}")
        logger.info(f"Frequency: {frequency}")
        
        # Determine data path based on frequency
        if frequency == "hourly":
            data_paths = [self.parsed_data_dir / "sql_results" / "timeseries" / "hourly"]
        elif frequency == "daily":
            # Check both daily aggregated and hourly paths
            data_paths = [
                self.parsed_data_dir / "sql_results" / "timeseries" / "aggregated" / "daily",
                self.parsed_data_dir / "sql_results" / "timeseries" / "hourly"
            ]
        else:
            data_paths = [self.parsed_data_dir / "sql_results" / "timeseries" / "aggregated" / frequency]
        
        # Try each path
        for data_path in data_paths:
            if not data_path.exists():
                logger.debug(f"Path not found: {data_path}")
                continue
            
            logger.info(f"Searching in: {data_path}")
            
            # Load all relevant Parquet files
            parquet_files = list(data_path.glob("*.parquet"))
            logger.info(f"Found {len(parquet_files)} parquet files")
            
            for parquet_file in parquet_files:
                try:
                    df = pd.read_parquet(parquet_file)
                    
                    # Filter by building IDs
                    if "building_id" in df.columns:
                        df_buildings = df[df["building_id"].astype(str).isin(building_ids_str)]
                        
                        if not df_buildings.empty:
                            # Apply variable name mappings
                            if "Variable" in df_buildings.columns:
                                # Map simulation variable names to requested names
                                df_buildings = self._map_simulation_variables(df_buildings, variables)
                                
                                if not df_buildings.empty:
                                    all_data.append(df_buildings)
                                    logger.info(f"Loaded {len(df_buildings)} rows from {parquet_file.name}")
                            else:
                                # No Variable column, include all data
                                all_data.append(df_buildings)
                                logger.info(f"Loaded {len(df_buildings)} rows from {parquet_file.name}")
                
                except Exception as e:
                    logger.warning(f"Error loading {parquet_file}: {e}")
        
        if not all_data:
            logger.warning("No simulated data found")
            return pd.DataFrame()
        
        # Combine all data
        combined_df = pd.concat(all_data, ignore_index=True)
        
        # Standardize column names
        combined_df = combined_df.rename(columns={
            "building_id": "BuildingID",
            "Variable": "VariableName"
        })
        
        # Convert BuildingID to string for consistency
        if 'BuildingID' in combined_df.columns:
            combined_df['BuildingID'] = combined_df['BuildingID'].astype(str)
        
        # If data is hourly but daily was requested, aggregate
        if frequency == "daily" and "hourly" in str(data_paths[0]):
            logger.info("Aggregating hourly data to daily")
            combined_df = self._aggregate_to_daily(combined_df)
        
        logger.info(f"Total simulated data loaded: {len(combined_df)} rows")
        
        return combined_df
    
    def _map_simulation_variables(self, df: pd.DataFrame, requested_variables: List[str]) -> pd.DataFrame:
        """Map simulation variable names to requested variable names"""
        # Create reverse mapping from config
        reverse_mapping = {}
        for requested_var in requested_variables:
            mapped_var = self.config.get_variable_mapping(requested_var)
            reverse_mapping[mapped_var] = requested_var
        
        # Also check for partial matches
        variable_mapping = {
            'Electricity:Facility [J](Hourly)': [
                'Facility Total Electric Demand Power',
                'Electricity:Facility',
                'Total Electric Energy'
            ],
            'Heating:EnergyTransfer [J](Hourly)': [
                'Zone Air System Sensible Heating Energy',
                'Heating:EnergyTransfer',
                'Total Heating Energy'
            ],
            'Cooling:EnergyTransfer [J](Hourly)': [
                'Zone Air System Sensible Cooling Energy',
                'Cooling:EnergyTransfer',
                'Total Cooling Energy'
            ]
        }
        
        # Extend reverse mapping with standard mappings
        for req_var, sim_vars in variable_mapping.items():
            if req_var in requested_variables:
                for sim_var in sim_vars:
                    reverse_mapping[sim_var] = req_var
        
        # Filter and map variables
        if reverse_mapping:
            # Filter to only variables we can map
            df_filtered = df[df["Variable"].isin(reverse_mapping.keys())].copy()
            
            # Map variable names
            df_filtered["Variable"] = df_filtered["Variable"].map(reverse_mapping)
            
            return df_filtered
        else:
            # No mapping, return data with requested variables if they exist
            return df[df["Variable"].isin(requested_variables)]
    
    def _aggregate_to_daily(self, df: pd.DataFrame) -> pd.DataFrame:
        """Aggregate hourly data to daily"""
        if 'DateTime' not in df.columns:
            logger.warning("DateTime column not found, cannot aggregate")
            return df
        
        # Ensure DateTime is datetime type
        df['DateTime'] = pd.to_datetime(df['DateTime'])
        
        # Create date column
        df['Date'] = df['DateTime'].dt.date
        
        # Group by building, variable, and date
        group_cols = ['BuildingID', 'Date']
        if 'VariableName' in df.columns:
            group_cols.insert(1, 'VariableName')
        
        # Determine aggregation method
        agg_func = 'sum'  # Default for energy
        if 'VariableName' in df.columns:
            # Use mean for temperature/power variables
            temp_mask = df['VariableName'].str.contains('Temperature|Power', case=False, na=False)
            if temp_mask.any():
                # Split into two groups
                energy_df = df[~temp_mask]
                other_df = df[temp_mask]
                
                # Aggregate separately
                agg_dfs = []
                if not energy_df.empty:
                    agg_dfs.append(energy_df.groupby(group_cols)['Value'].sum().reset_index())
                if not other_df.empty:
                    agg_dfs.append(other_df.groupby(group_cols)['Value'].mean().reset_index())
                
                if agg_dfs:
                    agg_df = pd.concat(agg_dfs, ignore_index=True)
                else:
                    agg_df = pd.DataFrame()
            else:
                # All energy variables
                agg_df = df.groupby(group_cols)['Value'].sum().reset_index()
        else:
            agg_df = df.groupby(group_cols)['Value'].agg(agg_func).reset_index()
        
        # Convert Date back to DateTime for consistency
        if not agg_df.empty:
            agg_df['DateTime'] = pd.to_datetime(agg_df['Date'])
            agg_df = agg_df.drop('Date', axis=1)
        
        return agg_df
    
    def transform_to_wide_format(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Transform time series data from long to wide format for validation
        """
        if df.empty:
            return df
        
        # Check if already in wide format
        format_type = self.aligner.detect_format(df)
        if format_type == 'wide':
            logger.info("Data already in wide format")
            return df
        
        # Transform from long to wide
        if 'DateTime' not in df.columns:
            logger.error("DateTime column required for wide transformation")
            return df
        
        # Ensure DateTime is datetime type
        df['DateTime'] = pd.to_datetime(df['DateTime'])
        
        # Create date string for column names
        # Use the format specified in config or default to MM/DD
        date_format = self.config.config['real_data']['date_parsing'].get('output_format', '%m/%d')
        df['DateStr'] = df['DateTime'].dt.strftime(date_format)
        
        # Pivot to wide format
        try:
            pivot_index = ['BuildingID']
            if 'VariableName' in df.columns:
                pivot_index.append('VariableName')
            
            wide_df = df.pivot_table(
                index=pivot_index,
                columns='DateStr',
                values='Value',
                aggfunc='mean'  # Handle any duplicates
            ).reset_index()
            
            # Sort columns to have dates in order
            date_cols = [col for col in wide_df.columns if col not in pivot_index]
            sorted_date_cols = sorted(date_cols, key=lambda x: self._parse_date_string(x) or x)
            
            ordered_cols = pivot_index + sorted_date_cols
            wide_df = wide_df[ordered_cols]
            
            logger.info(f"Transformed to wide format: {wide_df.shape}")
            return wide_df
            
        except Exception as e:
            logger.error(f"Error pivoting data: {e}")
            return df
    
    def align_data_structures(self, real_df: pd.DataFrame, sim_df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Align real and simulated data structures for comparison using the new alignment system
        """
        # Use the DataAligner for smart alignment
        real_aligned, sim_aligned = self.aligner.align_data(real_df, sim_df)
        
        # If both are in wide format, ensure they have the same date columns
        real_format = self.aligner.detect_format(real_aligned)
        sim_format = self.aligner.detect_format(sim_aligned)
        
        if real_format == 'wide' and sim_format == 'wide':
            # Find common date columns
            common_dates = self.aligner.extract_common_dates(real_aligned, sim_aligned)
            
            if not common_dates:
                raise ValueError("No common dates found between datasets")
            
            # Keep only common columns
            keep_cols = ['BuildingID']
            if 'VariableName' in real_aligned.columns:
                keep_cols.append('VariableName')
            keep_cols.extend(common_dates)
            
            # Filter columns
            real_aligned = real_aligned[[col for col in keep_cols if col in real_aligned.columns]]
            sim_aligned = sim_aligned[[col for col in keep_cols if col in sim_aligned.columns]]
            
            logger.info(f"Aligned to {len(common_dates)} common dates")
        
        return real_aligned, sim_aligned