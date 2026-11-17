"""Ciclo semanal completo: recoller, xerar, verificar, publicar.

Uso:  python scripts/weekly.py [--sen-ia] [--sen-rede]
Saída: data/informe.json (o que n8n le para avisar) e o sitio en _site/.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys

from common import CONFIG, DATA, agora, garda_arbore, hoxe, le_arbores
import build
import qa


def le_json(nome: str, defecto):
    ruta = DATA / nome
    return json.loads(ruta.read_text(encoding="utf-8")) if ruta.exists() else defecto


def garda_json(nome: str, valor) -> None:
    (DATA / nome).write_text(json.dumps(valor, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def pegada(datos: dict) -> str:
    return hashlib.sha256(json.dumps(datos, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:16]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sen-ia", "--sen-claude", dest="sen_ia", action="store_true", help="non xera textos (probas)")
    ap.add_argument("--sen-rede", action="store_true", help="non consulta fontes (probas)")
    args = ap.parse_args()

    rexistro = le_json("rexistro.json", [])
    estado = le_json("estado.json", {})
    informe = {"data": agora(), "fontes": [], "xeradas": [], "publicadas": [], "retidas": [], "erros": []}

    # 1. Recoller
    if not args.sen_rede:
        import collect
        informe["fontes"] = collect.recolle_todo()
    fallos = sum(1 for f in informe["fontes"] if not f["ok"])
    fontes_caidas = bool(informe["fontes"]) and fallos > len(informe["fontes"]) / 2
    if fontes_caidas:
        informe["erros"].append("máis da metade das fontes fallaron: esta semana non se publican fichas novas")

    # 2. Xerar textos (con tope semanal)
    from generate import CLAVE_ENV
    sen_clave = not os.environ.get(CLAVE_ENV)
    if sen_clave and not args.sen_ia:
        informe["erros"].append(f"falta o segredo {CLAVE_ENV}: esta semana non se redactan textos")
    if not args.sen_ia and not sen_clave and not fontes_caidas:
        from generate import ClienteDeepSeek, datos_para_modelo, redacta_e_verifica
        cliente = ClienteDeepSeek()
        tope = CONFIG["max_paxinas_novas_semana"]
        candidatas = []
        for a in le_arbores():
            if not qa.suficiente(a) or not qa.en_galicia(a.get("lat"), a.get("lon")):
                continue  # sen contido suficiente: non paga a pena xerar texto
            novos_datos = pegada(datos_para_modelo(a)) != (a.get("texto") or {}).get("pegada")
            if a.get("estado") != "publicado" or novos_datos:
                candidatas.append(a)
        # primeiro as do catálogo oficial, despois as máis documentadas
        candidatas.sort(key=lambda a: (a.get("orixe") != "xunta", -qa.conta_datos(a)))
        for a in candidatas[:tope]:
            try:
                t = redacta_e_verifica(a, cliente)
            except Exception as ex:
                informe["erros"].append(f"{a['slug']}: {str(ex)[:200]}")
                continue
            if t:
                t["pegada"] = pegada(datos_para_modelo(a))
            a["texto"] = t
            a["actualizado"] = hoxe()
            garda_arbore(a)
            informe["xeradas"].append(a["slug"])

    # 3. Verificar e decidir estados
    arbores = le_arbores()
    novas_esta_semana = 0
    for a in sorted(arbores, key=lambda a: a.get("estado") != "publicado"):
        resultado = qa.avalia(a, arbores)
        antes = a.get("estado")
        if resultado["estado"] == "publicado" and antes != "publicado":
            if fontes_caidas or novas_esta_semana >= CONFIG["max_paxinas_novas_semana"]:
                resultado = {**resultado, "estado": "retido", "motivos": ["agarda á semana seguinte (tope semanal)"]}
            else:
                novas_esta_semana += 1
                a["publicado_en"] = hoxe()
                rexistro.append({"data": hoxe(), "texto": f"Nova ficha: {a['nome']} ({a.get('concello') or 's/d'})"})
                informe["publicadas"].append(a["slug"])
        if antes == "publicado" and resultado["estado"] != "publicado":
            rexistro.append({"data": hoxe(), "texto": f"Ficha retirada temporalmente para revisión: {a['nome']}"})
        a["estado"] = resultado["estado"]
        a["qa"] = {**resultado, "data": hoxe()}
        if resultado["estado"] == "retido":
            informe["retidas"].append({"slug": a["slug"], "motivos": resultado["motivos"]})
        garda_arbore(a)

    # 4. Carballo do mes (rota polas fichas publicadas, sen repetir ata esgotalas)
    mes = hoxe()[:7]
    publicadas = [a["slug"] for a in le_arbores() if a["estado"] == "publicado"]
    if publicadas and estado.get("mes") != mes:
        destacados = [s for s in estado.get("destacados", []) if s in publicadas]
        quedan = [s for s in publicadas if s not in destacados]
        if not quedan:  # xa saíron todas: empeza unha nova volta
            destacados, quedan = [], publicadas
        escollido = sorted(quedan)[0]
        estado.update({"mes": mes, "carballo_do_mes": escollido, "destacados": destacados + [escollido]})
        rexistro.append({"data": hoxe(), "texto": f"Carballo do mes: {escollido}"})

    if not informe["publicadas"] and informe["xeradas"]:
        rexistro.append({"data": hoxe(), "texto": f"Actualizados os datos de {len(informe['xeradas'])} fichas"})
    garda_json("rexistro.json", rexistro)
    garda_json("estado.json", estado)

    # 5. Construír o sitio
    informe["sitio"] = build.construe()
    garda_json("informe.json", informe)
    print(json.dumps(informe, ensure_ascii=False, indent=2))
    return 1 if fontes_caidas else 0


if __name__ == "__main__":
    sys.exit(main())
