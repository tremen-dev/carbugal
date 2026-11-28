"""Recolledores de fontes abertas.

Cada función é independente: se unha fonte falla, as outras seguen e o fallo
queda anotado no informe semanal.

Fontes:
- Catálogo da Xunta: data/seed/catalogo-xunta.csv (importado a man unha vez desde o
  Anexo I do Decreto 67/2007 na redacción do Decreto 10/2015 e resolucións posteriores).
- Wikidata (CC0): descubre árbores individuais de Quercus en Galicia.
- Wikimedia Commons: fotos con autor e licenza lidos dos metadatos.
- iNaturalist: observacións e fotos con licenza CC0 / CC BY / CC BY-SA.
- GBIF: rexistros de Quercus en Galicia (só licenzas CC0 e CC BY).
- Propostas da xente: issues coa etiqueta "proposta" (creadas por n8n).
"""
from __future__ import annotations

import csv
import html
import json
import math
import os
import re
import urllib.parse

from common import (CONFIG, DATA, en_galicia, engade_fonte, engade_foto, garda_arbore,
                    hoxe, http_json, le_arbores, nova_arbore, slugify)

INAT = "https://api.inaturalist.org/v1"
GBIF = "https://api.gbif.org/v1"
COMMONS = "https://commons.wikimedia.org/w/api.php"
WIKIDATA_SPARQL = "https://query.wikidata.org/sparql"
XUNTA_URL = "https://cmatv.xunta.gal/seccion-organizacion/c/CMAOT_Arbores_senlleiras"


def _por_slug() -> dict[str, dict]:
    return {a["slug"]: a for a in le_arbores()}


# ---------------------------------------------------------------- Xunta
def importa_xunta() -> dict:
    """Crea ou actualiza fichas desde o CSV do catálogo oficial (só datos, sen textos nin fotos)."""
    ruta = DATA / "seed" / "catalogo-xunta.csv"
    arbores = _por_slug()
    novas = 0
    with ruta.open(encoding="utf-8") as f:
        for fila in csv.DictReader(f):
            if not fila.get("nome"):
                continue
            slug = slugify(fila["nome"])
            a = arbores.get(slug) or nova_arbore(fila["nome"], orixe="xunta")
            novas += slug not in arbores
            for campo in ("especie", "lugar", "concello", "provincia"):
                if fila.get(campo):
                    a[campo] = fila[campo].strip()
            if fila.get("lat") and fila.get("lon"):
                a["lat"], a["lon"] = float(fila["lat"]), float(fila["lon"])
                a["coords_aproximadas"] = False
            for medida in ("perimetro_m", "altura_m"):
                if fila.get(medida):
                    a["medidas"][medida] = {"valor": float(fila[medida]),
                                            "fonte": "Catálogo galego de árbores senlleiras"}
            a["catalogo_xunta"] = {"codigo": fila.get("codigo") or None,
                                   "fonte_url": fila.get("fonte_url") or XUNTA_URL}
            a["coords_privadas"] = fila.get("privada", "").lower() in ("si", "sí", "1", "true")
            engade_fonte(a, "Catálogo galego de árbores senlleiras (Xunta de Galicia)",
                         a["catalogo_xunta"]["fonte_url"])
            garda_arbore(a)
    return {"fonte": "xunta", "novas": novas}


# ---------------------------------------------------------------- Wikidata
SPARQL = """
SELECT ?item ?itemLabel ?coord ?commons ?imaxe ?taxonLabel ?concelloLabel WHERE {
  VALUES ?tipo { wd:Q10884 wd:Q811534 }
  ?item wdt:P31 ?tipo .
  # Caixa xeográfica de Galicia: moito máis rápida que percorrer P131+ (que esgotaba o tempo).
  SERVICE wikibase:box {
    ?item wdt:P625 ?coord .
    bd:serviceParam wikibase:cornerSouthWest "Point(-9.35 41.80)"^^geo:wktLiteral .
    bd:serviceParam wikibase:cornerNorthEast "Point(-6.70 43.80)"^^geo:wktLiteral .
  }
  ?item wdt:P131+ wd:Q3908 .   # só Galicia (a caixa colle tamén Portugal e Asturias)
  OPTIONAL { ?item wdt:P10241 ?taxon . }
  OPTIONAL { ?item wdt:P373 ?commons . }
  OPTIONAL { ?item wdt:P18 ?imaxe . }
  OPTIONAL { ?item wdt:P131 ?concello . }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "gl,es,en". }
}
"""


