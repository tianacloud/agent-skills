import json
import unittest
from datetime import datetime, timezone
from unittest.mock import patch
import tiana_debug as debug
from test_tiana_debug import FakeBackend


def record(stamp, **fields):
    return {'time_unix_nano': str(stamp), 'stream': {}, 'line': json.dumps(fields), 'fields': fields}


class WebDeletionTests(unittest.TestCase):
    def collect(self, events, links=None):
        links = links or [record(100, component='mgr', event='web.deletion.link', request_id='req', tenant_id='a', project_id='same')]
        client = FakeBackend([(int(r['time_unix_nano']), r['line']) for r in events])
        gaps = []
        with patch.object(debug, 'fetch_traces', side_effect=lambda c, ids, g: {i: {'batches': []} for i in ids}) as fetch:
            result, traces = debug.web_deletion_evidence(client, 'test', 'req', links,
                datetime.fromtimestamp(0, timezone.utc), datetime.fromtimestamp(1, timezone.utc), gaps)
        return result, traces, gaps, client

    def test_identity_history_and_independent_trace(self):
        events = [record(50, component='mgr', tenant_id='a', project_id='same', event='web.deletion.batch_completed', outcome='failed'),
                  record(150, component='mgr', tenant_id='b', project_id='same', event='web.deletion.completed', state='deleted'),
                  record(160, component='mgr', tenant_id='a', project_id='same', event='unrelated.failed', level='error'),
                  record(170, component='mgr', tenant_id='a', project_id='same', event='web.deletion.batch_completed', outcome='success', trace_id='1'*32),
                  record(180, component='mgr', tenant_id='a', project_id='same', event='web.deletion.completed', state='deleted', trace_id='2'*32)]
        result, traces, gaps, client = self.collect(events)
        self.assertEqual(result[0]['state'], 'deleted')
        self.assertEqual(len(result[0]['events']), 2)
        self.assertEqual(set(traces), {'1'*32, '2'*32})
        self.assertFalse(gaps)
        for _, _, params in client.queries:
            self.assertIn('tenant_id', params['query'])
            self.assertIn('project_id', params['query'])
            self.assertIn('event', params['query'])

    def test_concurrent_tenants_same_project_remain_independent(self):
        links = [record(100, component='mgr', event='web.deletion.link', request_id='req', tenant_id=t, project_id='same') for t in ('a', 'b')]
        events = [record(180, component='mgr', tenant_id='a', project_id='same', event='web.deletion.completed', state='deleted', trace_id='a'*32),
                  record(190, component='mgr', tenant_id='b', project_id='same', event='web.deletion.batch_completed', outcome='failed', trace_id='b'*32)]
        result, traces, gaps, _ = self.collect(events, links)
        self.assertEqual([(r['tenant_id'], r['state']) for r in result], [('a', 'deleted'), ('b', 'unknown')])
        self.assertEqual(result[0]['trace_ids'], ['a'*32])
        self.assertEqual(result[1]['trace_ids'], ['b'*32])
        self.assertTrue(gaps)

    def test_web_link_satisfies_accepted_association(self):
        logs = [record(100, component='mgr', event='request.completed', request_id='req', status=202),
                record(101, component='mgr', event='web.deletion.link', request_id='req', tenant_id='a', project_id='same')]
        gaps = []
        debug.async_acceptance_gaps(logs, gaps)
        self.assertFalse(gaps)

    def test_batch_success_is_not_terminal_and_absence_is_unknown(self):
        event = record(170, component='mgr', tenant_id='a', project_id='same', event='web.deletion.batch_completed', outcome='success')
        for events in ([], [event]):
            result, _, gaps, _ = self.collect(events)
            self.assertEqual(result[0]['state'], 'unknown')
            self.assertTrue(any('terminal' in gap for gap in gaps))

    def test_only_exact_request_mgr_link_can_expand(self):
        for fields in ({'request_id': 'other'}, {'component': 'control'}, {'tenant_id': ''}):
            link = record(100, component='mgr', event='web.deletion.link', request_id='req', tenant_id='a', project_id='same')
            link['fields'].update(fields)
            result, _, _, client = self.collect([], [link])
            self.assertFalse(result)
            self.assertFalse(client.queries)

    def test_truncated_result_remains_partial(self):
        events = [record(170, component='mgr', tenant_id='a', project_id='same', event='web.deletion.completed', state='deleted')]
        with patch.object(debug, 'PAGE_LIMIT', 1):
            result, _, gaps, _ = self.collect(events)
        self.assertEqual(result[0]['state'], 'deleted')
        self.assertTrue(any('truncat' in gap.lower() or 'saturat' in gap.lower() for gap in gaps))

if __name__ == '__main__':
    unittest.main()
