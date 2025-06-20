"""
Comfort Rules - Define rules for improving occupant comfort
"""
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field

@dataclass
class ComfortRule:
    """Defines a comfort improvement rule"""
    name: str
    description: str
    category: str
    comfort_metric: str  # 'thermal', 'visual', 'acoustic', 'iaq'
    parameters: Dict[str, Any]
    conditions: Dict[str, Any] = field(default_factory=dict)
    priority: int = 1  # 1 (highest) to 5 (lowest)

class ComfortRuleEngine:
    """Engine for applying comfort improvement rules"""
    
    def __init__(self):
        """Initialize comfort rule engine"""
        self.rules: Dict[str, ComfortRule] = {}
        self._initialize_rules()
    
    def _initialize_rules(self):
        """Initialize default comfort rules"""
        
        # Thermal Comfort Rules
        self.add_rule(ComfortRule(
            name='adaptive_setpoints',
            description='Implement adaptive comfort setpoints',
            category='hvac',
            comfort_metric='thermal',
            parameters={
                'heating_setpoint_adjustment': -1.0,
                'cooling_setpoint_adjustment': 1.0,
                'deadband': 3.0
            },
            conditions={'control_type': 'thermostatic'},
            priority=1
        ))
        
        self.add_rule(ComfortRule(
            name='radiant_temperature_control',
            description='Control based on operative temperature',
            category='hvac',
            comfort_metric='thermal',
            parameters={
                'use_mean_radiant_temp': True,
                'weight_factor': 0.5
            },
            conditions={'has_radiant_surfaces': True},
            priority=2
        ))
        
        self.add_rule(ComfortRule(
            name='humidity_control',
            description='Maintain optimal humidity levels',
            category='hvac',
            comfort_metric='thermal',
            parameters={
                'min_relative_humidity': 30,
                'max_relative_humidity': 60,
                'enable_humidification': True,
                'enable_dehumidification': True
            },
            priority=2
        ))
        
        # Visual Comfort Rules
        self.add_rule(ComfortRule(
            name='daylight_optimization',
            description='Optimize daylight utilization',
            category='lighting',
            comfort_metric='visual',
            parameters={
                'target_daylight_illuminance': 500,
                'daylight_sensors': True,
                'continuous_dimming': True,
                'min_light_output': 0.1
            },
            conditions={'has_windows': True},
            priority=1
        ))
        
        self.add_rule(ComfortRule(
            name='glare_control',
            description='Prevent discomfort glare',
            category='shading',
            comfort_metric='visual',
            parameters={
                'max_dgi': 22,  # Daylight Glare Index
                'control_strategy': 'automated_blinds',
                'blind_angle_control': True
            },
            conditions={'window_orientation': ['east', 'south', 'west']},
            priority=1
        ))
        
        self.add_rule(ComfortRule(
            name='circadian_lighting',
            description='Support circadian rhythms',
            category='lighting',
            comfort_metric='visual',
            parameters={
                'morning_cct': 5000,  # Cool white
                'afternoon_cct': 4000,  # Neutral
                'evening_cct': 3000,  # Warm white
                'transition_time': 60  # minutes
            },
            priority=3
        ))
        
        # Indoor Air Quality Rules
        self.add_rule(ComfortRule(
            name='enhanced_ventilation',
            description='Increase ventilation for better IAQ',
            category='ventilation',
            comfort_metric='iaq',
            parameters={
                'outdoor_air_increase': 1.3,  # 30% above minimum
                'co2_setpoint': 800,  # ppm
                'filtration_level': 'MERV13'
            },
            priority=1
        ))
        
        self.add_rule(ComfortRule(
            name='natural_ventilation_comfort',
            description='Use natural ventilation when comfortable',
            category='ventilation',
            comfort_metric='iaq',
            parameters={
                'min_outdoor_temp': 18,
                'max_outdoor_temp': 26,
                'max_outdoor_humidity': 70,
                'min_window_opening': 0.1,
                'max_window_opening': 0.5
            },
            conditions={'operable_windows': True},
            priority=2
        ))
        
        # Acoustic Comfort Rules
        self.add_rule(ComfortRule(
            name='hvac_noise_reduction',
            description='Reduce HVAC noise levels',
            category='hvac',
            comfort_metric='acoustic',
            parameters={
                'max_nc_level': 35,  # Noise Criteria
                'duct_velocity_limit': 5.0,  # m/s
                'use_sound_attenuators': True
            },
            priority=3
        ))
        
        # Multi-aspect Comfort Rules
        self.add_rule(ComfortRule(
            name='personal_comfort_systems',
            description='Enable personal environmental control',
            category='hvac',
            comfort_metric='thermal',
            parameters={
                'zone_control': True,
                'personal_fans': True,
                'task_lighting': True,
                'control_range': 3.0  # ±3°C
            },
            conditions={'space_type': ['office', 'workstation']},
            priority=2
        ))
    
    def add_rule(self, rule: ComfortRule):
        """Add a comfort rule"""
        self.rules[rule.name] = rule
    
    def get_rules_by_metric(self, comfort_metric: str) -> List[ComfortRule]:
        """Get all rules for a specific comfort metric"""
        return [rule for rule in self.rules.values() 
                if rule.comfort_metric == comfort_metric]
    
    def get_applicable_rules(self,
                           building_characteristics: Dict[str, Any],
                           comfort_metrics: Optional[List[str]] = None,
                           min_priority: int = 5) -> List[ComfortRule]:
        """Get applicable comfort rules for a building"""
        applicable_rules = []
        
        for rule in self.rules.values():
            # Filter by comfort metric
            if comfort_metrics and rule.comfort_metric not in comfort_metrics:
                continue
            
            # Filter by priority
            if rule.priority > min_priority:
                continue
            
            # Check conditions
            if self._check_conditions(rule.conditions, building_characteristics):
                applicable_rules.append(rule)
        
        return applicable_rules
    
    def _check_conditions(self, 
                         conditions: Dict[str, Any], 
                         characteristics: Dict[str, Any]) -> bool:
        """Check if conditions are met"""
        for key, required_value in conditions.items():
            if key not in characteristics:
                return False
            
            actual_value = characteristics[key]
            
            if isinstance(required_value, list):
                if actual_value not in required_value:
                    return False
            else:
                if actual_value != required_value:
                    return False
        
        return True
    
    def create_comfort_package(self,
                             building_characteristics: Dict[str, Any],
                             comfort_priorities: List[str]) -> List[ComfortRule]:
        """
        Create a package of comfort improvements
        
        Args:
            building_characteristics: Building properties
            comfort_priorities: Ordered list of comfort metrics
            
        Returns:
            List of selected rules
        """
        selected_rules = []
        
        # Process by priority order
        for metric in comfort_priorities:
            metric_rules = self.get_rules_by_metric(metric)
            
            # Filter applicable rules
            applicable = [r for r in metric_rules 
                         if self._check_conditions(r.conditions, building_characteristics)]
            
            # Sort by priority
            applicable.sort(key=lambda r: r.priority)
            
            # Select top rules for this metric
            selected_rules.extend(applicable[:2])  # Max 2 per metric
        
        return selected_rules
    
    def calculate_comfort_score(self,
                              applied_rules: List[ComfortRule],
                              weights: Optional[Dict[str, float]] = None) -> float:
        """
        Calculate overall comfort improvement score
        
        Args:
            applied_rules: List of applied rules
            weights: Weights for different comfort metrics
            
        Returns:
            Comfort score (0-100)
        """
        if not weights:
            weights = {
                'thermal': 0.4,
                'visual': 0.3,
                'iaq': 0.2,
                'acoustic': 0.1
            }
        
        metric_scores = {metric: 0 for metric in weights.keys()}
        metric_counts = {metric: 0 for metric in weights.keys()}
        
        # Calculate scores by metric
        for rule in applied_rules:
            metric = rule.comfort_metric
            if metric in metric_scores:
                # Score based on priority (1=100, 5=20)
                score = 120 - (rule.priority * 20)
                metric_scores[metric] += score
                metric_counts[metric] += 1
        
        # Average scores by metric
        for metric in metric_scores:
            if metric_counts[metric] > 0:
                metric_scores[metric] /= metric_counts[metric]
        
        # Calculate weighted total
        total_score = sum(metric_scores[metric] * weights.get(metric, 0) 
                         for metric in metric_scores)
        
        return min(100, total_score)
    
    def get_conflicting_rules(self, rules: List[ComfortRule]) -> List[Tuple[str, str, str]]:
        """
        Find conflicting comfort rules
        
        Returns:
            List of (rule1, rule2, conflict_reason) tuples
        """
        conflicts = []
        
        # Define known conflicts
        conflict_pairs = [
            ('adaptive_setpoints', 'tight_temperature_control', 
             'Adaptive setpoints conflict with tight control'),
            ('natural_ventilation_comfort', 'humidity_control',
             'Natural ventilation may conflict with humidity control'),
            ('daylight_optimization', 'glare_control',
             'Maximum daylight may cause glare issues')
        ]
        
        rule_names = [r.name for r in rules]
        
        for rule1, rule2, reason in conflict_pairs:
            if rule1 in rule_names and rule2 in rule_names:
                conflicts.append((rule1, rule2, reason))
        
        return conflicts
    
    def generate_control_sequence(self, rules: List[ComfortRule]) -> Dict[str, Any]:
        """Generate control sequence from comfort rules"""
        control_sequence = {
            'thermal': {},
            'lighting': {},
            'ventilation': {},
            'shading': {}
        }
        
        for rule in rules:
            if rule.category == 'hvac':
                if 'setpoint' in rule.name:
                    control_sequence['thermal']['setpoints'] = rule.parameters
                elif 'humidity' in rule.name:
                    control_sequence['thermal']['humidity'] = rule.parameters
                    
            elif rule.category == 'lighting':
                control_sequence['lighting'][rule.name] = rule.parameters
                
            elif rule.category == 'ventilation':
                control_sequence['ventilation'][rule.name] = rule.parameters
                
            elif rule.category == 'shading':
                control_sequence['shading'][rule.name] = rule.parameters
        
        return control_sequence