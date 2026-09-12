"""Supplement: a changed approach may release the unrelated newest payload."""
import json
from pathlib import Path
import sys
from types import SimpleNamespace

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT/'scripts'))
import qualify_compiler_delivery as q


def main():
    output=q.DEST/'offline-002-groups-alone'
    q.require(not output.exists(),'supplement already exists')
    manifest=q.verify_originals()
    launch=q.read(q.RUN/'private-runtime/launch.json')
    tokenizer=Path(launch[0]).with_name('llama-tokenize.exe')
    q.require(q.sha256_file(tokenizer)==q.TOKENIZER_SHA,'tokenizer differs')
    q.require(q.sha256_file(Path(launch[2]))==manifest['actor']['model_sha256'],'model differs')
    profile=SimpleNamespace(model_path=Path(launch[2]),tokenizer_path=tokenizer)
    output.mkdir();rows=[]
    try:
        for cell,n in q.CASES:
            tag=f'{cell}-X16000-{n+1:03d}-x{n:03d}';stem=q.RUN/'admission'/tag
            original=q.read(Path(str(stem)+'-endpoint-request.json'))
            native=Path(str(stem)+'-native.txt').read_bytes().decode()
            pairs=q.read(q.RUN/'segments'/f'{cell}-X16000-pairs.json')[:n]
            q.exact_pairs_match(original,pairs)
            candidate=q.read(Path(str(stem)+'-candidate.json'))
            hashes={f['path']:f['sha256'] for f in candidate['files']}
            for name,group in q.GROUPS.items():
                selected={q.material_sequence(pairs,m,hashes) for m in group}
                req=q.grouped_request(original,pairs,selected);raw=q.native_for(req,original,native)
                count=q.tokenizer_count(profile,raw)
                folder=output/tag;folder.mkdir(exist_ok=True)
                (folder/(name+'-request.json')).write_bytes(q.canonical_json_bytes(req))
                (folder/(name+'-native.txt')).write_bytes(raw)
                row=dict(id=tag,group=name,retained_sequences=sorted(selected),newest_retained=n in selected,
                         input_tokens=count,fits_16000=count<=16000,physical_generation_space=56576-count,
                         completion_sent=False,selection='reviewer-selected after possibly changing approach')
                rows.append(row);print(json.dumps(row),flush=True)
        q.verify_originals()
        result=dict(status='offline_supplement_no_completions',original_seal_sha256=q.SEAL_SHA,rows=rows,
            source_sha256={p.relative_to(ROOT).as_posix():q.sha256_file(p) for p in (Path(__file__),Path(q.__file__))},
            limitation='No new-result delivery guarantee when that result is excluded; no actor group selection or contribution.')
        (output/'MEASUREMENTS.json').write_bytes(q.canonical_json_bytes(result))
        files=[dict(path=p.relative_to(output).as_posix(),sha256=q.sha256_file(p),size_bytes=p.stat().st_size)
               for p in sorted(output.rglob('*')) if p.is_file()]
        (output/'SEAL.json').write_bytes(q.canonical_json_bytes(dict(files=files,aggregate_sha256=q.sha256_bytes(q.canonical_json_bytes(files)))))
    except BaseException as e:
        (output/'FAILED.json').write_bytes(q.canonical_json_bytes(dict(error_type=type(e).__name__,error=str(e),completed_rows=rows)))
        raise


if __name__=='__main__': main()
