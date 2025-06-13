"""
calibration_algorithms.py

Advanced optimization algorithms for calibration:
- Particle Swarm Optimization (PSO)
- Differential Evolution (DE)
- NSGA-II (Multi-objective GA)
- CMA-ES (Covariance Matrix Adaptation Evolution Strategy)
- Hybrid/Adaptive algorithms

Author: Your Team
"""

import numpy as np
import random
from typing import List, Dict, Tuple, Callable, Optional, Any
import logging
from dataclasses import dataclass
import copy

logger = logging.getLogger(__name__)

# Try importing optional optimization libraries
try:
    from pymoo.algorithms.moo.nsga2 import NSGA2
    from pymoo.core.problem import Problem
    from pymoo.optimize import minimize
    from pymoo.operators.crossover.sbx import SBX
    from pymoo.operators.mutation.pm import PM
    from pymoo.operators.sampling.rnd import FloatRandomSampling
    HAVE_PYMOO = True
except ImportError:
    HAVE_PYMOO = False
    logger.info("pymoo not available for NSGA-II")

try:
    import cma
    HAVE_CMA = True
except ImportError:
    HAVE_CMA = False
    logger.info("cma not available for CMA-ES")


@dataclass
class OptimizationResult:
    """Container for optimization results"""
    best_params: Dict[str, float]
    best_objective: float
    history: List[Tuple[Dict[str, float], float]]
    convergence_data: Dict[str, List[float]] = None
    pareto_front: List[Tuple[Dict[str, float], List[float]]] = None


