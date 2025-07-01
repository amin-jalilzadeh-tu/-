import json
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import pandas as pd
import numpy as np
from dataclasses import dataclass, asdict
import hashlib

logger = logging.getLogger(__name__)


@dataclass
class ParameterVersion:
    """Represents a version of parameters"""
    version_id: str
    iteration_id: int
    timestamp: datetime
    parameters: Dict[str, Any]
    metrics: Dict[str, float]
    metadata: Dict[str, Any]
    parent_version: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'version_id': self.version_id,
            'iteration_id': self.iteration_id,
            'timestamp': self.timestamp.isoformat(),
            'parameters': self.parameters,
            'metrics': self.metrics,
            'metadata': self.metadata,
            'parent_version': self.parent_version
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ParameterVersion':
        """Create from dictionary"""
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)


class ParameterStore:
    """
    Manages versioned storage of parameters across iterations
    """
    
    def __init__(self, job_id: str, base_dir: Optional[str] = None):
        self.job_id = job_id
        self.base_dir = Path(base_dir or f"iterations/{job_id}/parameter_store")
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
        # Storage paths
        self.versions_dir = self.base_dir / "versions"
        self.versions_dir.mkdir(exist_ok=True)
        
        self.index_file = self.base_dir / "parameter_index.json"
        self.lineage_file = self.base_dir / "parameter_lineage.json"
        
        # Load or initialize index
        self.index = self._load_index()
        self.lineage = self._load_lineage()
        
    def _load_index(self) -> Dict[str, Dict[str, Any]]:
        """Load parameter index"""
        if self.index_file.exists():
            with open(self.index_file, 'r') as f:
                return json.load(f)
        return {}
    
    def _load_lineage(self) -> Dict[str, List[str]]:
        """Load parameter lineage (parent-child relationships)"""
        if self.lineage_file.exists():
            with open(self.lineage_file, 'r') as f:
                return json.load(f)
        return {}
    
    def _save_index(self):
        """Save parameter index"""
        with open(self.index_file, 'w') as f:
            json.dump(self.index, f, indent=2)
    
    def _save_lineage(self):
        """Save parameter lineage"""
        with open(self.lineage_file, 'w') as f:
            json.dump(self.lineage, f, indent=2)
    
    def _generate_version_id(self, parameters: Dict[str, Any], iteration_id: int) -> str:
        """Generate unique version ID based on parameters and iteration"""
        # Create a deterministic hash of parameters
        param_str = json.dumps(parameters, sort_keys=True)
        param_hash = hashlib.md5(param_str.encode()).hexdigest()[:8]
        
        # Include iteration for uniqueness
        version_id = f"v{iteration_id:03d}_{param_hash}"
        
        return version_id
    
    def store_parameters(self, 
                        iteration_id: int,
                        parameters: Dict[str, Any],
                        metrics: Dict[str, float],
                        metadata: Optional[Dict[str, Any]] = None,
                        parent_version: Optional[str] = None) -> str:
        """
        Store a new version of parameters
        """
        # Generate version ID
        version_id = self._generate_version_id(parameters, iteration_id)
        
        # Create parameter version
        version = ParameterVersion(
            version_id=version_id,
            iteration_id=iteration_id,
            timestamp=datetime.now(),
            parameters=parameters,
            metrics=metrics,
            metadata=metadata or {},
            parent_version=parent_version
        )
        
        # Save version file
        version_file = self.versions_dir / f"{version_id}.json"
        with open(version_file, 'w') as f:
            json.dump(version.to_dict(), f, indent=2)
        
        # Update index
        self.index[version_id] = {
            'iteration_id': iteration_id,
            'timestamp': version.timestamp.isoformat(),
            'metrics_summary': {
                'cv_rmse': metrics.get('cv_rmse', float('inf')),
                'rmse': metrics.get('rmse', float('inf')),
                'r2': metrics.get('r2', 0.0)
            },
            'file': str(version_file)
        }
        self._save_index()
        
        # Update lineage
        if parent_version:
            if parent_version not in self.lineage:
                self.lineage[parent_version] = []
            self.lineage[parent_version].append(version_id)
            self._save_lineage()
        
        logger.info(f"Stored parameter version: {version_id}")
        return version_id
    
    def get_version(self, version_id: str) -> Optional[ParameterVersion]:
        """Retrieve a specific parameter version"""
        if version_id not in self.index:
            logger.warning(f"Version {version_id} not found")
            return None
        
        version_file = Path(self.index[version_id]['file'])
        if not version_file.exists():
            logger.error(f"Version file {version_file} not found")
            return None
        
        with open(version_file, 'r') as f:
            data = json.load(f)
            return ParameterVersion.from_dict(data)
    
    def get_best_version(self, metric: str = 'cv_rmse') -> Optional[ParameterVersion]:
        """Get the best performing parameter version"""
        if not self.index:
            return None
        
        # Find best version based on metric
        best_version_id = None
        best_value = float('inf') if metric != 'r2' else -float('inf')
        
        for version_id, info in self.index.items():
            metric_value = info['metrics_summary'].get(metric, float('inf'))
            
            if metric == 'r2':
                if metric_value > best_value:
                    best_value = metric_value
                    best_version_id = version_id
            else:
                if metric_value < best_value:
                    best_value = metric_value
                    best_version_id = version_id
        
        return self.get_version(best_version_id) if best_version_id else None
    
    def get_version_history(self, version_id: str) -> List[ParameterVersion]:
        """Get the history (lineage) of a parameter version"""
        history = []
        current_id = version_id
        
        # Traverse backwards through parent versions
        while current_id:
            version = self.get_version(current_id)
            if version:
                history.append(version)
                current_id = version.parent_version
            else:
                break
        
        # Return in chronological order
        return list(reversed(history))
    
    def get_iteration_parameters(self, iteration_id: int) -> Optional[ParameterVersion]:
        """Get parameters for a specific iteration"""
        for version_id, info in self.index.items():
            if info['iteration_id'] == iteration_id:
                return self.get_version(version_id)
        return None
    
    def compare_versions(self, version_id1: str, version_id2: str) -> Dict[str, Any]:
        """Compare two parameter versions"""
        v1 = self.get_version(version_id1)
        v2 = self.get_version(version_id2)
        
        if not v1 or not v2:
            logger.error("One or both versions not found")
            return {}
        
        comparison = {
            'version_1': version_id1,
            'version_2': version_id2,
            'parameter_differences': {},
            'metric_differences': {},
            'time_difference': (v2.timestamp - v1.timestamp).total_seconds()
        }
        
        # Compare parameters
        all_params = set(v1.parameters.keys()) | set(v2.parameters.keys())
        for param in all_params:
            val1 = v1.parameters.get(param)
            val2 = v2.parameters.get(param)
            
            if val1 != val2:
                comparison['parameter_differences'][param] = {
                    'version_1': val1,
                    'version_2': val2,
                    'change': val2 - val1 if isinstance(val1, (int, float)) and isinstance(val2, (int, float)) else 'N/A'
                }
        
        # Compare metrics
        all_metrics = set(v1.metrics.keys()) | set(v2.metrics.keys())
        for metric in all_metrics:
            val1 = v1.metrics.get(metric)
            val2 = v2.metrics.get(metric)
            
            if val1 != val2:
                comparison['metric_differences'][metric] = {
                    'version_1': val1,
                    'version_2': val2,
                    'improvement': val1 - val2 if metric != 'r2' else val2 - val1
                }
        
        return comparison
    
    def export_parameter_evolution(self, output_path: str):
        """Export parameter evolution as DataFrame"""
        data = []
        
        for version_id in sorted(self.index.keys()):
            version = self.get_version(version_id)
            if version:
                row = {
                    'version_id': version_id,
                    'iteration_id': version.iteration_id,
                    'timestamp': version.timestamp,
                    **version.parameters,
                    **{f"metric_{k}": v for k, v in version.metrics.items()}
                }
                data.append(row)
        
        df = pd.DataFrame(data)
        df.to_csv(output_path, index=False)
        logger.info(f"Exported parameter evolution to {output_path}")
        
        return df
    
    def create_checkpoint(self, version_id: str, checkpoint_name: str) -> str:
        """Create a named checkpoint for a parameter version"""
        checkpoint_dir = self.base_dir / "checkpoints"
        checkpoint_dir.mkdir(exist_ok=True)
        
        version = self.get_version(version_id)
        if not version:
            raise ValueError(f"Version {version_id} not found")
        
        checkpoint_file = checkpoint_dir / f"{checkpoint_name}.json"
        checkpoint_data = {
            'checkpoint_name': checkpoint_name,
            'version_id': version_id,
            'created_at': datetime.now().isoformat(),
            'version_data': version.to_dict()
        }
        
        with open(checkpoint_file, 'w') as f:
            json.dump(checkpoint_data, f, indent=2)
        
        logger.info(f"Created checkpoint '{checkpoint_name}' for version {version_id}")
        return str(checkpoint_file)
    
    def restore_checkpoint(self, checkpoint_name: str) -> Optional[ParameterVersion]:
        """Restore parameters from a checkpoint"""
        checkpoint_file = self.base_dir / "checkpoints" / f"{checkpoint_name}.json"
        
        if not checkpoint_file.exists():
            logger.error(f"Checkpoint '{checkpoint_name}' not found")
            return None
        
        with open(checkpoint_file, 'r') as f:
            checkpoint_data = json.load(f)
            version_data = checkpoint_data['version_data']
            return ParameterVersion.from_dict(version_data)
    
    def cleanup_old_versions(self, keep_best_n: int = 10, keep_days: int = 30):
        """Clean up old parameter versions while keeping best performers"""
        # Get all versions sorted by performance
        versions_by_metric = []
        for version_id in self.index:
            version = self.get_version(version_id)
            if version:
                cv_rmse = version.metrics.get('cv_rmse', float('inf'))
                versions_by_metric.append((cv_rmse, version_id, version.timestamp))
        
        versions_by_metric.sort(key=lambda x: x[0])  # Sort by CV-RMSE
        
        # Determine which versions to keep
        keep_versions = set()
        
        # Keep best N versions
        for _, version_id, _ in versions_by_metric[:keep_best_n]:
            keep_versions.add(version_id)
        
        # Keep recent versions
        cutoff_date = datetime.now() - pd.Timedelta(days=keep_days)
        for _, version_id, timestamp in versions_by_metric:
            if timestamp > cutoff_date:
                keep_versions.add(version_id)
        
        # Keep checkpointed versions
        checkpoint_dir = self.base_dir / "checkpoints"
        if checkpoint_dir.exists():
            for checkpoint_file in checkpoint_dir.glob("*.json"):
                with open(checkpoint_file, 'r') as f:
                    checkpoint_data = json.load(f)
                    keep_versions.add(checkpoint_data['version_id'])
        
        # Remove old versions
        removed_count = 0
        for version_id in list(self.index.keys()):
            if version_id not in keep_versions:
                version_file = Path(self.index[version_id]['file'])
                if version_file.exists():
                    version_file.unlink()
                del self.index[version_id]
                removed_count += 1
        
        if removed_count > 0:
            self._save_index()
            logger.info(f"Cleaned up {removed_count} old parameter versions")
        
        return removed_count