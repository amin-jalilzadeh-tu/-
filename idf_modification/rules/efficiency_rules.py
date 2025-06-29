"""
Efficiency Rules - Updated with parser-compatible parameter names
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
        """Initialize default efficiency rules with parser-compatible parameter names"""
        
        # HVAC Efficiency Rules
        self.add_rule(EfficiencyRule(
            name='high_efficiency_cooling',
            description='Upgrade to high efficiency cooling equipment',
            category='hvac',
            target_parameter='cooling_cop',  # Matches HVACModifier parameter
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
            target_parameter='fan_efficiency',  # Matches HVACModifier parameter
            modification_type='absolute',
            modification_value=0.9,
            conditions={'current_efficiency': {'max': 0.7}},
            expected_impact={'fan_energy': -20},
            cost_level='medium',
            applicability=['commercial', 'institutional']
        ))
        
        self.add_rule(EfficiencyRule(
            name='high_efficiency_heating',
            description='Upgrade heating equipment efficiency',
            category='hvac',
            target_parameter='heating_efficiency',  # Matches HVACModifier parameter
            modification_type='absolute',
            modification_value=0.95,
            conditions={'current_efficiency': {'max': 0.8}},
            expected_impact={'heating_energy': -15},
            cost_level='high',
            applicability=['all_buildings']
        ))
        
        # Envelope Rules
        self.add_rule(EfficiencyRule(
            name='super_insulation_walls',
            description='Add super insulation to walls',
            category='materials',
            target_parameter='conductivity',  # Matches MaterialsModifier parameter
            modification_type='multiplier',
            modification_value=0.5,
            conditions={'wall_r_value': {'max': 20}},
            expected_impact={'heating_energy': -20, 'cooling_energy': -10},
            cost_level='high',
            applicability=['residential', 'commercial']
        ))
        
        self.add_rule(EfficiencyRule(
            name='low_e_windows',
            description='Install low-e high performance windows',
            category='materials',
            target_parameter='u_factor',  # Matches MaterialsModifier parameter
            modification_type='absolute',
            modification_value=1.2,
            conditions={'window_type': 'single_pane'},
            expected_impact={'heating_energy': -15, 'cooling_energy': -10},
            cost_level='high',
            applicability=['all_buildings']
        ))
        
        self.add_rule(EfficiencyRule(
            name='low_shgc_windows',
            description='Install low solar heat gain windows',
            category='materials',
            target_parameter='shgc',  # Matches MaterialsModifier parameter
            modification_type='absolute',
            modification_value=0.25,
            conditions={'climate': ['hot', 'warm']},
            expected_impact={'cooling_energy': -20},
            cost_level='medium',
            applicability=['all_buildings']
        ))
        
        # Lighting Rules
        self.add_rule(EfficiencyRule(
            name='led_retrofit',
            description='LED lighting retrofit',
            category='lighting',
            target_parameter='watts_per_area',  # Matches LightingModifier parameter
            modification_type='multiplier',
            modification_value=0.5,
            conditions={'lighting_type': ['fluorescent', 'incandescent']},
            expected_impact={'lighting_energy': -50},
            cost_level='medium',
            applicability=['all_buildings']
        ))
        
        self.add_rule(EfficiencyRule(
            name='task_lighting',
            description='Implement task/ambient lighting strategy',
            category='lighting',
            target_parameter='watts_per_area',  # Matches LightingModifier parameter
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
            target_parameter='watts_per_area',  # Matches EquipmentModifier parameter
            modification_type='multiplier',
            modification_value=0.75,
            conditions={'equipment_age': {'min': 10}},
            expected_impact={'plug_loads': -25},
            cost_level='medium',
            applicability=['office', 'institutional']
        ))
        
        self.add_rule(EfficiencyRule(
            name='plug_load_reduction',
            description='Plug load management and reduction',
            category='equipment',
            target_parameter='design_level',  # Matches EquipmentModifier parameter
            modification_type='multiplier',
            modification_value=0.8,
            conditions={'has_plug_load_management': False},
            expected_impact={'plug_loads': -20},
            cost_level='low',
            applicability=['office', 'educational']
        ))
        
        # Infiltration Rules
        self.add_rule(EfficiencyRule(
            name='air_sealing_retrofit',
            description='Comprehensive air sealing retrofit',
            category='infiltration',
            target_parameter='air_changes_per_hour',  # Matches InfiltrationModifier parameter
            modification_type='multiplier',
            modification_value=0.3,
            conditions={'building_age': {'min': 20}},
            expected_impact={'heating_energy': -10, 'cooling_energy': -5},
            cost_level='low',
            applicability=['all_buildings']
        ))
        
        self.add_rule(EfficiencyRule(
            name='weatherstripping',
            description='Add weatherstripping to doors and windows',
            category='infiltration',
            target_parameter='flow_per_zone_area',  # Matches InfiltrationModifier parameter
            modification_type='multiplier',
            modification_value=0.5,
            conditions={'has_weatherstripping': False},
            expected_impact={'heating_energy': -5, 'cooling_energy': -3},
            cost_level='low',
            applicability=['all_buildings']
        ))
        
        # Ventilation Rules
        self.add_rule(EfficiencyRule(
            name='demand_controlled_ventilation',
            description='Implement CO2-based demand controlled ventilation',
            category='ventilation',
            target_parameter='outdoor_air_flow_per_person',  # Matches VentilationModifier parameter
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
            target_parameter='sensible_effectiveness',  # Matches VentilationModifier parameter
            modification_type='absolute',
            modification_value=0.8,
            conditions={'has_heat_recovery': False},
            expected_impact={'ventilation_energy': -40},
            cost_level='high',
            applicability=['all_buildings']
        ))
        
        # DHW Rules
        self.add_rule(EfficiencyRule(
            name='high_efficiency_water_heater',
            description='Install high efficiency water heater',
            category='dhw',
            target_parameter='heater_efficiency',  # Matches DHWModifier parameter
            modification_type='absolute',
            modification_value=0.95,
            conditions={'current_efficiency': {'max': 0.8}},
            expected_impact={'dhw_energy': -20},
            cost_level='medium',
            applicability=['all_buildings']
        ))
        
        self.add_rule(EfficiencyRule(
            name='low_flow_fixtures',
            description='Install low flow fixtures',
            category='dhw',
            target_parameter='use_flow_rate',  # Matches DHWModifier parameter
            modification_type='multiplier',
            modification_value=0.6,
            conditions={'has_low_flow': False},
            expected_impact={'dhw_energy': -15},
            cost_level='low',
            applicability=['all_buildings']
        ))
        
        # Shading Rules
        self.add_rule(EfficiencyRule(
            name='automated_shading',
            description='Install automated shading controls',
            category='shading',
            target_parameter='shading_control_type',  # Matches ShadingModifier parameter
            modification_type='discrete',
            modification_value='OnIfHighSolarOnWindow',
            conditions={'has_automated_shading': False},
            expected_impact={'cooling_energy': -15},
            cost_level='medium',
            applicability=['office', 'educational']
        ))
    
    def add_rule(self, rule: EfficiencyRule):
        """Add a rule to the engine"""
        self.rules[rule.name] = rule
    
    def get_rules_by_category(self, category: str) -> List[EfficiencyRule]:
        """Get all rules for a specific category"""
        return [rule for rule in self.rules.values() if rule.category == category]
    
    def get_applicable_rules(self, 
                           building_characteristics: Dict[str, Any],
                           categories: Optional[List[str]] = None,
                           cost_levels: Optional[List[str]] = None) -> List[EfficiencyRule]:
        """Get rules applicable to a specific building"""
        applicable_rules = []
        
        for rule in self.rules.values():
            # Filter by category
            if categories and rule.category not in categories:
                continue
            
            # Filter by cost level
            if cost_levels and rule.cost_level not in cost_levels:
                continue
            
            # Check applicability
            if 'all_buildings' not in rule.applicability:
                building_type = building_characteristics.get('building_type', 'unknown')
                if building_type not in rule.applicability:
                    continue
            
            # Check conditions
            if self._check_conditions(rule.conditions, building_characteristics):
                applicable_rules.append(rule)
        
        return applicable_rules
    
    def _check_conditions(self, conditions: Dict[str, Any], characteristics: Dict[str, Any]) -> bool:
        """Check if conditions are met for a rule"""
        for param, condition in conditions.items():
            if param not in characteristics:
                continue  # Skip if characteristic not available
            
            value = characteristics[param]
            
            if isinstance(condition, dict):
                if 'min' in condition and value < condition['min']:
                    return False
                if 'max' in condition and value > condition['max']:
                    return False
            elif isinstance(condition, list):
                if value not in condition:
                    return False
            else:
                if value != condition:
                    return False
        
        return True
    
    def rank_rules_by_impact(self, rules: List[EfficiencyRule]) -> List[Tuple[EfficiencyRule, float]]:
        """Rank rules by their expected impact"""
        ranked = []
        
        for rule in rules:
            # Calculate total impact score
            total_impact = sum(abs(impact) for impact in rule.expected_impact.values())
            avg_impact = total_impact / len(rule.expected_impact) if rule.expected_impact else 0
            
            # Adjust for cost level
            cost_factor = {'low': 1.2, 'medium': 1.0, 'high': 0.8}
            score = avg_impact * cost_factor.get(rule.cost_level, 1.0)
            
            ranked.append((rule, score))
        
        return sorted(ranked, key=lambda x: x[1], reverse=True)
    
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
            'task_lighting': ['lighting_controls'],
            'automated_shading': ['shading_controls']
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
    
    def import_rules(self, input_path: str):
        """Import rules from JSON"""
        with open(input_path, 'r') as f:
            rules_data = json.load(f)
        
        for name, rule_data in rules_data.items():
            rule = EfficiencyRule(
                name=name,
                description=rule_data['description'],
                category=rule_data['category'],
                target_parameter=rule_data['target_parameter'],
                modification_type=rule_data['modification_type'],
                modification_value=rule_data['modification_value'],
                conditions=rule_data.get('conditions', {}),
                expected_impact=rule_data.get('expected_impact', {}),
                cost_level=rule_data.get('cost_level', 'medium'),
                applicability=rule_data.get('applicability', [])
            )
            self.add_rule(rule)