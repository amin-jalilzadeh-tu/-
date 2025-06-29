# Deep Analysis of the Sensitivity Analysis Project

## Project Overview

This is a comprehensive **building energy sensitivity analysis framework** designed to analyze how different building parameters (like HVAC settings, materials, equipment specifications) affect energy consumption and other performance metrics. It's specifically designed to work with EnergyPlus building energy simulations.

## Input Data

The framework uses several types of input data:

### 1. **IDF Parameters** (from parsed EnergyPlus files)

- Building materials properties
- HVAC system parameters
- Zone configurations
- Equipment specifications
- Schedule definitions
- Stored in: `parsed_data/idf_data/by_category/`

### 2. **Simulation Results**

- **Base results**: Original simulation outputs
- **Modified results**: Results after parameter modifications
- Time series data (hourly, daily, monthly)
- Categories: HVAC, energy, electricity, temperature, zones, ventilation
- Stored in: `parsed_data/sql_results/` and `parsed_modified_results/`

### 3. **Modification Tracking**

- Records of what parameters were changed
- Original vs new values
- Percentage changes
- Stored in: `modified_idfs/modifications_detail_*.parquet`

### 4. **Building Metadata**

- Building types, zones, equipment relationships
- Zone-to-equipment mappings
- Building registry information

## Processes/Analysis Types

### 1. **Traditional Sensitivity Analysis**

- Scenario-based approach
- Analyzes pre-defined parameter variations
- Methods: correlation, regression, mutual information, random forest

### 2. **Modification-Based Analysis**

- Analyzes actual parameter modifications
- Multi-level support:
  - **Building level**: Overall building sensitivity
  - **Zone level**: Zone-specific sensitivity
  - **Equipment level**: Individual equipment impact
  - **Cross-level**: Interactions between levels

### 3. **Advanced Analysis Features**

#### a) **Uncertainty Quantification**

- Monte Carlo uncertainty propagation
- Confidence bounds on sensitivity indices
- Parameter distribution specifications
- Bootstrap confidence intervals

#### b) **Threshold Analysis**

- Detects breakpoints where behavior changes
- Methods: Tree-based, statistical CUSUM, PELT algorithm
- Identifies critical parameter values

#### c) **Regional Sensitivity**

- Analyzes sensitivity in different parameter ranges
- Local sensitivity at operating points
- Methods: K-means clustering, grid partitioning, quantile-based

#### d) **Sobol Analysis**

- Variance-based decomposition
- First-order and total effect indices
- Second-order interactions
- Saltelli sampling method

#### e) **Temporal Patterns**

- Time-varying sensitivity analysis
- Fourier analysis for periodic patterns
- Time-lag detection
- Seasonal pattern identification

### 4. **Time Slicing Capabilities**

- Peak months (cooling/heating seasons)
- Time of day (peak hours)
- Day of week (weekdays vs weekends)
- Custom time periods
- Comparative analysis across time slices

## Statistical Models Applied

### 1. **Correlation Analysis**

- Pearson, Spearman, Kendall correlations
- Confidence intervals using Fisher's z-transformation

### 2. **Regression Methods**

- Linear regression
- Ridge regression
- Lasso regression
- Standardized coefficients

### 3. **Machine Learning**

- Random Forest feature importance
- Mutual information
- Decision trees for threshold detection

### 4. **Statistical Tests**

- Significance testing (p-values)
- Confidence intervals
- Stationarity tests
- Change point detection

### 5. **Advanced Methods**

- Elasticity analysis (percentage change sensitivity)
- Bootstrap analysis for uncertainty
- Bayesian uncertainty quantification
- Fourier transforms for frequency analysis

## Outputs

### 1. **Sensitivity Scores**

- Parameter rankings by importance
- Sensitivity indices for each parameter-output pair
- Statistical significance measures
- Confidence intervals

### 2. **Reports** (Multiple Formats)

