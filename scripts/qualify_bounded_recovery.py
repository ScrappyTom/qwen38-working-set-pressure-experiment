"""Exact recovery of the actual larger read under native whole-input admission."""
import bounded_parser as task
from prepare_bounded_parser import Counter, run_action
from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes, sha256_file
from working_set_exp.working_session import WorkingSession


def main():
    output=task.AREA/"recovery-001"
    task.require(not output.exists(),"preserve previous recovery qualification")
    output.mkdir()
    status="incomplete"
    try:
        _,_,tokenizer=task.runtime_paths()
        counter=Counter(output,tokenizer)
        acquired=task.read(task.PACKAGE/"broad-read-route.json")[-1]
        pair=dict(response=acquired["action"],result=acquired["result"])
        body=canonical_json_bytes(pair["result"])
        original=task.initial_session()
        value=WorkingSession(original.candidate,original.checker,original.task,pairs=[pair],call_limit=24)
        rows=[]
        run_action(value,dict(action="read",path="Lib/configparser.py",start_line=299,end_line=341),counter,rows)
        parts,offset=[],0
        for _ in range(20):
            result=run_action(value,dict(action="reopen_result",handle="RES-0001",offset=offset),counter,rows)
            task.require(result["accepted"] and result["sha256"]==sha256_bytes(body),"saved result recovery differs")
            parts.append(result["exact_utf8"].encode())
            task.require(any(s["path"]=="Lib/configparser.py" for s in value.sources()),"recovery displaced supporting library source")
            if result["next_offset"] is None:
                break
            task.require(result["next_offset"]>offset,"historical pagination did not advance")
            offset=result["next_offset"]
        else:
            raise ValueError("recovery did not finish within qualification bound")
        task.require(b"".join(parts)==body and value.payload("RES-0001")==body,"exact reconstructed result differs")
        result=dict(status="native_exact_recovery_qualified",completion_requests=0,
            original_result_bytes=len(body),original_result_sha256=sha256_bytes(body),
            original_source_lines=[pair["result"]["source"]["returned_start_line"],pair["result"]["source"]["returned_end_line"]],
            recovery_pages=len(parts),peak_input=max(r["after_tokens"] for r in rows),
            source_companion_retained=True,private_reasoning_in_recovery=False,source_package_sha256=sha256_file(task.PACKAGE/"SEAL.json"))
        task.save(output,"ROUTE.json",rows)
        task.save(output,"RESULTS.json",result)
        status=result["status"]
        print(canonical_json_bytes(result).decode(),flush=True)
    except BaseException as error:
        task.save(output,"FAILED.json",dict(error_type=type(error).__name__,error=str(error)))
        raise
    finally:
        files=[dict(path=p.relative_to(output).as_posix(),size_bytes=p.stat().st_size,sha256=sha256_file(p))
               for p in sorted(output.rglob("*")) if p.is_file()]
        task.save(output,"SEAL.json",dict(status=status,files=files,source_sha256=task.source_identities(),
            aggregate_sha256=sha256_bytes(canonical_json_bytes(files)),completion_requests=0))


if __name__=="__main__":
    main()
