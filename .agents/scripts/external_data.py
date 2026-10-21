"""Bounded read-only enrichment for a persisted crawl.

Collect configured API responses without persisting authentication tokens.
"""

import json
import os
import re
import time
from datetime import date
from urllib.parse import quote, urlencode

from crawl_store import now, url_key

API_PAGE_SIZE = 1000


def api_json(client, url, *, payload=None, headers=None):
    for attempt in range(3):
        response = client.fetch(url, method='POST' if payload is not None else 'GET',
                                body=json.dumps(payload).encode() if payload is not None else None,
                                headers=({'Content-Type': 'application/json'} if payload is not None else {}) | (headers or {}),
                                allow_redirects=False)
        if response.status not in (429, 500, 502, 503, 504) or attempt == 2:
            break
        delay = min(2 ** attempt, 2)
        if hasattr(client, 'remaining_time') and client.remaining_time() <= delay:
            raise ValueError('API retry time budget exhausted')
        time.sleep(delay)
    if response.status != 200:
        raise ValueError(f'API returned HTTP {response.status}')
    result = json.loads(response.body)
    if not isinstance(result, dict):
        raise ValueError('API response must be a JSON object')
    return result


def cached(store, crawl_id, url, source, property_name, period):
    row = store.db.execute('SELECT data_json FROM external_data WHERE crawl_id=? AND url=? AND source=? AND property=? AND period=?',
                           (crawl_id, url, source, property_name, period)).fetchone()
    return json.loads(row[0]) if row else None


