"""
unified_calibration.py

Key Features:
  - Load scenario CSV files you want to calibrate (DH, Elec, Fenez, etc.).
  - Optionally filter parameters by a sensitivity CSV (top N).
  - Create ParamSpecs for param_value (and optionally param_min, param_max).
  - Provide random, GA, or Bayesian methods to find param sets that minimize an error.
  - The error function can be:
       (A) Re-run E+ (placeholder here),
       (B) Use a trained surrogate (with "use_surrogate": true).
  - Save one calibration_history.csv for all attempts.
  - Write separate best-param CSV for each scenario file, e.g.:
       calibrated_params_scenario_params_dhw.csv
       calibrated_params_scenario_params_elec.csv
    with updated values for param_value, param_min, param_max, etc.

Author: Example
"""

import os
import csv
import random
import copy
import numpy as np
import pandas as pd
from typing import List, Dict, Tuple, Callable, Optional

# scikit-optimize for bayesian calibration
try:
    from skopt import gp_minimize
    from skopt.space import Real, Integer
    from skopt.utils import use_named_args
    HAVE_SKOPT = True
except ImportError:
    gp_minimize = None
    Real = None
    Integer = None
    use_named_args = None
    HAVE_SKOPT = False

# For Surrogate usage
import joblib

###############################################################################
# 0) Global placeholders for loaded Surrogate + Real Data
###############################################################################
MODEL_SURROGATE = None
MODEL_COLUMNS   = None
REAL_DATA_DICT  = None

###############################################################################
# 1) ParamSpec
###############################################################################

class ParamSpec:
    """
    name: the internal name of the parameter (str)
    min_value, max_value: float boundaries
    is_integer: bool => if True, round to int
    """
    def __init__(self, name: str, min_value: float, max_value: float, is_integer: bool = False):
        self.name = name
        self.min_value = min_value
        self.max_value = max_value
        self.is_integer = is_integer

    def sample_random(self) -> float:
        val = random.uniform(self.min_value, self.max_value)
        return int(round(val)) if self.is_integer else val


###############################################################################
# 2) Scenario CSV loading
###############################################################################

def load_scenario_csvs(scenario_folder: str, scenario_files: List[str]) -> pd.DataFrame:
    """
    Reads specified scenario CSVs from scenario_folder, merges them.
    Each file is expected to have columns e.g.:
      scenario_index, ogc_fid, object_name, param_name,
      param_value, param_min, param_max, ...
    We'll store "source_file" for each row. 
    """
    if not scenario_files:
        # default to all
        scenario_files = [
            "scenario_params_dhw.csv",
            "scenario_params_elec.csv",
            "scenario_params_fenez.csv",
            "scenario_params_hvac.csv",
            "scenario_params_vent.csv"
        ]

    dfs = []
    for fname in scenario_files:
        fpath = os.path.join(scenario_folder, fname)
        if os.path.isfile(fpath):
            df_temp = pd.read_csv(fpath)
            df_temp["source_file"] = fname
            dfs.append(df_temp)
        else:
            print(f"[WARN] Scenario file '{fname}' not found => skipping.")
    if not dfs:
        raise FileNotFoundError(f"No scenario CSV found in {scenario_folder} for files={scenario_files}")

    merged = pd.concat(dfs, ignore_index=True)
    return merged


def optionally_filter_by_sensitivity(
    df_scen: pd.DataFrame,
    sensitivity_csv: str,
    top_n: int = 10,
    param_col: str = "param",
    metric_col: str = "mu_star"
) -> pd.DataFrame:
    """
    If 'sensitivity_csv' is found, read it, sort by metric_col descending,
    pick top_n param names => keep only those in df_scen. 
    We'll match df_scen["param_name"] to param_col in the sensitivity CSV.
    """
    if not sensitivity_csv or not os.path.isfile(sensitivity_csv):
        print("[INFO] No sensitivity CSV or not found => skipping filter.")
        return df_scen

    df_sens = pd.read_csv(sensitivity_csv)
    if param_col not in df_sens.columns or metric_col not in df_sens.columns:
        print(f"[WARN] param_col='{param_col}' or metric_col='{metric_col}' not found => skipping filter.")
        return df_scen

    df_sens_sorted = df_sens.sort_values(metric_col, ascending=False)
    top_params = df_sens_sorted[param_col].head(top_n).tolist()
    print(f"[INFO] Filtering scenario params to top {top_n} from {sensitivity_csv} => {top_params}")

    df_filt = df_scen[df_scen["param_name"].isin(top_params)].copy()
    if df_filt.empty:
        print("[WARN] After filter, no scenario params remain => returning original.")
        return df_scen
    return df_filt


