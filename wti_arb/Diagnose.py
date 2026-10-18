
"""
diagnose.py - find out why venue_scan can't reach the APIs.
Run:  python3 diagnose.py
"""
import json
import platform
import socket
import ssl
import sys
import urllib.error
import urllib.request

print("=" * 68)
print("ENVIRONMENT")
print("=" * 68)
print(f"python      : {sys.version.split()[0]}  ({sys.executable})")
print(f"platform    : {platform.platform()}")
print(f"openssl     : {ssl.OPENSSL_VERSION}")
try:
    import certifi
    print(f"certifi     : installed at {certifi.where()}")
except ImportError:
    print("certifi     : NOT INSTALLED")

ctx = ssl.create_default_context()
print(f"default CAs : {ctx.cert_store_stats()}")
if ctx.cert_store_stats().get("x509_ca", 0) == 0:
    print("  >>> ZERO certificate authorities loaded. This is the bug. <<<")

print()
print("=" * 68)
print("CONNECTIVITY")
print("=" * 68)

TESTS = [
    ("DNS: api.elections.kalshi.com", "dns", "api.elections.kalshi.com"),
    ("DNS: gamma-api.polymarket.com", "dns", "gamma-api.polymarket.com"),
    ("TCP: kalshi:443", "tcp", ("api.elections.kalshi.com", 443)),
    ("HTTPS: example.com", "http", "https://example.com"),
    ("HTTPS: kalshi status", "http",
     "https://api.elections.kalshi.com/trade-api/v2/exchange/status"),
    ("HTTPS: kalshi events", "http",
     "https://api.elections.kalshi.com/trade-api/v2/events"
     "?series_ticker=KXWTIW&status=open&limit=5"),
    ("HTTPS: polymarket", "http",
     "https://gamma-api.polymarket.com/markets?limit=1"),
]

socket.setdefaulttimeout(12)
results = {}

for label, kind, target in TESTS:
    try:
        if kind == "dns":
            ip = socket.gethostbyname(target)
            print(f"{label:32s} OK   -> {ip}")
            results[label] = "ok"
        elif kind == "tcp":
            s = socket.create_connection(target, timeout=10)
            s.close()
            print(f"{label:32s} OK")
            results[label] = "ok"
        else:
            req = urllib.request.Request(
                target, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=15) as r:
                body = r.read(300)
                print(f"{label:32s} OK   {r.status}  {body[:70]}")
                results[label] = "ok"
    except urllib.error.HTTPError as e:
        print(f"{label:32s} HTTP {e.code} {e.reason}")
        results[label] = f"http{e.code}"
    except urllib.error.URLError as e:
        print(f"{label:32s} URLError: {e.reason}")
        results[label] = f"urlerror:{e.reason}"
    except Exception as e:
        print(f"{label:32s} {type(e).__name__}: {e}")
        results[label] = type(e).__name__

print()
print("=" * 68)
print("DIAGNOSIS")
print("=" * 68)

vals = " ".join(str(v) for v in results.values())

if "CERTIFICATE_VERIFY_FAILED" in vals or ctx.cert_store_stats().get("x509_ca", 0) == 0:
    print("""
SSL CERTIFICATE PROBLEM  (the usual macOS cause)

Python from python.org uses its own certificate bundle, not the macOS
keychain, and it is empty until you run the installer's cert script.

  FIX 1 - run Python's certificate installer:
      /Applications/Python\\ 3.x/Install\\ Certificates.command
      (tab-complete the version; double-clicking it in Finder also works)

  FIX 2 - install certifi and point Python at it:
      pip3 install --upgrade certifi
      Then re-run this script; it should show certifi installed.

  FIX 3 - use Homebrew python instead (uses system certs):
      brew install python
      /opt/homebrew/bin/python3 venue_scan.py
""")
elif "urlerror" in vals and "getaddrinfo" in vals:
    print("""
DNS FAILURE - hostnames are not resolving.

  - If your VPN is on, turn it OFF and re-run. Split-tunnel VPNs often
    break DNS for non-browser processes.
  - Try:  ping api.elections.kalshi.com
""")
elif "urlerror" in vals:
    print("""
CONNECTION BLOCKED at the network layer.

  Most likely your VPN. Your screenshots show one running. Browsers often
  keep working while command-line tools do not, because the VPN client
  proxies browser traffic but not raw sockets.

  Turn the VPN off and re-run this script.
""")
elif "http403" in vals:
    print("""
403 FORBIDDEN - reached the server, got refused.

  Not an API key issue (these endpoints are public). Usually geo-blocking
  or a VPN exit node the venue blocks. Try toggling the VPN.
""")
elif all(v == "ok" for v in results.values()):
    print("""
EVERYTHING WORKS. Network is fine.

  If venue_scan still finds nothing, the SERIES TICKERS are wrong,
  not the connection. Get the real ticker from the Kalshi URL:
      kalshi.com/markets/kxwtiw/wti-oil-weekly-range
                          ^^^^^^ this is the series ticker

  Then:  python3 venue_scan.py --series KXWTIW --size 50
""")
else:
    print("Mixed results - see above. The first failing line is the real cause.")

print()
print("Raw results:", json.dumps(results, indent=2))