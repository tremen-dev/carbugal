"""Probas sen rede nin API: QA, xeración con cliente simulado e construción do sitio."""
import json
import shutil
import sys
import tempfile
import types
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "scripts"))

import common  # noqa: E402


def arbore_exemplo(**cambios):
    a = common.nova_arbore("Carballo de Proba", orixe="xunta", especie="Quercus robur",
                           concello="Concello de Proba", provincia="Lugo", lat=43.1, lon=-7.8)
    a["catalogo_xunta"] = {"codigo": None, "fonte_url": "https://example.org/xunta"}
    a["medidas"] = {"perimetro_m": {"valor": 7.5, "fonte": "Catálogo"}}
    a["observacions"] = {"total_1km": 12, "ultima": "2026-10-01", "fonte": "iNaturalist"}
    a["fontes"] = [{"nome": "Xunta", "url": "https://example.org/xunta"},
                   {"nome": "Wikidata", "url": "https://example.org/wd"}]
    a["fotos"] = [{"url": "https://example.org/f.jpg", "autor": "Ana", "licenza": "CC BY-SA 4.0",
                   "orixe": "https://example.org/orixe", "fonte": "Wikimedia Commons"}]
    a["wikidata"] = "Q1"
    a.update(cambios)
    return a


class ClienteFalso:
    """Imita ClienteDeepSeek.json devolvendo as respostas da cola."""
    def __init__(self, respostas):
        self.respostas = list(respostas)

    def json(self, sistema, contido):
        r = self.respostas.pop(0)
        return r.model_dump() if hasattr(r, "model_dump") else r


class Probas(unittest.TestCase):
    def setUp(self):
        import qa
        qa.erros_languagetool = lambda texto: []  # sen rede nas probas
        self.qa = qa

    def test_licenzas(self):
        self.assertEqual(common.normaliza_licenza("cc-by-sa"), "CC BY-SA")
        self.assertEqual(common.normaliza_licenza("CC BY-SA 4.0"), "CC BY-SA 4.0")
        self.assertIsNone(common.normaliza_licenza("cc-by-nc"))
        self.assertIsNone(common.normaliza_licenza("CC BY-ND 4.0"))
        self.assertIsNone(common.normaliza_licenza("all rights reserved"))

    def test_foto_sen_autor_rexeitada(self):
        a = arbore_exemplo(fotos=[])
        self.assertFalse(common.engade_foto(a, {"url": "u", "licenza": "cc0", "orixe": "o"}))
        self.assertTrue(common.engade_foto(a, {"url": "u", "licenza": "cc0", "orixe": "o", "autor": "X"}))

    def test_sen_foto_propia_so_mapa(self):
        a = arbore_exemplo(fotos=[{"url": "u", "autor": "X", "licenza": "cc0", "orixe": "o", "proxima": True}])
        self.assertEqual(self.qa.avalia(a, [])["estado"], "so_mapa")

    def test_xeracion_descarta_frases_non_sostidas(self):
        from generate import Frase, Redaccion, Veredicto, Verificacion, redacta_e_verifica
        red = Redaccion(resumo="O Carballo de Proba medra no Concello de Proba.", frases=[
            Frase(texto="É un Quercus robur.", campos=["especie"]),
            Frase(texto="O seu tronco mide 7.5 metros de perímetro.", campos=["medidas.perimetro_m"]),
            Frase(texto="Ten 500 anos.", campos=[]),
            Frase(texto="Está no catálogo oficial da Xunta.", campos=["no_catalogo_oficial_da_xunta"]),
        ])
        ver = Verificacion(veredictos=[Veredicto(indice=i, sostida=i != 3, motivo="") for i in range(5)])
        t = redacta_e_verifica(arbore_exemplo(), ClienteFalso([red, ver]))
        self.assertEqual(len(t["frases"]), 3)
        self.assertIn("Ten 500 anos.", t["descartadas"])

    def test_numero_inventado_retido(self):
        a = arbore_exemplo()
        from generate import datos_para_modelo
        a["texto"] = {"resumo": "Un carballo vello.", "datos_usados": datos_para_modelo(a),
                      "frases": [{"texto": "Mide 7.5 metros.", "campos": []}, {"texto": "Ten 300 anos.", "campos": []},
                                 {"texto": "É un Quercus robur.", "campos": []}]}
        r = self.qa.avalia(a, [])
        self.assertEqual(r["estado"], "retido")
        self.assertTrue(any("300" in m for m in r["motivos"]))

    def test_texto_correcto_publicado(self):
        a = arbore_exemplo()
        from generate import datos_para_modelo
        a["texto"] = {"resumo": "Un carballo do catálogo oficial.", "datos_usados": datos_para_modelo(a),
                      "frases": [{"texto": "Mide 7.5 metros de perímetro.", "campos": []},
                                 {"texto": "É un Quercus robur de Lugo.", "campos": []},
                                 {"texto": "Hai 12 observacións de carballos preto.", "campos": []}]}
        self.assertEqual(self.qa.avalia(a, [])["estado"], "publicado")

    def test_castelan_retido(self):
        a = arbore_exemplo()
        a["texto"] = {"resumo": "Este árbol es muy antiguo.", "datos_usados": {},
                      "frases": [{"texto": "a", "campos": []}] * 3}
        self.assertIn("posible castelán mesturado no texto", self.qa.avalia(a, [])["motivos"])

    def test_construe_sitio(self):
        import build
        tmp = Path(tempfile.mkdtemp())
        orixinal = (common.ARBORES, build.SITE_OUT)
        try:
            arb = tmp / "arbores"; arb.mkdir()
            a = arbore_exemplo(estado="publicado", coords_privadas=True,
                               texto={"resumo": "Resumo <script>", "frases": [{"texto": "Frase.", "campos": []}]})
            (arb / f"{a['slug']}.json").write_text(json.dumps(a), encoding="utf-8")
            common.ARBORES = arb
            build.SITE_OUT = tmp / "_site"
            import importlib
            build.le_arbores = lambda: [json.loads(p.read_text()) for p in arb.glob("*.json")]
            r = build.construe()
            self.assertEqual(r["paxinas"], 1)
            ficha = (tmp / "_site" / "carballos" / a["slug"] / "index.html").read_text()
            self.assertIn("Resumo &lt;script&gt;", ficha)
            self.assertIn("aproximada", ficha)
            geo = json.loads((tmp / "_site" / "datos" / "arbores.geojson").read_text())
            lon, lat = geo["features"][0]["geometry"]["coordinates"]
            self.assertAlmostEqual(lat % 0.005, 0, places=6)
        finally:
            common.ARBORES, build.SITE_OUT = orixinal
            shutil.rmtree(tmp)


if __name__ == "__main__":
    unittest.main()