###############################################################################
# 3) Build ParamSpecs from scenario rows
###############################################################################

def build_param_specs_from_scenario(
    df_scen: pd.DataFrame,
    calibrate_min_max: bool = True
) -> List[ParamSpec]:
    """
    For each row in df_scen, produce param_value plus param_min/param_max if calibrate_min_max is True.

    We do something like:
      base_key = f"{source_file}:{param_name}"
      Then create:
         base_key_VAL
         base_key_MIN
         base_key_MAX
    with numeric ranges.

    You can revise the logic so param_min param_max come from row["param_min"], row["param_max"] if you want them separate.
    """

    specs = []
    for idx, row in df_scen.iterrows():
        p_name = row.get("param_name", "UnknownParam")
        source_file = row.get("source_file", "")
        base_val    = row.get("param_value", np.nan)
        base_min    = row.get("param_min",  np.nan)
        base_max    = row.get("param_max",  np.nan)

        # unify a base key
        base_key = f"{source_file}:{p_name}".replace(".csv","")

        # fallback if param_value is missing
        try:
            valf = float(base_val)
        except:
            valf = 1.0  # fallback

        # fallback if param_min/param_max missing
        # we do a small check => if invalid, use ±20% around val
        if pd.isna(base_min) or pd.isna(base_max) or (base_min >= base_max):
            base_min = valf * 0.8
            base_max = valf * 1.2
            if base_min >= base_max:
                base_max = base_min + 0.001

        # (A) param_value => name= base_key+"_VAL"
        specs.append(ParamSpec(
            name=f"{base_key}_VAL",
            min_value=float(base_min),
            max_value=float(base_max),
            is_integer=False
        ))

        if calibrate_min_max:
            # (B) param_min => vary in [0, valf], or [0, base_min], or something
            # We'll just do e.g. [0, min(valf, base_min)]
            mmn = 0.0
            mmx = min(valf, base_min) if base_min < valf else valf
            if mmx <= mmn:
                mmx = mmn + 0.001
            specs.append(ParamSpec(
                name=f"{base_key}_MIN",
                min_value=mmn,
                max_value=mmx,
                is_integer=False
            ))

            # (C) param_max => vary in [valf, 2*], or [base_max, 2 base_max], etc.
            mm2 = max(valf, base_max)
            mm2b = mm2 * 2.0
            specs.append(ParamSpec(
                name=f"{base_key}_MAX",
                min_value=mm2,
                max_value=mm2b,
                is_integer=False
            ))

    return specs


###############################################################################
# 4) Evaluate param_dict => surrogate or E+
###############################################################################

def load_surrogate_once(model_path: str, columns_path: str):
    """
    Loads the surrogate model and column list into global variables if not loaded yet.
    Adjust as needed if you have multiple surrogates or different model paths.
    """
    global MODEL_SURROGATE, MODEL_COLUMNS
    if MODEL_SURROGATE is None or MODEL_COLUMNS is None:
        print(f"[INFO] Loading surrogate => {model_path} / {columns_path}")
        MODEL_SURROGATE = joblib.load(model_path)
        MODEL_COLUMNS   = joblib.load(columns_path)


