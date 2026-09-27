from contextlib import closing
import json
from pathlib import Path
import shutil
import sqlite3
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
from urllib.request import Request, urlopen
from urllib.error import HTTPError

SCRIPTS = Path(__file__).resolve().parents[1] / 'skills/local-material-library/scripts'
sys.path.insert(0, str(SCRIPTS))
from library import Library, handler_for, ThreadingHTTPServer, export_data
from demo import generate, make_pdf


class LibraryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.source = generate(self.root / 'source')
        self.lib = Library(self.source, self.root / 'data')
        self.lib.scan()

    def tearDown(self):
        self.temp.cleanup()

    def test_full_pdf_search_and_pagination(self):
        result = self.lib.listing('WATERMARKET')
        self.assertEqual(result['total'], 2)
        self.assertTrue(all(row['hit'] == 3 for row in result['items']))
        pdf = result['items'][0]
        self.assertNotEqual(self.lib.render(pdf['id'], 1), self.lib.render(pdf['id'], 3))
        with self.assertRaises(ValueError):
            self.lib.render(pdf['id'], 4)
        for n in range(36):
            (self.source / f'{n}.txt').write_text('共同检索短词 水利', encoding='utf-8')
        self.lib.scan()
        first = self.lib.listing('水利')
        second = self.lib.listing('水利', offset=30)
        self.assertEqual(first['total'], 37)
        self.assertEqual(len(first['items']), 30)
        self.assertEqual(len(second['items']), 7)
        self.assertFalse({x['id'] for x in first['items']} & {x['id'] for x in second['items']})
        self.assertEqual(self.lib.listing('%')['total'], 0)

    def test_metadata_move_hide_and_change(self):
        row = self.lib.listing('水利访谈')['items'][0]
        self.lib.edit(row['id'], {'category': '自定专题', 'tags': '待核对', 'hidden': True})
        old = self.source / row['path']
        old.rename(self.source / '已移动.md')
        self.lib.scan()
        updated = self.lib.record(row['id'])
        self.assertEqual(updated['path'], '已移动.md')
        self.assertEqual(updated['category'], '自定专题')
        self.assertEqual(self.lib.listing('待核对', state='hidden')['total'], 1)
        self.lib.edit(row['id'], {'hidden': False})
        (self.source / '已移动.md').write_text('replacementcontent', encoding='utf-8')
        self.lib.scan()
        self.assertEqual(self.lib.listing('replacementcontent')['items'][0]['id'], row['id'])
        (self.source / '已移动.md').unlink()
        self.lib.scan()
        self.assertEqual(self.lib.record(row['id'])['missing'], 1)

    def test_duplicate_docx_backup_and_binding(self):
        self.assertEqual(self.lib.listing(state='duplicates')['total'], 2)
        self.assertEqual(self.lib.listing('地方文献')['total'], 1)
        export_data(self.lib.data, self.root / 'backup')
        with closing(sqlite3.connect(self.root / 'backup/library.sqlite')) as con:
            self.assertEqual(con.execute('SELECT count(*) FROM files').fetchone()[0], 5)
        other = self.root / 'other'
        other.mkdir()
        with self.assertRaises(ValueError):
            Library(other, self.lib.data)

    def test_no_twenty_page_sampling(self):
        make_pdf(self.source / 'long-book.pdf', [f'Ordinary text with enough characters page {n}' for n in range(26)] + ['FINALPAGE evidence only on physical page twenty seven'])
        self.lib.scan()
        result = self.lib.listing('FINALPAGE')
        self.assertEqual(result['total'], 1)
        self.assertEqual(result['items'][0]['hit'], 27)
        self.assertEqual(result['items'][0]['counts']['native'], 27)

    def test_failed_extraction_is_visible_and_retried(self):
        path = self.source / 'broken.pdf'
        path.write_bytes(b'not a pdf')
        self.assertEqual(len(self.lib.scan()['errors']), 1)
        row = self.lib.listing('broken.pdf')['items'][0]
        self.assertTrue(row['error'])
        make_pdf(path, ['Repaired searchable document content'])
        self.lib.scan()
        self.assertEqual(self.lib.listing('Repaired')['items'][0]['id'], row['id'])
        self.assertFalse(self.lib.record(row['id'])['error'])

    def test_ocr_resume_state_without_external_engine(self):
        pdf = self.lib.listing('Regional survey.pdf')['items'][0]
        self.lib.put_page(pdf['id'], 1, '', 'pending')
        self.lib.put_page(pdf['id'], 2, '', 'pending')
        class Result:
            stdout = 'List of languages\nchi_sim\neng\n'
        def run(args, **kwargs):
            r = Result()
            if '--list-langs' not in args:
                r.stdout = '识别内容'
            return r
        with patch('library.shutil.which', return_value='/fake/tesseract'), patch('library.subprocess.run', side_effect=run):
            self.assertEqual(self.lib.ocr(batch=1, file_id=pdf['id'])['completed'], 1)
            self.assertEqual(self.lib.detail(pdf['id'], 2)['page']['status'], 'pending')
            self.assertEqual(self.lib.ocr(batch=1, file_id=pdf['id'])['completed'], 1)
        self.lib.scan()
        self.assertEqual(self.lib.detail(pdf['id'], 1)['page']['status'], 'ocr')
        with patch('library.shutil.which', return_value=None), self.assertRaises(ValueError):
            self.lib.ocr()

    def test_http_boundaries(self):
        server = ThreadingHTTPServer(('127.0.0.1', 0), handler_for(self.lib, 'Demo'))
        thread = threading.Thread(target=server.serve_forever)
        thread.start()
        base = f'http://127.0.0.1:{server.server_port}'
        try:
            with urlopen(base + '/api/status') as response:
                token = json.load(response)['token']
            for path in ['/../library.sqlite', '/.env', '/api/original/9999']:
                with self.assertRaises(HTTPError) as cm:
                    urlopen(base + path)
                self.assertEqual(cm.exception.code, 404)
            with self.assertRaises(HTTPError) as cm:
                urlopen(Request(base + '/api/scan', data=b'{}'))
            self.assertEqual(cm.exception.code, 403)
            with self.assertRaises(HTTPError):
                urlopen(Request(base + '/api/status', headers={'Host': 'evil.example'}))
            with self.assertRaises(HTTPError):
                urlopen(Request(base + '/api/scan', data=b'{}', headers={'X-Library-Token':token, 'Origin':'https://evil.example'}))
            row = self.lib.listing('水利访谈')['items'][0]
            request = Request(base + f'/api/edit/{row["id"]}', data=json.dumps({'tags':'HTTP saved'}).encode(), headers={'X-Library-Token':token})
            with urlopen(request) as response:
                self.assertTrue(json.load(response)['ok'])
            self.assertEqual(self.lib.record(row['id'])['tags'], 'HTTP saved')
        finally:
            server.shutdown()
            thread.join()
            server.server_close()


if __name__ == '__main__':
    unittest.main()
