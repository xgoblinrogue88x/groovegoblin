"""Deterministic cover API checks; never contact live services."""
from io import BytesIO
import unittest
from unittest.mock import Mock, patch
from PIL import Image
from groove_artwork import read_online_cover, HTTPSRedirect

class CoverLookupTests(unittest.TestCase):
    def test_cover_uses_only_public_release_id_over_https(self):
        data=BytesIO();Image.new('RGB',(100,80),'green').save(data,format='PNG')
        response=Mock();response.__enter__=Mock(return_value=response);response.__exit__=Mock(return_value=False)
        response.read.return_value=data.getvalue();response.geturl.return_value='https://archive.org/cover.png'
        opener=Mock();opener.open.return_value=response
        with patch('groove_artwork.urllib.request.build_opener',return_value=opener):
            image=read_online_cover('12345678-1234-1234-1234-123456789abc')
        self.assertEqual(image.size,(100,80))
        request=opener.open.call_args.args[0]
        self.assertEqual(request.full_url,'https://coverartarchive.org/release-group/12345678-1234-1234-1234-123456789abc/front-250')
        self.assertEqual(request.data,None)

    def test_invalid_ids_make_no_request_and_http_redirect_is_rejected(self):
        with patch('groove_artwork.urllib.request.build_opener') as build:
            self.assertIsNone(read_online_cover('../../private/file'))
        build.assert_not_called()
        with self.assertRaises(ValueError):
            HTTPSRedirect().redirect_request(None,None,302,'',{},'http://example.com/image')
