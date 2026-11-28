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
    """Imita client.messages.parse devolvendo as respostas da cola."""
    def __init__(self, respostas):
        self.respostas = list(respostas)
        self.messages = types.SimpleNamespace(parse=self._parse)

    def _parse(self, **kw):
        return types.SimpleNamespace(stop_reason="end_turn", parsed_output=self.respostas.pop(0))


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
        from generate import datos_para_claude
        a["texto"] = {"resumo": "Un carballo vello.", "datos_usados": datos_para_claude(a),
                      "frases": [{"texto": "Mide 7.5 metros.", "campos": []}, {"texto": "Ten 300 anos.", "campos": []},
                                 {"texto": "É un Quercus robur.", "campos": []}]}
        r = self.qa.avalia(a, [])
        self.assertEqual(r["estado"], "retido")
        self.assertTrue(any("300" in m for m in r["motivos"]))

    def test_texto_correcto_publicado(self):
        a = arbore_exemplo()
        from generate import datos_para_claude
        a["texto"] = {"resumo": "Un carballo do catálogo oficial.", "datos_usados": datos_para_claude(a),
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
        import re
        import xml.etree.ElementTree as ET
        import build
        tmp = Path(tempfile.mkdtemp())
        orixinal = (common.ARBORES, build.SITE_OUT, build.le_arbores)
        try:
            arb = tmp / "arbores"; arb.mkdir()
            a = arbore_exemplo(estado="publicado", coords_privadas=True, actualizado="2026-01-15",
                               publicado_en="2026-01-10",
                               texto={"resumo": "Resumo <script>", "frases": [{"texto": "Frase.", "campos": []}]})
            (arb / f"{a['slug']}.json").write_text(json.dumps(a), encoding="utf-8")
            common.ARBORES = arb
            build.SITE_OUT = tmp / "_site"
            build.le_arbores = lambda: [json.loads(p.read_text()) for p in arb.glob("*.json")]
            r = build.construe()
            self.assertEqual(r["paxinas"], 1)

            portada = (tmp / "_site" / "index.html").read_text(encoding="utf-8")
            self.assertIn("<title>Carballos Únicos de Galiza · Catálogo e mapa de árbores senlleiras</title>", portada)
            self.assertNotIn("Inicio ·", portada)
            self.assertIn('href="https://fonts.gstatic.com" crossorigin', portada)
            self.assertIn('href="/static/favicon-48.png"', portada)
            self.assertIn('href="/static/icona-192.png"', portada)
            self.assertIn('href="/static/apple-touch-icon.png"', portada)
            self.assertIn('property="og:locale" content="gl_ES"', portada)
            self.assertIn('name="twitter:card"', portada)

            ld_portada = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', portada).group(1))
            tipos_portada = {n["@type"] for n in ld_portada["@graph"]}
            self.assertEqual(tipos_portada, {"WebSite", "Organization"})

            ficha = (tmp / "_site" / "carballos" / a["slug"] / "index.html").read_text(encoding="utf-8")
            self.assertIn("Resumo &lt;script&gt;", ficha)
            self.assertIn("aproximada", ficha)
            self.assertIn('alt="Carballo de Proba (Quercus robur) en Concello de Proba"', ficha)
            self.assertIn('fetchpriority="high"', ficha)
            self.assertNotIn('alt="" fetchpriority="high"', ficha)

            # A foto principal non debe levar loading="lazy"
            img_principal = re.search(r'<figure class=""><img [^>]+>', ficha).group(0)
            self.assertNotIn('loading="lazy"', img_principal)

            # JSON-LD seguro fronte a </script> e parseable
            ld_raw = re.search(r'<script type="application/ld\+json">(.*?)</script>', ficha).group(1)
            self.assertNotIn("<script>", ld_raw)
            ld_ficha = json.loads(ld_raw)
            grafo = {n["@type"]: n for n in ld_ficha["@graph"]}
            self.assertIn("BreadcrumbList", grafo)
            self.assertAlmostEqual(grafo["Place"]["geo"]["latitude"] % 0.005, 0, places=6)
            self.assertEqual(grafo["Place"]["image"][0]["license"], "https://creativecommons.org/licenses/by-sa/4.0/")

            # Metadescricións únicas nas seccións principais
            desc_sobre = re.search(r'<meta name="description" content="([^"]+)">',
                                   (tmp / "_site" / "sobre" / "index.html").read_text(encoding="utf-8")).group(1)
            desc_mapa = re.search(r'<meta name="description" content="([^"]+)">',
                                  (tmp / "_site" / "mapa" / "index.html").read_text(encoding="utf-8")).group(1)
            self.assertNotEqual(desc_sobre, common.CONFIG["lema"])
            self.assertNotEqual(desc_mapa, desc_sobre)

            # 404.html con noindex e sen canonical
            p404 = (tmp / "_site" / "404.html").read_text(encoding="utf-8")
            self.assertIn('content="noindex, follow"', p404)
            self.assertNotIn('rel="canonical"', p404)

            # Sitemap con lastmod real na ficha e sen lastmod en /sobre/
            root = ET.fromstring((tmp / "_site" / "sitemap.xml").read_text(encoding="utf-8"))
            ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
            urls = {u.find("s:loc", ns).text: (u.find("s:lastmod", ns).text if u.find("s:lastmod", ns) is not None else None)
                    for u in root.findall("s:url", ns)}
            self.assertEqual(urls[f"https://carbugal.com/carballos/{a['slug']}/"], "2026-01-15")
            self.assertIsNone(urls["https://carbugal.com/sobre/"])
            self.assertNotIn("https://carbugal.com/404.html", urls)

            geo = json.loads((tmp / "_site" / "datos" / "arbores.geojson").read_text())
            lon, lat = geo["features"][0]["geometry"]["coordinates"]
            self.assertAlmostEqual(lat % 0.005, 0, places=6)
        finally:
            common.ARBORES, build.SITE_OUT, build.le_arbores = orixinal
            shutil.rmtree(tmp)

    def test_coincide_concello(self):
        import collect
        self.assertFalse(collect._coincide_concello({"municipality": "Bueu", "province": "Pontevedra"}, "Vedra"))
        self.assertTrue(collect._coincide_concello({"municipality": "Vedra", "state_district": "A Coruña"}, "Vedra"))
        self.assertFalse(collect._coincide_concello(
            {"locality": "A Porqueira", "municipality": "Vilamartín de Valdeorras"}, "A Porqueira"
        ))
        self.assertFalse(collect._coincide_concello(
            {"village": "A Porqueira", "municipality": "Vilamartín de Valdeorras"}, "A Porqueira"
        ))
        self.assertTrue(collect._coincide_concello({"municipality": "Porqueira"}, "A Porqueira"))
        self.assertTrue(collect._coincide_concello({"municipality": "A Pobra do Brollón"}, "A Pobra de Brollón"))

    def test_xeocodifica_rexeita_outro_concello(self):
        import time
        import collect

        arbore = common.nova_arbore(
            "Carballo fastixiado do Pazo de Santa Cruz",
            orixe="xunta",
            lugar="Pazo de Santa Cruz",
            concello="Vedra",
            provincia="A Coruña",
        )
        consultas = []
        gardadas = []

        def fake_http_json(url, params=None, **kw):
            consultas.append(params["q"])
            if len(consultas) == 1:
                return [{
                    "lat": "42.3250997",
                    "lon": "-8.795752",
                    "address": {"municipality": "Bueu", "province": "Pontevedra"},
                }]
            return [{
                "lat": "42.7858183",
                "lon": "-8.4277546",
                "address": {"municipality": "Vedra", "state_district": "A Coruña"},
            }]

        orig_http = collect.http_json
        orig_le = collect.le_arbores
        orig_garda = collect.garda_arbore
        orig_sleep = time.sleep
        try:
            collect.http_json = fake_http_json
            collect.le_arbores = lambda: [arbore]
            collect.garda_arbore = gardadas.append
            time.sleep = lambda _: None
            res = collect.xeocodifica()
        finally:
            collect.http_json = orig_http
            collect.le_arbores = orig_le
            collect.garda_arbore = orig_garda
            time.sleep = orig_sleep

        self.assertEqual(res["xeocodificadas"], 1)
        self.assertEqual(len(consultas), 2)
        self.assertEqual(len(gardadas), 1)
        self.assertAlmostEqual(arbore["lat"], 42.7858183)
        self.assertAlmostEqual(arbore["lon"], -8.4277546)
        self.assertTrue(arbore["coords_aproximadas"])


if __name__ == "__main__":
    unittest.main()