class ParticleSwarmOptimizer:
    """Particle Swarm Optimization implementation"""
    
    def __init__(self,
                 n_particles: int = 30,
                 max_iter: int = 100,
                 inertia: float = 0.9,
                 cognitive: float = 2.0,
                 social: float = 2.0,
                 inertia_decay: float = 0.99,
                 velocity_clamp: float = 0.2):
        """
        Args:
            n_particles: Number of particles in swarm
            max_iter: Maximum iterations
            inertia: Inertia weight
            cognitive: Cognitive parameter (particle best attraction)
            social: Social parameter (global best attraction)
            inertia_decay: Decay factor for inertia per iteration
            velocity_clamp: Maximum velocity as fraction of parameter range
        """
        self.n_particles = n_particles
        self.max_iter = max_iter
        self.inertia = inertia
        self.cognitive = cognitive
        self.social = social
        self.inertia_decay = inertia_decay
        self.velocity_clamp = velocity_clamp
        
    def optimize(self,
                objective_func: Callable,
                param_specs: List['ParamSpec'],
                verbose: bool = True) -> OptimizationResult:
        """
        Run PSO optimization
        
        Args:
            objective_func: Function to minimize
            param_specs: Parameter specifications
            verbose: Print progress
            
        Returns:
            OptimizationResult
        """
        n_dims = len(param_specs)
        
        # Initialize particles
        positions = np.zeros((self.n_particles, n_dims))
        velocities = np.zeros((self.n_particles, n_dims))
        pbest_positions = np.zeros((self.n_particles, n_dims))
        pbest_scores = np.full(self.n_particles, float('inf'))
        
        # Global best
        gbest_position = np.zeros(n_dims)
        gbest_score = float('inf')
        
        # Initialize positions and velocities
        for i in range(self.n_particles):
            for j, spec in enumerate(param_specs):
                positions[i, j] = spec.sample_random()
                
                # Initialize velocity as small fraction of range
                param_range = spec.max_value - spec.min_value
                
                # Add bounds checking to prevent overflow
                if param_range > 1e10:  # Arbitrary large threshold
                    logger.warning(f"Parameter {spec.name} has extremely large range: {param_range}")
                    param_range = 1e10  # Cap the range
                
                v_max = param_range * self.velocity_clamp
                
                # Additional safety check
                v_max = min(v_max, 1e8)  # Ensure v_max doesn't exceed numpy limits
                
                if v_max > 0:
                    velocities[i, j] = np.random.uniform(-v_max, v_max)
                else:
                    velocities[i, j] = 0.0
        
        # History tracking
        history = []
        convergence_data = {
            'gbest_score': [],
            'mean_score': [],
            'diversity': []
        }
        
        # PSO iterations
        current_inertia = self.inertia
        
        for iteration in range(self.max_iter):
            scores = np.zeros(self.n_particles)
            
            # Evaluate all particles
            for i in range(self.n_particles):
                # Convert position to param dict
                param_dict = {}
                for j, spec in enumerate(param_specs):
                    val = positions[i, j]
                    # Clamp to bounds
                    val = np.clip(val, spec.min_value, spec.max_value)
                    if spec.is_integer:
                        val = int(round(val))
                    param_dict[spec.name] = val
                
                # Evaluate
                score = objective_func(param_dict)
                scores[i] = score
                history.append((param_dict.copy(), score))
                
                # Update personal best
                if score < pbest_scores[i]:
                    pbest_scores[i] = score
                    pbest_positions[i] = positions[i].copy()
                
                # Update global best
                if score < gbest_score:
                    gbest_score = score
                    gbest_position = positions[i].copy()
            
            # Update velocities and positions
            for i in range(self.n_particles):
                for j in range(n_dims):
                    # Velocity update equation
                    r1, r2 = np.random.random(), np.random.random()
                    
                    velocities[i, j] = (
                        current_inertia * velocities[i, j] +
                        self.cognitive * r1 * (pbest_positions[i, j] - positions[i, j]) +
                        self.social * r2 * (gbest_position[j] - positions[i, j])
                    )
                    
                    # Clamp velocity
                    v_max = (param_specs[j].max_value - param_specs[j].min_value) * self.velocity_clamp
                    velocities[i, j] = np.clip(velocities[i, j], -v_max, v_max)
                    
                    # Position update
                    positions[i, j] += velocities[i, j]
            
            # Update inertia
            current_inertia *= self.inertia_decay
            
            # Track convergence
            convergence_data['gbest_score'].append(gbest_score)
            convergence_data['mean_score'].append(np.mean(scores))
            
            # Calculate diversity (standard deviation of positions)
            diversity = np.mean(np.std(positions, axis=0))
            convergence_data['diversity'].append(diversity)
            
            if verbose and iteration % 10 == 0:
                logger.info(f"[PSO] Iteration {iteration}: best={gbest_score:.6f}, "
                          f"mean={np.mean(scores):.6f}, diversity={diversity:.6f}")
        
        # Convert best position to param dict
        best_params = {}
        for j, spec in enumerate(param_specs):
            val = gbest_position[j]
            val = np.clip(val, spec.min_value, spec.max_value)
            if spec.is_integer:
                val = int(round(val))
            best_params[spec.name] = val
        
        return OptimizationResult(
            best_params=best_params,
            best_objective=gbest_score,
            history=history,
            convergence_data=convergence_data
        )


