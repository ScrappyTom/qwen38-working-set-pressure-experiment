"""Opt-in decision interface: stable visible evidence and explicit check criteria."""
import ast
import copy
import difflib

from . import check_assessment, decision_view
from .candidate import Candidate
from .jsonutil import sha256_bytes
from .operable_session import OperableSession
from .working_session import WorkingSession, MAX_FRAGMENT_BYTES


class DecisionSession(OperableSession):
    mutation_actions = ('patch', 'replace_region')
    assessment_api = check_assessment

    def __init__(self, *args, check_contracts=None, **kwargs):
        self.recovery_focus = []
        self.check_contracts = copy.deepcopy(check_contracts or {})
        super().__init__(*args, **kwargs)
        if any(scope not in self.checkers or contract.get('checker_sha256')!=sha256_bytes(self.checkers[scope])
               for scope,contract in self.check_contracts.items()):
            raise ValueError('check interpretation contract belongs to a different checker')

    def clone(self):
        other = super().clone()
        other.recovery_focus = copy.deepcopy(self.recovery_focus)
        return other

    def action_rule(self):
        from .accounted_contribution import account_rule
        return dict(oneOf=[*decision_view.action_rule(self.checkers)['oneOf'], account_rule()])

    def reply_schema(self):
        return decision_view.reply_schema(self.checkers)

    def edit_scope(self, action):
        if not action:
            return None
        if action['action'] == 'replace_region':
            try:
                return self.edit_checks.get(self.resolve_region(action['region'])['path'])
            except ValueError:
                return None  # The operation itself returns a clean guarded rejection.
        return super().edit_scope(action)

    def _contract(self, handle):
        record = self.observations.read(handle)
        contract = self.check_contracts.get(record['check_id'])
        return contract if contract and contract['checker_sha256']==record['checker_sha256'] else None

    def _assessment(self, handle):
        return self.assessment_api.assessment(self.observations, handle, self._contract(handle))

    def verification_view(self):
        checks = {}
        for scope in self.checkers:
            state = self.scoped_check_state(scope)
            if state:
                sequence = int(state['handle'].split('-')[1])
                result = self.pairs[sequence-1]['result']
                state = dict(state)
                if result.get('observation'):
                    value = self._assessment(result['observation'])
                    state['assessment'] = self.assessment_api.overview(value)
                    state['inspect'] = dict(action='inspect_check', observation=result['observation'], offset=0)
                else:
                    state['assessment_unavailable'] = 'Historical receipt has no preserved observation in this configuration.'
            checks[scope] = state
        public = checks['public']
        return dict(checks=checks, after_accepted_edit=dict(self.edit_checks),
                    submission=dict(scope='public', eligible=bool(public and public['applies_to_current'] and public['passed'])),
                    outstanding=[dict(scope=s, criteria=v.get('assessment',{}).get('failed_criteria', []),
                                      result_handle=v['handle']) for s,v in checks.items()
                                 if v and v['applies_to_current'] and not v['passed']])

    def view(self, **kwargs):
        value = super().view(**kwargs)
        value.pop('current_check')
        value['verification'] = self.verification_view()
        value['schema_version'] = 'decision-view-v1'
        if self.recovery:
            account = self.working_account()
            if account and self.control_tier == 0:
                value['working_account'] = dict(account, text_complete=True)
            elif account:
                raw = account['text'].encode()
                size = 512 if self.control_tier == 1 else 0
                prefix = raw[:size].decode('utf-8',errors='ignore')
                value['working_account'] = {k:v for k,v in account.items() if k!='text'} | dict(
                    text_prefix=prefix, text_complete=len(prefix.encode())==len(raw), full_text_bytes=len(raw),
                    exact_text_in=account['action_handle'], display_reduction_reason='complete input did not fit with the fuller account')
            # A final control fallback may omit bodies, but never forget retained focus.
            visible = [self.source(span) for span in self.recovery_focus] if self.control_tier < 2 else []
        else:
            visible = self.sources()
        # No raw source bodies are hidden inside feedback. The list is authoritative
        # for current-source visibility, independent of the deduplication layout.
        value['working_set']['sources'] = visible
        value['latest_feedback'] = decision_view.receipt_view(value['latest_feedback'])
        if value['latest_feedback']:
            result=value['latest_feedback']['result']
            if result.get('executed') and result.get('observation') and result.get('check_id'):
                result['report']=self.assessment_api.overview(self._assessment(result['observation']))
        visible_spans = self._verified_source_ranges(visible)
        inventory = self.selection_inventory(count=8)
        for entry in inventory['entries']:
            if entry['kind'] == 'source':
                entry['body_shown_in_full'] = any(s['path']==entry['path'] and s['start_line']<=entry['start_line'] and s['end_line']>=entry['end_line'] for s in visible_spans)
        value.pop('selection', None)  # One inventory, with actual visibility below.
        value['presentation']['selected_bodies_omitted'] = bool(
            self.recovery and (self.saved or any(not any(
                s['path']==r['path'] and s['start_line']<=r['start_line'] and s['end_line']>=r['end_line']
                for s in visible_spans) for r in self.ranges)))
        value['visibility'] = dict(source_bodies='working_set.sources', retained_inventory=inventory,
            shown_regions=[s['region_ref'] for s in visible],
            recovery_inspections_retained=len(self.recovery_focus),
            capacity_omitted_inspections=bool(self.recovery and self.control_tier==2 and self.recovery_focus))
        return value

    def mark_delivered(self, view):
        if view != self.view():
            raise ValueError('delivered decision view differs')
        self.delivered_sources = copy.deepcopy(view['working_set']['sources'])
        pages = list(view['working_set']['saved_results'])
        if view['latest_feedback']:
            result = view['latest_feedback']['result']
            pages.extend(result.get('saved_results', []))
            if result.get('kind') == 'saved_bytes':
                pages.append(result)
        for page in pages:
            self.delivered_sources.extend(self._archived_sources_visible(page))

    def summary(self, sequence):
        row = super().summary(sequence)
        action = self.pairs[sequence-1]['response']
        for key in ('start_line','end_line','region','observation','stream','offset'):
            if key in action:
                row[key] = action[key]
        return row

    def _record(self, action, result):
        super()._record(action, result)
        if self.recovery and action['action']=='read' and result.get('accepted'):
            source = result['source']
            span = dict(path=source['path'], start_line=source['returned_start_line'], end_line=source['returned_end_line'])
            if span not in self.recovery_focus:
                self.recovery_focus.append(span)

    def _fit_pages(self, action, spans, handles, measure, replace):
        if replace:
            other = self.clone()
            other.recovery, other.control_tier, other.recovery_obstacle = False, 0, None
            other.recovery_focus = []
            return WorkingSession._fit_pages(other, action, spans, handles, measure, True)
        if self.recovery:
            other = self.clone()
            other._inspect_only = False
            other.control_tier = 0
            return WorkingSession._fit_pages(other, action, spans, handles, measure, False)
        return super()._fit_pages(action, spans, handles, measure, False)

    def _fits_feedback(self, measure):
        if self.recovery:
            self.control_tier = 0
        return super()._fits_feedback(measure)

    def _select(self, action, measure):
        result = super()._select(action, measure)
        result.recovery_focus = []
        return result

    def _refresh_ranges(self, *args):
        super()._refresh_ranges(*args)
        selected = self.ranges
        try:
            self.ranges = copy.deepcopy(self.recovery_focus)
            super()._refresh_ranges(*args)
            self.recovery_focus = self.ranges
        finally:
            self.ranges = selected

    def commit_admission_error(self, action):
        if action['action']=='replace_region':
            return 'The complete replacement and refreshed evidence cannot fit; no edit committed. Select a smaller group.'
        return super().commit_admission_error(action)

    def _patch(self, action):
        if action['action'] != 'replace_region':
            return super()._patch(action)
        span = self.resolve_region(action['region'])
        path, before = span['path'], self.candidate
        if action['expected_candidate_id'] != before.candidate_id:
            raise ValueError('stale candidate binding')
        if not any(s['path']==path and s['start_line']<=span['start_line'] and s['end_line']>=span['end_line']
                   for s in self._verified_source_ranges(self.delivered_sources)):
            raise ValueError('complete replacement region was not visible in the preceding input')
        text, new = before.file_map[path].decode(), action['new']
        lines = text.splitlines(keepends=True)
        start = len(''.join(lines[:span['start_line']-1]))
        end = len(''.join(lines[:span['end_line']]))
        old = text[start:end]
        if old == new or max(len(old.encode()),len(new.encode())) > MAX_FRAGMENT_BYTES:
            raise ValueError('replacement must change source and fit the host fragment allowance')
        changed = text[:start]+new+text[end:]
        files = before.file_map
        files[path] = changed.encode()
        self.candidate = Candidate.create(files,max_file_bytes=before.max_file_bytes)
        self.versions[self.candidate.candidate_id] = self.candidate
        self._refresh_ranges(path,text,changed,start,end,new)
        self.diffs[len(self.pairs)+1] = ''.join(difflib.unified_diff(text.splitlines(keepends=True),changed.splitlines(keepends=True),fromfile='a/'+path,tofile='b/'+path))
        return dict(accepted=True,path=path,previous_candidate_id=before.candidate_id,
                    candidate_id=self.candidate.candidate_id,file_sha256=self.candidate.file_sha256(path),
                    replaced_region=action['region'],old_source_sha256=sha256_bytes(old.encode()),
                    exact_action_handle=f'EVT-{len(self.pairs)+1:04d}')

    def _ordinary(self, action):
        name = action['action']
        if name == 'inspect_check':
            return self.assessment_api.inspect_check(self.observations, action['observation'], action['offset'], self._contract(action['observation']))
        result = super()._ordinary(action)
        if name == 'search' and result.get('accepted'):
            # Return a mechanically identified edit-sized region, not merely a
            # context prefix that makes the actor count an entire function's lines.
            for match in result.get('matches', []):
                if not match['path'].endswith('.py'):
                    continue
                try:
                    tree = ast.parse(self.candidate.file_map[match['path']].decode())
                except SyntaxError:
                    continue
                found = [n for n in ast.walk(tree) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))
                         and min([n.lineno,*[d.lineno for d in n.decorator_list]])<=match['line']<=n.end_lineno]
                if found:
                    node = min(found,key=lambda n:n.end_lineno-n.lineno)
                    region = dict(**self.region(match['path'],self.candidate.file_sha256(match['path']),
                        min([node.lineno,*[d.lineno for d in node.decorator_list]]),node.end_lineno),
                        extent_kind='enclosing Python function',name=node.name)
                    if region not in result.setdefault('regions',[]):
                        result['regions'].append(region)
        if name == 'check' and result.get('observation'):
            # The executed observation remains durable even if this later view fails.
            try:
                result['report'] = self.assessment_api.overview(self._assessment(result['observation']))
            except (ValueError, TypeError, KeyError, AttributeError) as error:
                result['assessment_status'] = 'unavailable'
                result['assessment_error'] = type(error).__name__
        if name == 'inspect_observation' and result.get('accepted'):
            result['observation_capture_complete'] = result.pop('capture_complete')
            result['shown_bytes'] = (result['next_offset'] or result['captured_bytes']) - result['offset']
            result['page_complete'] = result['offset']==0 and result['next_offset'] is None
            result['raw_page_may_split_serialized_record'] = not result['page_complete']
        return result
