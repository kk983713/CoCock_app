#!/usr/bin/env python3
"""
Simple local token store for Turnstile PoC.

Usage:
  python3 scripts/token_store.py --port 8765

Endpoints:
  POST /store  - body: JSON {"token": "..."} -> returns {"id": "..."}
  GET  /retrieve?id=<id> -> returns {"token": "..."} or 404

This is intentionally tiny and for local development only. It stores tokens in memory
and is NOT secure. Bind to localhost only and run in your dev environment.
"""
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import argparse
import uuid
import time
from urllib.parse import urlparse, parse_qs

STORE: dict[str, tuple[float, str]] = {}
TTL_SECONDS = 300.0  # tokens expire after 5 minutes


class TokenStoreHandler(BaseHTTPRequestHandler):
    def _set_cors_headers(self, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        # Allow local pages (served from a different port) to POST
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_OPTIONS(self):
        self._set_cors_headers(200)

    def do_POST(self):
        if self.path != "/store":
            self._set_cors_headers(404)
            self.wfile.write(json.dumps({"error": "not found"}).encode())
            return
        length = int(self.headers.get("content-length", "0"))
        raw = self.rfile.read(length) if length else b""
        try:
            payload = json.loads(raw.decode("utf-8"))
            token = payload.get("token")
            if not token:
                raise ValueError("missing token")
        except Exception as e:
            self._set_cors_headers(400)
            self.wfile.write(json.dumps({"error": "invalid payload", "detail": str(e)}).encode())
            return

        # cleanup expired entries
        now = time.time()
        to_delete = [k for k, (ts, _) in STORE.items() if now - ts > TTL_SECONDS]
        for k in to_delete:
            del STORE[k]

        id_ = uuid.uuid4().hex
        STORE[id_] = (time.time(), token)
        # log the store action for debugging (include User-Agent)
        ua = self.headers.get("User-Agent", "<no-ua>")
        print(f"[token_store] STORE id={id_} from={self.client_address[0]} ua={ua}")
        self._set_cors_headers(200)
        self.wfile.write(json.dumps({"id": id_}).encode())

    def do_GET(self):
        parsed = urlparse(self.path)
        # Support two GET endpoints:
        #  - /retrieve?id=...  (one-time consume)
        #  - /peek?id=...      (check existence without consuming)
        if parsed.path not in ("/retrieve", "/peek"):
            self._set_cors_headers(404)
            self.wfile.write(json.dumps({"error": "not found"}).encode())
            return
        qs = parse_qs(parsed.query)
        id_ = qs.get("id", [None])[0]
        if not id_:
            self._set_cors_headers(400)
            self.wfile.write(json.dumps({"error": "missing id"}).encode())
            return
        entry = STORE.get(id_)
        if not entry:
            # log not found
            ua = self.headers.get('User-Agent', '<no-ua>')
            print(f"[token_store] RETRIEVE id={id_} not_found from={self.client_address[0]} ua={ua}")
            self._set_cors_headers(404)
            self.wfile.write(json.dumps({"error": "not found"}).encode())
            return
        ts, token = entry
        # If this is a peek, do not remove the entry
        if parsed.path == "/peek":
            ua = self.headers.get("User-Agent", "<no-ua>")
            print(f"[token_store] PEEK id={id_} present from={self.client_address[0]} ua={ua}")
            self._set_cors_headers(200)
            self.wfile.write(json.dumps({"found": True}).encode())
            return

        # Otherwise this is /retrieve: remove after retrieval to make it one-time
        try:
            del STORE[id_]
        except KeyError:
            pass
        # log successful retrieve (include User-Agent)
        ua = self.headers.get("User-Agent", "<no-ua>")
        print(f"[token_store] RETRIEVE id={id_} token_len={len(token)} from={self.client_address[0]} ua={ua}")
        self._set_cors_headers(200)
        self.wfile.write(json.dumps({"token": token}).encode())


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8765)
    args = p.parse_args()
    server_address = (args.host, args.port)
    httpd = HTTPServer(server_address, TokenStoreHandler)
    print(f"Token store listening on http://{args.host}:{args.port} (TTL={TTL_SECONDS}s)")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("Shutting down")
        httpd.server_close()


if __name__ == "__main__":
    main()