class DifferentialEvolution:
    """Differential Evolution optimization"""
    
    def __init__(self,
                 pop_size: int = 50,
                 max_iter: int = 100,
                 mutation_factor: float = 0.8,
                 crossover_prob: float = 0.7,
                 strategy: str = "best1bin",
                 adaptive: bool = True):
        """
        Args:
            pop_size: Population size
            max_iter: Maximum iterations
            mutation_factor: Mutation factor F
            crossover_prob: Crossover probability CR
            strategy: DE strategy ('best1bin', 'rand1bin', 'rand2bin', 'best2bin')
            adaptive: Use adaptive F and CR
        """
        self.pop_size = pop_size
        self.max_iter = max_iter
        self.mutation_factor = mutation_factor
        self.crossover_prob = crossover_prob
        self.strategy = strategy
        self.adaptive = adaptive
        
    def optimize(self,
                objective_func: Callable,
                param_specs: List['ParamSpec'],
                verbose: bool = True) -> OptimizationResult:
        """Run DE optimization"""
        n_dims = len(param_specs)
        
        # Initialize population
        population = np.zeros((self.pop_size, n_dims))
        fitness = np.full(self.pop_size, float('inf'))
        
        for i in range(self.pop_size):
            for j, spec in enumerate(param_specs):
                population[i, j] = spec.sample_random()
        
        # Evaluate initial population
        for i in range(self.pop_size):
            param_dict = self._array_to_dict(population[i], param_specs)
            fitness[i] = objective_func(param_dict)
        
        best_idx = np.argmin(fitness)
        best_individual = population[best_idx].copy()
        best_fitness = fitness[best_idx]
        
        history = []
        convergence_data = {
            'best_fitness': [],
            'mean_fitness': [],
            'std_fitness': []
        }
        
        # Adaptive parameters
        if self.adaptive:
            F_values = np.full(self.pop_size, self.mutation_factor)
            CR_values = np.full(self.pop_size, self.crossover_prob)
        
        # DE iterations
        for generation in range(self.max_iter):
            new_population = population.copy()
            new_fitness = fitness.copy()
            
            for i in range(self.pop_size):
                # Mutation
                if self.strategy == "best1bin":
                    # DE/best/1/bin
                    r1, r2 = self._select_random_indices(i, self.pop_size, 2)
                    mutant = best_individual + self.mutation_factor * (population[r1] - population[r2])
                elif self.strategy == "rand1bin":
                    # DE/rand/1/bin
                    r1, r2, r3 = self._select_random_indices(i, self.pop_size, 3)
                    mutant = population[r1] + self.mutation_factor * (population[r2] - population[r3])
                elif self.strategy == "rand2bin":
                    # DE/rand/2/bin
                    r1, r2, r3, r4, r5 = self._select_random_indices(i, self.pop_size, 5)
                    mutant = population[r1] + self.mutation_factor * (
                        (population[r2] - population[r3]) + (population[r4] - population[r5])
                    )
                elif self.strategy == "best2bin":
                    # DE/best/2/bin
                    r1, r2, r3, r4 = self._select_random_indices(i, self.pop_size, 4)
                    mutant = best_individual + self.mutation_factor * (
                        (population[r1] - population[r2]) + (population[r3] - population[r4])
                    )
                else:
                    raise ValueError(f"Unknown strategy: {self.strategy}")
                
                # Adaptive mutation factor
                if self.adaptive:
                    F = F_values[i]
                    mutant = best_individual + F * (population[r1] - population[r2])
                
                # Crossover
                trial = population[i].copy()
                CR = CR_values[i] if self.adaptive else self.crossover_prob
                
                # Binomial crossover
                j_rand = np.random.randint(n_dims)
                for j in range(n_dims):
                    if np.random.random() < CR or j == j_rand:
                        trial[j] = mutant[j]
                
                # Boundary constraints
                for j, spec in enumerate(param_specs):
                    trial[j] = np.clip(trial[j], spec.min_value, spec.max_value)
                
                # Selection
                param_dict = self._array_to_dict(trial, param_specs)
                trial_fitness = objective_func(param_dict)
                history.append((param_dict.copy(), trial_fitness))
                
                if trial_fitness < fitness[i]:
                    new_population[i] = trial
                    new_fitness[i] = trial_fitness
                    
                    # Update best
                    if trial_fitness < best_fitness:
                        best_fitness = trial_fitness
                        best_individual = trial.copy()
                    
                    # Adaptive parameter update (successful)
                    if self.adaptive:
                        # Simple adaptation: increase F and CR slightly
                        F_values[i] = min(1.0, F_values[i] * 1.1)
                        CR_values[i] = min(1.0, CR_values[i] * 1.1)
                else:
                    # Adaptive parameter update (unsuccessful)
                    if self.adaptive:
                        # Decrease F and CR slightly
                        F_values[i] = max(0.1, F_values[i] * 0.9)
                        CR_values[i] = max(0.1, CR_values[i] * 0.9)
            
            population = new_population
            fitness = new_fitness
            
            # Update convergence data
            convergence_data['best_fitness'].append(best_fitness)
            convergence_data['mean_fitness'].append(np.mean(fitness))
            convergence_data['std_fitness'].append(np.std(fitness))
            
            if verbose and generation % 10 == 0:
                logger.info(f"[DE] Generation {generation}: best={best_fitness:.6f}, "
                          f"mean={np.mean(fitness):.6f}, std={np.std(fitness):.6f}")
        
        # Convert best to param dict
        best_params = self._array_to_dict(best_individual, param_specs)
        
        return OptimizationResult(
            best_params=best_params,
            best_objective=best_fitness,
            history=history,
            convergence_data=convergence_data
        )
    
    def _array_to_dict(self, array: np.ndarray, param_specs: List['ParamSpec']) -> Dict[str, float]:
        """Convert numpy array to parameter dictionary"""
        param_dict = {}
        for j, spec in enumerate(param_specs):
            val = array[j]
            if spec.is_integer:
                val = int(round(val))
            param_dict[spec.name] = val
        return param_dict
    
    def _select_random_indices(self, exclude: int, pop_size: int, n: int) -> List[int]:
        """Select n random indices excluding the given index"""
        indices = list(range(pop_size))
        indices.remove(exclude)
        return random.sample(indices, n)


