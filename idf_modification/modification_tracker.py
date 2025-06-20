"""
Track all changes made to IDF files.

This module provides functionality to log and track all modifications applied
to IDF files for auditing and rollback purposes.
"""
"""
Modification Tracker Module - Track all modifications made
"""
import json
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
import sqlite3
from dataclasses import dataclass, asdict
import numpy as np

from .base_modifier import ModificationResult

@dataclass
class VariantSummary:
    """Summary of a single variant"""
    variant_id: str
    file_path: str
    total_modifications: int
    categories_modified: List[str]
    success_rate: float
    creation_time: str
    
@dataclass
class SessionSummary:
    """Summary of a modification session"""
    session_id: str
    building_id: str
    base_idf_path: str
    start_time: str
    end_time: Optional[str]
    total_variants: int
    total_modifications: int
    categories_modified: List[str]
    variants: List[VariantSummary]

class ModificationTracker:
    """Track all modifications made during IDF generation"""
    
    def __init__(self, output_path: Path):
        """
        Initialize modification tracker
        
        Args:
            output_path: Base path for tracking outputs
        """
        self.output_path = Path(output_path)
        self.tracking_dir = self.output_path / 'tracking'
        self.tracking_dir.mkdir(parents=True, exist_ok=True)
        
        # Current session data
        self.current_session: Optional[SessionSummary] = None
        self.current_variant: Optional[VariantSummary] = None
        self.session_modifications: List[pd.DataFrame] = []
        
        # Initialize tracking database
        self.db_path = self.tracking_dir / 'modifications.db'
        self._init_database()
        
    def _init_database(self):
        """Initialize SQLite database for tracking"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create tables
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                building_id TEXT,
                base_idf_path TEXT,
                start_time TEXT,
                end_time TEXT,
                total_variants INTEGER,
                total_modifications INTEGER,
                categories_modified TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS variants (
                variant_id TEXT,
                session_id TEXT,
                file_path TEXT,
                total_modifications INTEGER,
                categories_modified TEXT,
                success_rate REAL,
                creation_time TEXT,
                FOREIGN KEY (session_id) REFERENCES sessions (session_id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS modifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                variant_id TEXT,
                category TEXT,
                object_type TEXT,
                object_name TEXT,
                parameter TEXT,
                original_value TEXT,
                new_value TEXT,
                change_type TEXT,
                rule_applied TEXT,
                success INTEGER,
                validation_status TEXT,
                message TEXT,
                FOREIGN KEY (session_id) REFERENCES sessions (session_id),
                FOREIGN KEY (variant_id) REFERENCES variants (variant_id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def start_session(self, session_id: str, building_id: str, base_idf_path: str):
        """Start a new modification session"""
        self.current_session = SessionSummary(
            session_id=session_id,
            building_id=building_id,
            base_idf_path=base_idf_path,
            start_time=datetime.now().isoformat(),
            end_time=None,
            total_variants=0,
            total_modifications=0,
            categories_modified=[],
            variants=[]
        )
        
        # Clear session data
        self.session_modifications = []
    
    def start_variant(self, variant_id: str):
        """Start tracking a new variant"""
        self.current_variant = VariantSummary(
            variant_id=variant_id,
            file_path='',
            total_modifications=0,
            categories_modified=[],
            success_rate=0.0,
            creation_time=datetime.now().isoformat()
        )
    
    def track_modifications(self, category: str, modifications: List[ModificationResult]):
        """Track modifications for a category"""
        if not modifications:
            return
            
        # Convert to DataFrame
        data = []
        for mod in modifications:
            data.append({
                'session_id': self.current_session.session_id,
                'variant_id': self.current_variant.variant_id,
                'category': category,
                'object_type': mod.object_type,
                'object_name': mod.object_name,
                'parameter': mod.parameter,
                'original_value': str(mod.original_value),
                'new_value': str(mod.new_value),
                'change_type': mod.change_type,
                'rule_applied': mod.rule_applied,
                'success': mod.success,
                'validation_status': mod.validation_status,
                'message': mod.message
            })
        
        df = pd.DataFrame(data)
        self.session_modifications.append(df)
        
        # Update current variant
        if self.current_variant:
            self.current_variant.total_modifications += len(modifications)
            if category not in self.current_variant.categories_modified:
                self.current_variant.categories_modified.append(category)
        
        # Save to database
        self._save_modifications_to_db(df)
    
    def complete_variant(self, variant_id: str, file_path: str, all_modifications: List[ModificationResult]):
        """Complete tracking for a variant"""
        if self.current_variant:
            self.current_variant.file_path = file_path
            
            # Calculate success rate
            if all_modifications:
                success_count = sum(1 for mod in all_modifications if mod.success)
                self.current_variant.success_rate = success_count / len(all_modifications)
            
            # Add to session
            self.current_session.variants.append(self.current_variant)
            self.current_session.total_variants += 1
            self.current_session.total_modifications += self.current_variant.total_modifications
            
            # Update categories
            for cat in self.current_variant.categories_modified:
                if cat not in self.current_session.categories_modified:
                    self.current_session.categories_modified.append(cat)
            
            # Save variant to database
            self._save_variant_to_db(self.current_variant)
            
            # Save variant summary as parquet
            variant_dir = Path(file_path).parent
            summary_path = variant_dir / f"{variant_id}_modifications.parquet"
            
            if self.session_modifications:
                variant_df = pd.concat([df[df['variant_id'] == variant_id] 
                                      for df in self.session_modifications], ignore_index=True)
                variant_df.to_parquet(summary_path, index=False)
    
    def fail_variant(self, variant_id: str, error_message: str):
        """Record a failed variant"""
        if self.current_variant:
            self.current_variant.file_path = 'FAILED'
            self.current_variant.success_rate = 0.0
            
            # Still add to session
            self.current_session.variants.append(self.current_variant)
            
            # Log error
            error_data = {
                'session_id': self.current_session.session_id,
                'variant_id': variant_id,
                'error_time': datetime.now().isoformat(),
                'error_message': error_message
            }
            
            error_path = self.tracking_dir / 'errors.json'
            errors = []
            if error_path.exists():
                with open(error_path) as f:
                    errors = json.load(f)
            errors.append(error_data)
            
            with open(error_path, 'w') as f:
                json.dump(errors, f, indent=2)
    
    def save_session_summary(self, output_dir: Path):
        """Save session summary"""
        if not self.current_session:
            return
            
        self.current_session.end_time = datetime.now().isoformat()
        
        # Save to database
        self._save_session_to_db(self.current_session)
        
        # Save as JSON
        summary_path = output_dir / 'session_summary.json'
        with open(summary_path, 'w') as f:
            json.dump(asdict(self.current_session), f, indent=2)
        
        # Save all modifications as parquet
        if self.session_modifications:
            all_mods_df = pd.concat(self.session_modifications, ignore_index=True)
            mods_path = output_dir / 'all_modifications.parquet'
            all_mods_df.to_parquet(mods_path, index=False)
            
            # Save summary statistics
            stats_path = output_dir / 'modification_statistics.csv'
            stats = self._calculate_statistics(all_mods_df)
            stats.to_csv(stats_path, index=False)
    
    def _calculate_statistics(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate modification statistics"""
        stats = []
        
        # By category
        for category in df['category'].unique():
            cat_df = df[df['category'] == category]
            stats.append({
                'grouping': 'category',
                'group_value': category,
                'total_modifications': len(cat_df),
                'successful': len(cat_df[cat_df['success'] == True]),
                'failed': len(cat_df[cat_df['success'] == False]),
                'success_rate': len(cat_df[cat_df['success'] == True]) / len(cat_df) if len(cat_df) > 0 else 0,
                'unique_objects': cat_df['object_name'].nunique(),
                'unique_parameters': cat_df['parameter'].nunique()
            })
        
        # By parameter
        for param in df['parameter'].unique():
            param_df = df[df['parameter'] == param]
            stats.append({
                'grouping': 'parameter',
                'group_value': param,
                'total_modifications': len(param_df),
                'successful': len(param_df[param_df['success'] == True]),
                'failed': len(param_df[param_df['success'] == False]),
                'success_rate': len(param_df[param_df['success'] == True]) / len(param_df) if len(param_df) > 0 else 0,
                'unique_objects': param_df['object_name'].nunique(),
                'unique_parameters': 1
            })
        
        return pd.DataFrame(stats)
    
    def _save_session_to_db(self, session: SessionSummary):
        """Save session to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO sessions VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            session.session_id,
            session.building_id,
            session.base_idf_path,
            session.start_time,
            session.end_time,
            session.total_variants,
            session.total_modifications,
            json.dumps(session.categories_modified)
        ))
        
        conn.commit()
        conn.close()
    
    def _save_variant_to_db(self, variant: VariantSummary):
        """Save variant to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO variants VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            variant.variant_id,
            self.current_session.session_id,
            variant.file_path,
            variant.total_modifications,
            json.dumps(variant.categories_modified),
            variant.success_rate,
            variant.creation_time
        ))
        
        conn.commit()
        conn.close()
    
    def _save_modifications_to_db(self, df: pd.DataFrame):
        """Save modifications to database"""
        conn = sqlite3.connect(self.db_path)
        df.to_sql('modifications', conn, if_exists='append', index=False)
        conn.close()
    
    def generate_report(self) -> str:
        """Generate HTML report of modifications"""
        # This would generate a comprehensive HTML report
        # For now, return a simple summary
        report = f"""
        <html>
        <head>
            <title>Modification Report - {self.current_session.session_id}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                table {{ border-collapse: collapse; width: 100%; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
            </style>
        </head>
        <body>
            <h1>IDF Modification Report</h1>
            <h2>Session: {self.current_session.session_id}</h2>
            <p>Building ID: {self.current_session.building_id}</p>
            <p>Base IDF: {self.current_session.base_idf_path}</p>
            <p>Total Variants: {self.current_session.total_variants}</p>
            <p>Total Modifications: {self.current_session.total_modifications}</p>
            
            <h3>Variants Summary</h3>
            <table>
                <tr>
                    <th>Variant ID</th>
                    <th>File Path</th>
                    <th>Modifications</th>
                    <th>Success Rate</th>
                </tr>
        """
        
        for variant in self.current_session.variants:
            report += f"""
                <tr>
                    <td>{variant.variant_id}</td>
                    <td>{variant.file_path}</td>
                    <td>{variant.total_modifications}</td>
                    <td>{variant.success_rate:.1%}</td>
                </tr>
            """
            
        report += """
            </table>
        </body>
        </html>
        """
        
        return report
    
    def get_modification_history(self, 
                               building_id: Optional[str] = None,
                               session_id: Optional[str] = None) -> pd.DataFrame:
        """Get modification history from database"""
        conn = sqlite3.connect(self.db_path)
        
        query = "SELECT * FROM modifications WHERE 1=1"
        params = []
        
        if building_id:
            query += " AND session_id IN (SELECT session_id FROM sessions WHERE building_id = ?)"
            params.append(building_id)
            
        if session_id:
            query += " AND session_id = ?"
            params.append(session_id)
            
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        
        return df