def load_real_data_once(real_csv: str):
    """
    You can interpret your real_data_csv and store it as a dictionary 
    if you have multiple scenario_index or building IDs. For this example, 
    we store a single usage or a dict with a single key.
    """
    global REAL_DATA_DICT
    if REAL_DATA_DICT is None:
        print(f"[INFO] Loading real data => {real_csv}")
        # Example approach: read the entire CSV, sum or do something
        df = pd.read_csv(real_csv)
        # We'll just store a single number or store a dict of building-> usage
        # For demonstration, do a single building => buildingID=0 => usage= 1.23e7
        REAL_DATA_DICT = {0: 1.23e7}


def transform_calib_name_to_surrogate_col(full_name: str) -> str:
    """
    If your calibration param name is "scenario_params_dhw.csv:dhw.setpoint_c_VAL",
    we might want to map it to "dhw.setpoint_c" for the surrogate.
    This is a simple approach:
      1) remove "_VAL", "_MIN", "_MAX"
      2) remove "scenario_params_dhw.csv:" prefix
    """
    # remove prefix
    if ":" in full_name:
        full_name = full_name.split(":",1)[1]  # e.g. "dhw.setpoint_c_VAL"
    # remove suffix
    for suffix in ["_VAL","_MIN","_MAX"]:
        if full_name.endswith(suffix):
            full_name = full_name[: -len(suffix)]
    return full_name


def build_feature_row_from_param_dict(param_dict: Dict[str, float]) -> pd.DataFrame:
    """
    1) We have a list of columns the surrogate expects => MODEL_COLUMNS
    2) param_dict keys are e.g. "scenario_params_dhw.csv:dhw.setpoint_c_VAL" => 58.0
    3) Map them => "dhw.setpoint_c" => 58.0
    """
    global MODEL_COLUMNS
    row_dict = {col: 0.0 for col in MODEL_COLUMNS}

    for k, v in param_dict.items():
        short_k = transform_calib_name_to_surrogate_col(k)
        if short_k in row_dict:
            row_dict[short_k] = v

    return pd.DataFrame([row_dict])


def predict_error_with_surrogate(param_dict: Dict[str, float], config: dict) -> float:
    """
    1) load surrogate if not loaded
    2) build feature row
    3) predict => predicted usage
    4) get real usage => compute error
    """
    model_path  = config.get("surrogate_model_path", "heating_surrogate_model.joblib")
    columns_path= config.get("surrogate_columns_path","heating_surrogate_columns.joblib")
    real_csv    = config.get("real_data_csv", "")

    load_surrogate_once(model_path, columns_path)
    load_real_data_once(real_csv)

    df_sample = build_feature_row_from_param_dict(param_dict)
    preds = MODEL_SURROGATE.predict(df_sample)

    # If single-output => preds is shape (1,)
    predicted_usage = preds[0] if len(preds.shape)==1 else preds[0,0]

    # Retrieve real usage. Here we just pick buildingID=0
    # If you have multiple buildingIDs => param_dict might contain scenario_index
    real_usage = REAL_DATA_DICT[0]

    # error measure => absolute difference
    error = abs(predicted_usage - real_usage)
    return error


def run_energyplus_and_compute_error(param_dict: Dict[str, float], config: dict) -> float:
    """
    Placeholder for re-running E+. 
    For now, we do sum of param_dict + random noise, measure difference from 50.
    """
    val_sum = sum(param_dict.values())
    noise = random.uniform(-2.0, 2.0)
    error = abs(val_sum - 50) + noise
    return error


def simulate_or_surrogate(param_dict: Dict[str, float], config: dict) -> float:
    """
    If config["use_surrogate"] => call surrogate
    else => re-run E+
    """
    use_sur = config.get("use_surrogate", False)
    if use_sur:
        return predict_error_with_surrogate(param_dict, config)
    else:
        return run_energyplus_and_compute_error(param_dict, config)


###############################################################################
# 5) Random / GA / Bayes calibration
###############################################################################