class NSGA2Optimizer:
    """NSGA-II for multi-objective optimization"""
    
    def __init__(self,
                 pop_size: int = 100,
                 n_generations: int = 100,
                 crossover_prob: float = 0.9,
                 mutation_prob: float = None,
                 eta_crossover: float = 15,
                 eta_mutation: float = 20):
        """
        Args:
            pop_size: Population size
            n_generations: Number of generations
            crossover_prob: Crossover probability
            mutation_prob: Mutation probability (auto-calculated if None)
            eta_crossover: Distribution index for crossover
            eta_mutation: Distribution index for mutation
        """
        self.pop_size = pop_size
        self.n_generations = n_generations
        self.crossover_prob = crossover_prob
        self.mutation_prob = mutation_prob
        self.eta_crossover = eta_crossover
        self.eta_mutation = eta_mutation
        
    def optimize(self,
                multi_objective_func: Callable,
                param_specs: List['ParamSpec'],
                n_objectives: int,
                verbose: bool = True) -> OptimizationResult:
        """
        Run NSGA-II optimization
        
        Args:
            multi_objective_func: Function returning list of objectives
            param_specs: Parameter specifications
            n_objectives: Number of objectives
            verbose: Print progress
            
        Returns:
            OptimizationResult with pareto_front
        """
        if not HAVE_PYMOO:
            raise ImportError("pymoo is required for NSGA-II. Install with: pip install pymoo")
        
        # Create pymoo problem
        class CalibrationProblem(Problem):
            def __init__(self):
                n_vars = len(param_specs)
                xl = np.array([spec.min_value for spec in param_specs])
                xu = np.array([spec.max_value for spec in param_specs])
                
                super().__init__(
                    n_var=n_vars,
                    n_obj=n_objectives,
                    n_constr=0,
                    xl=xl,
                    xu=xu
                )
                self.param_specs = param_specs
                self.history = []
            
            def _evaluate(self, x, out, *args, **kwargs):
                # Evaluate population
                n_samples = x.shape[0]
                objectives = np.zeros((n_samples, self.n_obj))
                
                for i in range(n_samples):
                    # Convert to param dict
                    param_dict = {}
                    for j, spec in enumerate(self.param_specs):
                        val = x[i, j]
                        if spec.is_integer:
                            val = int(round(val))
                        param_dict[spec.name] = val
                    
                    # Evaluate objectives
                    obj_values = multi_objective_func(param_dict)
                    objectives[i] = obj_values
                    
                    # Store in history
                    self.history.append((param_dict.copy(), obj_values))
                
                out["F"] = objectives
        
        # Create problem instance
        problem = CalibrationProblem()
        
        # Configure algorithm
        algorithm = NSGA2(
            pop_size=self.pop_size,
            sampling=FloatRandomSampling(),
            crossover=SBX(prob=self.crossover_prob, eta=self.eta_crossover),
            mutation=PM(prob=self.mutation_prob, eta=self.eta_mutation),
            eliminate_duplicates=True
        )
        
        # Run optimization
        res = minimize(
            problem,
            algorithm,
            ('n_gen', self.n_generations),
            verbose=verbose,
            save_history=True
        )
        
        # Extract pareto front
        pareto_front = []
        for i in range(len(res.X)):
            param_dict = {}
            for j, spec in enumerate(param_specs):
                val = res.X[i, j]
                if spec.is_integer:
                    val = int(round(val))
                param_dict[spec.name] = val
            
            objectives = res.F[i].tolist()
            pareto_front.append((param_dict, objectives))
        
        # Find best compromise solution (closest to ideal point)
        ideal_point = np.min(res.F, axis=0)
        distances = np.linalg.norm(res.F - ideal_point, axis=1)
        best_idx = np.argmin(distances)
        
        best_params = {}
        for j, spec in enumerate(param_specs):
            val = res.X[best_idx, j]
            if spec.is_integer:
                val = int(round(val))
            best_params[spec.name] = val
        
        # Convergence data
        convergence_data = {
            'n_pareto': [len(hist.opt.get("F")) for hist in res.history],
            'hypervolume': []  # Could calculate if reference point is known
        }
        
        return OptimizationResult(
            best_params=best_params,
            best_objective=distances[best_idx],
            history=problem.history,
            convergence_data=convergence_data,
            pareto_front=pareto_front
        )


