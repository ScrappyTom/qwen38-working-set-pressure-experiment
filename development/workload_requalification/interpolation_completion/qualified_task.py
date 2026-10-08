"""Prospective checkpoint correction; preparation001 remains byte-for-byte intact.

Reuse saved_report_entry's typed address comparison. This lineage's inherited
receipts predate applied_diff, so their sealed map supplies the historical binding;
new entries must match their actual accepted patch receipts.
"""
import completion_task as original


class Task(original.Task):
    def __init__(self, version='002'):
        super().__init__(version)

    def restore(self, state, candidate, replay_folder=None, replay=False):
        value = state['diffs']
        if not isinstance(value, dict):
            raise ValueError('checkpoint diff map is not an address map')
        restored = {}
        for key, diff in value.items():
            if type(key) is int:
                number = key
            elif (type(key) is str and key.isascii() and key.isdecimal()
                    and str(int(key)) == key):
                number = int(key)
            else:
                raise ValueError('checkpoint diff address is not canonical')
            if number <= 0 or number in restored or type(diff) is not str:
                raise ValueError('checkpoint diff address or value differs')
            restored[number] = diff
        expected = {int(k): v for k, v in self.inherited_state['diffs'].items()}
        for number, pair in enumerate(state['pairs'], 1):
            if number <= self.INHERITED_OPERATIONS:
                continue
            if pair['response'].get('action') == 'patch' and pair['result'].get('accepted'):
                diff = pair['result'].get('applied_diff')
                if type(diff) is not str:
                    raise ValueError('checkpoint accepted patch has no exact diff receipt')
                expected[number] = diff
        if restored != expected:
            raise ValueError('checkpoint diff map differs from accepted patch history')
        # Compare in the writer's declared numeric domain. Do not change the
        # input dictionary, saved snapshot, receipt, or historical serializer.
        return super().restore({**state, 'diffs': restored}, candidate, replay_folder, replay)