def random_search_calibration(
    param_specs: List[ParamSpec],
    eval_func: Callable[[Dict[str, float]], float],
    n_iterations: int
) -> Tuple[Dict[str, float], float, list]:
    best_params = None
    best_err = float('inf')
    history = []
    for _ in range(n_iterations):
        p_dict = {}
        for s in param_specs:
            p_dict[s.name] = s.sample_random()
        err = eval_func(p_dict)
        history.append((p_dict, err))
        if err < best_err:
            best_err = err
            best_params = p_dict
    return best_params, best_err, history


def ga_calibration(
    param_specs: List[ParamSpec],
    eval_func: Callable[[Dict[str, float]], float],
    pop_size: int,
    generations: int,
    crossover_prob: float,
    mutation_prob: float
) -> Tuple[Dict[str, float], float, list]:

    def random_individual():
        p = {}
        for s in param_specs:
            p[s.name] = s.sample_random()
        return p

    def evaluate(ind: dict) -> Tuple[float, float]:
        e = eval_func(ind)
        # fitness = 1 / (1+error)
        fit = 1.0 / (1.0 + e)
        return fit, e

    def tournament_select(pop, k=3):
        contenders = random.sample(pop, k)
        best = max(contenders, key=lambda x: x["fitness"])
        return copy.deepcopy(best)

    def crossover(p1: dict, p2: dict):
        c1, c2 = {}, {}
        for k in p1.keys():
            if random.random() < 0.5:
                c1[k] = p1[k]
                c2[k] = p2[k]
            else:
                c1[k] = p2[k]
                c2[k] = p1[k]
        return c1, c2

    def mutate(ind: dict):
        for s in param_specs:
            if random.random() < mutation_prob:
                ind[s.name] = s.sample_random()

    population = []
    history = []
    # init
    for _ in range(pop_size):
        ind = random_individual()
        fit, err = evaluate(ind)
        population.append({"params": ind, "fitness": fit, "error": err})
        history.append((ind, err))

    for g in range(generations):
        new_pop = []
        while len(new_pop) < pop_size:
            pa = tournament_select(population)
            pb = tournament_select(population)
            if random.random() < crossover_prob:
                c1, c2 = crossover(pa["params"], pb["params"])
            else:
                c1, c2 = pa["params"], pb["params"]
            mutate(c1)
            mutate(c2)
            f1, e1 = evaluate(c1)
            f2, e2 = evaluate(c2)
            new_pop.append({"params": c1, "fitness": f1, "error": e1})
            new_pop.append({"params": c2, "fitness": f2, "error": e2})
            history.append((c1, e1))
            history.append((c2, e2))
        # sort by fitness desc, keep top pop_size
        new_pop.sort(key=lambda x: x["fitness"], reverse=True)
        population = new_pop[:pop_size]
        best_ind = max(population, key=lambda x: x["fitness"])
        print(f"[GA] gen={g} best_error={best_ind['error']:.3f}")

    best_ind = max(population, key=lambda x: x["fitness"])
    return best_ind["params"], best_ind["error"], history


def bayes_calibration(
    param_specs: List[ParamSpec],
    eval_func: Callable[[Dict[str, float]], float],
    n_calls: int
) -> Tuple[Dict[str, float], float, list]:
    if not HAVE_SKOPT or gp_minimize is None:
        print("[WARN] scikit-optimize not installed => fallback random.")
        return random_search_calibration(param_specs, eval_func, n_calls)

    skopt_dims = []
    param_names = []
    for s in param_specs:
        param_names.append(s.name)
        if s.is_integer:
            skopt_dims.append(Integer(s.min_value, s.max_value, name=s.name))
        else:
            skopt_dims.append(Real(s.min_value, s.max_value, name=s.name))

    @use_named_args(skopt_dims)
    def objective(**kwargs):
        return eval_func(kwargs)

    res = gp_minimize(
        objective,
        dimensions=skopt_dims,
        n_calls=n_calls,
        n_initial_points=5,
        random_state=42
    )
    best_err = res.fun
    best_x = res.x
    best_params = {}
    for i, val in enumerate(best_x):
        best_params[param_names[i]] = val

    history = []
    for i, x_list in enumerate(res.x_iters):
        pdict = {}
        for j, val in enumerate(x_list):
            pdict[param_names[j]] = val
        e = res.func_vals[i]
        history.append((pdict, e))

    return best_params, best_err, history


