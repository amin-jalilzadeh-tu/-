"""
Efficiency Rules - Define rules for improving building efficiency
"""
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
import json

@dataclass
class EfficiencyRule:
    """Defines an efficiency improvement rule"""
    name: str
    description: str
    category: str
    target_parameter: str
    modification_type: str  # 'multiplier', 'absolute', 'percentage'
    modification_value: Any
    conditions: Dict[str, Any] = field(default_factory=dict)
    expected_impact: Dict[str, float] = field(default_factory=dict)
    cost_level: str = 'medium'  # 'low', 'medium', 'high'
    applicability: List[str] = field(default_factory=list)

class EfficiencyRuleEngine:
    """Engine for applying efficiency improvement rules"""
    
    def __init__(self):
        """Initialize rule engine with predefined rules"""
        self.rules: Dict[str, EfficiencyRule] = {}
        self._initialize_rules()
    
    def _initialize_rules(self):
        """Initialize default efficiency rules"""
        
        # HVAC Efficiency Rules
        self.add_rule(EfficiencyRule(
            name='high_efficiency_cooling',
            description='Upgrade to high efficiency cooling equipment',
            category='hvac',
            target_parameter='cooling_cop',
            modification_type='multiplier',
            modification_value=1.4,
            conditions={'current_cop': {'max': 3.5}},
            expected_impact={'cooling_energy': -25},
            cost_level='high',
            applicability=['all_buildings']
        ))
        
        self.add_rule(EfficiencyRule(
            name='premium_efficiency_motors',
            description='Upgrade to premium efficiency fan motors',
            category='hvac',
            target_parameter='fan_efficiency',
            modification_type='absolute',
            modification_value=0.9,
            conditions={'current_efficiency': {'max': 0.7}},
            expected_impact={'fan_energy': -20},
            cost_level='medium',
            applicability=['commercial', 'institutional']
        ))
        
        # Envelope Rules
        self.add_rule(EfficiencyRule(
            name='super_insulation_walls',
            description='Add super insulation to walls',
            category='materials',
            target_parameter='wall_r_value',
            modification_type='multiplier',
            modification_value=2.0,
            conditions={'climate_zone': ['4', '5', '6', '7', '8']},
            expected_impact={'heating_energy': -20, 'cooling_energy': -10},
            cost_level='high',
            applicability=['residential', 'small_commercial']
        ))
        
        self.add_rule(EfficiencyRule(
            name='cool_roof',
            description='Install cool roof with high reflectance',
            category='materials',
            target_parameter='roof_solar_absorptance',
            modification_type='absolute',
            modification_value=0.2,
            conditions={'climate_zone': ['1', '2', '3']},
            expected_impact={'cooling_energy': -15},
            cost_level='medium',
            applicability=['all_buildings']
        ))
        
        self.add_rule(EfficiencyRule(
            name='triple_pane_windows',
            description='Upgrade to triple pane windows',
            category='materials',
            target_parameter='window_u_factor',
            modification_type='multiplier',
            modification_value=0.4,
            conditions={'climate_zone': ['5', '6', '7', '8']},
            expected_impact={'heating_energy': -15, 'cooling_energy': -5},
            cost_level='high',
            applicability=['residential', 'office']
        ))
        
        # Lighting Rules
        self.add_rule(EfficiencyRule(
            name='led_retrofit',
            description='Complete LED lighting retrofit',
            category='lighting',
            target_parameter='lighting_power_density',
            modification_type='multiplier',
            modification_value=0.4,
            conditions={'current_lpd': {'min': 10}},
            expected_impact={'lighting_energy': -60},
            cost_level='medium',
            applicability=['all_buildings']
        ))
        
        self.add_rule(EfficiencyRule(
            name='task_ambient_lighting',
            description='Implement task-ambient lighting strategy',
            category='lighting',
            target_parameter='lighting_power_density',
            modification_type='multiplier',
            modification_value=0.7,
            conditions={'space_type': ['office', 'classroom']},
            expected_impact={'lighting_energy': -30},
            cost_level='low',
            applicability=['office', 'educational']
        ))
        
        # Equipment Rules
        self.add_rule(EfficiencyRule(
            name='energy_star_equipment',
            description='Upgrade to Energy Star rated equipment',
            category='equipment',
            target_parameter='equipment_power_density',
            modification_type='multiplier',
            modification_value=0.75,
            conditions={'equipment_age': {'min': 10}},
            expected_impact={'plug_loads': -25},
            cost_level='medium',
            applicability=['office', 'institutional']
        ))
        
        # Infiltration Rules
        self.add_rule(EfficiencyRule(
            name='air_sealing_retrofit',
            description='Comprehensive air sealing retrofit',
            category='infiltration',
            target_parameter='infiltration_rate',
            modification_type='multiplier',
            modification_value=0.3,
            conditions={'building_age': {'min': 20}},
            expected_impact={'heating_energy': -10, 'cooling_energy': -5},
            cost_level='low',
            applicability=['all_buildings']
        ))
        
        # Ventilation Rules
        self.add_rule(EfficiencyRule(
            name='demand_controlled_ventilation',
            description='Implement CO2-based demand controlled ventilation',
            category='ventilation',
            target_parameter='outdoor_air_flow',
            modification_type='multiplier',
            modification_value=0.6,
            conditions={'occupancy_type': 'variable'},
            expected_impact={'ventilation_energy': -30},
            cost_level='medium',
            applicability=['office', 'educational', 'assembly']
        ))
        
        self.add_rule(EfficiencyRule(
            name='energy_recovery_ventilation',
            description='Add energy recovery to ventilation system',
            category='ventilation',
            target_parameter='heat_recovery_effectiveness',
            modification_type='absolute',
            modification_value=0.75,
            conditions={'outdoor_air_flow': {'min': 0.5}},
            expected_impact={'ventilation_energy': -50},
            cost_level='high',
            applicability=['all_buildings']
        ))
    
    def add_rule(self, rule: EfficiencyRule):
        """Add a rule to the engine"""
        self.rules[rule.name] = rule
    
    def get_applicable_rules(self, 
                           building_characteristics: Dict[str, Any],
                           categories: Optional[List[str]] = None,
                           cost_levels: Optional[List[str]] = None) -> List[EfficiencyRule]:
        """
        Get rules applicable to a building
        
        Args:
            building_characteristics: Building properties
            categories: Filter by categories
            cost_levels: Filter by cost levels
            
        Returns:
            List of applicable rules
        """
        applicable_rules = []
        
        for rule in self.rules.values():
            # Category filter
            if categories and rule.category not in categories:
                continue
            
            # Cost level filter
            if cost_levels and rule.cost_level not in cost_levels:
                continue
            
            # Check applicability
            building_type = building_characteristics.get('building_type', 'all_buildings')
            if 'all_buildings' not in rule.applicability and building_type not in rule.applicability:
                continue
            
            # Check conditions
            if self._check_conditions(rule.conditions, building_characteristics):
                applicable_rules.append(rule)
        
        return applicable_rules
    
    def _check_conditions(self, 
                         conditions: Dict[str, Any], 
                         characteristics: Dict[str, Any]) -> bool:
        """Check if conditions are met"""
        for key, condition in conditions.items():
            if key not in characteristics:
                continue
            
            value = characteristics[key]
            
            if isinstance(condition, dict):
                # Range conditions
                if 'min' in condition and value < condition['min']:
                    return False
                if 'max' in condition and value > condition['max']:
                    return False
            elif isinstance(condition, list):
                # Value must be in list
                if value not in condition:
                    return False
            else:
                # Direct comparison
                if value != condition:
                    return False
        
        return True
    
    def rank_rules_by_impact(self, 
                           rules: List[EfficiencyRule],
                           impact_weights: Optional[Dict[str, float]] = None) -> List[Tuple[EfficiencyRule, float]]:
        """
        Rank rules by expected impact
        
        Args:
            rules: List of rules to rank
            impact_weights: Weights for different impact types
            
        Returns:
            List of (rule, score) tuples sorted by score
        """
        if not impact_weights:
            impact_weights = {
                'heating_energy': 1.0,
                'cooling_energy': 1.0,
                'lighting_energy': 1.0,
                'plug_loads': 0.8,
                'fan_energy': 0.6,
                'ventilation_energy': 0.6
            }
        
        rule_scores = []
        
        for rule in rules:
            score = 0
            for impact_type, reduction in rule.expected_impact.items():
                weight = impact_weights.get(impact_type, 0.5)
                # Negative reduction means savings
                score += abs(reduction) * weight
            
            rule_scores.append((rule, score))
        
        # Sort by score (highest first)
        rule_scores.sort(key=lambda x: x[1], reverse=True)
        
        return rule_scores
    
    def create_efficiency_package(self,
                                building_characteristics: Dict[str, Any],
                                target_reduction: float = 30,
                                budget_level: str = 'medium') -> List[EfficiencyRule]:
        """
        Create a package of efficiency measures
        
        Args:
            building_characteristics: Building properties
            target_reduction: Target energy reduction percentage
            budget_level: Budget constraint
            
        Returns:
            List of selected rules
        """
        # Get applicable rules
        cost_levels = {'low': ['low'], 
                      'medium': ['low', 'medium'], 
                      'high': ['low', 'medium', 'high']}
        
        applicable_rules = self.get_applicable_rules(
            building_characteristics,
            cost_levels=cost_levels[budget_level]
        )
        
        # Rank by impact
        ranked_rules = self.rank_rules_by_impact(applicable_rules)
        
        # Select rules to meet target
        selected_rules = []
        total_reduction = 0
        
        for rule, score in ranked_rules:
            # Estimate total reduction (simplified)
            rule_reduction = sum(abs(r) for r in rule.expected_impact.values()) / len(rule.expected_impact)
            
            if total_reduction < target_reduction:
                selected_rules.append(rule)
                total_reduction += rule_reduction * 0.7  # Assume some overlap
            else:
                break
        
        return selected_rules
    
    def get_rule_dependencies(self, rule: EfficiencyRule) -> List[str]:
        """Get dependencies for a rule"""
        # Define rule dependencies
        dependencies = {
            'demand_controlled_ventilation': ['co2_sensors'],
            'energy_recovery_ventilation': ['balanced_ventilation'],
            'task_ambient_lighting': ['lighting_controls'],
            'cool_roof': ['roof_replacement_scheduled']
        }
        
        return dependencies.get(rule.name, [])
    
    def validate_rule_combination(self, rules: List[EfficiencyRule]) -> Tuple[bool, List[str]]:
        """
        Validate if rules can be applied together
        
        Returns:
            Tuple of (is_valid, conflict_messages)
        """
        conflicts = []
        
        # Check for parameter conflicts
        parameter_rules = {}
        for rule in rules:
            if rule.target_parameter in parameter_rules:
                conflicts.append(
                    f"Conflict: Both '{rule.name}' and '{parameter_rules[rule.target_parameter]}' "
                    f"modify {rule.target_parameter}"
                )
            parameter_rules[rule.target_parameter] = rule.name
        
        # Check for logical conflicts
        rule_names = [r.name for r in rules]
        
        # Example conflicts
        if 'natural_ventilation' in rule_names and 'energy_recovery_ventilation' in rule_names:
            conflicts.append("Natural ventilation conflicts with mechanical energy recovery")
        
        return len(conflicts) == 0, conflicts
    
    def estimate_combined_impact(self, rules: List[EfficiencyRule]) -> Dict[str, float]:
        """Estimate combined impact of multiple rules"""
        combined_impact = {}
        
        # Simple combination with diminishing returns
        for rule in rules:
            for impact_type, reduction in rule.expected_impact.items():
                if impact_type not in combined_impact:
                    combined_impact[impact_type] = 0
                
                # Apply with diminishing returns factor
                current = combined_impact[impact_type]
                # Each additional measure has 80% effectiveness
                combined_impact[impact_type] = current + reduction * (0.8 ** len([r for r in rules[:rules.index(rule)] 
                                                                                  if impact_type in r.expected_impact]))
        
        return combined_impact
    
    def export_rules(self, output_path: str):
        """Export rules to JSON"""
        rules_data = {}
        for name, rule in self.rules.items():
            rules_data[name] = {
                'description': rule.description,
                'category': rule.category,
                'target_parameter': rule.target_parameter,
                'modification_type': rule.modification_type,
                'modification_value': rule.modification_value,
                'conditions': rule.conditions,
                'expected_impact': rule.expected_impact,
                'cost_level': rule.cost_level,
                'applicability': rule.applicability
            }
        
        with open(output_path, 'w') as f:
            json.dump(rules_data, f, indent=2)