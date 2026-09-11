import json
from pathlib import Path


CONFIG = Path(__file__).resolve().parent.parent / "config" / "jobs.json"


def load_job(job_id):
    if not isinstance(job_id, str) or not job_id:
        raise ValueError("job_id must be a nonempty string")
    jobs = json.loads(CONFIG.read_text(encoding="utf-8"))
    if job_id not in jobs:
        raise ValueError("unknown job")
    settings = jobs[job_id]
    if set(settings) != {"policy"} or settings["policy"] not in {"line", "statement"}:
        raise ValueError("invalid job configuration")
    return settings
