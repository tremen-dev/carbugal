"""Textos das fichas con Claude, ancorados só nos datos da propia ficha.

1. `redacta`: Claude escribe un resumo e unhas frases, e indica para cada frase
   que campos dos datos a sosteñen.
2. `verifica`: unha segunda chamada, independente, contrasta cada frase cos
   datos e marca as que non están sostidas. Esas frases elimínanse.
Se Claude declina a petición (stop_reason "refusal"), a ficha queda sen texto e
qa.py retena; non se reintenta con outro modelo.
"""
from __future__ import annotations

import json
from typing import TYPE_CHECKING

from pydantic import BaseModel

from common import CONFIG, agora

if TYPE_CHECKING:
    import anthropic

MODELO = CONFIG["modelo_claude"]

SISTEMA_REDACCION = """Es o redactor de Carballos Únicos de Galiza, un catálogo divulgativo e sen ánimo de lucro dos carballos senlleiros de Galicia.
Escribes en galego normativo, con ton próximo, tranquilo e documental.
Regras:
- Usa SÓ os feitos do JSON que recibes. Non engadas datos, datas, idades, lendas nin historia que non estean nel.
- Se un dato non está, non o menciones nin o supoñas.
- Cada frase indica en "campos" as claves do JSON que a sosteñen (por exemplo "medidas.perimetro_m", "concello").
- As fotos de "proximas" son doutros carballos da contorna: non digas que son desta árbore.
- Nada de superlativos comerciais nin vocabulario do motor ou da venda.
- Entre 3 e 7 frases, cada unha distinta e con información propia; o resumo, unha frase de menos de 30 palabras."""

SISTEMA_VERIFICACION = """Es un verificador. Recibes un JSON de datos e unha lista de frases en galego.
Para cada frase decide se TODO o que afirma está sostido polos datos. Calquera dato, número, data, adxectivo valorativo ou relación que non estea nos datos fai que a frase non estea sostida.
Responde para cada frase co seu índice, sostida true/false e un motivo curto."""


class Frase(BaseModel):
    texto: str
    campos: list[str]


class Redaccion(BaseModel):
    resumo: str
    frases: list[Frase]


class Veredicto(BaseModel):
    indice: int
    sostida: bool
    motivo: str


class Verificacion(BaseModel):
    veredictos: list[Veredicto]


def datos_para_claude(a: dict) -> dict:
    """Só os feitos que Claude pode usar: sen URLs de fotos nin estados internos."""
    return {
        "nome": a["nome"],
        "especie": a.get("especie"),
        "lugar": a.get("lugar"),
        "concello": a.get("concello"),
        "provincia": a.get("provincia"),
        "no_catalogo_oficial_da_xunta": bool(a.get("catalogo_xunta")),
        "medidas": {k: v["valor"] for k, v in (a.get("medidas") or {}).items()},
        "observacions_de_carballos_a_menos_de_1_km": a.get("observacions", {}).get("total_1km"),
        "ultima_observacion_proxima": a.get("observacions", {}).get("ultima"),
        "numero_de_fotos_propias": sum(1 for f in a.get("fotos", []) if not f.get("proxima")),
        "historia_aportada_pola_comunidade": (a.get("proposta") or {}).get("historia"),
        "fontes": [f["nome"] for f in a.get("fontes", [])],
    }


def _chama(cliente: anthropic.Anthropic, sistema: str, contido: str, formato):
    r = cliente.messages.parse(
        model=MODELO,
        max_tokens=4000,
        system=sistema,
        messages=[{"role": "user", "content": contido}],
        output_format=formato,
    )
    if r.stop_reason == "refusal" or r.parsed_output is None:
        return None
    return r.parsed_output


def redacta_e_verifica(a: dict, cliente: anthropic.Anthropic | None = None) -> dict | None:
    if cliente is None:
        import anthropic
        cliente = anthropic.Anthropic()
    datos = datos_para_claude(a)
    datos_json = json.dumps(datos, ensure_ascii=False, indent=2)
    red = _chama(cliente, SISTEMA_REDACCION, f"Datos da árbore:\n{datos_json}", Redaccion)
    if red is None:
        return None
    frases = [red.resumo] + [f.texto for f in red.frases]
    lista = "\n".join(f"{i}. {t}" for i, t in enumerate(frases))
    ver = _chama(cliente, SISTEMA_VERIFICACION, f"Datos:\n{datos_json}\n\nFrases:\n{lista}", Verificacion)
    if ver is None:
        return None
    sostidas = {v.indice for v in ver.veredictos if v.sostida}
    return {
        "resumo": red.resumo if 0 in sostidas else None,
        "frases": [f.model_dump() for i, f in enumerate(red.frases, start=1) if i in sostidas],
        "descartadas": [frases[v.indice] for v in ver.veredictos
                        if not v.sostida and 0 <= v.indice < len(frases)],
        "datos_usados": datos,
        "modelo": MODELO,
        "xerado": agora(),
    }