###############################################################################
# 6) Save history & best param CSV
###############################################################################

def save_history_to_csv(history: list, filename: str):
    if not history:
        print("[WARN] No history => skipping save.")
        return
    rows = []
    all_params = set()
    for (pdict, err) in history:
        rows.append((pdict, err))
        all_params.update(pdict.keys())
    all_params = sorted(all_params)
    os.makedirs(os.path.dirname(filename) or ".", exist_ok=True)
    with open(filename, "w", newline="") as f:
        writer = csv.writer(f)
        header = list(all_params) + ["error"]
        writer.writerow(header)
        for (pdict, err) in rows:
            rowvals = [pdict.get(p, "") for p in all_params]
            rowvals.append(err)
            writer.writerow(rowvals)
    print(f"[INFO] Wrote calibration history => {filename}")


def fix_min_max_relations(best_params: Dict[str, float]):
    """
    Optional step: ensure param_min <= param_val <= param_max.
    For each group: basekey_VAL, basekey_MIN, basekey_MAX, reorder if needed.
    E.g. 'scenario_params_dhw.csv:dhw.setpoint_c_VAL' => ...
    """
    from collections import defaultdict
    groups = defaultdict(dict)
    for k,v in best_params.items():
        if k.endswith("_VAL"):
            base = k[:-4]  # remove _VAL
            groups[base]["VAL"] = v
        elif k.endswith("_MIN"):
            base = k[:-4]  # remove _MIN
            groups[base]["MIN"] = v
        elif k.endswith("_MAX"):
            base = k[:-4]  # remove _MAX
            groups[base]["MAX"] = v

    for base, triple in groups.items():
        if "VAL" in triple and "MIN" in triple and "MAX" in triple:
            mn  = triple["MIN"]
            val = triple["VAL"]
            mx  = triple["MAX"]
            new_min = min(mn, val, mx)
            new_max = max(mn, val, mx)
            new_val = max(new_min, min(val, new_max))
            best_params[base+"_MIN"] = new_min
            best_params[base+"_VAL"] = new_val
            best_params[base+"_MAX"] = new_max


def save_best_params_separately(
    best_params: Dict[str, float],
    df_scen: pd.DataFrame,
    out_folder: str = "./",
    prefix: str = "calibrated_params_"
):
    """
    Writes separate CSV for each scenario file.
    E.g.: prefix + "scenario_params_dhw.csv"
    Each file has rows with columns:
      scenario_index, ogc_fid, object_name, param_name,
      old_param_value, new_param_value,
      old_param_min, new_param_min,
      old_param_max, new_param_max,
      source_file
    """
    fix_min_max_relations(best_params)
    os.makedirs(out_folder, exist_ok=True)
    grouped = df_scen.groupby("source_file")

    for sfile, group_df in grouped:
        out_rows = []
        for _, row in group_df.iterrows():
            p_name = row["param_name"]
            s_file = row["source_file"]
            old_val = row.get("param_value",  np.nan)
            old_min = row.get("param_min",    np.nan)
            old_max = row.get("param_max",    np.nan)

            base_key = f"{s_file}:{p_name}".replace(".csv","")
            new_val_key = base_key + "_VAL"
            new_min_key = base_key + "_MIN"
            new_max_key = base_key + "_MAX"

            new_val = best_params.get(new_val_key, old_val)
            new_min = best_params.get(new_min_key, old_min)
            new_max = best_params.get(new_max_key, old_max)

            out_rows.append({
                "scenario_index": row.get("scenario_index",""),
                "ogc_fid": row.get("ogc_fid",""),
                "object_name": row.get("object_name",""),
                "param_name": p_name,
                "old_param_value": old_val,
                "new_param_value": new_val,
                "old_param_min": old_min,
                "new_param_min": new_min,
                "old_param_max": old_max,
                "new_param_max": new_max,
                "source_file": s_file
            })

        df_out = pd.DataFrame(out_rows)
        out_name = prefix + sfile  # e.g. "calibrated_params_scenario_params_dhw.csv"
        out_path = os.path.join(out_folder, out_name)
        df_out.to_csv(out_path, index=False)
        print(f"[INFO] Wrote best params => {out_path}")


