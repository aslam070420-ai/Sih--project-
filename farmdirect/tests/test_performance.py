"""Run from farmdirect: python -m unittest discover -s tests -v

Uses temporary demo data and disables external market providers for repeatability.
"""
import gzip
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))


class PerformanceRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.env = patch.dict(os.environ, {
            'FARMDIRECT_DB': str(Path(cls.temp.name)/'test.db'),
            'FARMDIRECT_DATABASE_URL': '', 'DATABASE_URL': '', 'POSTGRES_URL': '',
            'FD_AGMARKNET2_ENABLED': '0', 'FD_TN_MARKET_ENABLED': '0',
            'FD_ENAM_ENABLED': '0', 'DATA_GOV_IN_API_KEY': '', 'FD_AUTO_SEED': '1',
            'FD_SECURE_COOKIES': '0', 'VERCEL': '',
        })
        cls.env.start()
        from app_factory import create_app
        cls.app = create_app()
        cls.app.config.update(TESTING=True)
        cls.client = cls.app.test_client()

    @classmethod
    def tearDownClass(cls):
        cls.env.stop()
        cls.temp.cleanup()

    def setUp(self):
        with self.client.session_transaction() as session:
            session.clear()

    def test_static_skips_database_even_with_login_cookie(self):
        with self.client.session_transaction() as session:
            session['uid'] = 123
        with patch('app_factory._ensure_data_ready', side_effect=AssertionError('DB initialization')), \
             patch('auth.db.query', side_effect=AssertionError('User lookup')):
            for route in ['/static/js/farmdirect-core.bundle.js', '/sw.js']:
                self.assertEqual(self.client.get(route, buffered=True).status_code, 200)

    def test_gzip_integrity_negotiation_head_and_conditional_requests(self):
        url = '/static/js/farmdirect-core.bundle.js'
        plain = self.client.get(url, headers={'Accept-Encoding': 'identity'}, buffered=True)
        packed = self.client.get(url, headers={'Accept-Encoding': 'gzip'}, buffered=True)
        self.assertEqual(gzip.decompress(packed.data), plain.data)
        self.assertLess(len(packed.data), len(plain.data) * .4)
        self.assertIn('Accept-Encoding', packed.headers['Vary'])
        self.assertEqual(packed.mimetype, plain.mimetype)
        refused = self.client.get(url, headers={'Accept-Encoding': 'gzip;q=0, identity;q=1'}, buffered=True)
        self.assertNotIn('Content-Encoding', refused.headers)
        head = self.client.head(url, headers={'Accept-Encoding': 'gzip'}, buffered=True)
        self.assertEqual(head.headers['Content-Length'], packed.headers['Content-Length'])
        self.assertEqual(head.data, b'')
        cached = self.client.get(url, headers={'Accept-Encoding': 'gzip', 'If-None-Match': packed.headers['ETag']}, buffered=True)
        self.assertEqual(cached.status_code, 304)
        # A gzip validator must not validate the identity representation.
        plain_again = self.client.get(url, headers={'Accept-Encoding': 'identity', 'If-None-Match': packed.headers['ETag']}, buffered=True)
        self.assertEqual(plain_again.status_code, 200)

    def test_versioned_assets_and_worker_agree(self):
        version = self.app.config['FD_ASSET_VERSION']
        with self.app.test_request_context():
            from flask import url_for
            url = url_for('static', filename='css/farmdirect-core.bundle.css')
        self.assertIn(f'v={version}', url)
        self.assertIn('immutable', self.client.get(url, buffered=True).headers['Cache-Control'])
        self.assertNotIn('immutable', self.client.get(url.replace(version, 'old'), buffered=True).headers['Cache-Control'])
        self.assertIn(version, self.client.get('/sw.js', buffered=True).get_data(as_text=True))

    def test_all_compressed_assets_match_their_sources(self):
        files = list((PROJECT/'static').rglob('*.gz'))
        self.assertGreater(len(files), 10)
        for file in files:
            with self.subTest(file=file.name):
                self.assertEqual(gzip.decompress(file.read_bytes()), file.with_suffix('').read_bytes())

    def test_cold_start_does_not_import_ai_or_initialize_db(self):
        code = '''import sys
from app_factory import create_app
import app_factory
app = create_app()
assert not any(name in sys.modules for name in ('numpy','pandas','sklearn'))
assert app.test_client().get('/static/js/farmdirect-core.bundle.js').status_code == 200
assert not app_factory._APP_READY
'''
        result = subprocess.run([sys.executable, '-c', code], cwd=PROJECT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_public_pages_and_market_filters(self):
        for route in ['/', '/marketplace', '/marketplace?crop=Tomato&sort=price_asc',
                      '/marketplace?page=2', '/marketplace?lat=19.9975&lng=73.7898&radius=25',
                      '/login', '/register', '/market-intelligence', '/api/products',
                      '/api/market/live-batch?crops=Tomato,Onion&status=0']:
            with self.subTest(route=route):
                response = self.client.get(route)
                self.assertEqual(response.status_code, 200)

    def test_ai_features_still_run(self):
        forecast = self.client.get('/api/ai/forecast?crop=Tomato&horizon=7')
        price = self.client.get('/api/ai/price?crop=Tomato&grade=A&qty=100')
        self.assertEqual(forecast.status_code, 200)
        self.assertGreater(forecast.json['predicted_demand'], 0)
        self.assertEqual(price.status_code, 200)
        self.assertGreater(price.json['suggested_price'], 0)

    def test_role_pages_and_cart_flow(self):
        self.client.get('/')
        import db
        roles = {
            'consumer': ['/consumer/dashboard', '/orders', '/cart'],
            'farmer': ['/farmer/dashboard', '/farmer/orders', '/farmer/earnings',
                       '/farmer/forecast', '/farmer/price', '/farmer/listings/new', '/ivr/simulator'],
            'buyer': ['/buyer/dashboard'],
            'admin': ['/admin', '/admin/ivr', '/logistics', '/logistics/routes'],
        }
        for role, routes in roles.items():
            user = db.query('SELECT id FROM users WHERE role=? AND active=1 LIMIT 1', (role,), one=True)
            with self.client.session_transaction() as session:
                session['uid'] = user['id']
            for route in routes:
                with self.subTest(role=role, route=route):
                    self.assertEqual(self.client.get(route).status_code, 200)
            if role == 'consumer':
                product = db.query("SELECT id FROM products WHERE status='active' AND quantity_kg>2 LIMIT 1", one=True)
                self.assertEqual(self.client.get(f"/product/{product['id']}").status_code, 200)
                response = self.client.post('/api/cart/add', json={'product_id': product['id'], 'quantity_kg': 1})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(self.client.get('/checkout').status_code, 200)

    def test_market_status_aggregates_match_database(self):
        result = self.client.get('/api/market/status')
        self.assertEqual(result.status_code, 200)
        import db
        expected = db.query('SELECT COUNT(*) n, COUNT(DISTINCT crop) crops, MAX(arrival_date) latest FROM mandi_prices', one=True)
        self.assertEqual(result.json['cached_rows'], expected['n'])
        self.assertEqual(result.json['cached_crops'], expected['crops'])
        self.assertEqual(result.json['latest_arrival_date'], expected['latest'])


if __name__ == '__main__':
    unittest.main()
