"""
Dependency Rules - Define parameter dependencies and constraints
"""
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, field

@dataclass
class DependencyRule:
    """Defines a dependency between parameters"""
    name: str
    description: str
    primary_parameter: str
    dependent_parameters: List[str]
    relationship_type: str  # 'requires', 'excludes', 'proportional', 'conditional'
    conditions: Dict[str, Any] = field(default_factory=dict)
    constraints: Dict[str, Any] = field(default_factory=dict)

class DependencyRuleEngine:
    """Engine for managing parameter dependencies"""
    
    def __init__(self):
        """Initialize dependency rule engine"""
        self.rules: Dict[str, DependencyRule] = {}
        self.parameter_graph: Dict[str, Set[str]] = {}
        self._initialize_rules()
        self._build_dependency_graph()
    
    def _initialize_rules(self):
        """Initialize default dependency rules"""
        
        # HVAC Dependencies
        self.add_rule(DependencyRule(
            name='cooling_capacity_airflow',
            description='Cooling capacity requires proportional airflow',
            primary_parameter='cooling_capacity',
            dependent_parameters=['supply_air_flow_rate'],
            relationship_type='proportional',
            constraints={
                'ratio_min': 0.00004,  # m3/s per W
                'ratio_max': 0.00006
            }
        ))
        
        self.add_rule(DependencyRule(
            name='heat_recovery_requires_balanced',
            description='Heat recovery requires balanced ventilation',
            primary_parameter='heat_recovery_effectiveness',
            dependent_parameters=['exhaust_air_flow', 'outdoor_air_flow'],
            relationship_type='requires',
            constraints={
                'balance_tolerance': 0.1  # 10% imbalance allowed
            }
        ))
        
        self.add_rule(DependencyRule(
            name='dcv_requires_sensors',
            description='DCV requires CO2 sensors',
            primary_parameter='demand_controlled_ventilation',
            dependent_parameters=['co2_sensor_control'],
            relationship_type='requires'
        ))
        
        # Envelope Dependencies
        self.add_rule(DependencyRule(
            name='window_frame_performance',
            description='Window frame must match glazing performance',
            primary_parameter='glazing_u_factor',
            dependent_parameters=['frame_u_factor'],
            relationship_type='proportional',
            constraints={
                'max_difference': 1.0  # W/m2-K
            }
        ))
        
        self.add_rule(DependencyRule(
            name='insulation_thickness_limit',
            description='Insulation thickness limited by cavity depth',
            primary_parameter='insulation_thickness',
            dependent_parameters=['wall_cavity_depth'],
            relationship_type='conditional',
            conditions={'construction_type': 'cavity_wall'},
            constraints={
                'max_fill_ratio': 0.95
            }
        ))
        
        # Lighting Dependencies
        self.add_rule(DependencyRule(
            name='dimming_requires_controls',
            description='Continuous dimming requires dimming ballasts',
            primary_parameter='continuous_dimming',
            dependent_parameters=['dimming_ballast_type'],
            relationship_type='requires'
        ))
        
        self.add_rule(DependencyRule(
            name='daylight_sensors_placement',
            description='Daylight sensors require proper placement',
            primary_parameter='daylight_dimming_control',
            dependent_parameters=['sensor_coverage_area', 'sensor_height'],
            relationship_type='requires',
            constraints={
                'max_coverage_area': 100,  # m2
                'max_sensor_height': 4  # m
            }
        ))
        
        # Shading Dependencies
        self.add_rule(DependencyRule(
            name='automated_shading_controls',
            description='Automated shading requires control system',
            primary_parameter='automated_blinds',
            dependent_parameters=['shading_control_type', 'shading_setpoint'],
            relationship_type='requires'
        ))
        
        # System Interactions
        self.add_rule(DependencyRule(
            name='natural_vent_excludes_tight_control',
            description='Natural ventilation excludes tight temperature control',
            primary_parameter='natural_ventilation',
            dependent_parameters=['temperature_deadband'],
            relationship_type='excludes',
            conditions={'temperature_deadband': {'max': 2.0}}
        ))
        
        self.add_rule(DependencyRule(
            name='radiant_response_time',
            description='Radiant systems require adjusted control',
            primary_parameter='radiant_heating_cooling',
            dependent_parameters=['control_throttling_range', 'control_time_step'],
            relationship_type='conditional',
            constraints={
                'min_throttling_range': 2.0,
                'max_time_step': 15  # minutes
            }
        ))
    
    def add_rule(self, rule: DependencyRule):
        """Add a dependency rule"""
        self.rules[rule.name] = rule
    
    def _build_dependency_graph(self):
        """Build parameter dependency graph"""
        self.parameter_graph.clear()
        
        for rule in self.rules.values():
            primary = rule.primary_parameter
            
            if primary not in self.parameter_graph:
                self.parameter_graph[primary] = set()
            
            for dependent in rule.dependent_parameters:
                self.parameter_graph[primary].add(dependent)
    
    def get_dependencies(self, parameter: str) -> Set[str]:
        """Get all parameters that depend on the given parameter"""
        return self.parameter_graph.get(parameter, set())
    
    def get_all_dependencies(self, parameters: List[str]) -> Set[str]:
        """Get all dependencies for a list of parameters"""
        all_deps = set()
        
        for param in parameters:
            deps = self.get_dependencies(param)
            all_deps.update(deps)
            
            # Recursive dependencies
            for dep in deps:
                all_deps.update(self.get_all_dependencies([dep]))
        
        return all_deps
    
    def check_dependencies(self, 
                         modifications: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Check if all dependencies are satisfied
        
        Args:
            modifications: Dictionary of parameter modifications
            
        Returns:
            Tuple of (all_satisfied, list_of_violations)
        """
        violations = []
        
        for param, value in modifications.items():
            # Get rules where this is primary parameter
            relevant_rules = [r for r in self.rules.values() 
                            if r.primary_parameter == param]
            
            for rule in relevant_rules:
                if rule.relationship_type == 'requires':
                    # Check if all required parameters are present
                    for dep in rule.dependent_parameters:
                        if dep not in modifications:
                            violations.append(
                                f"{param} requires {dep} to be specified"
                            )
                
                elif rule.relationship_type == 'excludes':
                    # Check if excluded parameters are not present
                    for dep in rule.dependent_parameters:
                        if dep in modifications:
                            # Check exclusion conditions
                            if self._check_exclusion(rule, modifications[dep]):
                                violations.append(
                                    f"{param} excludes {dep} with value {modifications[dep]}"
                                )
        
        return len(violations) == 0, violations
    
    def _check_exclusion(self, rule: DependencyRule, value: Any) -> bool:
        """Check if exclusion condition is met"""
        if not rule.conditions:
            return True  # Always excluded
        
        for param, condition in rule.conditions.items():
            if isinstance(condition, dict):
                if 'max' in condition and value > condition['max']:
                    return True
                if 'min' in condition and value < condition['min']:
                    return True
        
        return False
    
    def apply_proportional_dependencies(self,
                                      modifications: Dict[str, Any]) -> Dict[str, Any]:
        """Apply proportional relationships between parameters"""
        updated_mods = modifications.copy()
        
        for param, value in modifications.items():
            relevant_rules = [r for r in self.rules.values() 
                            if r.primary_parameter == param and 
                            r.relationship_type == 'proportional']
            
            for rule in relevant_rules:
                for dep_param in rule.dependent_parameters:
                    if dep_param not in updated_mods:
                        # Calculate proportional value
                        if 'ratio_min' in rule.constraints:
                            ratio = rule.constraints['ratio_min']
                            updated_mods[dep_param] = value * ratio
        
        return updated_mods
    
    def validate_constraints(self,
                           modifications: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate parameter constraints
        
        Returns:
            Tuple of (all_valid, list_of_violations)
        """
        violations = []
        
        for rule in self.rules.values():
            if rule.primary_parameter in modifications:
                primary_value = modifications[rule.primary_parameter]
                
                # Check constraints with dependent parameters
                for dep_param in rule.dependent_parameters:
                    if dep_param in modifications:
                        dep_value = modifications[dep_param]
                        
                        # Validate based on relationship type
                        if rule.relationship_type == 'proportional':
                            if not self._validate_proportional(
                                primary_value, dep_value, rule.constraints
                            ):
                                violations.append(
                                    f"{rule.primary_parameter} and {dep_param} "
                                    f"violate proportional constraint"
                                )
                        
                        elif rule.relationship_type == 'conditional':
                            if not self._validate_conditional(
                                modifications, rule.conditions, rule.constraints
                            ):
                                violations.append(
                                    f"{rule.name}: conditional constraint violated"
                                )
        
        return len(violations) == 0, violations
    
    def _validate_proportional(self, 
                             primary: float, 
                             dependent: float,
                             constraints: Dict[str, Any]) -> bool:
        """Validate proportional relationship"""
        if primary == 0:
            return dependent == 0
        
        ratio = dependent / primary
        
        if 'ratio_min' in constraints and ratio < constraints['ratio_min']:
            return False
        if 'ratio_max' in constraints and ratio > constraints['ratio_max']:
            return False
        if 'max_difference' in constraints:
            if abs(primary - dependent) > constraints['max_difference']:
                return False
        
        return True
    
    def _validate_conditional(self,
                            modifications: Dict[str, Any],
                            conditions: Dict[str, Any],
                            constraints: Dict[str, Any]) -> bool:
        """Validate conditional constraints"""
        # Check if conditions are met
        for cond_param, cond_value in conditions.items():
            if cond_param in modifications:
                if modifications[cond_param] != cond_value:
                    return True  # Condition not met, no constraint
        
        # Apply constraints
        for const_param, const_value in constraints.items():
            if const_param in modifications:
                if isinstance(const_value, (int, float)):
                    if modifications[const_param] > const_value:
                        return False
        
        return True
    
    def get_modification_order(self, 
                             parameters: List[str]) -> List[str]:
        """
        Get order to apply modifications considering dependencies
        
        Uses topological sort
        """
        # Build adjacency list
        graph = {}
        in_degree = {}
        
        for param in parameters:
            graph[param] = []
            in_degree[param] = 0
        
        # Add edges based on dependencies
        for param in parameters:
            deps = self.get_dependencies(param)
            for dep in deps:
                if dep in parameters:
                    graph[param].append(dep)
                    in_degree[dep] += 1
        
        # Topological sort
        queue = [p for p in parameters if in_degree[p] == 0]
        order = []
        
        while queue:
            param = queue.pop(0)
            order.append(param)
            
            for neighbor in graph[param]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        
        # If not all parameters are in order, there's a cycle
        if len(order) != len(parameters):
            # Return original order as fallback
            return parameters
        
        return order
    
    def suggest_missing_parameters(self,
                                 modifications: Dict[str, Any]) -> Dict[str, Any]:
        """Suggest missing dependent parameters"""
        suggestions = {}
        
        for param in modifications:
            deps = self.get_dependencies(param)
            
            for dep in deps:
                if dep not in modifications and dep not in suggestions:
                    # Get rule for this dependency
                    relevant_rules = [r for r in self.rules.values()
                                    if r.primary_parameter == param and 
                                    dep in r.dependent_parameters]
                    
                    if relevant_rules:
                        rule = relevant_rules[0]
                        
                        # Suggest value based on relationship
                        if rule.relationship_type == 'proportional':
                            if 'ratio_min' in rule.constraints:
                                suggestions[dep] = {
                                    'suggested_value': modifications[param] * rule.constraints['ratio_min'],
                                    'reason': rule.description
                                }
                        elif rule.relationship_type == 'requires':
                            suggestions[dep] = {
                                'suggested_value': 'required',
                                'reason': rule.description
                            }
        
        return suggestions