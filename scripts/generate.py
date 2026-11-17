"""Textos das fichas cun modelo de IA (DeepSeek), ancorados só nos datos da propia ficha.

1. `redacta`: o modelo escribe un resumo e unhas frases, e indica para cada frase
   que campos dos datos a sosteñen.
2. `verifica`: unha segunda chamada, independente, contrasta cada frase cos
   datos e marca as que non están sostidas. Esas frases elimínanse.
Se a resposta non é JSON válido co formato pedido, a ficha queda sen texto e
qa.py retena.

A API de DeepSeek é compatible coa de OpenAI; chámase con urllib, sen dependencias.
A clave lese da variable de contorno DEEPSEEK_API_KEY (segredo do repositorio).
"""
from __future__ import annotations

import json
import os
import time
import urllib.request

from pydantic import BaseModel, ValidationError

from common import CONFIG, USER_AGENT, agora

MODELO = CONFIG["modelo_ia"]
API_URL = CONFIG["ia_api_url"]
CLAVE_ENV = "DEEPSEEK_API_KEY"

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

FORMATO = {
    "Redaccion": 'Responde só cun obxecto JSON: {"resumo": "...", "frases": [{"texto": "...", "campos": ["..."]}]}',
    "Verificacion": 'Responde só cun obxecto JSON: {"veredictos": [{"indice": 0, "sostida": true, "motivo": "..."}]}',
}


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


def datos_para_modelo(a: dict) -> dict:
    """Só os feitos que o modelo pode usar: sen URLs de fotos nin estados internos."""
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


datos_para_claude = datos_para_modelo  # nome antigo


class ClienteDeepSeek:
    """Chamada mínima a /chat/completions en modo JSON."""

    def __init__(self, clave: str | None = None):
        self.clave = clave or os.environ[CLAVE_ENV]

    def json(self, sistema: str, contido: str) -> dict | None:
        corpo = json.dumps({
            "model": MODELO,
            "messages": [{"role": "system", "content": sistema},
                         {"role": "user", "content": contido}],
            "response_format": {"type": "json_object"},
            "temperature": 0.3,
            "max_tokens": 4000,
        }).encode()
        cab = {"Authorization": f"Bearer {self.clave}", "Content-Type": "application/json",
               "User-Agent": USER_AGENT}
        for intento in range(3):
            try:
                req = urllib.request.Request(API_URL, data=corpo, headers=cab)
                with urllib.request.urlopen(req, timeout=180) as r:
                    resposta = json.loads(r.read().decode("utf-8"))
                break
            except Exception:
                if intento == 2:
                    raise
                time.sleep(5 * (intento + 1))
        escolla = resposta["choices"][0]
        if escolla.get("finish_reason") not in ("stop", None):
            return None  # cortada ou filtrada
        try:
            return json.loads(escolla["message"]["content"] or "")
        except json.JSONDecodeError:
            return None


def _chama(cliente, sistema: str, contido: str, formato):
    bruto = cliente.json(sistema + "\n\n" + FORMATO[formato.__name__], contido)
    if not bruto:
        return None
    try:
        return formato.model_validate(bruto)
    except ValidationError:
        return None


def redacta_e_verifica(a: dict, cliente=None) -> dict | None:
    cliente = cliente or ClienteDeepSeek()
    datos = datos_para_modelo(a)
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