- **JSON Reports**: Detailed analysis results
- **HTML Reports**: Interactive visualizations
- **CSV Files**: For Excel/data analysis
- **LaTeX Tables**: For academic papers
- **Parquet Files**: Efficient data storage

### 3. **Visualizations**

- Sensitivity heatmaps
- Parameter ranking plots
- Level comparison plots (building/zone/equipment)
- Time slice comparisons
- Temporal pattern visualizations

### 4. **Specialized Exports**

#### For Surrogate Modeling:

- Top sensitive parameters
- Parameter importance scores
- Formatted for machine learning workflows

#### For Calibration:

- Calibration parameter recommendations
- Suggested parameter ranges
- Grouped by sensitivity levels

#### Time Slice Analysis:

- Parameter stability across time periods
- Time-dependent sensitivity patterns
- Peak period specific parameters

### 5. **Advanced Analysis Results**

- **Uncertainty bounds**: Confidence intervals on sensitivity
- **Thresholds**: Critical parameter values
- **Regional maps**: Sensitivity variation across parameter space
- **Variance decomposition**: Sobol indices
- **Temporal patterns**: Seasonal/periodic sensitivity

## Key Features

1. **Multi-method Support**: Combines traditional and modern sensitivity analysis approaches
2. **Hierarchical Analysis**: From building to zone to equipment level
3. **Time-aware**: Can analyze different time periods separately
4. **Uncertainty Quantification**: Provides confidence in results
5. **Automated Reporting**: Generates comprehensive reports automatically
6. **Integration Ready**: Designed to fit into larger building simulation workflows
7. **Extensible**: Modular design allows adding new analysis methods

## Typical Workflow

1. **Load Data**: Parameters and simulation results
2. **Configure Analysis**: Choose methods and options
3. **Run Analysis**: Execute selected sensitivity methods
4. **Post-process**: Statistical significance, uncertainty bounds
5. **Generate Reports**: Create visualizations and exports
6. **Export Results**: For downstream tools (calibration, surrogate modeling)

This framework is particularly valuable for:

- Building energy modelers optimizing designs
- Researchers studying building performance
- Engineers calibrating building models
- Policy makers understanding key efficiency drivers

# Mathematical Formulas Used in Advanced Sensitivity Models

## 1. Sobol Variance Decomposition

### First-Order Sobol Indices

```python
# Variance of output
Var(Y) = Var(f(X))

# First-order index for parameter Xi
S_i = Var(E[Y|X_i]) / Var(Y)

# Implementation formula:
S_i = (1/n) * Σ(f_B * (f_AB_i - f_A)) / Var(Y)
```

Where:

- `f_A`, `f_B`: Model outputs from two independent sample matrices
- `f_AB_i`: Output when column i comes from matrix B, rest from A

### Total Effect Indices

```python
# Total effect index
S_Ti = 1 - Var(E[Y|X_~i]) / Var(Y)

# Implementation:
S_Ti = 1 - (1/n) * Σ(f_B * (f_BA_i - f_A)) / Var(Y)

# Or approximation:
S_Ti = (1/2n) * Σ((f_A - f_AB_i)²) / Var(Y)
```

### Second-Order Indices

```python
# Second-order interaction
S_ij = Var(E[Y|X_i, X_j]) / Var(Y) - S_i - S_j

# Implementation:
V_ij = (1/n) * Σ(f_AB_i * f_AB_j) - E[f_A] * E[f_B]
S_ij = V_ij / Var(Y) - S_i - S_j
```

## 2. Uncertainty Quantification

### Monte Carlo Propagation

```python
# Parameter sampling with distributions
X_sampled ~ Distribution(μ, σ)

# Output uncertainty
Y_uncertain = f(X_sampled + noise)

# Confidence bounds (percentile method)
CI_lower = percentile(Y_samples, α/2)
CI_upper = percentile(Y_samples, 1-α/2)
```

### Analytical Error Propagation

