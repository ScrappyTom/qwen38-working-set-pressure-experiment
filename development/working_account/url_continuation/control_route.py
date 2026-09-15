"""Rejected joint updates followed by recovery; researcher-scripted, no inference."""
import continuation_task as study
import manage_continuation as management
import qualify


def scripted_reply(module, session, number):
    if number <= 2:
        text = ("A specific pending question." if number == 1 else "Explicit qualification size stress. " * 9000)
        sources = [dict(path="missing.py", start_line=1, end_line=0)] if number == 1 else []
        return dict(discussion="Offline rejection-path qualification, not task material or model behavior.",
                    account=text, operation=dict(action="work_on", sources=sources, results=[]))
    if number == 3:
        assert session.working_account() is None
        assert session.ranges == study.initial_session().ranges
        assert all(not p["result"]["accepted"] for p in session.pairs[-2:])
    return management.scripted_reply(module, session, number - 2)


if __name__ == "__main__":
    qualify.manage.prepare_one(study.Task("capacity"), scripted_reply, [True, True])
