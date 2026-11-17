"""Utilidades comúns: rutas, HTTP, licenzas e lectura/escritura das fichas."""
from __future__ import annotations

import json
import re
import time
import unicodedata
import urllib.parse
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
ARBORES = DATA / "arbores"
SITE_OUT = ROOT / "_site"
CONFIG = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))

USER_AGENT = "carbugal-catalogo/1.0 (+https://carbugal.com/como-se-fai/)"

# Galicia, caixa aproximada (lat/lon) para filtrar coordenadas.
GALICIA_BBOX = {"min_lat": 41.80, "max_lat": 43.80, "min_lon": -9.35, "max_lon": -6.70}

# Lista branca de licenzas de imaxe. Nada fóra desta lista se publica.
LICENZAS_OK = {
    "cc0": "CC0",
    "cc0-1.0": "CC0",
    "pd": "Dominio público",
    "public-domain": "Dominio público",
    "cc-by": "CC BY",
    "cc-by-2.0": "CC BY 2.0",
    "cc-by-3.0": "CC BY 3.0",
    "cc-by-4.0": "CC BY 4.0",
    "cc-by-sa": "CC BY-SA",
    "cc-by-sa-2.0": "CC BY-SA 2.0",
    "cc-by-sa-3.0": "CC BY-SA 3.0",
    "cc-by-sa-4.0": "CC BY-SA 4.0",
}


def normaliza_licenza(texto: str | None) -> str | None:
    """Devolve a etiqueta canónica se a licenza está na lista branca; se non, None."""
    if not texto:
        return None
    t = texto.strip().lower().replace(" ", "-").replace("_", "-")
    t = t.replace("cc-by-sa-4.0-international", "cc-by-sa-4.0")
    if any(x in t for x in ("nc", "nd")) and t.startswith("cc"):
        return None
    return LICENZAS_OK.get(t)


def slugify(texto: str) -> str:
    t = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-")


def en_galicia(lat: float | None, lon: float | None) -> bool:
    if lat is None or lon is None:
        return False
    b = GALICIA_BBOX
    return b["min_lat"] <= lat <= b["max_lat"] and b["min_lon"] <= lon <= b["max_lon"]


def http_json(url: str, params: dict | None = None, headers: dict | None = None,
              data: bytes | None = None, retries: int = 3, timeout: int = 60):
    if params:
        url = url + ("&" if "?" in url else "?") + urllib.parse.urlencode(params, doseq=True)
    h = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    h.update(headers or {})
    last = None
    for intento in range(retries):
        try:
            req = urllib.request.Request(url, headers=h, data=data)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:  # rede: reintento con espera
            last = e
            time.sleep(2 ** intento)
    raise RuntimeError(f"Fallou {url}: {last}")


def hoxe() -> str:
    return date.today().isoformat()


def agora() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def le_arbores() -> list[dict]:
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted(ARBORES.glob("*.json"))]


def garda_arbore(a: dict) -> None:
    ARBORES.mkdir(parents=True, exist_ok=True)
    (ARBORES / f"{a['slug']}.json").write_text(
        json.dumps(a, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def nova_arbore(nome: str, **campos) -> dict:
    a = {
        "slug": slugify(nome),
        "nome": nome,
        "especie": None,
        "concello": None,
        "provincia": None,
        "lat": None,
        "lon": None,
        "lugar": None,
        "coords_privadas": False,
        "coords_aproximadas": False,
        "orixe": None,            # xunta | wikidata | proposta
        "catalogo_xunta": None,   # {"codigo": ..., "fonte_url": ...}
        "medidas": {},            # {"perimetro_m": {"valor": 7.2, "fonte": "..."}}
        "fotos": [],
        "observacions": {"total_1km": 0, "ultima": None, "fonte": None},
        "wikidata": None,
        "commons_categoria": None,
        "fontes": [],
        "texto": None,
        "estado": "candidato",    # candidato | so_mapa | publicado | retido
        "qa": {},
        "creado": hoxe(),
        "actualizado": hoxe(),
    }
    a.update({k: v for k, v in campos.items() if v is not None})
    return a


def engade_fonte(a: dict, nome: str, url: str) -> None:
    if not any(f["url"] == url for f in a["fontes"]):
        a["fontes"].append({"nome": nome, "url": url})


def engade_foto(a: dict, foto: dict) -> bool:
    """Engade unha foto só se trae os catro campos de atribución e licenza válida."""
    lic = normaliza_licenza(foto.get("licenza"))
    if not lic or not all(foto.get(k) for k in ("url", "autor", "orixe")):
        return False
    foto = {**foto, "licenza": lic, "data": foto.get("data") or hoxe()}
    if any(f["url"] == foto["url"] for f in a["fotos"]):
        return False
    a["fotos"].append(foto)
    return True
