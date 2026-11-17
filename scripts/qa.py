"""Controis de calidade. Deciden o estado de cada ficha:

- publicado: ten páxina propia.
- so_mapa:   aparece só no mapa (contido insuficiente para unha páxina propia).
- retido:    algo fallou (texto non verificado, lingua, duplicado...).
"""
from __future__ import annotations

import re
from difflib import SequenceMatcher

from common import CONFIG, en_galicia, http_json, normaliza_licenza

# Palabras castelás frecuentes que delatan mestura de linguas.
CASTELAN = re.compile(r"\b(del|muy|árbol|árboles|también|ubicado|hoja|hojas|años|sin)\b", re.I)
NUMERO = re.compile(r"\d+(?:[.,]\d+)?")


def conta_datos(a: dict) -> int:
    datos = [a.get("especie"), a.get("concello"), a.get("provincia"), a.get("lat"),
             a.get("catalogo_xunta"), a.get("wikidata"),
             (a.get("observacions") or {}).get("total_1km")]
    return sum(1 for d in datos if d) + len(a.get("medidas") or {})


def suficiente(a: dict) -> bool:
    """Contido mínimo para ter páxina propia: datos, unha foto da propia árbore e fontes."""
    propias = [f for f in fotos_validas(a) if not f.get("proxima")]
    return (conta_datos(a) >= CONFIG["min_datos_ficha"] and len(propias) >= 1
            and len(a.get("fontes", [])) >= CONFIG["min_fontes_ficha"])


def fotos_validas(a: dict) -> list[dict]:
    return [f for f in a.get("fotos", [])
            if normaliza_licenza(f.get("licenza")) and f.get("autor") and f.get("orixe")]


def numeros_sen_soporte(texto: str, datos: dict) -> list[str]:
    plano = " ".join(str(v) for v in _aplana(datos))
    permitidos = set(NUMERO.findall(plano.replace(",", ".")))
    return [n for n in NUMERO.findall(texto.replace(",", ".")) if n not in permitidos]


def _aplana(x):
    if isinstance(x, dict):
        for v in x.values():
            yield from _aplana(v)
    elif isinstance(x, list):
        for v in x:
            yield from _aplana(v)
    elif x is not None:
        yield x


def similitude(t1: str, t2: str) -> float:
    return SequenceMatcher(None, t1.lower(), t2.lower()).ratio()


def texto_plano(a: dict) -> str:
    t = a.get("texto") or {}
    return " ".join([t.get("resumo") or ""] + [f["texto"] for f in t.get("frases", [])]).strip()


def avalia(a: dict, outras: list[dict]) -> dict:
    """Devolve {"estado": ..., "motivos": [...], "avisos": [...]} sen modificar a ficha."""
    motivos, avisos = [], []

    if not en_galicia(a.get("lat"), a.get("lon")):
        return {"estado": "retido", "motivos": ["coordenadas fóra de Galicia ou ausentes"], "avisos": []}

    fotos = fotos_validas(a)
    if len(fotos) != len(a.get("fotos", [])):
        avisos.append("hai fotos sen licenza ou atribución válidas: non se mostrarán")

    if not suficiente(a):
        return {"estado": "so_mapa", "motivos": ["contido insuficiente para páxina propia"], "avisos": avisos}

    texto = a.get("texto")
    if not texto:
        return {"estado": "retido", "motivos": ["sen texto verificado"], "avisos": avisos}
    if len(texto.get("frases", [])) + bool(texto.get("resumo")) < CONFIG["min_frases_verificadas"]:
        motivos.append("menos frases verificadas das necesarias")
    plano = texto_plano(a)
    sen_soporte = numeros_sen_soporte(plano, texto.get("datos_usados", {}))
    if sen_soporte:
        motivos.append(f"números sen soporte nos datos: {', '.join(sen_soporte)}")
    if CASTELAN.search(plano):
        motivos.append("posible castelán mesturado no texto")
    erros = erros_languagetool(plano)
    if len(erros) > 2:  # os topónimos dan algún falso positivo: tolérase ata 2
        motivos.append(f"{len(erros)} erros de lingua segundo LanguageTool")
    for o in outras:
        if o["slug"] == a["slug"] or o.get("estado") != "publicado":
            continue
        op = texto_plano(o)
        if op and similitude(plano, op) > 0.8:
            motivos.append(f"texto demasiado parecido a {o['slug']}")
        fa = (texto.get("frases") or [{}])[0].get("texto", "")
        fo = ((o.get("texto") or {}).get("frases") or [{}])[0].get("texto", "")
        if fa and fo and similitude(fa, fo) > 0.85:
            motivos.append(f"primeira frase repetida con {o['slug']}")

    return {"estado": "retido" if motivos else "publicado", "motivos": motivos, "avisos": avisos}


def erros_languagetool(texto: str) -> list[str]:
    """Revisión ortográfica e gramatical en galego coa API pública de LanguageTool.
    Se a API non responde, devolve [] e o ciclo segue (queda o filtro de castelán)."""
    try:
        import urllib.parse
        r = http_json("https://api.languagetool.org/v2/check",
                      data=urllib.parse.urlencode({"text": texto, "language": "gl-ES"}).encode(),
                      headers={"Content-Type": "application/x-www-form-urlencoded"}, retries=1)
    except Exception:
        return []
    return [m["message"] for m in r.get("matches", [])
            if m.get("rule", {}).get("issueType") in ("misspelling", "grammar")]
