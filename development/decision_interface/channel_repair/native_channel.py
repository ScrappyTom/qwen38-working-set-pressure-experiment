"""Native delimiter-to-final qualification; no inference or task execution."""
import argparse
import json
from types import SimpleNamespace

import channel_task as study
from manage import load_helper


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--folder', default='native-001')
    args = parser.parse_args()
    harness = load_helper('channel_native_harness', 'development/decision_interface/native.py')
    original_cases = harness.cases
    def cases():
        for name, final, wanted in original_cases():
            yield name, 'Check the requested reply.\n</think>\n' + final, wanted
        final = json.dumps(dict(discussion='transport ready'))
        yield 'empty_thinking', '</think>\n' + final, True
        yield 'action_shaped_private_text', '{"operation":{"action":"submit"}}\n</think>\n' + final, True
        yield 'overlapping_delimiter_prefixes', '<< / </t </th </thi </thin </think <<think> é\n</think>\n' + final, True
        yield 'long_thinking', ('Review a provisional result.\n'*4000) + '</think>\n' + final, True
        yield 'no_close_no_final', final, False
        yield 'close_but_incomplete_final', '</think>\n{"discussion":', False
        yield 'close_but_wrong_final', '</think>\nThis is not an action.', False
    def decode_synthetic(text):
        # Only researcher-constructed grammar test strings; never live output.
        # Production still accepts the endpoint's complete final field alone.
        return study.decode_reply(text.split('</think>', 1)[1].lstrip())
    harness.study = study
    harness.cases = cases
    harness.decision_view = SimpleNamespace(decode_reply=decode_synthetic)
    # The inherited grammar test tokenizes ordinary final text. For this boundary,
    # use the same code with special-token recognition enabled so </think> is real.
    import inspect
    source = inspect.getsource(harness.run).replace('False,False);assert count>=0', 'False,True);assert count>=0')
    namespace = dict(harness.__dict__)
    exec(compile(source, __file__ + ':native_harness', 'exec'), namespace)
    namespace['run'](study.AREA/args.folder)


if __name__ == '__main__':
    main()