def enrich(store, crawl_id, origin, urls, client, *, ga4_property=None,
           gsc_property=None, period=None, psi_limit=0, moz_limit=0,
           api_limit=50, crux_limit=0):
    """Query selected sources with explicit limits. Return coverage, never inferred passes."""
    selected = urls[:api_limit]
    selected_keys = {url_key(url): url for url in selected}
    summary = {'selected_urls': len(selected), 'available_urls': len(urls), 'sources': {}, 'warnings': []}
    start_date, end_date = period if period else (None, None)
    period_label = f'{start_date} to {end_date}' if period else None
    if ga4_property:
        token = os.environ.get('SEO_KIT_GA4_ACCESS_TOKEN')
        prior = cached(store, crawl_id, origin, 'ga4_query', ga4_property, period_label) if period_label else None
        if prior and prior.get('requested_limit', 0) >= api_limit and prior.get('selected_urls') == selected:
            summary['sources']['ga4'] = prior
        elif not token:
            summary['warnings'].append('GA4 unmeasured: SEO_KIT_GA4_ACCESS_TOKEN absent')
        elif not re.fullmatch(r'\d+', ga4_property) or not period:
            summary['warnings'].append('GA4 unmeasured: numeric property and date range required')
        else:
            try:
                collected, offset, total = [], 0, None
                while offset < api_limit:
                    result = api_json(client, f'https://analyticsdata.googleapis.com/v1beta/properties/{ga4_property}:runReport',
                        payload={'dateRanges': [{'startDate': start_date, 'endDate': end_date}],
                                 'dimensions': [{'name': 'pageLocation'}],
                                 'metrics': [{'name': 'screenPageViews'}, {'name': 'activeUsers'}],
                                 'limit': str(min(API_PAGE_SIZE, api_limit - offset)), 'offset': str(offset)}, headers={'Authorization': 'Bearer ' + token})
                    page = result.get('rows', [])
                    if not isinstance(page, list):
                        raise ValueError('GA4 rows must be an array')
                    collected.extend(page)
                    offset += len(page)
                    total = result.get('rowCount')
                    if not page or len(page) < min(API_PAGE_SIZE, api_limit - offset + len(page)) or isinstance(total, int) and offset >= total:
                        break
                result = {'rows': collected, 'rowCount': total}
                count = 0
                for row in result.get('rows', []):
                    url = row.get('dimensionValues', [{}])[0].get('value')
                    if url and url_key(url) in selected_keys:
                        url = selected_keys[url_key(url)]
                        values = row.get('metricValues', [])
                        store.external(crawl_id, url, 'ga4', ga4_property, period_label,
                                       {'screen_page_views': values[0].get('value') if values else None,
                                        'active_users': values[1].get('value') if len(values) > 1 else None})
                        count += 1
                summary['sources']['ga4'] = {'rows_matched': count, 'rows_returned': len(result.get('rows', [])),
                    'row_count': result.get('rowCount'), 'requested_limit': api_limit, 'selected_urls': selected, 'status': 'measured_sample' if count else 'unmeasured', 'coverage': 'sample, query may be truncated'}
                store.external(crawl_id, origin, 'ga4_query', ga4_property, period_label, summary['sources']['ga4'])
            except (OSError, ValueError, KeyError, TypeError, IndexError, AttributeError) as error:
                summary['warnings'].append(f'GA4 unmeasured: {type(error).__name__}: {error}')
    if gsc_property:
        token = os.environ.get('SEO_KIT_GSC_ACCESS_TOKEN')
        prior = cached(store, crawl_id, origin, 'gsc_performance_query', gsc_property, period_label) if period_label else None
        if prior and prior.get('requested_limit', 0) >= api_limit and prior.get('selected_urls') == selected:
            summary['sources']['gsc_performance'] = prior
        elif not token:
            summary['warnings'].append('GSC performance unmeasured: SEO_KIT_GSC_ACCESS_TOKEN absent')
        elif not period:
            summary['warnings'].append('GSC performance unmeasured: date range required')
        else:
            try:
                endpoint = 'https://www.googleapis.com/webmasters/v3/sites/' + quote(gsc_property, safe='') + '/searchAnalytics/query'
                collected, offset = [], 0
                while offset < api_limit:
                    batch = min(API_PAGE_SIZE, api_limit - offset)
                    result = api_json(client, endpoint,
                        payload={'startDate': start_date, 'endDate': end_date, 'dimensions': ['page'], 'rowLimit': batch, 'startRow': offset},
                        headers={'Authorization': 'Bearer ' + token})
                    page = result.get('rows', [])
                    if not isinstance(page, list):
                        raise ValueError('GSC rows must be an array')
                    collected.extend(page)
                    offset += len(page)
                    if len(page) < batch:
                        break
                result = {'rows': collected}
                count = 0
                for row in result.get('rows', []):
                    url = row.get('keys', [None])[0]
                    if url and url_key(url) in selected_keys:
                        url = selected_keys[url_key(url)]
                        store.external(crawl_id, url, 'gsc_performance', gsc_property, period_label,
                            {key: row.get(key) for key in ('clicks', 'impressions', 'ctr', 'position')})
                        count += 1
                summary['sources']['gsc_performance'] = {'rows_matched': count, 'rows_returned': len(result.get('rows', [])),
                    'requested_limit': api_limit, 'selected_urls': selected, 'status': 'measured_sample' if count else 'unmeasured', 'coverage': 'top rows only, Search Console does not guarantee all rows'}
                store.external(crawl_id, origin, 'gsc_performance_query', gsc_property, period_label, summary['sources']['gsc_performance'])
            except (OSError, ValueError, KeyError, TypeError, IndexError, AttributeError) as error:
                summary['warnings'].append(f'GSC performance unmeasured: {type(error).__name__}: {error}')
    if psi_limit:
        key = os.environ.get('SEO_KIT_PSI_API_KEY')
        if not key:
            summary['warnings'].append('PageSpeed unmeasured: SEO_KIT_PSI_API_KEY absent')
        else:
            count = 0
            for url in selected[:psi_limit]:
                if store.db.execute('SELECT 1 FROM external_data WHERE crawl_id=? AND url=? AND source="pagespeed_lab" LIMIT 1', (crawl_id, url)).fetchone():
                    count += 1
                    continue
                try:
                    endpoint = 'https://pagespeedonline.googleapis.com/pagespeedonline/v5/runPagespeed?' + urlencode({'url': url, 'strategy': 'mobile', 'key': key})
                    result = api_json(client, endpoint)
                    lighthouse = result.get('lighthouseResult', {})
                    score = lighthouse.get('categories', {}).get('performance', {}).get('score')
                    if isinstance(score, bool) or not isinstance(score, (float, int)) or not 0 <= score <= 1:
                        raise ValueError('PageSpeed returned no Lighthouse performance score')
                    store.external(crawl_id, url, 'pagespeed_lab', origin, result.get('analysisUTCTimestamp', now()),
                        {'performance_score': score,
                         'audits': lighthouse.get('audits', {}), 'categories': lighthouse.get('categories', {}), 'runtime_error': lighthouse.get('runtimeError'), 'warnings': lighthouse.get('runWarnings', []), 'environment': lighthouse.get('environment', {}),
                         'lighthouse_version': lighthouse.get('lighthouseVersion'), 'kind': 'lab'})
                    count += 1
                except (OSError, ValueError, KeyError, TypeError, IndexError, AttributeError) as error:
                    summary['warnings'].append(f'PageSpeed {url} unmeasured: {type(error).__name__}: {error}')
            summary['sources']['pagespeed_lab'] = {'queried_urls': count, 'selected_urls': min(psi_limit, len(selected)), 'status': 'measured_sample' if count else 'unmeasured'}
    if moz_limit:
        token = os.environ.get('SEO_KIT_MOZ_TOKEN')
        prior = cached(store, crawl_id, origin, 'moz_link_sample', origin, 'index state at query time')
        if prior and prior.get('requested_limit', 0) >= min(moz_limit, 50):
            summary['sources']['moz_link_sample'] = {'rows_returned': prior['rows_returned'], 'requested_limit': prior['requested_limit'], 'coverage': 'sample only', 'status': 'measured_sample' if prior['rows_returned'] else 'unmeasured'}
        elif not token:
            summary['warnings'].append('Moz unmeasured: SEO_KIT_MOZ_TOKEN absent')
        else:
            try:
                if not store.reserve_quota('moz_rows', now()[:7], min(moz_limit, 50), 50):
                    raise ValueError('local monthly Moz budget of 50 rows exhausted. Reservations include failed queries')
                result = api_json(client, 'https://api.moz.com/jsonrpc', payload={
                    'jsonrpc': '2.0', 'id': 'seo-kit-link-sample', 'method': 'data.site.link.list',
                    'params': {'data': {'site_query': {'query': origin, 'scope': 'root_domain'}, 'offset': {'limit': min(moz_limit, 50)}}}},
                    headers={'x-moz-token': token})
                if result.get('error'):
                    raise ValueError('Moz API returned an error')
                data = result.get('result', {})
                links = data.get('links', [])
                if not isinstance(links, list) or len(links) > min(moz_limit, 50):
                    raise ValueError('Moz returned an invalid or oversized sample')
                store.external(crawl_id, origin, 'moz_link_sample', origin, 'index state at query time',
                    {'links': links, 'rows_returned': len(links), 'requested_limit': min(moz_limit, 50),
                     'status': 'measured_sample' if links else 'unmeasured',
                     'coverage': 'sample only, not a complete link profile'})
                summary['sources']['moz_link_sample'] = {'rows_returned': len(links), 'requested_limit': min(moz_limit, 50),
                    'coverage': 'sample only', 'status': 'measured_sample' if links else 'unmeasured'}
            except (OSError, ValueError, KeyError, TypeError, IndexError, AttributeError) as error:
                summary['warnings'].append(f'Moz unmeasured: {type(error).__name__}: {error}')
    if crux_limit:
        key = os.environ.get('SEO_KIT_CRUX_API_KEY')
        measured = 0
        if not key:
            summary['warnings'].append('CrUX URL unmeasured: SEO_KIT_CRUX_API_KEY absent')
        else:
            for url in selected[:crux_limit]:
                previous = store.db.execute('SELECT data_json FROM external_data WHERE crawl_id=? AND url=? AND source="crux_url_field" AND property=? ORDER BY queried_at DESC LIMIT 1', (crawl_id, url, origin)).fetchone()
                prior = json.loads(previous[0]) if previous else None
                if prior is not None:
                    measured += prior.get('status') == 'measured'
                    continue
                try:
                    data = api_json(client, 'https://chromeuxreport.googleapis.com/v1/records:queryRecord', payload={'url': url, 'formFactor': 'PHONE'}, headers={'X-Goog-Api-Key': key})
                    record = data.get('record')
                    if not isinstance(record, dict) or not record.get('metrics') or not record.get('collectionPeriod'):
                        raise ValueError('CrUX URL record has no field data')
                    collection = record['collectionPeriod']
                    bounds = [date(**{key: collection[bound][key] for key in ('year','month','day')}).isoformat() for bound in ('firstDate','lastDate')]
                    store.external(crawl_id, url, 'crux_url_field', origin, ' to '.join(bounds), {'status': 'measured', 'kind': 'field', 'record': record})
                    measured += 1
                except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
                    store.external(crawl_id, url, 'crux_url_field', origin, 'latest collection', {'status': 'unmeasured', 'reason': str(error), 'kind': 'field'})
            summary['sources']['crux_url_field'] = {'measured_urls': measured, 'selected_urls': min(crux_limit, len(selected)), 'status': 'measured_sample' if measured else 'unmeasured'}
    return summary