```python
# Relative uncertainties
σ_X_rel = σ_X / μ_X
σ_Y_rel = σ_Y / μ_Y

# Propagated uncertainty (assuming independence)
σ_sensitivity_rel = √(σ_X_rel² + σ_Y_rel²)

# Absolute uncertainty
σ_sensitivity = base_score * σ_sensitivity_rel

# Confidence bounds
CI = base_score ± z_α/2 * σ_sensitivity
```

Where `z_α/2` is the z-score for confidence level (1-α)

### Bayesian Uncertainty Update

```python
# Prior: N(μ_prior, σ²_prior)
# Likelihood: N(observed, σ²_obs)

# Posterior precision
τ_posterior = 1/σ²_prior + 1/σ²_obs

# Posterior mean
μ_posterior = (μ_prior/σ²_prior + observed/σ²_obs) * (1/τ_posterior)

# Posterior standard deviation
σ_posterior = √(1/τ_posterior)
```

## 3. Threshold/Breakpoint Detection

### Decision Tree Method

```python
# Minimize sum of squared errors in segments
SSE = Σ(y_left - ȳ_left)² + Σ(y_right - ȳ_right)²

# Split criterion at threshold t
t* = argmin_t [SSE_left(t) + SSE_right(t)]
```

### CUSUM (Cumulative Sum) Test

```python
# Residuals from linear fit
r_i = y_i - (ax_i + b)

# CUSUM statistic
S_i = Σ(r_j - r̄) for j=1 to i

# Change points at peaks
peaks = argmax(|S_i|)
```

### PELT (Pruned Exact Linear Time)

```python
# Cost function (negative log-likelihood)
C(y_s:t) = (t-s) * [log(2πσ²) + 1]
where σ² = Var(y_s:t)

# Optimization with penalty β
F[t] = min_{0≤s<t} [F[s] + C(y_s:t) + β]

# BIC penalty
β = 2 * log(n)
```

## 4. Regional Sensitivity Analysis

### Local Sensitivity in Region

```python
# Local correlation in region R
ρ_R = Corr(X_R, Y_R)

# Local slope (normalized)
β_R = Cov(X_R, Y_R) / Var(X_R)
β_normalized = β_R * (σ_X_R / σ_Y_R)

# Nonlinearity measure
NL = 1 - (SSE_linear / SSE_quadratic)

# Combined regional sensitivity
S_R = w_linear * |ρ_R| + w_nonlinear * |β_normalized|
where w_linear = 1 - NL, w_nonlinear = NL
```

### Local Derivatives at Operating Point

```python
# Fit polynomial locally
y = Σ(a_i * x^i) for i=0 to n

# kth derivative at point x_0
∂^k y/∂x^k |_{x=x_0} = k! * a_k + higher order terms
```

## 5. Temporal Pattern Analysis

### Fourier Analysis

```python
# Remove mean
y_centered = y - ȳ

# Apply window function (Hann)
w(n) = 0.5 * (1 - cos(2πn/N))
y_windowed = y_centered * w

# FFT
Y(f) = Σ(y_windowed[n] * e^(-2πifn/N))

# Power spectrum
P(f) = |Y(f)|²

# Dominant frequency
f_dominant = argmax(P(f)) for f > 0
```

### Time-Lag Cross-Correlation

```python
# Cross-correlation at lag τ
R_xy(τ) = E[(X_t - μ_X)(Y_{t+τ} - μ_Y)] / (σ_X * σ_Y)

# For discrete signals
R_xy(τ) = Σ(x[i] * y[i+τ]) / √(Σx²[i] * Σy²[i])

# Optimal lag
τ* = argmax(|R_xy(τ)|)
```

### Trend Analysis

```python
# Linear trend
y(t) = βt + α + ε

# Slope and significance
β = Cov(t, y) / Var(t)
r² = (Corr(t, y))²
p_value = 2 * (1 - t_cdf(|t_stat|, df))

# Stationarity test (F-test for equal variances)
F = Var(y_first_half) / Var(y_second_half)
p_stationarity = 2 * min(F_cdf(F), 1 - F_cdf(F))
```

