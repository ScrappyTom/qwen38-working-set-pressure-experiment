"""Use the real qualification logger, not a simplified record mock."""
import copy
from pathlib import Path
import tempfile
import unittest

import verify_preparation_envelope as audit
from manage import legacy
from working_set_exp.custody import verify_records


class EnvelopeTests(unittest.TestCase):
    def test_real_envelope_and_exact_body_preserved_with_negative_controls(self):
        task=audit.original.study.Task('E14-CLOSURE-MINT')
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            log=legacy.QualificationLog(root/'records.jsonl','qualification-envelope-test',task_module=task)
            task.attach_observations(task.initial_session(),root,log)
            records=verify_records(root/'records.jsonl',root)
            self.assertEqual(audit.qualified_imports(task,root,records,['']),3)
            with self.assertRaises(AssertionError):
                audit.DOMAIN_CHECK(task,root,records,[''])
            original=copy.deepcopy(records)
            for key,value in [('qualification_only',False),('completion_sent',True),('actor_acquisitions',1)]:
                damaged=copy.deepcopy(records)
                damaged[0]['payload'][key]=value
                with self.subTest(key=key), self.assertRaises(AssertionError):
                    audit.qualified_imports(task,root,damaged,[''])
            self.assertEqual(records,original)
            (root/'imported-captures/OBS-0001.json').write_bytes(task.imports()[2]['OBS-0002'])
            with self.assertRaises(AssertionError):
                audit.qualified_imports(task,root,records,[''])


if __name__=='__main__': unittest.main()