class CMAESOptimizer:
    """CMA-ES (Covariance Matrix Adaptation Evolution Strategy)"""
    
    def __init__(self,
                 sigma0: float = 0.5,
                 popsize: Optional[int] = None,
                 max_iter: int = 100):
        """
        Args:
            sigma0: Initial standard deviation
            popsize: Population size (auto-calculated if None)
            max_iter: Maximum iterations
        """
        self.sigma0 = sigma0
        self.popsize = popsize
        self.max_iter = max_iter
        
    def optimize(self,
                objective_func: Callable,
                param_specs: List['ParamSpec'],
                verbose: bool = True) -> OptimizationResult:
        """Run CMA-ES optimization"""
        if not HAVE_CMA:
            raise ImportError("cma is required for CMA-ES. Install with: pip install cma")
        
        n_dims = len(param_specs)
        
        # Initial point (center of parameter space)
        x0 = [(spec.min_value + spec.max_value) / 2 for spec in param_specs]
        
        # Bounds
        bounds = [[spec.min_value for spec in param_specs],
                  [spec.max_value for spec in param_specs]]
        
        # History tracking
        history = []
        
        # Objective wrapper
        def cma_objective(x):
            param_dict = {}
            for i, spec in enumerate(param_specs):
                val = x[i]
                # Apply bounds
                val = np.clip(val, spec.min_value, spec.max_value)
                if spec.is_integer:
                    val = int(round(val))
                param_dict[spec.name] = val
            
            obj_val = objective_func(param_dict)
            history.append((param_dict.copy(), obj_val))
            return obj_val
        
        # Configure CMA-ES
        opts = {
            'bounds': bounds,
            'maxiter': self.max_iter,
            'verbose': -9 if not verbose else 1
        }
        if self.popsize:
            opts['popsize'] = self.popsize
        
        # Run optimization
        es = cma.CMAEvolutionStrategy(x0, self.sigma0, opts)
        es.optimize(cma_objective)
        
        # Get results
        best_x = es.result.xbest
        best_params = {}
        for i, spec in enumerate(param_specs):
            val = best_x[i]
            val = np.clip(val, spec.min_value, spec.max_value)
            if spec.is_integer:
                val = int(round(val))
            best_params[spec.name] = val
        
        convergence_data = {
            'sigma': es.logger.data['sigma'],
            'fitness': es.logger.data['fit']
        }
        
        return OptimizationResult(
            best_params=best_params,
            best_objective=es.result.fbest,
            history=history,
            convergence_data=convergence_data
        )