###############################################################################
# 7) Master function => run_unified_calibration
###############################################################################

def run_unified_calibration(calibration_config: dict):
    """
    Example usage from main.py:
      if cal_cfg.get("perform_calibration", False):
          run_unified_calibration(cal_cfg)

    The calibration_config can have keys like:
    {
      "scenario_folder": "output/scenarios",
      "scenario_files": [ "scenario_params_dhw.csv", ... ],
      "subset_sensitivity_csv": "morris_sensitivity.csv",
      "top_n_params": 10,
      "method": "ga",
      "use_surrogate": true,
      "real_data_csv": "output/results/mock_merged_daily_mean.csv",
      "surrogate_model_path": "heating_surrogate_model.joblib",
      "surrogate_columns_path": "heating_surrogate_columns.joblib",
      "calibrate_min_max": true,
      "ga_pop_size": 10,
      "ga_generations": 5,
      "ga_crossover_prob": 0.7,
      "ga_mutation_prob": 0.2,
      "bayes_n_calls": 15,
      "random_n_iter": 20,
      "output_history_csv": "calibration_history.csv",
      "best_params_folder": "output/calibrated",
      "history_folder": "output/calibrated"
    }
    """

    scenario_folder = calibration_config["scenario_folder"]
    scenario_files  = calibration_config.get("scenario_files", [])
    subset_sens     = calibration_config.get("subset_sensitivity_csv", "")
    top_n           = calibration_config.get("top_n_params", 9999)
    method          = calibration_config.get("method", "ga")  # "random","ga","bayes"
    calibrate_mm    = calibration_config.get("calibrate_min_max", True)
    output_hist_csv = calibration_config.get("output_history_csv", "calibration_history.csv")
    best_params_dir = calibration_config.get("best_params_folder","./")
    hist_dir        = calibration_config.get("history_folder","./")

    # 1) load scenario CSV
    df_scen = load_scenario_csvs(scenario_folder, scenario_files)

    # 2) optional filter by sensitivity
    df_scen = optionally_filter_by_sensitivity(df_scen, subset_sens, top_n)

    # 3) build param specs
    param_specs = build_param_specs_from_scenario(df_scen, calibrate_min_max=calibrate_mm)

    # 4) define local eval function
    def local_eval_func(pdict: Dict[str, float]) -> float:
        return simulate_or_surrogate(pdict, calibration_config)

    # 5) run method
    if method == "random":
        n_iter = calibration_config.get("random_n_iter", 20)
        best_params, best_err, history = random_search_calibration(param_specs, local_eval_func, n_iter)
    elif method == "ga":
        pop_size       = calibration_config.get("ga_pop_size", 10)
        generations    = calibration_config.get("ga_generations", 5)
        crossover_prob = calibration_config.get("ga_crossover_prob", 0.7)
        mutation_prob  = calibration_config.get("ga_mutation_prob", 0.2)
        best_params, best_err, history = ga_calibration(
            param_specs, local_eval_func,
            pop_size, generations, crossover_prob, mutation_prob
        )
    elif method == "bayes":
        n_calls = calibration_config.get("bayes_n_calls", 15)
        best_params, best_err, history = bayes_calibration(param_specs, local_eval_func, n_calls)
    else:
        raise ValueError(f"Unknown calibration method: {method}")

    print(f"[CAL] Method={method}, Best error={best_err:.3f}, best_params={best_params}")

    # 6) Save history
    hist_path = os.path.join(hist_dir, output_hist_csv)
    save_history_to_csv(history, hist_path)

    # 7) Create separate best-param CSV for each scenario file
    save_best_params_separately(
        best_params,
        df_scen,
        out_folder=best_params_dir,
        prefix="calibrated_params_"
    )

    print("[CAL] Calibration complete.")
