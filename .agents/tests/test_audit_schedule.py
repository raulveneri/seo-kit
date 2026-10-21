"""Scheduled audit job configuration and process-boundary tests."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))

from audit_schedule import load_job, run_job


class ScheduleTests(unittest.TestCase):
    def test_job_resolves_host_paths_and_passes_arguments_without_shell(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'job.json'
            path.write_text(json.dumps({'url': 'https://example.org/', 'database': 'crawl.sqlite',
                                       'output_directory': '.', 'crawl_limit': '500',
                                       'exclude_path': ['$(touch should-not-exist)'], 'job_timeout_seconds': 10}), encoding='utf-8')
            job = load_job(path)
            with patch('audit_schedule.subprocess.run', return_value=subprocess.CompletedProcess([], 0, '', '')) as process:
                event = run_job(job)
            arguments = process.call_args.args[0]
            self.assertIn('500', arguments)
            self.assertIn('$(touch should-not-exist)', arguments)
            self.assertNotIn('shell', process.call_args.kwargs)
            self.assertEqual(process.call_args.kwargs['timeout'], 10)
            self.assertEqual(event['exit_code'], 0)
            self.assertTrue(Path(event['report']).parent == Path(directory))

    def test_timeout_emits_machine_readable_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            job = {'url': 'https://example.org/', 'database': str(Path(directory) / 'crawl.sqlite'), 'output_directory': directory}
            with patch('audit_schedule.subprocess.run', side_effect=subprocess.TimeoutExpired([], 1)):
                event = run_job(job)
            self.assertEqual(event['exit_code'], 124)
            self.assertIsNone(event['report'])

    def test_once_cli_returns_failed_job_status_without_network(self):
        root = Path(__file__).resolve().parents[2]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'job.json'
            path.write_text(json.dumps({'url': 'https://example.org/', 'database': 'crawl.sqlite',
                                       'output_directory': '.', 'max_requests': 0}), encoding='utf-8')
            result = subprocess.run([sys.executable, '.agents/scripts/audit_schedule.py', '--job', str(path), '--once'],
                                    cwd=root, capture_output=True, text=True)
            self.assertEqual(result.returncode, 1)
            event = json.loads(result.stdout)
            self.assertEqual(event['exit_code'], 2)
            self.assertIsNone(event['report'])


if __name__ == '__main__':
    unittest.main()
