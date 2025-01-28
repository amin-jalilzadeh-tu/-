# validation/visualize.py
import matplotlib.pyplot as plt

def plot_time_series_comparison(merged_df, building_id, variable_name):
    """
    Creates a simple line plot comparing sim vs. obs over time 
    (e.g., 01-Jan, 02-Jan, etc.).
    merged_df has columns: Date, Value_obs, Value_sim
    """
    if merged_df.empty:
        print(f"[DEBUG] No data to plot for Bldg={building_id}, Var={variable_name}")
        return

    x_vals = merged_df['Date']  # might be strings like '01-Jan'
    obs_vals = merged_df['Value_obs']
    sim_vals = merged_df['Value_sim']

    plt.figure(figsize=(10,6))
    plt.plot(x_vals, obs_vals, 'o-', label='Observed')
    plt.plot(x_vals, sim_vals, 's-', label='Simulated')

    plt.title(f"Building {building_id} - {variable_name}")
    plt.xlabel("Date")
    plt.ylabel("Value")
    plt.legend()
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()

def scatter_plot_comparison(merged_df, building_id, variable_name):
    """
    Creates a scatter plot of Observed vs. Simulated for a quick correlation check.
    """
    if merged_df.empty:
        print(f"[DEBUG] No data to plot scatter for Bldg={building_id}, Var={variable_name}")
        return

    obs_vals = merged_df['Value_obs']
    sim_vals = merged_df['Value_sim']

    plt.figure(figsize=(6,6))
    plt.scatter(obs_vals, sim_vals, alpha=0.7)
    # 1:1 line
    mn, mx = min(obs_vals.min(), sim_vals.min()), max(obs_vals.max(), sim_vals.max())
    plt.plot([mn, mx], [mn, mx], color='red', linestyle='--', label='1:1 line')

    plt.title(f"Scatter Comparison: Bldg={building_id}, Var={variable_name}")
    plt.xlabel("Observed")
    plt.ylabel("Simulated")
    plt.legend()
    plt.tight_layout()
    plt.show()

def bar_chart_metrics(metric_dict, title="Validation Metrics"):
    """
    Suppose metric_dict is e.g.:
      {
        (0, 'Cooling'): {'MBE': 2.3, 'CVRMSE': 18.5, 'NMBE': -0.4, 'Pass': True},
        (0, 'Heating'): { ... },
        (1, 'Cooling'): { ... },
        ...
      }
    We'll create a bar chart of CV(RMSE) across all keys.
    """
    import numpy as np

    if not metric_dict:
        print("[DEBUG] No metrics to plot - metric_dict is empty.")
        return

    labels = []
    cvrmse_values = []
    pass_status = []

    for (b_id, var), mvals in metric_dict.items():
        label = f"B{b_id}-{var}"
        labels.append(label)
        cvrmse_values.append(mvals['CVRMSE'])
        pass_status.append(mvals['Pass'])

    x = range(len(labels))

    plt.figure(figsize=(10,5))
    bars = plt.bar(x, cvrmse_values, color='blue', alpha=0.6)

    # Color code pass/fail if you want:
    for i, bar in enumerate(bars):
        if pass_status[i]:
            bar.set_color('green')
        else:
            bar.set_color('red')

    plt.xticks(list(x), labels, rotation=45, ha='right')
    plt.ylabel("CV(RMSE) (%)")
    plt.title(title)

    if cvrmse_values:
        plt.ylim(0, max(cvrmse_values)*1.1)
    plt.tight_layout()
    plt.show()
