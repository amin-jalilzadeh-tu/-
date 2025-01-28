# validation/metrics.py
import numpy as np

def mean_bias_error(sim_values, obs_values):
    """
    MBE = ( sum(obs_i - sim_i) / sum(obs_i) ) * 100
    """
    sim = np.array(sim_values, dtype=float)
    obs = np.array(obs_values, dtype=float)
    denominator = np.sum(obs)
    if denominator == 0:
        return float('nan')
    mbe = (np.sum(obs - sim) / denominator) * 100.0
    return mbe

def cv_rmse(sim_values, obs_values):
    """
    CV(RMSE) = ( RMSE / mean(obs) ) * 100
    """
    sim = np.array(sim_values, dtype=float)
    obs = np.array(obs_values, dtype=float)
    obs_mean = np.mean(obs)
    if obs_mean == 0:
        return float('nan')
    mse = np.mean((obs - sim)**2)
    rmse = np.sqrt(mse)
    return (rmse / obs_mean) * 100.0

def nmbe(sim_values, obs_values):
    """
    NMBE = 100 * ( sum(obs_i - sim_i) / (n * mean(obs)) )
    """
    sim = np.array(sim_values, dtype=float)
    obs = np.array(obs_values, dtype=float)
    n = len(sim)
    obs_mean = np.mean(obs)
    if obs_mean == 0:
        return float('nan')
    nmbe_val = 100.0 * (np.sum(obs - sim) / (n * obs_mean))
    return nmbe_val