### Seasonality Detection

```python
# Autocorrelation at lag L
ACF(L) = Cov(y_t, y_{t+L}) / Var(y)

# Seasonal strength at period P
strength_P = |ACF(P)|

# Seasonal pattern extraction
pattern[i] = mean(y[i + k*P]) for all valid k
```

## 6. Statistical Methods

### Elasticity

```python
# Point elasticity
ε = (∂y/∂x) * (x/y)

# Arc elasticity (discrete approximation)
ε = (Δy/y) / (Δx/x) = (%Δy) / (%Δx)

# Local linear approximation
ε = β * (x̄/ȳ)
where β is regression slope
```

### Mutual Information

```python
# Discrete approximation (k-NN estimator)
I(X;Y) = ψ(k) + ψ(n) - <ψ(n_x + 1) + ψ(n_y + 1)>

# Where:
# ψ is digamma function
# n_x, n_y are number of neighbors in marginal spaces
# <·> denotes averaging over all points
```

### Bootstrap Confidence Intervals

```python
# Bootstrap sampling
X_boot = sample_with_replacement(X, size=n)
θ_boot = statistic(X_boot)

# Percentile method
CI = [percentile(θ_boot, α/2), percentile(θ_boot, 1-α/2)]

# For correlation (Fisher's z-transform)
z = arctanh(r)
SE_z = 1/√(n-3)
CI_z = z ± z_{α/2} * SE_z
CI_r = [tanh(CI_z_lower), tanh(CI_z_upper)]
```

## 7. Multi-Level Sensitivity

### Building to Zone Aggregation

```python
# Weighted aggregation
S_building = Σ(w_i * S_zone_i)

# Weights by area
w_i = Area_i / Σ(Area_j)

# Weights by volume  
w_i = Volume_i / Σ(Volume_j)

# Equal weights
w_i = 1/n_zones
```

### Cross-Level Elasticity

```python
# Zone modifications → Building outputs
ε_cross = (%ΔY_building) / (%ΔX_zone_aggregate)

# Where zone aggregate change:
%ΔX_zone_aggregate = mean(%ΔX_i) for all zones i
```

These formulas represent the mathematical foundation of the sensitivity analysis framework, enabling quantitative assessment of parameter importance, uncertainty bounds, and complex relationships in building energy models.





# appendix


Let me explain this paragraph in simple terms:

## The Problem: Theory vs Reality in Building Changes

Imagine you're trying to improve your home's energy efficiency. Here's the disconnect:

**Theoretical Approach** (what traditional analysis does):

* "Your walls could have insulation from R-1 to R-100"
* "Your windows could be anything from single-pane to quintuple-pane"
* "Your AC could range from 50% to 200% efficiency"

It tests EVERYTHING that's physically possible.

**Reality** (what actually happens):

* Your walls are already built - you can maybe add R-10 more insulation in the attic
* You can realistically upgrade from double to triple-pane windows (not quintuple)
* Your AC can be upgraded from 80% to 95% efficiency (not 200%)

## Why This Matters

Traditional analysis might tell you: "If you had R-100 insulation, you'd save 90% on heating!"

But that's like saying: "If you could run 100 mph, you'd win every marathon!"

It's technically true but completely useless because:

* R-100 insulation doesn't fit in normal walls
* It costs more than your house
* No contractor knows how to install it

## The New Approach

Instead of testing impossible scenarios, the modification-based method looks at:

* What changes people ACTUALLY make
* What's available in the market
* What fits in existing buildings
* What people can afford

So instead of "R-1 to R-100", it tests "R-13 to R-21" because that's what real retrofits do.

 **In simple terms** : It's the difference between a diet plan that says "just eat 500 calories a day" (theoretically works but impossible to sustain) versus one that says "replace soda with water and take the stairs" (actually doable).

This makes the analysis results more useful because they tell you about changes you can actually implement, not fantasy scenarios.