def descubre_wikidata() -> dict:
    # POST: a consulta vai no corpo e non nunha URL longa.
    corpo = urllib.parse.urlencode({"query": SPARQL, "format": "json"}).encode()
    res = http_json(WIKIDATA_SPARQL, data=corpo, timeout=90,
                    headers={"Accept": "application/sparql-results+json",
                             "Content-Type": "application/x-www-form-urlencoded"})
    arbores = _por_slug()
    novas = 0
    for b in res["results"]["bindings"]:
        nome = b["itemLabel"]["value"]
        taxon = b.get("taxonLabel", {}).get("value", "")
        nome_l = nome.lower()
        en_catalogo = slugify(nome) in arbores
        e_quercus = (
            taxon.startswith("Quercus")
            or any(p in nome_l for p in ("carball", "carvalh", "sobreira", "aciñeira", "cerquiñ", "rebolo"))
        )
        if not (en_catalogo or e_quercus):
            continue
        m = re.match(r"Point\(([-\d.]+) ([-\d.]+)\)", b["coord"]["value"])
        lon, lat = (float(m.group(1)), float(m.group(2))) if m else (None, None)
        if not en_galicia(lat, lon):
            continue
        qid = b["item"]["value"].rsplit("/", 1)[-1]
        existente = next((a for a in arbores.values() if a.get("wikidata") == qid), None)
        a = existente or arbores.get(slugify(nome)) or nova_arbore(nome, orixe="wikidata")
        if a["slug"] not in arbores:
            novas += 1
        a["wikidata"] = qid
        a["especie"] = a["especie"] or (taxon or None)
        a["concello"] = a["concello"] or b.get("concelloLabel", {}).get("value")
        if a["lat"] is None or a.get("coords_aproximadas"):  # Wikidata ten coordenadas da propia árbore
            a["lat"], a["lon"], a["coords_aproximadas"] = lat, lon, False
        if b.get("commons"):
            a["commons_categoria"] = b["commons"]["value"]
        if b.get("imaxe"):
            a["wikidata_imaxe"] = urllib.parse.unquote(b["imaxe"]["value"].rsplit("/", 1)[-1])
        engade_fonte(a, "Wikidata", f"https://www.wikidata.org/wiki/{qid}")
        garda_arbore(a)
        arbores[a["slug"]] = a
    return {"fonte": "wikidata", "novas": novas}


# ---------------------------------------------------------------- Xeocodificación
NOMINATIM = "https://nominatim.openstreetmap.org/search"
_STOP_TOPONIMO = {"a", "o", "as", "os", "de", "do", "da", "dos", "das"}


def _tokens_toponimo(texto: str) -> list[str]:
    return [t for t in slugify(texto).split("-") if t and t not in _STOP_TOPONIMO]


def _coincide_concello(enderezo: dict, concello: str) -> bool:
    obx = _tokens_toponimo(concello)
    if not obx:
        return True
    if enderezo.get("municipality"):
        return _tokens_toponimo(enderezo["municipality"]) == obx
    return any(enderezo.get(k) and _tokens_toponimo(enderezo[k]) == obx
               for k in ("city", "town", "village"))


