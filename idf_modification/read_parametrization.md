1. **Assigned parameter CSV files** (input files):
   * `assigned_dhw_params.csv`
   * `assigned_hvac_building.csv`
   * `assigned_hvac_zones.csv`
   * `assigned_lighting.csv` (for electrical parameters)
   * `assigned_equipment.csv` (for equipment parameters)
   * `structured_fenez_params.csv` (for fenestration parameters)
   * `assigned_vent_building.csv`
   * `assigned_vent_zones.csv`

These files are loaded through the `load_assigned_csv()` function and used to generate parameter scenarios.

### Output CSV Files:

These are explicitly saved by the scenario generation functions:

* `scenario_params.csv` (general scenario parameters; name could vary)
* Specific scenario parameter CSV files, such as:
  * `scenario_params_hvac.csv`
  * `scenario_params_dhw.csv`
  * `scenario_params_elec.csv`
  * `scenario_params_equipment.csv`
  * `scenario_params_fenez.csv`
  * `scenario_params_vent.csv`
