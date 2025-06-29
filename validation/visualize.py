# validation/visualize.py
import matplotlib.pyplot as plt
import numpy as np

def plot_time_series_comparison(merged_df, building_id, variable_name):
    """
    Creates a line plot comparing sim vs. obs over time.
    merged_df has columns: Date, Value_obs, Value_sim
    """
    if merged_df.empty:
        print(f"[DEBUG] No data to plot for Bldg={building_id}, Var={variable_name}")
        return

    # Use Timestamp if available, otherwise fall back to Date
    x_axis = merged_df['Timestamp'] if 'Timestamp' in merged_df.columns else merged_df['Date']
    obs_vals = merged_df['Value_obs']
    sim_vals = merged_df['Value_sim']

    plt.figure(figsize=(12, 6))
    plt.plot(x_axis, obs_vals, 'o-', label='Observed', markersize=4, alpha=0.8)
    plt.plot(x_axis, sim_vals, 's-', label='Simulated', markersize=4, alpha=0.8)

    plt.title(f"Time Series Comparison: Building {building_id} - {variable_name}")
    plt.xlabel("Date/Time")
    plt.ylabel("Value")
    plt.legend()
    plt.grid(True, which='major', linestyle='--', linewidth=0.5)
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()

def scatter_plot_comparison(merged_df, building_id, variable_name):
    """
    Creates a scatter plot of Observed vs. Simulated for a correlation check.
    """
    if merged_df.empty:
        print(f"[DEBUG] No data to plot scatter for Bldg={building_id}, Var={variable_name}")
        return

    obs_vals = merged_df['Value_obs']
    sim_vals = merged_df['Value_sim']

    plt.figure(figsize=(7, 7))
    plt.scatter(obs_vals, sim_vals, alpha=0.6, edgecolors='k', linewidths=0.5)
    
    # Add 1:1 line for reference
    lims = [
        min(plt.xlim()[0], plt.ylim()[0]),
        max(plt.xlim()[1], plt.ylim()[1]),
    ]
    plt.plot(lims, lims, 'r--', alpha=0.75, lw=2, label='1:1 Line')
    
    plt.title(f"Scatter Comparison: Bldg={building_id}, Var={variable_name}")
    plt.xlabel("Observed Values")
    plt.ylabel("Simulated Values")
    plt.legend()
    plt.grid(True, linestyle='--', linewidth=0.5)
    plt.axis('equal') # Ensure the plot is square
    plt.tight_layout()
    plt.show()

def bar_chart_metrics(metric_dict, title="Validation Metrics"):
    """
    Generic bar chart plotter for metrics. Assumes a specific dictionary structure.
    Bars are green if pass, red if fail.
    """
    if not metric_dict:
        print("[DEBUG] No metrics to plot - metric_dict is empty.")
        return

    labels = []
    cvrmse_values = []
    pass_status = []

    for key, mvals in metric_dict.items():
        # Adapt label based on key structure
        if len(key) == 2: # (b_id, var)
            label = f"B{key[0]}-{key[1]}"
        elif len(key) == 3: # (real, sim, var)
            label = f"R{key[0]}-S{key[1]}-{key[2]}"
        else: # Fallback for unknown key structure
            label = str(key)

        labels.append(label)
        cvrmse_values.append(mvals.get('CVRMSE', 0))
        pass_status.append(mvals.get('Pass', False))

    x = np.arange(len(labels))

    plt.figure(figsize=(12, 7))
    bars = plt.bar(x, cvrmse_values, color='gray')

    for i, bar in enumerate(bars):
        bar.set_color('g' if pass_status[i] else 'r')

    plt.xticks(x, labels, rotation=45, ha='right')
    plt.ylabel("CV(RMSE) (%)")
    plt.title(title)
    if cvrmse_values:
        plt.ylim(0, max(cvrmse_values) * 1.15)
    
    plt.grid(axis='y', linestyle='--', linewidth=0.5)
    plt.tight_layout()
    plt.show()

# --- NEW FUNCTIONS ---

def plot_diurnal_profile(diurnal_df, building_id, variable_name):
    """
    Plots the average daily profile for observed vs. simulated data.

    :param diurnal_df: DataFrame with 'Hour', 'Value_obs', 'Value_sim' columns.
    :param building_id: String identifier for the building comparison.
    :param variable_name: The name of the variable being plotted.
    """
    if diurnal_df.empty:
        print(f"[DEBUG] No diurnal data to plot for {building_id} - {variable_name}")
        return

    plt.figure(figsize=(10, 6))
    plt.plot(diurnal_df['Hour'], diurnal_df['Value_obs'], 'o-', label='Observed Average', alpha=0.8)
    plt.plot(diurnal_df['Hour'], diurnal_df['Value_sim'], 's-', label='Simulated Average', alpha=0.8)
    
    plt.title(f"Average Diurnal Profile: Bldg {building_id} - {variable_name}")
    plt.xlabel("Hour of Day")
    plt.ylabel("Average Value")
    plt.xticks(np.arange(0, 24, 2))
    plt.grid(True, which='both', linestyle='--', linewidth=0.5)
    plt.legend()
    plt.tight_layout()
    plt.show()

def plot_ramp_rate_distribution(obs_ramps, sim_ramps, building_id, variable_name):
    """
    Plots histograms of the ramp rates for comparison.

    :param obs_ramps: Array of observed ramp rates.
    :param sim_ramps: Array of simulated ramp rates.
    :param building_id: String identifier for the building comparison.
    :param variable_name: The name of the variable being analyzed.
    """
    if len(obs_ramps) == 0 or len(sim_ramps) == 0:
        print(f"[DEBUG] No ramp rate data to plot for {building_id} - {variable_name}")
        return

    plt.figure(figsize=(10, 6))
    
    # Determine common bin range
    min_val = min(np.min(obs_ramps), np.min(sim_ramps))
    max_val = max(np.max(obs_ramps), np.max(sim_ramps))
    bins = np.linspace(min_val, max_val, 50)

    plt.hist(obs_ramps, bins=bins, alpha=0.7, label='Observed Ramp Rates', density=True, color='blue')
    plt.hist(sim_ramps, bins=bins, alpha=0.7, label='Simulated Ramp Rates', density=True, color='orange')
    
    plt.title(f"Ramp Rate Distribution: Bldg {building_id} - {variable_name}")
    plt.xlabel("Ramp Rate (Value change per time step)")
    plt.ylabel("Probability Density")
    plt.legend()
    plt.grid(axis='y', linestyle='--', linewidth=0.5)
    plt.tight_layout()
    plt.show()