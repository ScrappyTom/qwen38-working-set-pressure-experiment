"""Restore sealed states into an explicitly prospective presentation variant."""
from pathlib import Path
import sys

AREA = Path(__file__).resolve().parent
sys.path.insert(0, str(AREA.parent))
import qualified_task
import completion_task as original
import run_completion as execution
from correction_context import CorrectionContextMixin


class Session(CorrectionContextMixin, original.Session):
    pass


def restored(stem='after/C63-O03', revised=True):
    task = qualified_task.Task()
    session = task.restore(original.read(task.RUN / (stem + '-state.json')),
                           original.read(task.RUN / (stem + '-candidate.json')),
                           task.RUN, replay=True)
    if revised:
        session.__class__ = Session
    feedback = original.read(task.RUN / (stem + '-preceding-feedback.json'))
    return task, session, feedback
