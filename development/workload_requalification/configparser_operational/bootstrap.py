"""Explicit import locations for the existing task/runtime chain; no execution."""
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[3]
IMPORT_DIRS=(
    'src','scripts','tests',
    'development/workload_requalification/configparser_operational',
    'development/workload_requalification/configparser_execution',
    'development/workload_requalification/action_lifecycle',
    'development/workload_requalification/configparser_original',
    'development/workload_requalification/navigation_continuity',
    'development/workload_requalification/small_repairs',
    'development/decision_interface/coherent_diagnostics',
    'development/decision_interface/recovery_inspection',
    'development/decision_interface/completion_cycle',
    'development/decision_interface/reference_repair',
    'development/decision_interface/feedback_repair',
    'development/decision_interface/channel_repair',
    'development/decision_interface/same_task',
    'development/decision_interface','development/operable_recovery',
    'development/working_account',
)
for relative in reversed(IMPORT_DIRS):
    path=str(ROOT/relative)
    if path not in sys.path:
        sys.path.insert(0,path)
