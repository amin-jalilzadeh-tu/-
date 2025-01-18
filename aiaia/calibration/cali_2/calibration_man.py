from cali_2.calibration_code import (
    CalibrationManager,
    PARAM_SPACE,
    save_history_to_csv
)

def main():
    manager = CalibrationManager(PARAM_SPACE)

    # 1) Random Search
    print("=== Calibrating with Random Search ===")
    best_params_random, best_err_random, hist_random = manager.run_calibration(
        method="random",
        n_iterations=30
    )
    print(f"[RANDOM] best error = {best_err_random:.3f}")
    print(f"[RANDOM] best params = {best_params_random}")
    save_history_to_csv(hist_random, "calibration_random.csv")

    # 2) Genetic Algorithm
    print("\n=== Calibrating with GA ===")
    best_params_ga, best_err_ga, hist_ga = manager.run_calibration(
        method="ga",
        pop_size=10,
        generations=5,
        crossover_prob=0.7,
        mutation_prob=0.2
    )
    print(f"[GA] best error = {best_err_ga:.3f}")
    print(f"[GA] best params = {best_params_ga}")
    save_history_to_csv(hist_ga, "calibration_ga.csv")

    # 3) Bayesian Optimization
    print("\n=== Calibrating with Bayesian Optimization ===")
    best_params_bayes, best_err_bayes, hist_bayes = manager.run_calibration(
        method="bayes",
        n_calls=20
    )
    print(f"[BAYES] best error = {best_err_bayes:.3f}")
    print(f"[BAYES] best params = {best_params_bayes}")
    save_history_to_csv(hist_bayes, "calibration_bayes.csv")


if __name__ == "__main__":
    main()
