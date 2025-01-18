"""
A simple runner script that imports the main sensitivity analysis and executes it.
"""

import cali_2.sensitivity_analysis

if __name__ == "__main__":
    cali_2.sensitivity_analysis.main()



"""
man.py

A simple entry-point script to run the surrogate model pipeline 
from the 'surrogate_model.py' module.
"""

import cali_2.build_surrogate_model

if __name__ == "__main__":
    cali_2.build_surrogate_model.main()
