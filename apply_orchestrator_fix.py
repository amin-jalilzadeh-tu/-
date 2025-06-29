"""
Automatically add the missing post-modification simulation section to orchestrator.py
"""

import os
import shutil
from datetime import datetime

def add_post_modification_simulation(orchestrator_path="orchestrator.py"):
    """Add the missing post-modification simulation section"""
    
    print("Adding Post-Modification Simulation to Orchestrator")
    print("="*60)
    
    # Check if file exists
    if not os.path.exists(orchestrator_path):
        print(f"Error: {orchestrator_path} not found!")
        return False
    
    # Read the file
    with open(orchestrator_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check if already has post-modification simulation
    if "Running simulations on modified IDFs" in content:
        print("✓ File already contains post-modification simulation code!")
        return True
    
    # Create backup
    backup_path = f"{orchestrator_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy2(orchestrator_path, backup_path)
    print(f"✓ Created backup: {backup_path}")
    
    # Find where to insert the code
    # Look for the end of modification section
    search_line = 'logger.info(f"[INFO] Total modifications applied: {len(all_modifications)}")'
    
    if search_line not in content:
        print("Warning: Could not find the expected line to insert after.")
        print("Looking for alternative insertion point...")
        
        # Try alternative
        if "[INFO] Total modifications applied:" in content:
            print("Found similar line. Please manually add the code after the modification section.")
            return False
    
    # The new code to insert
    new_code = '''
            # -------------------------------------------------------------------------
            # 13.5) Run Simulations on Modified IDFs (if enabled)
            # -------------------------------------------------------------------------
            # Optionally run simulations on modified IDFs
            if modification_cfg.get("post_modification", {}).get("run_simulations", False):
                logger.info("[INFO] Running simulations on modified IDFs...")
                
                # Import required modules
                from epw.run_epw_sims import simulate_all
                
                # Get simulation configuration
                sim_config = modification_cfg.get("post_modification", {}).get("simulation_config", {})
                num_workers = sim_config.get("num_workers", simulate_config.get("num_workers", 4))
                
                # Prepare modified IDF data for simulation
                modified_idfs_dir = os.path.join(job_output_dir, mod_engine.config['output_options']['output_dir'])
                logger.info(f"[INFO] Looking for modified IDFs in: {modified_idfs_dir}")
                
                # Load the IDF mapping data
                idf_map_csv = os.path.join(job_output_dir, "extracted_idf_buildings.csv")
                if not os.path.isfile(idf_map_csv):
                    logger.error(f"[ERROR] IDF mapping file not found: {idf_map_csv}")
                    logger.error("[ERROR] Cannot run simulations without building data.")
                else:
                    df_map = pd.read_csv(idf_map_csv)
                    logger.info(f"[INFO] Loaded IDF mapping with {len(df_map)} buildings")
                    
                    # CRITICAL FIX: Convert ogc_fid to string for comparison
                    df_map['ogc_fid_str'] = df_map['ogc_fid'].astype(str)
                    
                    # Find all modified IDF files
                    modified_buildings = []
                    
                    for root, dirs, files in os.walk(modified_idfs_dir):
                        for file in files:
                            if file.endswith('.idf'):
                                full_path = os.path.join(root, file)
                                
                                # Extract building ID from filename
                                # Format: building_4136733_variant_0.idf
                                parts = file.replace('.idf', '').split('_')
                                
                                if len(parts) >= 2 and parts[0] == 'building':
                                    building_id = parts[1]
                                    
                                    # Find variant ID
                                    variant_id = 'unknown'
                                    if 'variant' in parts:
                                        variant_idx = parts.index('variant')
                                        if variant_idx + 1 < len(parts):
                                            variant_id = f"variant_{parts[variant_idx + 1]}"
                                    
                                    logger.debug(f"[DEBUG] Processing file: {file}, building_id: {building_id}, variant: {variant_id}")
                                    
                                    # FIXED: Compare using string column
                                    orig_building = df_map[df_map['ogc_fid_str'] == building_id]
                                    
                                    if not orig_building.empty:
                                        building_data = orig_building.iloc[0].to_dict()
                                        
                                        # Store the full filename with relative path from modified_idfs_dir
                                        # This is important for simulate_all to find the files
                                        rel_path = os.path.relpath(full_path, modified_idfs_dir)
                                        building_data['idf_name'] = rel_path
                                        building_data['variant_id'] = variant_id
                                        building_data['original_ogc_fid'] = building_id  # Keep original ID
                                        
                                        # Ensure ogc_fid is string for consistency
                                        building_data['ogc_fid'] = str(building_data['ogc_fid'])
                                        
                                        modified_buildings.append(building_data)
                                        logger.debug(f"[DEBUG] Added modified building: {building_id}, variant: {variant_id}, path: {rel_path}")
                                    else:
                                        logger.warning(f"[WARN] No building data found for ID '{building_id}'")
                                        logger.debug(f"[DEBUG] Available IDs: {df_map['ogc_fid_str'].unique()[:5].tolist()}...")  # Show first 5 for debugging
                    
                    if modified_buildings:
                        df_modified = pd.DataFrame(modified_buildings)
                        logger.info(f"[INFO] Found {len(df_modified)} modified IDF files to simulate")
                        logger.info(f"[INFO] Buildings to simulate: {df_modified.groupby('original_ogc_fid').size().to_dict()}")
                        
                        # Set output directory for modified simulation results
                        modified_sim_output = os.path.join(job_output_dir, "Modified_Sim_Results")
                        os.makedirs(modified_sim_output, exist_ok=True)
                        
                        # Get EPW configuration
                        # user_config_epw should already be loaded from section 9
                        
                        assigned_epw_log = {}  # Initialize empty log for EPW assignments
                        
                        # Log simulation setup
                        logger.info(f"[INFO] Simulation setup:")
                        logger.info(f"  - IDF directory: {modified_idfs_dir}")
                        logger.info(f"  - Output directory: {modified_sim_output}")
                        logger.info(f"  - Number of workers: {num_workers}")
                        logger.info(f"  - IDD file: {idf_creation.idf_config['iddfile']}")
                        
                        # Run simulations
                        try:
                            simulate_all(
                                df_buildings=df_modified,
                                idf_directory=modified_idfs_dir,
                                iddfile=idf_creation.idf_config["iddfile"],
                                base_output_dir=modified_sim_output,
                                user_config_epw=user_config_epw,
                                assigned_epw_log=assigned_epw_log,
                                num_workers=num_workers
                            )
                            
                            logger.info(f"[INFO] Completed simulations for {len(df_modified)} modified IDFs")
                            
                            # Optionally parse results
                            if modification_cfg.get("post_modification", {}).get("parse_results", {}).get("enabled", False):
                                logger.info("[INFO] Parsing modified simulation results...")
                                
                                # Create parser for modified results
                                modified_parser_output_dir = os.path.join(job_output_dir, "parsed_modified_data")
                                os.makedirs(modified_parser_output_dir, exist_ok=True)
                                
                                # Initialize analyzer for modified results
                                from parserr.energyplus_analyzer_main import EnergyPlusAnalyzer
                                from parserr.helpers import prepare_idf_sql_pairs_with_mapping
                                
                                analyzer_modified = EnergyPlusAnalyzer(modified_parser_output_dir)
                                
                                # Get parse configuration
                                parse_cfg_mod = modification_cfg.get("post_modification", {}).get("parse_results", {})
                                parse_idf = parse_cfg_mod.get("parse_idf", False)
                                parse_sql = parse_cfg_mod.get("parse_sql", True)
                                categories = parse_cfg_mod.get("categories", None)
                                
                                # Prepare IDF-SQL pairs for modified results
                                pairs_with_mapping = prepare_idf_sql_pairs_with_mapping(
                                    sim_output_dir=modified_sim_output,
                                    idf_dir=modified_idfs_dir,
                                    idf_map_csv=idf_map_csv
                                )
                                
                                if pairs_with_mapping:
                                    logger.info(f"[INFO] Found {len(pairs_with_mapping)} modified file pairs to parse")
                                    
                                    # Parse modified results
                                    analyzer_modified.analyze_multiple_files(
                                        pairs_with_mapping,
                                        parse_idf=parse_idf,
                                        parse_sql=parse_sql,
                                        categories=categories,
                                        save_summary=True,
                                        save_by_category=True,
                                        save_by_building=True
                                    )
                                    
                                    logger.info("[INFO] Parsing of modified results completed")
                                    analyzer_modified.close()
                                else:
                                    logger.warning("[WARN] No modified IDF-SQL pairs found for parsing")
                                
                        except Exception as e:
                            logger.error(f"[ERROR] Simulation failed: {str(e)}")
                            import traceback
                            traceback.print_exc()
                            
                    else:
                        logger.warning("[WARN] No modified IDF files found to simulate")
                        logger.warning(f"[WARN] Check directory: {modified_idfs_dir}")
            else:
                logger.info("[INFO] Post-modification simulations not enabled")'''
    
    # Insert the new code
    # Replace the search line with itself plus the new code
    new_content = content.replace(
        search_line,
        search_line + new_code
    )
    
    # Write the updated content
    with open(orchestrator_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print("✓ Added post-modification simulation section successfully!")
    print("\nThe following was added:")
    print("- Post-modification simulation check")
    print("- Building ID data type fix") 
    print("- Modified IDF file discovery")
    print("- Simulation execution")
    print("- Optional result parsing")
    
    return True

def verify_addition(orchestrator_path="orchestrator.py"):
    """Verify the code was added correctly"""
    
    print("\nVerifying Addition")
    print("-"*40)
    
    with open(orchestrator_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    checks = {
        "Post-mod simulation section": "# 13.5) Run Simulations on Modified IDFs" in content,
        "Run simulations check": "Running simulations on modified IDFs" in content,
        "Data type fix": "df_map['ogc_fid_str'] = df_map['ogc_fid'].astype(str)" in content,
        "Modified simulation call": "simulate_all(" in content and "modified_sim_output" in content
    }
    
    all_good = True
    for check, result in checks.items():
        status = "✓" if result else "✗"
        print(f"{status} {check}")
        if not result:
            all_good = False
    
    return all_good

if __name__ == "__main__":
    import sys
    
    # Get orchestrator path from command line or use default
    orchestrator_path = sys.argv[1] if len(sys.argv) > 1 else "orchestrator.py"
    
    print(f"Target file: {orchestrator_path}")
    print()
    
    # Add the missing section
    success = add_post_modification_simulation(orchestrator_path)
    
    if success:
        # Verify the addition
        if verify_addition(orchestrator_path):
            print("\n✅ Code added and verified successfully!")
            print("\nYour orchestrator now includes post-modification simulation functionality.")
            print("\nMake sure your combined.json has:")
            print('  "post_modification": {')
            print('    "run_simulations": true')
            print('  }')
        else:
            print("\n⚠ Code was added but verification shows issues.")
            print("Please check the file manually.")
    else:
        print("\n❌ Could not add code automatically.")
        print("Please add the post-modification simulation section manually.")
    
    input("\nPress Enter to exit...")