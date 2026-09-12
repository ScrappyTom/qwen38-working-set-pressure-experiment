"""Read-only admission screen of this checkout's complete implementation source."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from working_set_exp import candidate as host
from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes, sha256_file


def inspect(files):
    try:
        value = host.Candidate.create(files)
        return dict(accepted=True, candidate_id=value.candidate_id)
    except host.CandidateError as error:
        return dict(accepted=False, error_type=type(error).__name__, error=str(error))


def main():
    target = ROOT / "development/long_work/admission-001.json"
    if target.exists():
        raise FileExistsError("preserve the existing admission screen")
    files = {p.relative_to(ROOT).as_posix():p.read_bytes()
             for p in sorted((ROOT / "src/working_set_exp").rglob("*.py"))}
    inventory = [dict(path=name, size_bytes=len(raw), sha256=sha256_bytes(raw),
        longest_line_bytes=max(map(len,raw.splitlines()),default=0), admission=inspect({name:raw}))
        for name,raw in files.items()]
    result = dict(scope="all current src/working_set_exp Python source; no synthetic padding or generated run artifacts",
        source_files=len(files), source_bytes=sum(map(len,files.values())), full_admission=inspect(files),
        individually_rejected=sum(not row["admission"]["accepted"] for row in inventory), files=inventory,
        host_source_sha256=sha256_file(Path(host.__file__)), probe_source_sha256=sha256_file(Path(__file__)),
        effective_limits=dict(files=host.MAX_FILES, total_bytes=host.MAX_TOTAL_BYTES,
            file_bytes=host.MAX_FILE_BYTES, line_bytes=host.MAX_LINE_BYTES),
        completion_requests=0, tokenizer_calls=0, runtime_policy_changed=False)
    with target.open("xb") as stream:
        stream.write(canonical_json_bytes(result))
    print({k:result[k] for k in ("source_files","source_bytes","individually_rejected","full_admission","completion_requests")})


if __name__ == "__main__":
    main()
