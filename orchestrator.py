"""
orchestrator.py

Thin wrapper that imports from the orchestrator package and maintains
the same interface for job_manager.py
"""

from orchestrator.main import orchestrate_workflow, WorkflowCanceled

# Re-export for backward compatibility
__all__ = ['orchestrate_workflow', 'WorkflowCanceled']