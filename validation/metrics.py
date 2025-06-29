# validation/metrics.py
import numpy as np

def mean_bias_error(sim_values, obs_values):
    """
    Calculates the Mean Bias Error (MBE) as a percentage.
    MBE = ( sum(sim_i - obs_i) / sum(obs_i) ) * 100
    Note: Some definitions use (obs - sim). This implementation uses (sim - obs)
    to show simulation bias. A positive value means the simulation overpredicts.
    """
    sim = np.array(sim_values, dtype=float)
    obs = np.array(obs_values, dtype=float)
    
    # Ensure denominator is not zero and there are values to process
    if np.sum(obs) == 0 or len(obs) == 0:
        return np.nan
        
    return np.sum(sim - obs) / np.sum(obs) * 100.0

def cv_rmse(sim_values, obs_values):
    """
    Calculates the Coefficient of Variation of the Root Mean Square Error (CV(RMSE)) as a percentage.
    CV(RMSE) = ( RMSE / mean(obs) ) * 100
    """
    sim = np.array(sim_values, dtype=float)
    obs = np.array(obs_values, dtype=float)
    
    obs_mean = np.mean(obs)
    if obs_mean == 0 or len(obs) == 0:
        return np.nan
        
    mse = np.mean((sim - obs)**2)
    rmse = np.sqrt(mse)
    return (rmse / obs_mean) * 100.0

def nmbe(sim_values, obs_values):
    """
    Calculates the Normalized Mean Bias Error (NMBE) as a percentage.
    NMBE = ( sum(sim_i - obs_i) / (n * mean(obs)) ) * 100
    This is equivalent to MBE but normalized by the mean of observations.
    """
    sim = np.array(sim_values, dtype=float)
    obs = np.array(obs_values, dtype=float)
    
    n = len(obs)
    obs_mean = np.mean(obs)
    
    if n == 0 or obs_mean == 0:
        return np.nan
        
    return (np.sum(sim - obs) / (n * obs_mean)) * 100.0

# --- NEW FUNCTIONS ---

def analyze_peaks(obs_values, sim_values, n_peaks=5):
    """
    Finds the top N peaks in the observed data and compares them with simulated data
    at the same time steps.

    :param obs_values: Array of observed values.
    :param sim_values: Array of simulated values.
    :param n_peaks: The number of top peaks to analyze.
    :return: A dictionary of metrics related to the peaks.
    """
    obs = np.array(obs_values, dtype=float)
    sim = np.array(sim_values, dtype=float)
    
    if len(obs) < n_peaks:
        return {}
        
    # Find the indices of the N largest values in the observed data
    peak_indices = np.argsort(obs)[-n_peaks:]
    
    peak_obs = obs[peak_indices]
    peak_sim = sim[peak_indices]

    # Avoid division by zero if an observed peak is 0
    # Replace 0 with a very small number for calculation, or handle as nan
    non_zero_peak_obs = np.where(peak_obs == 0, np.nan, peak_obs)
    
    with np.errstate(divide='ignore', invalid='ignore'):
      avg_magnitude_diff_pct = np.nanmean(np.abs(peak_obs - peak_sim) / non_zero_peak_obs) * 100.0

    return {
        "peak_avg_obs_val": np.mean(peak_obs),
        "peak_avg_sim_val": np.mean(peak_sim),
        "peak_avg_magnitude_diff_pct": avg_magnitude_diff_pct
    }

def analyze_ramp_rates(obs_values, sim_values):
    """
    Calculates and compares the distribution of ramp rates (first derivative).

    :param obs_values: Array of observed values.
    :param sim_values: Array of simulated values.
    :return: A dictionary of statistics about the ramp rates.
    """
    obs = np.array(obs_values, dtype=float)
    sim = np.array(sim_values, dtype=float)

    # np.diff calculates the difference between adjacent elements
    obs_ramps = np.diff(obs)
    sim_ramps = np.diff(sim)

    if len(obs_ramps) == 0:
        return {}

    return {
        "ramp_rate_obs_mean_abs": np.mean(np.abs(obs_ramps)),
        "ramp_rate_sim_mean_abs": np.mean(np.abs(sim_ramps)),
        "ramp_rate_obs_max_abs": np.max(np.abs(obs_ramps)),
        "ramp_rate_sim_max_abs": np.max(np.abs(sim_ramps)),
    }