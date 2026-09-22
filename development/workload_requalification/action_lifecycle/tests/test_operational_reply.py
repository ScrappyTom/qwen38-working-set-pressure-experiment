"""CPU-only operational contract checks; native decoder qualification is separate."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import operational_reply as subject
from working_set_exp import decision_view, working_view


ROOT = Path(__file__).resolve().parents[4]
CHECKS = {'public': 'Original acceptance check', 'local': 'Scoped check'}
SHA = 'a' * 64
REGION = 'SRC-' + SHA


def converter_class():
    path = ROOT / 'development/bounded_working_set/parser-documentation/grammar-review/json_schema_to_grammar.py'
    assert hashlib.sha256(path.read_bytes()).hexdigest() == 'ee451dc460aa31185226e58988626f64e75ab735169fa3e484fcf16889475ae3'
    spec = importlib.util.spec_from_file_location('operational_schema_converter', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.SchemaConverter


class ReplyTests(unittest.TestCase):
    def test_retained_families_keep_all_original_operations(self):
        operations = [
            dict(action='p0_page', path='src', offset=0),
            dict(action='tree', path='src', offset=0, limit=16),
            dict(action='search', path='src', query='target', offset=0, limit=16),
            dict(action='check', check_id='local', expected_candidate_id=SHA),
            dict(action='submit', expected_candidate_id=SHA),
            dict(action='read', path='a.py', start_line=1, end_line=0),
            dict(action='work_on', sources=[dict(path='a.py', start_line=1, end_line=2)], results=['RES-0001']),
            dict(action='patch', path='a.py', old='old\n', new='new\n', expected_candidate_id=SHA, expected_file_sha256=SHA),
            dict(action='history', before=0, path=''),
            dict(action='reopen_result', handle='RES-0001', offset=0),
            dict(action='reopen_event', handle='EVT-0001', offset=0),
            dict(action='inspect_observation', observation='CHK-0001', stream='stdout', offset=0),
            dict(action='selection_page', offset=0),
            dict(action='work_on_exact', regions=[REGION], results=['EVT-0001']),
            dict(action='inspect_check', observation='CHK-0001', offset=0),
            dict(action='replace_region', region=REGION, expected_candidate_id=SHA, new='literal\n'),
        ]
        expected = {f['properties']['action']['const'] for f in decision_view.action_rule(CHECKS)['oneOf']}
        self.assertEqual({o['action'] for o in operations}, expected)
        for operation in operations:
            for account in (None, '', 'Unresolved; implementation not inspected.'):
                reply = dict(discussion='Next operation.')
                if account is not None:
                    reply['account'] = account
                reply['operation'] = operation
                with self.subTest(action=operation['action'], account=account):
                    self.assertEqual(subject.decode_reply(json.dumps(reply), CHECKS), reply)
                    working_view.validate(reply, decision_view.reply_schema(CHECKS)['json_schema']['schema'])
        for account in ('Unresolved question', ''):
            reply = dict(discussion='Record account.', account=account)
            self.assertEqual(subject.decode_reply(json.dumps(reply), CHECKS), reply)

    def test_discussion_only_and_invalid_forms_reject_without_repair(self):
        invalid = [dict(discussion='Read README next.'), {}, dict(account='note'),
                   dict(discussion='next', account=None),
                   dict(discussion='next', operation={}),
                   dict(discussion='next', account='note', unknown=True),
                   dict(discussion='next', operation=dict(action='stop')),
                   dict(discussion='next', operation=dict(action='read', path='a.py', start_line=0, end_line=0)),
                   dict(discussion='next', operation=dict(action='check', check_id='unknown', expected_candidate_id=SHA)),
                   dict(discussion='next', operation=dict(action='submit', expected_candidate_id=SHA), check_after='public')]
        for reply in invalid:
            original = copy.deepcopy(reply)
            with self.subTest(reply=reply), self.assertRaises(ValueError):
                subject.validate_reply(reply, CHECKS)
            self.assertEqual(reply, original)
        with self.assertRaises(ValueError):
            subject.decode_reply('{"discussion":"one","discussion":"two","account":""}', CHECKS)

    def test_literal_source_preserves_exact_body_with_and_without_account(self):
        body = 'value = "quote: \\\"; slash: \\\\"\r\n# café\nSOURCE\n{"nested":"text"}\n'
        for account in (None, '', 'Provisional source'):
            header = dict(discussion='Save literal source.')
            if account is not None:
                header['account'] = account
            header['operation'] = dict(action='replace_region', region=REGION, expected_candidate_id=SHA)
            content = json.dumps(header, ensure_ascii=False) + '\nSOURCE\n' + body
            reply = subject.decode_reply(content, CHECKS)
            self.assertEqual(reply, decision_view.decode_reply(content))
            self.assertEqual(reply['operation']['new'].encode(), body.encode())
        header = dict(discussion='Delete.', operation=dict(action='replace_region', region=REGION, expected_candidate_id=SHA))
        self.assertEqual(subject.decode_reply(json.dumps(header) + '\nSOURCE\n', CHECKS)['operation']['new'], '')
        with self.assertRaises(ValueError):
            subject.decode_reply(json.dumps(header, indent=2) + '\nSOURCE\n' + body, CHECKS)
        with self.assertRaises(ValueError):
            subject.decode_reply('{"discussion":"not an operation"}\nSOURCE\n' + body, CHECKS)

    def test_old_schema_unchanged_and_only_terminal_form_removed(self):
        original = decision_view.reply_schema(CHECKS)
        snapshot = json.dumps(original)
        new = subject.reply_schema(CHECKS)
        expected = copy.deepcopy(original)
        del expected['json_schema']['schema']['oneOf'][0]
        self.assertEqual(json.dumps(new), json.dumps(expected))
        self.assertEqual(json.dumps(original), snapshot)
        self.assertEqual(json.dumps(decision_view.reply_schema(CHECKS)), snapshot)
        working_view.validate(dict(discussion='Historical stop remains valid.'), original['json_schema']['schema'])
        new['json_schema']['schema']['oneOf'][0]['properties']['discussion']['type'] = 'integer'
        self.assertEqual(json.dumps(decision_view.reply_schema(CHECKS)), snapshot)

    def test_outer_schema_drift_fails_closed(self):
        original = decision_view.reply_schema(CHECKS)
        mutations = []
        missing = copy.deepcopy(original); missing['json_schema']['schema']['oneOf'].pop(0); mutations.append(missing)
        extra = copy.deepcopy(original); extra['json_schema']['schema']['oneOf'].append(extra['json_schema']['schema']['oneOf'][0]); mutations.append(extra)
        reordered = copy.deepcopy(original); reordered['json_schema']['schema']['oneOf'].reverse(); mutations.append(reordered)
        changed = copy.deepcopy(original); changed['json_schema']['schema']['oneOf'][0]['properties']['discussion']['maxLength'] = 8; mutations.append(changed)
        for mutated in mutations:
            with self.subTest(mutated=mutated), patch.object(decision_view, 'reply_schema', return_value=mutated):
                with self.assertRaises(ValueError):
                    subject.reply_schema(CHECKS)

    def test_grammar_reuses_literal_rules_and_narrows_only_ordinary_entry(self):
        converter = converter_class()
        old = decision_view.reply_grammar(CHECKS, converter)
        new = subject.reply_grammar(CHECKS, converter)
        old_rules = dict(line.split(' ::= ', 1) for line in old.splitlines())
        new_rules = dict(line.split(' ::= ', 1) for line in new.splitlines())
        self.assertEqual({k:v for k,v in old_rules.items() if k.startswith('h-')},
                         {k:v for k,v in new_rules.items() if k.startswith('h-')})
        self.assertEqual(old_rules['root'], new_rules['root'])
        self.assertEqual(len(old_rules['ordinary-reply'].split(' | ')), 4)
        self.assertEqual(len(new_rules['ordinary-reply'].split(' | ')), 3)
        # Independent direct conversion of the narrowed ordinary schema must agree.
        direct = converter(prop_order={}, allow_fetch=False, dotall=False, raw_pattern=False)
        direct.visit(subject.reply_schema(CHECKS)['json_schema']['schema'], 'ordinary-reply')
        self.assertEqual(new.split('\nh-', 1)[0], direct.format_grammar())
        self.assertEqual(decision_view.reply_grammar(CHECKS, converter), old)

    def test_missing_ordinary_grammar_entry_fails_closed(self):
        with patch.object(decision_view, 'reply_grammar', return_value='root ::= "bad"'):
            with self.assertRaisesRegex(ValueError, 'not narrowed'):
                subject.reply_grammar(CHECKS, converter_class())

    def test_reference_changes_only_forms_and_terminal_rule(self):
        # Use the actual latest prepared operational input, including task-specific
        # explicit checks and navigation additions; never synthesize tool effects.
        path = ROOT / 'development/workload_requalification/navigation_continuity/receipts/preparation-001/initial-wire-request.json'
        text = json.loads(path.read_text(encoding='utf-8'))['messages'][0]['content']
        new = subject.operating_reference(text)
        expected = text.replace(subject._FORMS_BEFORE, subject._FORMS_AFTER, 1).replace(
            subject._TERMINATION_BEFORE, subject._TERMINATION_AFTER, 1)
        self.assertEqual(new, expected)
        self.assertNotIn('Discussion alone ends the run', new)
        self.assertIn('discussion alone is not an accepted reply', new)
        self.assertIn('An account-only reply records the account and continues.', new)
        self.assertEqual(new[new.index('You may maintain'):], text[text.index('You may maintain'):])
        for changed in (text.replace(subject._FORMS_BEFORE, '', 1),
                        text + subject._FORMS_BEFORE,
                        text.replace(subject._TERMINATION_BEFORE, '', 1),
                        new):
            with self.assertRaises(ValueError):
                subject.operating_reference(changed)


if __name__ == '__main__':
    unittest.main()
