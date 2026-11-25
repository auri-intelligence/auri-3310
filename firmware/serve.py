"""Development server for the web simulator: like `python -m http.server`, but tells browsers
(especially phones on the LAN) never to reuse a cached copy, so every reload gets the latest files.

  python serve.py            listens on all interfaces, port 8000
"""
import functools
import http.server
import os
import sys


class NoCache(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Cache-Control', 'no-store, must-revalidate')
        self.send_header('Expires', '0')
        super().end_headers()


if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    here = os.path.dirname(os.path.abspath(__file__))
    handler = functools.partial(NoCache, directory=here)
    http.server.ThreadingHTTPServer(('0.0.0.0', port), handler).serve_forever()
