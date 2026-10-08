"""No execution, exact historical quotation, unchanged selected reasoning."""
import copy
import unittest
import consult


class ConsultationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old=consult.original()
        cls.request=consult.request_for(1)

    def test_exact_quotation_and_no_action_channel(self):
        self.assertEqual(len(self.request['messages']),2)
        self.assertNotEqual(self.request['messages'][0],self.old['messages'][0])
        for row in self.old['messages']:
            self.assertIn(row['content'],self.request['messages'][1]['content'])
        self.assertFalse(consult.composition.EXECUTION_KEYS & self.request.keys())
        self.assertFalse(hasattr(consult.task,'process_reply'))

    def test_settings_only_change_seed_and_nonexecuting_messages(self):
        for key,value in self.old.items():
            if key not in consult.composition.EXECUTION_KEYS | {'messages','seed'}:
                self.assertEqual(self.request[key],value,key)
        self.assertEqual(self.request['seed'],42)
        self.assertTrue(all(self.request[k]==-1 for k in consult.composition.BUDGETS))

    def test_added_reviewer_material_is_rejected(self):
        changed=copy.deepcopy(self.request)
        changed['messages'][1]['content']+='\nReviewer-provided missing definition'
        with self.assertRaises(ValueError):
            consult.composition.validate_request(changed,self.old,consult.SYSTEM,
                (consult.AREA/'QUESTION_1.txt').read_text(encoding='utf-8'))

    def test_native_keeps_original_input_inside_review(self):
        native=consult.native_for(self.request)
        self.assertTrue(native.endswith(b'<|im_start|>assistant\n<think>\n'))
        for row in self.old['messages']:
            self.assertIn(row['content'].encode(),native)

    def test_second_dispatch_and_unreviewed_followup_unavailable(self):
        for turn,follow in ((2,None),(1,'unreviewed')):
            with self.assertRaises(ValueError): consult.request_for(turn,follow)


if __name__=='__main__': unittest.main()