class HybridOptimizer:
    """Hybrid optimization combining multiple algorithms"""
    
    def __init__(self, stages: List[Dict[str, Any]]):
        """
        Args:
            stages: List of optimization stages, each with:
                - 'algorithm': 'pso', 'de', 'cmaes', etc.
                - 'iterations': Number of iterations for this stage
                - 'bounds_multiplier': Multiplier for parameter bounds
                - Additional algorithm-specific parameters
        """
        self.stages = stages
        
    def optimize(self,
                objective_func: Callable,
                param_specs: List['ParamSpec'],
                verbose: bool = True) -> OptimizationResult:
        """Run hybrid optimization"""
        best_params = None
        best_objective = float('inf')
        all_history = []
        stage_results = []
        
        # Working parameter specs (may be modified between stages)
        current_specs = copy.deepcopy(param_specs)
        
        for stage_idx, stage in enumerate(self.stages):
            logger.info(f"\n[Hybrid] Starting stage {stage_idx + 1}/{len(self.stages)}: "
                       f"{stage['algorithm']}")
            
            # Adjust bounds if specified
            if 'bounds_multiplier' in stage and best_params is not None:
                mult = stage['bounds_multiplier']
                for spec in current_specs:
                    if spec.name in best_params:
                        center = best_params[spec.name]
                        range_val = spec.max_value - spec.min_value
                        new_range = range_val * mult
                        spec.min_value = max(spec.min_value, center - new_range / 2)
                        spec.max_value = min(spec.max_value, center + new_range / 2)
            
            # Select and configure algorithm
            algorithm = stage['algorithm'].lower()
            
            if algorithm == 'pso':
                opt = ParticleSwarmOptimizer(
                    n_particles=stage.get('n_particles', 30),
                    max_iter=stage.get('iterations', 50),
                    inertia=stage.get('inertia', 0.9),
                    cognitive=stage.get('cognitive', 2.0),
                    social=stage.get('social', 2.0)
                )
            elif algorithm == 'de':
                opt = DifferentialEvolution(
                    pop_size=stage.get('pop_size', 50),
                    max_iter=stage.get('iterations', 50),
                    mutation_factor=stage.get('mutation_factor', 0.8),
                    crossover_prob=stage.get('crossover_prob', 0.7),
                    strategy=stage.get('strategy', 'best1bin')
                )
            elif algorithm == 'cmaes':
                opt = CMAESOptimizer(
                    sigma0=stage.get('sigma0', 0.5),
                    popsize=stage.get('popsize'),
                    max_iter=stage.get('iterations', 50)
                )
            else:
                raise ValueError(f"Unknown algorithm: {algorithm}")
            
            # Run optimization for this stage
            result = opt.optimize(objective_func, current_specs, verbose=verbose)
            
            # Update best if improved
            if result.best_objective < best_objective:
                best_objective = result.best_objective
                best_params = result.best_params
            
            # Collect history
            all_history.extend(result.history)
            stage_results.append({
                'stage': stage_idx,
                'algorithm': algorithm,
                'result': result
            })
            
            logger.info(f"[Hybrid] Stage {stage_idx + 1} complete. "
                       f"Best objective: {result.best_objective:.6f}")
        
        # Compile convergence data from all stages
        convergence_data = {
            'stage_results': stage_results,
            'stage_best_objectives': [r['result'].best_objective for r in stage_results]
        }
        
        return OptimizationResult(
            best_params=best_params,
            best_objective=best_objective,
            history=all_history,
            convergence_data=convergence_data
        )


def create_adaptive_optimizer(initial_algorithm: str = 'de',
                            switch_threshold: float = 0.01,
                            switch_patience: int = 20) -> HybridOptimizer:
    """
    Create an adaptive optimizer that switches algorithms based on convergence
    
    Args:
        initial_algorithm: Starting algorithm
        switch_threshold: Relative improvement threshold to trigger switch
        switch_patience: Iterations without improvement before switching
    """
    stages = [
        {
            'algorithm': initial_algorithm,
            'iterations': 50,
            'adaptive': True,
            'switch_threshold': switch_threshold,
            'switch_patience': switch_patience
        },
        {
            'algorithm': 'pso',
            'iterations': 30,
            'bounds_multiplier': 0.5
        },
        {
            'algorithm': 'cmaes',
            'iterations': 20,
            'bounds_multiplier': 0.2,
            'sigma0': 0.1
        }
    ]
    
    return HybridOptimizer(stages)