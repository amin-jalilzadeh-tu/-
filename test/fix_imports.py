#!/usr/bin/env python
# run_test.py - Cross-platform test runner

import subprocess
import sys
import os

def clear_screen():
    """Clear the console screen"""
    os.system('cls' if os.name == 'nt' else 'clear')

def run_command(cmd):
    """Run a command and wait for it to complete"""
    print(f"\nRunning: {' '.join(cmd)}")
    print("-" * 50)
    result = subprocess.run(cmd, shell=False)
    return result.returncode

def main_menu():
    """Display main menu and handle user choice"""
    while True:
        clear_screen()
        print("=" * 50)
        print("IDF Modification Test Suite")
        print("=" * 50)
        print("\nSelect an option:")
        print("1. Run setup (first time only)")
        print("2. Run all tests")
        print("3. Run baseline only")
        print("4. Run efficient HVAC scenario")
        print("5. Run efficient lighting scenario")
        print("6. Run envelope upgrade scenario")
        print("7. Run comprehensive retrofit")
        print("8. Run multiple scenarios")
        print("9. Run custom scenario")
        print("D. Run diagnostics")
        print("F. Fix import issues")
        print("0. Exit")
        print()
        
        choice = input("Enter your choice (0-9, D, F): ").strip().upper()
        
        if choice == "0":
            print("Exiting...")
            break
            
        elif choice == "1":
            run_command([sys.executable, "setup_test.py"])
            
        elif choice == "2":
            run_command([sys.executable, "main_test.py"])
            
        elif choice == "3":
            run_command([sys.executable, "main_test.py", "--scenarios", "baseline"])
            
        elif choice == "4":
            run_command([sys.executable, "main_test.py", "--scenarios", "baseline", "efficient_hvac"])
            
        elif choice == "5":
            run_command([sys.executable, "main_test.py", "--scenarios", "baseline", "efficient_lighting"])
            
        elif choice == "6":
            run_command([sys.executable, "main_test.py", "--scenarios", "baseline", "envelope_upgrade"])
            
        elif choice == "7":
            run_command([sys.executable, "main_test.py", "--scenarios", "baseline", "comprehensive_retrofit"])
            
        elif choice == "8":
            print("\nAvailable scenarios:")
            print("- baseline")
            print("- efficient_hvac")
            print("- efficient_lighting") 
            print("- envelope_upgrade")
            print("- comprehensive_retrofit")
            scenarios = input("\nEnter scenario names separated by spaces: ").strip().split()
            if scenarios:
                cmd = [sys.executable, "main_test.py", "--scenarios"] + scenarios
                run_command(cmd)
            
        elif choice == "9":
            config_file = input("Enter path to custom config file (or press Enter for default): ").strip()
            if config_file:
                run_command([sys.executable, "main_test.py", "--config", config_file])
            else:
                scenarios = input("Enter custom scenario names separated by spaces: ").strip().split()
                if scenarios:
                    cmd = [sys.executable, "main_test.py", "--scenarios"] + scenarios
                    run_command(cmd)
        
        elif choice == "D":
            run_command([sys.executable, "check_setup.py"])
            
        elif choice == "F":
            run_command([sys.executable, "fix_imports.py"])
        
        else:
            print("Invalid choice!")
        
        input("\nPress Enter to continue...")

if __name__ == "__main__":
    try:
        main_menu()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(0)