def xeocodifica() -> dict:
    """Para árbores sen coordenadas: localización aproximada do lugar co OpenStreetMap (Nominatim).
    Queda marcada como aproximada e substitúese se Wikidata trae as coordenadas da árbore."""
    import time
    feitas = 0
    for a in le_arbores():
        if a["lat"] is not None or not a.get("concello"):
            continue
        for consulta in filter(None, [
                f"{a['lugar']}, {a['concello']}, Galicia" if a.get("lugar") else None,
                f"{a['concello']}, {a.get('provincia') or ''}, Galicia"]):
            time.sleep(1.1)  # política de uso de Nominatim: 1 petición por segundo
            res = http_json(NOMINATIM, {
                "q": consulta, "format": "json", "addressdetails": 1, "limit": 5, "countrycodes": "es",
            })
            match = next(
                (r for r in (res or [])
                 if en_galicia(float(r["lat"]), float(r["lon"]))
                 and _coincide_concello(r.get("address") or {}, a["concello"])),
                None,
            )
            if match:
                a["lat"], a["lon"] = float(match["lat"]), float(match["lon"])
                a["coords_aproximadas"] = True
                engade_fonte(a, "OpenStreetMap (Nominatim), localización aproximada",
                             "https://www.openstreetmap.org/copyright")
                garda_arbore(a)
                feitas += 1
                break
    return {"fonte": "nominatim", "xeocodificadas": feitas}


# ---------------------------------------------------------------- Commons
_COMMONS_STOP = {
    "carballo", "carballos", "carballa", "sobreira", "sobreiras", "acineira",
    "cerquino", "rebolo", "grande", "vello", "pazo", "casa", "capela",
    "campo", "xardin", "historico", "fastixiado",
}
_COMMONS_ARBORE = ("carball", "sobreir", "acineir", "cerquin", "rebol", "quercus", "arbor")
_COMMONS_EXTS = (".jpg", ".jpeg", ".png", ".webp")


