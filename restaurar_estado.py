#!/usr/bin/env python3
"""Restaura sesión E2E del artefacto privado 'estado-matrix' vía API REST.
(download-artifact@v4 falla entre corridas; la API REST es confiable)."""
import json, os, subprocess, sys, urllib.request

API = f"https://api.github.com/repos/{os.environ['REPO']}/actions/artifacts"
GT = os.environ["GT"]
H = {"Authorization": f"Bearer {GT}", "Accept": "application/vnd.github+json"}

def api(path, raw=False):
    req = urllib.request.Request(API + path, headers=H)
    with urllib.request.urlopen(req, timeout=60) as r:
        return r if raw else json.load(r)

arts = [a for a in api("?per_page=100").get("artifacts", [])
        if a["name"] == "estado-matrix" and not a["expired"]]
if not arts:
    print("sin artefacto previo: login fresco")
    sys.exit(0)
aid = max(arts, key=lambda a: a["created_at"])["id"]
# NO seguir el redirect con el token (Azure lo rechaza): pedir Location y bajar limpio
req = urllib.request.Request(f"{API}/{aid}/zip", headers=dict(H, **{"Range": "bytes=0-"}))
class SinRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k): return None
opener = urllib.request.build_opener(SinRedirect)
try:
    opener.open(req, timeout=60)
except urllib.error.HTTPError as e:
    if e.code not in (302, 303, 307):
        raise
    ubic = e.headers["Location"]
req2 = urllib.request.Request(ubic)  # sin token: URL firmada
with urllib.request.urlopen(req2, timeout=180) as r:
    open("estado.zip", "wb").write(r.read())
subprocess.run(["unzip", "-o", "estado.zip"], check=True)
os.remove("estado.zip")
print(f"estado restaurado (artefacto {aid})")
# limpieza: dejar solo el más reciente
for a in arts:
    if a["id"] != aid:
        req = urllib.request.Request(f"{API}/{a['id']}", method="DELETE", headers=H)
        try:
            urllib.request.urlopen(req, timeout=30)
        except Exception:
            pass
print("artefactos viejos limpiados")
