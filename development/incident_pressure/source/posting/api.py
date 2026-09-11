from .configuration import load_job
from .decode import decode
from .policies import calculate


def export(job_id, csv_text):
    settings = load_job(job_id)
    records = decode(csv_text)
    result = calculate(records, settings["policy"])
    return {
        "job_id": job_id,
        "effective_policy": settings["policy"],
        "records": [{"entry_id": key, "amount": str(amount)} for key, amount in records],
        "minor_units": result,
    }
