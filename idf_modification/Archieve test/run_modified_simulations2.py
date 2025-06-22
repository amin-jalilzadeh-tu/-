"""
Simple wrapper to run simulations on modified IDFs
Configured for your specific setup
"""

import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from standalone_simulation_runner import StandaloneSimulationRunner
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Your specific configuration
JOB_ID = "650e5027-2c43-4a30-b588-5e4d72c0ac23"
OUTPUT_DIR = r"D:\Documents\daily\E_Plus_2040_py\output"
CONFIG_PATH = r"D:\Documents\daily\E_Plus_2040_py\combined.json"

def main():
    """Run simulations with your configuration"""
    try:
        logger.info("="*60)
        logger.info("RUNNING SIMULATIONS ON MODIFIED IDFs")
        logger.info("="*60)
        
        # Initialize runner
        runner = StandaloneSimulationRunner(
            job_id=JOB_ID,
            base_output_dir=OUTPUT_DIR
        )
        
        # Load your combined.json configuration
        logger.info(f"Loading configuration from: {CONFIG_PATH}")
        runner.load_configuration(CONFIG_PATH)
        
        # Check prerequisites
        logger.info("\nChecking prerequisites...")
        if not runner.check_prerequisites():
            logger.error("Prerequisites not met. Please fix the issues above.")
            return False
        
        # Ask user what to do
        print("\nOptions:")
        print("1. Run all simulations")
        print("2. Test single building")
        print("3. Run with custom workers")
        print("4. Check only (no simulation)")
        
        choice = input("\nSelect option (1-4): ").strip()
        
        if choice == "1":
            # Run all simulations
            success = runner.run_simulations(num_workers=4)
            
        elif choice == "2":
            # Test single building
            building_id = input("Enter building ID to test: ").strip()
            success = runner.test_single_building(building_id)
            
        elif choice == "3":
            # Custom workers
            workers = int(input("Number of parallel workers (1-16): ").strip())
            success = runner.run_simulations(num_workers=workers)
            
        elif choice == "4":
            # Just check
            logger.info("Prerequisites check completed. No simulations run.")
            return True
            
        else:
            logger.error("Invalid choice")
            return False
        
        if success:
            logger.info("\n✅ SIMULATIONS COMPLETED SUCCESSFULLY")
            
            # Ask about parsing
            parse = input("\nParse simulation results? (y/n): ").strip().lower()
            if parse == 'y':
                runner.parse_results()
        else:
            logger.error("\n❌ SIMULATIONS FAILED")
            
        return success
        
    except Exception as e:
        logger.error(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    
    # Wait for user input before closing
    input("\nPress Enter to exit...")
    
    sys.exit(0 if success else 1)