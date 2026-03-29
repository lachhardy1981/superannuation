#!/usr/bin/env python3
"""Simple static file server for the Super dashboard."""
import os, socketserver, http.server

os.chdir(os.path.dirname(os.path.abspath(__file__)))

PORT = 8080
Handler = http.server.SimpleHTTPRequestHandler

with socketserver.TCPServer(("", PORT), Handler) as httpd:
    print(f"Serving Super Dashboard at http://localhost:{PORT}")
    print(f"  Dashboard  → http://localhost:{PORT}/")
    print(f"  SP500 Chart→ http://localhost:{PORT}/sp500.html")
    httpd.serve_forever()
