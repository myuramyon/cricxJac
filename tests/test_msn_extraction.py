import textwrap
from app.adapters.msn_adapter import MSNAdapter


def test_extract_json_ld_json():
    html = textwrap.dedent('''
    <html><head>
    <script type="application/ld+json">
    {"@context":"http://schema.org","events":[{"match_id":"M1","runs":4,"ball":1,"over":0}]}
    </script>
    </head><body></body></html>
    ''')
    adapter = MSNAdapter(lambda e: None, config={'allow_scrape': True})
    blobs = adapter._extract_json_from_html(html)
    assert isinstance(blobs, list)
    assert any(isinstance(b, dict) and b.get('events') for b in blobs)


def test_extract_js_assignment_json():
    html = textwrap.dedent('''
    <html><script>window.__INITIAL_STATE__ = {"events": [{"match_id":"M2","runs":1,"ball":2,"over":0}]};</script></html>
    ''')
    adapter = MSNAdapter(lambda e: None, config={'allow_scrape': True})
    blobs = adapter._extract_json_from_html(html)
    assert any(isinstance(b, dict) and b.get('events') for b in blobs)
