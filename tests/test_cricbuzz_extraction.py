import textwrap
from app.adapters.cricbuzz_adapter import CricbuzzAdapter


def test_cricbuzz_html_json_extraction():
    html = textwrap.dedent('''
    <html><script>var initialState = {"matches": [{"match_id":"MB","events": [{"match_id":"MB","runs":6,"ball":1,"over":0}]}]};</script></html>
    ''')
    adapter = CricbuzzAdapter(lambda e: None, config={'url': 'http://example.local', 'allow_scrape': True})
    from app.adapters.cricbuzz_adapter_helpers import extract_json_from_html
    snippets = extract_json_from_html(html)
    assert any(isinstance(s, dict) for s in snippets)
