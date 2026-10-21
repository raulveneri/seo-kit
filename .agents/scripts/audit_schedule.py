#!/usr/bin/env python3
"""Run host-declared audit jobs once or at a fixed interval without a UI."""

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from live_http import checked_url


REPOSITORY = Path(__file__).resolve().parents[2]
OPTIONS = {
    'crawl_limit', 'max_requests', 'max_inspections', 'max_seconds', 'max_disk_bytes',
    'max_response_bytes', 'delay', 'render', 'gsc_property', 'ga4_property',
    'max_sitemaps', 'resource_limit', 'crux_limit', 'amp_validator', 'period_start', 'period_end', 'psi_limit', 'moz_limit', 'api_limit',
    'evidence', 'backlinks_export', 'backlinks_source', 'backlinks_period', 'store_html', 'retention_days',
}
FLAGS = {'crux', 'gsc_performance', 'resume'}
REPEATED = {'priority_url', 'resource_host', 'exclude_parameter', 'exclude_path'}


def outside_repository(path):
    resolved = Path(path).expanduser().resolve()
    if resolved.is_relative_to(REPOSITORY):
        raise ValueError('job configuration and audit artifacts must be outside this repository')
    return resolved


def load_job(path):
    path = outside_repository(path)
    if path.stat().st_size > 1_000_000:
        raise ValueError('job configuration exceeds 1 MB')
    job = json.loads(path.read_text(encoding='utf-8'))
    required = {'url', 'database', 'output_directory'}
    if not isinstance(job, dict) or not required.issubset(job) or set(job) - required - OPTIONS - FLAGS - REPEATED - {'job_timeout_seconds'}:
        raise ValueError('job requires url, database, output_directory and supported audit options only')
    checked_url(job['url'])
    for key in ('database', 'output_directory', 'evidence', 'backlinks_export'):
        if key in job:
            value = Path(job[key]).expanduser()
            if not value.is_absolute():
                value = path.parent / value
            job[key] = str(outside_repository(value))
    if not Path(job['database']).parent.is_dir() or not Path(job['output_directory']).is_dir():
        raise ValueError('database parent and output_directory must already exist')
    for key in FLAGS:
        if key in job and not isinstance(job[key], bool):
            raise ValueError(f'{key} must be boolean')
    for key in REPEATED:
        if key in job and (not isinstance(job[key], list) or any(not isinstance(item, str) for item in job[key])):
            raise ValueError(f'{key} must be a list of strings')
    for key in OPTIONS:
        if key in job and (isinstance(job[key], bool) or not isinstance(job[key], (str, int, float))):
            raise ValueError(f'{key} must be a string or number')
    if 'job_timeout_seconds' in job and (type(job['job_timeout_seconds']) is not int or job['job_timeout_seconds'] < 1):
        raise ValueError('job_timeout_seconds must be a positive integer')
    return job


def run_job(job):
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    output = Path(job['output_directory']) / f'audit-{timestamp}.json'
    command = [sys.executable, str(REPOSITORY / '.agents' / 'scripts' / 'live_audit.py'),
               '--url', job['url'], '--database', job['database'], '--output', str(output), '--format', 'json']
    for key in sorted(OPTIONS):
        if key in job:
            command.extend(['--' + key.replace('_', '-'), str(job[key])])
    for key in sorted(FLAGS):
        if job.get(key):
            command.append('--' + key.replace('_', '-'))
    for key in sorted(REPEATED):
        for value in job.get(key, []):
            command.extend(['--' + key.replace('_', '-'), value])
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=job.get('job_timeout_seconds', 3720))
    except subprocess.TimeoutExpired:
        return {'event': 'audit_finished', 'timestamp': timestamp, 'exit_code': 124,
                'report': None, 'error': 'audit job exceeded job_timeout_seconds. Database can be resumed'}
    return {'event': 'audit_finished', 'timestamp': timestamp, 'exit_code': result.returncode,
            'report': str(output) if result.returncode == 0 else None,
            'error': result.stderr[-4000:].strip() if result.returncode else None}


def main(argv=None):
    parser = argparse.ArgumentParser(description='Run a host-project SEO audit job on a schedule')
    parser.add_argument('--job', required=True, help='host-project JSON job file outside this repository')
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--once', action='store_true', help='one run, suitable for cron or systemd')
    mode.add_argument('--every-seconds', type=int, help='interval between run starts, at least 60 seconds')
    parser.add_argument('--runs', type=int, default=0, help='stop after N runs. 0 means no run limit')
    args = parser.parse_args(argv)
    if (args.every_seconds is not None and args.every_seconds < 60) or args.runs < 0:
        parser.error('interval must be at least 60 seconds and runs must be non-negative')
    try:
        job = load_job(args.job)
        count, failed = 0, False
        while True:
            started = time.monotonic()
            event = run_job(job)
            print(json.dumps(event, ensure_ascii=False), flush=True)
            failed = failed or event['exit_code'] != 0
            count += 1
            if args.once or (args.runs and count >= args.runs):
                return 1 if failed else 0
            time.sleep(max(0, args.every_seconds - (time.monotonic() - started)))
    except KeyboardInterrupt:
        return 130
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as error:
        parser.error(str(error))


if __name__ == '__main__':
    raise SystemExit(main())
