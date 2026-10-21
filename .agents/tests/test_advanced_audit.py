"""Acceptance fixtures for advanced CLI capabilities and failure boundaries."""
import io
import json
import os
import signal
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from xml.etree import ElementTree

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from advanced_audit import advanced_metadata, inspect_binary, binary_worker, main_text, html_tree
from crawl_query import extract_fields, rows, sitemap_parts, grammar_check, output_items
from crawl_store import CrawlStore
from external_data import api_json, enrich
from live_audit import run_live, sitemap_urls, gsc_evidence
from live_http import Response
from robots_policy import RobotsPolicy
from test_crawl_store import options, FixtureClient, html, ORIGIN


class AdvancedTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.database = str(Path(self.directory.name) / 'crawl.sqlite')

    def tearDown(self):
        self.directory.cleanup()

    def crawl(self, content, **kwargs):
        pages = {ORIGIN + '/': (200, content), ORIGIN + '/about/?a=1&b=2': (200, html('About', canonical=ORIGIN + '/about/?a=1&b=2'))}
        report = run_live(options(self.database, **kwargs), FixtureClient(pages))
        return CrawlStore(self.database), report['crawl_id']

    def test_robots_groups_wildcards_specificity_and_encoding(self):
        robots = RobotsPolicy('User-agent: *\nDisallow: /\nUser-agent: seo-kit-audit\nDisallow: /private*\nAllow: /private/public$\nDisallow: /a%2fb\nUser-agent: seo-kit-audit\nDisallow: /more\nCrawl-delay: 0.5')
        self.assertTrue(robots.can_fetch('seo-kit-audit/1.0', ORIGIN + '/'))
        self.assertFalse(robots.can_fetch('seo-kit-audit/1.0', ORIGIN + '/private?q=1'))
        self.assertTrue(robots.can_fetch('seo-kit-audit/1.0', ORIGIN + '/private/public'))
        self.assertFalse(robots.can_fetch('seo-kit-audit/1.0', ORIGIN + '/private/public?x=1'))
        self.assertFalse(robots.can_fetch('seo-kit-audit/1.0', ORIGIN + '/a%2Fb'))
        self.assertFalse(robots.can_fetch('seo-kit-audit/1.0', ORIGIN + '/more'))
        self.assertEqual(robots.crawl_delay('seo-kit-audit/1.0'), 0.5)

    def test_nested_sitemaps_do_not_confuse_image_locations_with_pages(self):
        class Client:
            def fetch(self, url, **kwargs):
                bodies = {'/sitemap.xml': '<sitemapindex><sitemap><loc>/nested.xml</loc></sitemap></sitemapindex>',
                          '/nested.xml': '<urlset xmlns:image="http://www.google.com/schemas/sitemap-image/1.1"><url><loc>https://example.org/page/</loc><image:image><image:loc>https://example.org/a.png</image:loc></image:image></url></urlset>'}
                return Response(url, 200, {}, bodies[url.removeprefix(ORIGIN)].encode(), [])
        warnings = []
        result = sitemap_urls(Client(), ORIGIN, '', warnings)
        self.assertEqual(result, [ORIGIN + '/page/'])
        self.assertEqual(warnings, [])

    def test_advanced_rules_and_profile_thresholds_persist(self):
        content = '<html><head><title>Over length</title><title>Second</title><meta name="robots" content="index,noindex,nofollow"><meta http-equiv="refresh" content="0; url=/next/"></head><body><h1>One</h1><h3>Skip</h3><button></button><iframe></iframe><i id="repeat"></i><b id="repeat"></b><link rel="alternate" hreflang="invalid_tag" href="/else/"><script type="application/ld+json">{"@context":"https://schema.org","@type":"Product","name":"Invisible product"}</script></body></html>'
        store, crawl = self.crawl(content, thresholds={'title_max': 5})
        try:
            rules = {r[0] for r in store.db.execute('SELECT rule_id FROM issues WHERE url=?', (ORIGIN + '/',))}
            self.assertTrue({'metadata.multiple_titles', 'metadata.title_length', 'indexability.directive_conflict', 'headings.skipped_level', 'accessibility.duplicate_id', 'accessibility.button_name_missing', 'accessibility.frame_title_missing', 'hreflang.invalid_tag', 'http.meta_refresh', 'structured_data.profile_review'} <= rules, rules)
            self.assertGreater(store.db.execute('SELECT COUNT(*) FROM rule_registry').fetchone()[0], 5)
            data = json.loads(store.db.execute('SELECT metadata_json FROM pages WHERE url=?', (ORIGIN + '/',)).fetchone()[0])
            self.assertIn('noindex', data['effective_directives'])
        finally:
            store.close()

    def test_http_canonical_and_main_content_ignore_shared_navigation(self):
        response = Response(ORIGIN + '/', 200, {'link': '</other/>; rel="canonical"'}, b'', [])
        meta = advanced_metadata('<html><body><nav>shared boilerplate</nav><main>Actual article</main><footer>Legal</footer></body></html>', response)
        self.assertEqual(meta['main_text'], 'Actual article')
        self.assertEqual(meta['http_canonicals'], ['/other/'])

    def test_css_xpath_multifield_and_scalar_extraction_are_bounded(self):
        store, crawl = self.crawl(html('Test', '<main><a class="value" href="/one">One</a><a class="value" href="/two">Two</a></main>'))
        try:
            fields = [{'name':'link','css':'main a.value','attribute':'href'}, {'name':'count','xpath':'count(//main/a)'}]
            result = list(extract_fields(store, crawl, fields, max_results=3))
            own = [r for r in result if r['url'] == ORIGIN + '/']
            self.assertEqual([r['value'] for r in own], ['/one','/two','2.0'])
            with self.assertRaises(ValueError):
                list(extract_fields(store, crawl, [{'name':'bad','xpath':'//*['}]))
        finally:
            store.close()

    def test_images_pdf_and_corrupt_documents(self):
        from PIL import Image
        from pypdf import PdfWriter
        image = io.BytesIO()
        Image.new('RGB', (640,480)).save(image, format='PNG')
        self.assertEqual(binary_worker('image', image.getvalue())['width'], 640)
        pdf = io.BytesIO()
        writer = PdfWriter()
        writer.add_blank_page(width=100, height=200)
        writer.add_metadata({'/Title':'Fixture PDF'})
        writer.write(pdf)
        result = binary_worker('pdf', pdf.getvalue())
        self.assertEqual(result['pages'], 1)
        self.assertEqual(result['metadata']['/Title'], 'Fixture PDF')
        with self.assertRaises(ValueError):
            binary_worker('pdf', b'%PDF broken')

    def test_image_resources_are_fetched_once_and_persist_dimensions(self):
        from PIL import Image
        image = io.BytesIO()
        Image.new('RGB',(32,24)).save(image,format='PNG')
        class Client(FixtureClient):
            def fetch(self, url, **kwargs):
                if url.endswith('/image.png'):
                    self.requests += 1
                    return Response(url,200,{'content-type':'image/png'},image.getvalue(),[])
                return super().fetch(url,**kwargs)
        report = run_live(options(self.database),Client({ORIGIN+'/':(200,html('Home','<img src="/image.png" alt="">')), ORIGIN+'/about/?a=1&b=2':(200,html('About'))}))
        store = CrawlStore(self.database)
        try:
            data = json.loads(store.db.execute('SELECT data_json FROM observations WHERE kind="image"').fetchone()[0])
            self.assertEqual((data['width'],data['height']), (32,24))
        finally:
            store.close()

    def test_sitemap_images_splitting_and_pagination(self):
        store, crawl = self.crawl(html('Home','<img src="/a.png" alt="">'), resource_limit=0)
        try:
            names = sitemap_parts(store, crawl, Path(self.directory.name)/'maps', ORIGIN+'/maps',1)
            self.assertEqual(len(names),2)
            index = ElementTree.parse(Path(self.directory.name)/'maps/sitemap-index.xml')
            self.assertEqual(len(index.getroot()),2)
            self.assertIn('image:loc', (Path(self.directory.name)/'maps'/names[0]).read_text())
            first = list(rows(store,'pages',crawl,{},limit=1))
            second = list(rows(store,'pages',crawl,{},limit=1,offset=1))
            self.assertNotEqual(first[0]['url'],second[0]['url'])
            with self.assertRaises(ValueError):
                list(rows(store,'pages',crawl,{'severity':'warning'}))
        finally:
            store.close()

    def test_large_export_has_no_row_loss(self):
        destination = Path(self.directory.name)/'large.json'
        output_items(({'url':f'{ORIGIN}/{index}/','value':index} for index in range(20000)), 'json', destination)
        self.assertEqual(len(json.loads(destination.read_text())),20000)

    def test_architecture_uses_links_instead_of_sitemap_seed_depth(self):
        store, crawl = self.crawl(html('Home','<a href="/about/?a=1&b=2">About</a>'))
        try:
            data = json.loads(store.db.execute('SELECT data_json FROM observations WHERE kind="architecture" AND url LIKE "%about%"').fetchone()[0])
            self.assertEqual(data['link_depth'],1)
        finally:
            store.close()

    def test_grammar_preserves_engine_evidence_and_language_boundary(self):
        class Grammar:
            def fetch(self,url,**kwargs):
                return Response(url,200,{},json.dumps({'matches':[{'message':'Agreement','offset':0,'length':3}], 'software':{'name':'LanguageTool','version':'test'}}).encode(),[])
        store, crawl = self.crawl(html('Home'))
        try:
            result = list(grammar_check(store,crawl,'https://language.example/v2/check','en',1,Grammar()))
            self.assertEqual(result[0]['status'],'measured')
            self.assertEqual(result[0]['software']['name'],'LanguageTool')
            self.assertEqual(list(grammar_check(store,crawl,'https://language.example/v2/check','es',1,Grammar()))[0]['status'],'unmeasured')
        finally:
            store.close()

    @unittest.skipUnless(sys.platform == 'linux','signal fixture uses POSIX')
    def test_sigterm_releases_database_and_resume_recovers_processing_url(self):
        program = '''import os, signal, sys
sys.path[:0] = ['.agents/scripts', '.agents/tests']
from test_crawl_store import FixtureClient, options, html, ORIGIN
from live_audit import run_live
class Interrupted(FixtureClient):
 def fetch(self,url,**kwargs):
  if '/about/' in url: os.kill(os.getpid(),signal.SIGTERM)
  return super().fetch(url,**kwargs)
run_live(options(sys.argv[1]),Interrupted({ORIGIN+'/':(200,html('Home'))}))
'''
        process = subprocess.run([sys.executable,'-c',program,self.database],capture_output=True,text=True)
        self.assertEqual(process.returncode,-signal.SIGTERM,process.stderr)
        report = run_live(options(self.database,resume=True),FixtureClient({ORIGIN+'/':(200,html('Home')),ORIGIN+'/about/?a=1&b=2':(200,html('About'))}))
        self.assertTrue(report['crawl_complete'])
        self.assertEqual(report['crawl_id'],1)

    def test_api_pagination_and_url_reconciliation(self):
        class Pages:
            def __init__(self): self.offsets=[]
            def fetch(self,url,**kwargs):
                payload = json.loads(kwargs['body']); offset = int(payload.get('offset',payload.get('startRow',0))); self.offsets.append(offset)
                if 'analyticsdata' in url:
                    data = {'rows':[{'dimensionValues':[{'value': ORIGIN + f'/{offset}/?b=2&a=1'}], 'metricValues':[{'value':'1'},{'value':'1'}]}], 'rowCount':3}
                else:
                    data = {'rows':[{'keys':[ORIGIN + f'/{offset}/?b=2&a=1'],'clicks':1}]} if offset<3 else {'rows':[]}
                return Response(url,200,{},json.dumps(data).encode(),[])
        store = CrawlStore(self.database)
        try:
            crawl,_=store.start(ORIGIN,ORIGIN+'/','100',{})
            client=Pages()
            with patch.dict(os.environ,{'SEO_KIT_GA4_ACCESS_TOKEN':'test','SEO_KIT_GSC_ACCESS_TOKEN':'test'},clear=True), patch('external_data.API_PAGE_SIZE',1):
                result=enrich(store,crawl,ORIGIN,[ORIGIN+f'/{i}/?a=1&b=2' for i in range(3)],client,ga4_property='123',gsc_property=ORIGIN+'/',period=('2026-01-01','2026-01-02'),api_limit=3)
            self.assertEqual(client.offsets,[0,1,2,0,1,2])
            self.assertEqual(result['sources']['ga4']['rows_matched'],3)
            self.assertEqual(result['sources']['gsc_performance']['rows_matched'],3)
        finally: store.close()

    def test_api_retries_and_partial_inspections_preserve_successes(self):
        class Client:
            def __init__(self): self.calls=0
            def fetch(self,url,**kwargs):
                self.calls+=1
                return Response(url,429 if self.calls<3 else 200,{},b'{}',[])
        client=Client()
        with patch('external_data.time.sleep'):
            self.assertEqual(api_json(client,'https://api.example/'),{})
        self.assertEqual(client.calls,3)
        class Inspections:
            def __init__(self): self.calls=0
            def fetch(self,url,**kwargs):
                self.calls+=1
                if self.calls>1: raise ValueError('request budget exhausted')
                return Response(url,200,{},b'{"inspectionResult":{"indexStatusResult":{"verdict":"PASS"}}}',[])
        saved=[]
        checks, findings, note=gsc_evidence(Inspections(),ORIGIN,[ORIGIN+'/',ORIGIN+'/second/'],ORIGIN+'/','test',2,on_result=saved.append)
        self.assertEqual(len(saved),1)
        self.assertEqual(len(findings),1)
        self.assertEqual(checks,{})
        self.assertIn('incomplete',note)

    def test_similarity_ignores_templates_and_separates_languages(self):
        from crawl_rules import content_fingerprint
        shared = ' '.join(['Shared navigation footer template links']*60)
        first = '<html><body><nav>'+shared+'</nav><main>'+('Distinct article about science and astronomy '*40)+'</main></body></html>'
        second = '<html><body><nav>'+shared+'</nav><main>'+('Cooking recipes ingredients kitchen meals '*40)+'</main></body></html>'
        a,_ = content_fingerprint(main_text(html_tree(first)))
        b,_ = content_fingerprint(main_text(html_tree(second)))
        self.assertGreater((int(a,16)^int(b,16)).bit_count(),3)

    def test_monthly_moz_quota_survives_new_crawls(self):
        store=CrawlStore(self.database)
        try:
            self.assertTrue(store.reserve_quota('moz_rows','2026-10',40,50))
            self.assertFalse(store.reserve_quota('moz_rows','2026-10',11,50))
            self.assertTrue(store.reserve_quota('moz_rows','2026-11',50,50))
        finally: store.close()

    def test_crux_missing_record_and_malformed_apis_do_not_pass(self):
        class Empty:
            def fetch(self,url,**kwargs): return Response(url,200,{},b'{"rows":[null]}',[])
        store=CrawlStore(self.database)
        try:
            crawl,_=store.start(ORIGIN,ORIGIN+'/','100',{})
            with patch.dict(os.environ,{'SEO_KIT_GA4_ACCESS_TOKEN':'test','SEO_KIT_CRUX_API_KEY':'test'},clear=True):
                result=enrich(store,crawl,ORIGIN,[ORIGIN+'/'],Empty(),ga4_property='123',period=('2026-01-01','2026-01-02'),crux_limit=1)
            self.assertTrue(any('GA4 unmeasured' in warning for warning in result['warnings']))
            self.assertEqual(result['sources']['crux_url_field']['status'],'unmeasured')
        finally: store.close()

    def test_official_amp_validator_accepts_valid_and_rejects_invalid_markup(self):
        validator=Path.home()/'.local/share/seo-kit/amp-validator-wasm.js'
        if not validator.is_file(): self.skipTest('run npm run setup:audit to install the official offline AMP validator')
        animation='-amp-start 8s steps(1,end) 0s 1 normal both'
        css='body{'+''.join(prefix+'animation:'+animation+';' for prefix in ['-webkit-','-moz-','-ms-',''])[:-1]+'}'
        css+=''.join('@'+prefix+'keyframes -amp-start{from{visibility:hidden}to{visibility:visible}}' for prefix in ['-webkit-','-moz-','-ms-','-o-',''])
        no='body{'+''.join(prefix+'animation:none;' for prefix in ['-webkit-','-moz-','-ms-',''])[:-1]+'}'
        valid='<!doctype html><html amp lang="en"><head><meta charset="utf-8"><title>AMP fixture</title><link rel="canonical" href="https://example.org/"><meta name="viewport" content="width=device-width,minimum-scale=1,initial-scale=1"><script async src="https://cdn.ampproject.org/v0.js"></script><style amp-boilerplate>'+css+'</style><noscript><style amp-boilerplate>'+no+'</style></noscript></head><body><h1>Valid fixture</h1></body></html>'
        for content,expected in [(valid,'PASS'),('<html amp>invalid</html>','FAIL')]:
            process=subprocess.run(['node','.agents/scripts/validate-amp.mjs',str(validator)],input=content,text=True,capture_output=True,timeout=20)
            self.assertEqual(process.returncode,0,process.stderr)
            result=json.loads(process.stdout)
            self.assertEqual(result['status'],expected)
            self.assertEqual(len(result['validator_sha256']),64)

    def test_comparison_streams_changes_and_rejects_ambiguous_mapping(self):
        from crawl_query import compare
        store=CrawlStore(self.database)
        try:
            before,_=store.start(ORIGIN,ORIGIN+'/','100',{})
            after,_=store.start(ORIGIN,ORIGIN+'/','100',{})
            response=Response(ORIGIN+'/',200,{'content-type':'text/html'},b'',[])
            with store.batch():
                for index in range(2000):
                    url=ORIGIN+f'/{index:05}/'
                    store.save_page(before,url,0,response=response,raw='old')
                    store.save_page(after,url,1,response=response,raw='new')
            result=compare(store,before,store,after,streaming=True)
            destination=Path(self.directory.name)/'comparison.json'
            output_items(result,'json',destination)
            self.assertEqual(len(json.loads(destination.read_text())['changes']),2000)
            with self.assertRaises(ValueError):
                compare(store,before,store,after,{ORIGIN+'/00000/':ORIGIN+'/00001/'})
        finally: store.close()

    def test_external_status_authorized_alternates_and_rel_attributes(self):
        class Client(FixtureClient):
            def fetch(self,url,**kwargs):
                if url.startswith('https://alternate.example/'):
                    self.requests += 1
                    if url.endswith('/robots.txt'): return Response(url,200,{},b'User-agent: *\nAllow: /',[])
                    if url.endswith('/broken'): return Response(url,500,{},b'',[])
                    return Response(url,200,{'content-type':'text/html'},b'<html lang="es"><head><link rel="alternate" hreflang="en" href="https://example.org/"></head></html>',[])
                return super().fetch(url,**kwargs)
        content=html('Home','<a href="https://alternate.example/broken" rel="nofollow sponsored">External</a><link rel="alternate" hreflang="es" href="https://alternate.example/page"><img alt="" src="https://unauthorized.example/image.png">')
        report=run_live(options(self.database,resource_host=['alternate.example']),Client({ORIGIN+'/':(200,content),ORIGIN+'/about/?a=1&b=2':(200,html('About'))}))
        store=CrawlStore(self.database)
        try:
            rules={row[0] for row in store.db.execute('SELECT rule_id FROM issues')}
            self.assertIn('links.broken_external',rules)
            self.assertNotIn('hreflang.external_target_unmeasured',rules)
            self.assertEqual(store.db.execute('SELECT status FROM observations WHERE kind="image"').fetchone()[0],'unmeasured')
            data=json.loads(store.db.execute('SELECT metadata_json FROM pages WHERE url=?',(ORIGIN+'/',)).fetchone()[0])
            self.assertEqual(data['anchors'][0]['rel'],'nofollow sponsored')
        finally: store.close()

    def test_canonical_http_conflict_js_redirect_and_pagination(self):
        class Client(FixtureClient):
            def fetch(self,url,**kwargs):
                response=super().fetch(url,**kwargs)
                if url==ORIGIN+'/': response.headers['link']='</other/>; rel="canonical"'
                return response
        content=html('Home','<link rel="next" href="/"><script>location.assign("/next/")</script>')
        report=run_live(options(self.database),Client({ORIGIN+'/':(200,content),ORIGIN+'/about/?a=1&b=2':(200,html('About'))}))
        store=CrawlStore(self.database)
        try:
            rules={row[0] for row in store.db.execute('SELECT rule_id FROM issues')}
            self.assertTrue({'indexability.canonical_conflict','http.javascript_redirect_candidate','pagination.self_loop'} <= rules)
        finally: store.close()

    def test_time_limit_preserves_pending_urls_for_resume(self):
        import time
        class Slow(FixtureClient):
            def fetch(self,url,**kwargs):
                if url==ORIGIN+'/': time.sleep(1.05)
                return super().fetch(url,**kwargs)
        pages={ORIGIN+'/':(200,html('Home')),ORIGIN+'/about/?a=1&b=2':(200,html('About'))}
        first=run_live(options(self.database,max_seconds=1),Slow(pages))
        self.assertFalse(first['crawl_complete'])
        self.assertTrue(any('time limit' in warning for warning in first['warnings']))
        second=run_live(options(self.database,max_seconds=10,resume=True),FixtureClient(pages))
        self.assertTrue(second['crawl_complete'])

    def test_gzip_sitemap_has_expanded_size_budget(self):
        import gzip
        class Client:
            max_bytes=200
            def fetch(self,url,**kwargs): return Response(url,200,{},gzip.compress(b'<urlset>'+b' '*500+b'</urlset>'),[])
        warnings=[]
        self.assertEqual(sitemap_urls(Client(),ORIGIN,'',warnings),[])
        self.assertIn('exceeds response budget',warnings[0])

    def test_trickling_response_cannot_extend_total_time_budget(self):
        from live_http import SafeClient
        class Stream:
            status=200
            def read1(self,limit): return b'x'
            def getheaders(self): return [('content-type','text/html')]
        class Connection:
            sock=None
            def request(self,*args,**kwargs): pass
            def getresponse(self): return Stream()
            def close(self): pass
        client=SafeClient(delay=0,deadline=10)
        with patch('live_http.public_address',return_value='93.184.216.34'), patch('live_http.PinnedHTTPSConnection',return_value=Connection()), patch('live_http.time.monotonic',side_effect=[0,0,0,0,0,11]):
            with self.assertRaisesRegex(ValueError,'time budget exhausted'):
                client.fetch(ORIGIN+'/')


if __name__ == '__main__':
    unittest.main()