def _limpa_html(t: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", t or "")).strip()


def _engade_imaxes_commons(a: dict, params: dict) -> int:
    res = http_json(COMMONS, {
        "action": "query", "format": "json", "prop": "imageinfo",
        "iiprop": "url|extmetadata", "iiurlwidth": 1200, **params,
    })
    engadidas = 0
    for paxina in (res.get("query", {}).get("pages", {}) or {}).values():
        info = (paxina.get("imageinfo") or [{}])[0]
        if not info.get("url"):
            continue
        meta = info.get("extmetadata", {})
        engadidas += engade_foto(a, {
            "url": info.get("thumburl") or info.get("url"),
            "autor": _limpa_html(meta.get("Artist", {}).get("value", "")),
            "licenza": meta.get("LicenseShortName", {}).get("value"),
            "orixe": info.get("descriptionurl"),
            "data": (meta.get("DateTimeOriginal", {}).get("value") or "")[:10] or None,
            "fonte": "Wikimedia Commons",
        })
    return engadidas


def _palabras_clave(slug: str) -> list[str]:
    return [w for w in slug.split("-") if len(w) >= 4 and w not in _COMMONS_STOP]


def fotos_commons() -> dict:
    engadidas = 0
    for a in le_arbores():
        antes = engadidas
        if not a.get("commons_categoria"):
            res_cat = http_json(COMMONS, {
                "action": "query", "format": "json", "list": "search",
                "srsearch": f'"{a["nome"]}"', "srnamespace": "14", "srlimit": "3",
            })
            for h in res_cat.get("query", {}).get("search", []):
                cat = h["title"].removeprefix("Category:")
                if slugify(cat) == a["slug"]:
                    a["commons_categoria"] = cat
                    break
        if a.get("commons_categoria"):
            engadidas += _engade_imaxes_commons(a, {
                "generator": "categorymembers",
                "gcmtitle": f"Category:{a['commons_categoria']}",
                "gcmtype": "file", "gcmlimit": 20,
            })
            engade_fonte(a, "Wikimedia Commons",
                         f"https://commons.wikimedia.org/wiki/Category:{a['commons_categoria'].replace(' ', '_')}")
        if a.get("wikidata_imaxe"):
            engadidas += _engade_imaxes_commons(a, {"titles": f"File:{a['wikidata_imaxe']}"})
        ten_propia = any(not f.get("proxima") for f in a.get("fotos", []))
        kws = _palabras_clave(a["slug"])
        if not ten_propia and kws:
            res_f = http_json(COMMONS, {
                "action": "query", "format": "json", "list": "search",
                "srsearch": a["nome"], "srnamespace": "6", "srlimit": "8",
            })
            titulos = []
            for h in res_f.get("query", {}).get("search", []):
                t = h["title"]
                if not t.lower().endswith(_COMMONS_EXTS):
                    continue
                tslug = slugify(t.removeprefix("File:").rsplit(".", 1)[0])
                if all(k in tslug for k in kws) and any(x in tslug for x in _COMMONS_ARBORE):
                    titulos.append(t)
            if titulos:
                n = _engade_imaxes_commons(a, {"titles": "|".join(titulos[:5])})
                engadidas += n
                if n:
                    engade_fonte(a, "Wikimedia Commons",
                                 f"https://commons.wikimedia.org/w/index.php?search={urllib.parse.quote(a['nome'])}")
        if engadidas > antes or a.get("commons_categoria"):
            garda_arbore(a)
    return {"fonte": "commons", "fotos_novas": engadidas}


# ---------------------------------------------------------------- iNaturalist
def observacions_inat() -> dict:
    radio = CONFIG["radio_observacions_km"]
    fotos = 0
    for a in le_arbores():
        if a["lat"] is None:
            continue
        res = http_json(f"{INAT}/observations", {
            "taxon_name": "Quercus", "lat": a["lat"], "lng": a["lon"], "radius": radio,
            "quality_grade": "research", "photo_license": "cc0,cc-by,cc-by-sa",
            "order_by": "observed_on", "order": "desc", "per_page": 30,
        })
        obs = res.get("results", [])
        a["observacions"] = {"total_1km": res.get("total_results", 0),
                             "ultima": obs[0].get("observed_on") if obs else None,
                             "fonte": "iNaturalist"}
        for o in obs[:5]:
            usuario = (o.get("user") or {})
            for ph in (o.get("photos") or [])[:1]:
                fotos += engade_foto(a, {
                    "url": (ph.get("url") or "").replace("/square.", "/medium."),
                    "autor": usuario.get("name") or usuario.get("login"),
                    "licenza": ph.get("license_code"),
                    "orixe": o.get("uri"),
                    "data": o.get("observed_on"),
                    "fonte": "iNaturalist",
                    "proxima": True,  # carballo observado preto, non necesariamente esta árbore
                })
        if a.get("orixe") == "proposta" and not a["proposta"].get("verificada"):
            # Verificada se hai polo menos unha observación de Quercus doutra persoa a menos de 100 m.
            preto = http_json(f"{INAT}/observations", {
                "taxon_name": "Quercus", "lat": a["lat"], "lng": a["lon"], "radius": 0.1,
                "quality_grade": "research", "per_page": 1})
            a["proposta"]["verificada"] = preto.get("total_results", 0) > 0
        a["fontes"] = [f for f in a.get("fontes", []) if f.get("nome") != "iNaturalist"]
        engade_fonte(a, "iNaturalist", f"https://www.inaturalist.org/observations?taxon_name=Quercus"
                                       f"&lat={a['lat']}&lng={a['lon']}&radius={radio}")
        garda_arbore(a)
    return {"fonte": "inaturalist", "fotos_novas": fotos}


# Fenoloxía de Galicia: anotacións de iNaturalist (term_id 12 = Plant Phenology;
# valores 13 = en flor, 14 = con froito, 15 = gromos de flor). Comprobar ids na API se cambian.
FENO = {"flor": 13, "froito": 14, "gromos": 15}


def fenoloxia_inat() -> dict:
    b = {"swlat": 41.80, "swlng": -9.35, "nelat": 43.80, "nelng": -6.70}
    saida = {"actualizado": hoxe(), "fonte": "iNaturalist", "meses": {}}
    for nome, valor in FENO.items():
        res = http_json(f"{INAT}/observations/histogram", {
            **b, "taxon_name": "Quercus", "quality_grade": "research",
            "date_field": "observed", "interval": "month_of_year",
            "term_id": 12, "term_value_id": valor,
        })
        saida["meses"][nome] = res.get("results", {}).get("month_of_year", {})
    (DATA / "fenoloxia.json").write_text(json.dumps(saida, ensure_ascii=False, indent=2) + "\n",
                                         encoding="utf-8")
    return {"fonte": "inaturalist-fenoloxia", "ok": True}


# ---------------------------------------------------------------- GBIF
def resumo_gbif() -> dict:
    params = {"scientificName": "Quercus", "country": "ES",
              "decimalLatitude": "41.80,43.80", "decimalLongitude": "-9.35,-6.70",
              "hasCoordinate": "true", "license": ["CC0_1_0", "CC_BY_4_0"],
              "limit": 0, "facet": "speciesKey", "facetLimit": 20}
    res = http_json(f"{GBIF}/occurrence/search", params)
    especies = []
    for f in (res.get("facets") or [{}])[0].get("counts", []):
        sp = http_json(f"{GBIF}/species/{f['name']}")
        especies.append({"especie": sp.get("canonicalName"), "rexistros": f["count"]})
    saida = {"actualizado": hoxe(), "total": res.get("count", 0), "especies": especies,
             "fonte": "GBIF.org, Occurrence Search",
             "consulta": "https://api.gbif.org/v1/occurrence/search?scientificName=Quercus&country=ES"
                         "&decimalLatitude=41.8,43.8&decimalLongitude=-9.35,-6.7&license=CC0_1_0&license=CC_BY_4_0"}
    (DATA / "gbif.json").write_text(json.dumps(saida, ensure_ascii=False, indent=2) + "\n",
                                    encoding="utf-8")
    return {"fonte": "gbif", "total": saida["total"]}


# ---------------------------------------------------------------- Propostas
def propostas_github() -> dict:
    """Le issues abertas coa etiqueta 'proposta'. n8n créaas co corpo en JSON."""
    repo = os.environ.get("GITHUB_REPOSITORY")
    token = os.environ.get("GITHUB_TOKEN")
    if not (repo and token):
        return {"fonte": "propostas", "omitido": "sen GITHUB_TOKEN"}
    issues = http_json(f"https://api.github.com/repos/{repo}/issues",
                       {"labels": "proposta", "state": "open", "per_page": 50},
                       headers={"Authorization": f"Bearer {token}"})
    arbores = _por_slug()
    novas = 0
    for i in issues:
        m = re.search(r"```json\s*(\{.*?\})\s*```", i.get("body") or "", re.S)
        if not m:
            continue
        p = json.loads(m.group(1))
        lat, lon = float(p.get("lat", "nan")), float(p.get("lon", "nan"))
        if math.isnan(lat) or not en_galicia(lat, lon) or not p.get("nome"):
            continue
        slug = slugify(p["nome"])
        if slug in arbores:
            continue
        a = nova_arbore(p["nome"], orixe="proposta", especie=p.get("especie"),
                        concello=p.get("concello"), lat=lat, lon=lon)
        a["proposta"] = {"issue": i["html_url"], "historia": p.get("historia"),
                         "verificada": False}
        a["coords_privadas"] = bool(p.get("terreo_privado"))
        if p.get("foto_url"):
            engade_foto(a, {"url": p["foto_url"], "autor": p.get("autor"),
                            "licenza": p.get("licenza"), "orixe": i["html_url"],
                            "fonte": "Proposta da comunidade"})
        engade_fonte(a, "Proposta da comunidade", i["html_url"])
        garda_arbore(a)
        novas += 1
    return {"fonte": "propostas", "novas": novas}


RECOLLEDORES = [importa_xunta, descubre_wikidata, xeocodifica, fotos_commons, observacions_inat,
                fenoloxia_inat, resumo_gbif, propostas_github]


def recolle_todo() -> list[dict]:
    informe = []
    for f in RECOLLEDORES:
        try:
            informe.append({**f(), "ok": True})
        except Exception as e:  # unha fonte caída non para o ciclo
            informe.append({"fonte": f.__name__, "ok": False, "erro": str(e)[:300]})
    return informe
