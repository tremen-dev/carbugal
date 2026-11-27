"""Xera a web estática en _site/ a partir de data/."""
from __future__ import annotations

import json
import shutil
from html import escape as e

from common import CONFIG, DATA, ROOT, SITE_OUT, hoxe, le_arbores

URL = CONFIG["site_url"].rstrip("/")
MESES = ["xan", "feb", "mar", "abr", "mai", "xuñ", "xul", "ago", "set", "out", "nov", "dec"]
FONTES_GOOGLE = ("https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,600"
                 "&family=Source+Sans+3:wght@400;600&display=swap")


def paxina(titulo: str, corpo: str, descricion: str = "", ruta: str = "/", extra_head: str = "") -> str:
    desc = descricion or CONFIG["lema"]
    return f"""<!doctype html>
<html lang="gl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(titulo)} · {e(CONFIG['nome'])}</title>
<meta name="description" content="{e(desc)}">
<link rel="canonical" href="{URL}{ruta}">
<link rel="icon" href="/static/simbolo.svg" type="image/svg+xml">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="{FONTES_GOOGLE}">
<link rel="stylesheet" href="/static/estilo.css">
{extra_head}
</head>
<body>
<header class="cab"><div class="envoltorio">
  <a class="marca" href="/"><img src="/static/simbolo.svg" width="44" height="44" alt="">
    <span><span class="nome">carb<span>u</span>gal</span><br><span class="sub">{e(CONFIG['nome'])}</span></span></a>
  <nav aria-label="Principal"><ul>
    <li><a href="/carballos/">Carballos</a></li><li><a href="/mapa/">Mapa</a></li>
    <li><a href="/fenoloxia/">O ano do carballo</a></li><li><a href="/propon/">Propón un carballo</a></li>
  </ul></nav>
</div></header>
<main><div class="envoltorio">
{corpo}
</div></main>
<footer><div class="envoltorio">
  <p><strong>{e(CONFIG['nome'])}</strong>. Proxecto cultural e divulgativo sen ánimo de lucro, sen publicidade e sen relación con ningunha empresa.</p>
  <p><a href="/como-se-fai/">Como se fai esta web</a> · <a href="/creditos/">Créditos e licenzas</a> ·
     <a href="/rexistro/">Rexistro de cambios</a> · <a href="/en-cifras/">En cifras</a> · <a href="/sobre/">Aviso legal</a></p>
  <p>Textos baixo <a href="https://creativecommons.org/licenses/by-sa/4.0/deed.gl">CC BY-SA 4.0</a>. Cada foto leva o seu autor e licenza. Mapa © colaboradores de OpenStreetMap.</p>
  <p class="pe-tremen">Un proxecto de <a class="tremen" href="https://tremen.dev" target="_blank" rel="noopener noreferrer"><img src="/static/tremen.svg" width="18" height="18" alt=""><span>tremen<span class="dev">.dev</span></span></a></p>
</div></footer>
</body>
</html>
"""


def escribe(ruta: str, html: str) -> None:
    destino = SITE_OUT / ruta.strip("/") / "index.html" if not ruta.endswith(".xml") else SITE_OUT / ruta.strip("/")
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(html, encoding="utf-8")


def coords_publicas(a: dict) -> tuple[float, float]:
    if a.get("coords_privadas") or a.get("coords_aproximadas"):
        paso = CONFIG["arredondar_coords_paso"]
        return round(round(a["lat"] / paso) * paso, 4), round(round(a["lon"] / paso) * paso, 4)
    return round(a["lat"], 5), round(a["lon"], 5)


def foto_html(f: dict, clase: str = "") -> str:
    pe = f"Foto: {e(f['autor'])}, <a href=\"{e(f['orixe'])}\">{e(f['licenza'])}</a> ({e(f.get('fonte', ''))})"
    return (f'<figure class="{clase}"><img src="{e(f["url"])}" alt="" loading="lazy">'
            f"<figcaption>{pe}</figcaption></figure>")


def propias(a: dict) -> list[dict]:
    return [f for f in a.get("fotos", []) if not f.get("proxima")]


def tarxeta(a: dict) -> str:
    f = (propias(a) or [{}])[0]
    img = f'<img src="{e(f["url"])}" alt="" loading="lazy">' if f.get("url") else ""
    resumo = (a.get("texto") or {}).get("resumo") or ""
    return (f'<article class="tarxeta">{img}<div class="corpo"><h3><a href="/carballos/{a["slug"]}/">{e(a["nome"])}</a></h3>'
            f'<p class="meta">{e(a.get("especie") or "")} · {e(a.get("concello") or "")}</p><p>{e(resumo)}</p></div></article>')


def ficha(a: dict) -> str:
    t = a.get("texto") or {}
    fotos = propias(a)
    proximas = [f for f in a.get("fotos", []) if f.get("proxima")]
    filas = [("Especie", a.get("especie")), ("Concello", a.get("concello")), ("Provincia", a.get("provincia"))]
    for k, v in (a.get("medidas") or {}).items():
        nome = {"perimetro_m": "Perímetro do tronco", "altura_m": "Altura"}.get(k, k)
        filas.append((nome, f"{v['valor']} m ({v['fonte']})"))
    if a.get("catalogo_xunta"):
        filas.append(("Catálogo oficial", "Incluído no Catálogo galego de árbores senlleiras"))
    obs = a.get("observacions") or {}
    if obs.get("total_1km"):
        filas.append(("Carballos observados a menos de 1 km", f"{obs['total_1km']} (iNaturalist; última: {obs.get('ultima') or 's/d'})"))
    lat, lon = coords_publicas(a)
    nota = (" (aproximada: terreo privado ou árbore fráxil)" if a.get("coords_privadas")
            else " (aproximada: localización do lugar, non da árbore)" if a.get("coords_aproximadas") else "")
    filas.append(("Lugar", a.get("lugar")))
    filas.append(("Localización", f"{lat}, {lon}{nota}"))
    taboa = "".join(f"<tr><th>{e(k)}</th><td>{e(str(v))}</td></tr>" for k, v in filas if v)
    aviso = ""
    if a.get("orixe") == "proposta" and not (a.get("proposta") or {}).get("verificada"):
        aviso = '<p class="aviso">Proposta da comunidade, aínda sen verificar por unha segunda observación independente.</p>'
    texto = "".join(f"<p>{e(f['texto'])}</p>" for f in t.get("frases", []))
    galeria = ""
    if len(fotos) > 1:
        galeria = "<h2>Máis fotos</h2><div class=\"galeria\">" + "".join(foto_html(f) for f in fotos[1:7]) + "</div>"
    arredor = ""
    if proximas:
        arredor = ("<h2>Carballos observados nos arredores</h2><p class=\"meta\">Fotos doutros carballos a menos de 1 km, "
                   "subidas a iNaturalist. Non son necesariamente esta árbore.</p><div class=\"galeria\">"
                   + "".join(foto_html(f) for f in proximas[:6]) + "</div>")
    fontes = "".join(f'<li><a href="{e(f["url"])}">{e(f["nome"])}</a></li>' for f in a.get("fontes", []))
    corpo = f"""
<p class="meta"><a href="/carballos/">Carballos</a> › {e(a.get('concello') or '')}</p>
<h1>{e(a['nome'])}</h1>
<p class="lema">{e(t.get('resumo') or '')}</p>
{aviso}
{foto_html(fotos[0]) if fotos else ''}
{texto}
<h2>Ficha</h2>
<table class="ficha">{taboa}</table>
<p><a class="boton sec" href="/mapa/#{a['slug']}">Ver no mapa</a></p>
{galeria}
{arredor}
<h2>Fontes</h2><ul>{fontes}</ul>
<p class="meta">Texto xerado automaticamente a partir destas fontes e verificado frase a frase. <a href="/como-se-fai/">Como se fai</a>. Última actualización: {e(a.get('actualizado') or '')}.</p>
"""
    return paxina(a["nome"], corpo, t.get("resumo") or "", f"/carballos/{a['slug']}/")


def grafico_fenoloxia(feno: dict) -> str:
    series = [("gromos", "Gromos de flor", "#A9B79A"), ("flor", "En flor", "#3F5A3A"), ("froito", "Con landras", "#B9853F")]
    maximo = max([int(v) for s in feno.get("meses", {}).values() for v in s.values()] or [1]) or 1
    largo, alto, x0, y0 = 720, 260, 40, 220
    ancho_mes = (largo - x0) / 12
    barras = []
    for m in range(1, 13):
        for i, (clave, _, cor) in enumerate(series):
            v = int(feno.get("meses", {}).get(clave, {}).get(str(m), 0))
            h = v / maximo * 180
            x = x0 + (m - 1) * ancho_mes + 6 + i * (ancho_mes - 12) / 3
            barras.append(f'<rect x="{x:.1f}" y="{y0 - h:.1f}" width="{(ancho_mes - 12) / 3 - 2:.1f}" height="{h:.1f}" fill="{cor}"><title>{MESES[m-1]}: {v}</title></rect>')
        barras.append(f'<text x="{x0 + (m - 0.5) * ancho_mes:.1f}" y="{y0 + 20}" text-anchor="middle" font-size="13" fill="currentColor">{MESES[m-1]}</text>')
    lenda = " · ".join(f'<span style="color:{c}">■</span> {e(n)}' for _, n, c in series)
    return (f'<svg class="barras" viewBox="0 0 {largo} {alto}" role="img" aria-label="Observacións de carballos por mes e fase">'
            f'{"".join(barras)}<line x1="{x0}" y1="{y0}" x2="{largo}" y2="{y0}" stroke="currentColor" stroke-opacity=".3"/></svg>'
            f'<p class="meta">{lenda}</p>')


def construe() -> dict:
    if SITE_OUT.exists():
        shutil.rmtree(SITE_OUT)
    shutil.copytree(ROOT / "site" / "static", SITE_OUT / "static")
    arbores = le_arbores()
    publicadas = sorted([a for a in arbores if a.get("estado") == "publicado"], key=lambda a: a.get("publicado_en", ""), reverse=True)
    no_mapa = [a for a in arbores if a.get("estado") in ("publicado", "so_mapa") and a.get("lat") is not None]
    estado = json.loads((DATA / "estado.json").read_text(encoding="utf-8")) if (DATA / "estado.json").exists() else {}
    do_mes = next((a for a in publicadas if a["slug"] == estado.get("carballo_do_mes")), publicadas[0] if publicadas else None)

    # Portada
    mes = ""
    if do_mes:
        mes = f'<h2>O carballo do mes</h2><div class="grella">{tarxeta(do_mes)}</div>'
    ultimas = "".join(tarxeta(a) for a in publicadas[:6])
    escribe("/", paxina("Inicio", f"""
<h1>Os carballos senlleiros de Galicia</h1>
<p class="lema">{e(CONFIG['lema'])}</p>
<p>Un catálogo aberto de carballos singulares: onde están, como son e que lles pasa ao longo do ano. {len(publicadas)} fichas e {len(no_mapa)} árbores no mapa.</p>
<p><a class="boton" href="/mapa/">Abrir o mapa</a> <a class="boton sec" href="/propon/">Propón un carballo</a></p>
{mes}
<h2>Últimas fichas</h2><div class="grella">{ultimas or '<p>As primeiras fichas están en preparación.</p>'}</div>
""", ruta="/"))

    # Listado e fichas
    escribe("/carballos/", paxina("Carballos", "<h1>Carballos</h1><div class=\"grella\">"
                                  + "".join(tarxeta(a) for a in sorted(publicadas, key=lambda a: a["nome"])) + "</div>", ruta="/carballos/"))
    for a in publicadas:
        escribe(f"/carballos/{a['slug']}/", ficha(a))

    # Mapa
    geo = {"type": "FeatureCollection", "features": []}
    for a in no_mapa:
        lat, lon = coords_publicas(a)
        geo["features"].append({"type": "Feature", "geometry": {"type": "Point", "coordinates": [lon, lat]},
                                "properties": {"slug": a["slug"], "nome": a["nome"], "especie": a.get("especie"),
                                               "concello": a.get("concello"), "ficha": a.get("estado") == "publicado"}})
    (SITE_OUT / "datos").mkdir(exist_ok=True)
    (SITE_OUT / "datos" / "arbores.geojson").write_text(json.dumps(geo, ensure_ascii=False), encoding="utf-8")
    leaflet = ('<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">'
               '<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>')
    escribe("/mapa/", paxina("Mapa", """
<h1>Mapa dos carballos</h1>
<div id="mapa" role="region" aria-label="Mapa interactivo"></div>
<p class="meta">As árbores en terreo privado ou fráxiles móstranse cunha localización aproximada.</p>
<script>
const mapa = L.map('mapa').setView([42.8, -8.0], 8);
L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {maxZoom: 18,
  attribution: '&copy; colaboradores de <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'}).addTo(mapa);
fetch('/datos/arbores.geojson').then(r => r.json()).then(geo => {
  const capas = {};
  L.geoJSON(geo, {pointToLayer: (f, ll) => L.circleMarker(ll, {radius: 7, color: '#3F5A3A', fillColor: f.properties.ficha ? '#B9853F' : '#A9B79A', fillOpacity: .9}),
    onEachFeature: (f, capa) => { const p = f.properties; capas[p.slug] = capa;
      const t = document.createElement('div'); const b = document.createElement('strong'); b.textContent = p.nome; t.appendChild(b);
      t.appendChild(document.createElement('br')); t.appendChild(document.createTextNode([p.especie, p.concello].filter(Boolean).join(' · ')));
      if (p.ficha) { const a = document.createElement('a'); a.href = '/carballos/' + p.slug + '/'; a.textContent = ' Ver ficha'; t.appendChild(a); }
      capa.bindPopup(t); }}).addTo(mapa);
  const slug = location.hash.slice(1); if (capas[slug]) { mapa.setView(capas[slug].getLatLng(), 14); capas[slug].openPopup(); }
});
</script>""", ruta="/mapa/", extra_head=leaflet))

    # Fenoloxía
    feno_ruta = DATA / "fenoloxia.json"
    if feno_ruta.exists():
        feno = json.loads(feno_ruta.read_text(encoding="utf-8"))
        escribe("/fenoloxia/", paxina("O ano do carballo", f"""
<h1>O ano do carballo</h1>
<p>Cando abrocha, florece e dá landras o carballo en Galicia, segundo as observacións anotadas en iNaturalist (todos os anos, por mes).</p>
{grafico_fenoloxia(feno)}
<p class="meta">Fonte: <a href="https://www.inaturalist.org/">iNaturalist</a>, observacións de grao investigación do xénero Quercus en Galicia. Actualizado: {e(feno.get('actualizado', ''))}.</p>
""", ruta="/fenoloxia/"))

    # En cifras (GBIF + IFN se existe)
    cifras = ""
    gbif = DATA / "gbif.json"
    if gbif.exists():
        g = json.loads(gbif.read_text(encoding="utf-8"))
        filas = "".join(f"<tr><th>{e(s['especie'] or '')}</th><td>{s['rexistros']}</td></tr>" for s in g["especies"])
        cifras += (f"<h2>Rexistros en GBIF</h2><p>{g['total']} rexistros de Quercus en Galicia con licenza CC0 ou CC BY.</p>"
                   f'<table class="ficha">{filas}</table><p class="meta">Fonte: <a href="{e(g["consulta"])}">{e(g["fonte"])}</a>, {e(g["actualizado"])}.</p>')
    ifn = DATA / "ifn" / "ifn-galicia.json"
    if ifn.exists():
        d = json.loads(ifn.read_text(encoding="utf-8"))
        if d.get("filas"):
            filas = "".join(f"<tr><th>{e(f['nome'])}</th><td>{e(str(f['valor']))} {e(f.get('unidade', ''))}</td></tr>" for f in d["filas"])
            cifras += (f"<h2>Inventario Forestal Nacional</h2><table class=\"ficha\">{filas}</table>"
                       f'<p class="meta">Fonte: <a href="{e(d["fonte_url"])}">{e(d["fonte"])}</a>.</p>')
    if cifras:
        escribe("/en-cifras/", paxina("En cifras", "<h1>Os carballos de Galicia en cifras</h1>" + cifras, ruta="/en-cifras/"))

    # Páxinas fixas
    escribe("/como-se-fai/", paxina("Como se fai esta web", f"""
<h1>Como se fai esta web</h1>
<p>Esta web actualízase soa cada semana. Un programa recolle datos de fontes abertas (o Catálogo galego de árbores senlleiras da Xunta, Wikidata, Wikimedia Commons, iNaturalist, GBIF e o Inventario Forestal Nacional), constrúe as fichas e o mapa, e redacta os textos coa axuda dun modelo de intelixencia artificial (Claude, de Anthropic).</p>
<p>Os textos só poden usar os datos da propia ficha. Despois, unha segunda revisión automática comproba frase a frase que todo o que se di está nos datos; o que non se pode comprobar elimínase. Tamén se revisan os números, a lingua e que os textos non se repitan entre fichas.</p>
<p>Só se usan fotos con licenzas libres (CC0, CC BY e CC BY-SA), sempre co nome do autor e unha ligazón á orixe. Se unha foto desaparece da súa orixe, retírase.</p>
<p>Publícanse como moito {CONFIG['max_paxinas_novas_semana']} fichas novas por semana. Os cambios quedan no <a href="/rexistro/">rexistro público</a>. Se atopas un erro, escríbenos a {e(CONFIG['contacto'])}.</p>
""", ruta="/como-se-fai/"))

    creditos = []
    for a in publicadas:
        for f in a.get("fotos", []):
            creditos.append(f'<li><a href="/carballos/{a["slug"]}/">{e(a["nome"])}</a>: {e(f["autor"])}, '
                            f'<a href="{e(f["orixe"])}">{e(f["licenza"])}</a> ({e(f.get("fonte", ""))})</li>')
    escribe("/creditos/", paxina("Créditos e licenzas", "<h1>Créditos e licenzas</h1><p>Todas as fotos publicadas, co seu autor, licenza e orixe.</p><ul>"
                                 + "".join(creditos) + "</ul>", ruta="/creditos/"))

    rex_ruta = DATA / "rexistro.json"
    rex = json.loads(rex_ruta.read_text(encoding="utf-8")) if rex_ruta.exists() else []
    filas = "".join(f"<tr><th>{e(r['data'])}</th><td>{e(r['texto'])}</td></tr>" for r in reversed(rex[-200:]))
    escribe("/rexistro/", paxina("Rexistro de cambios", f'<h1>Rexistro de cambios</h1><table class="ficha">{filas}</table>', ruta="/rexistro/"))

    escribe("/sobre/", paxina("Aviso legal", f"""
<h1>Sobre o proxecto e aviso legal</h1>
<p>{e(CONFIG['nome'])} é un proxecto cultural e divulgativo sen ánimo de lucro sobre os carballos senlleiros de Galicia. Non ten publicidade nin vende nada.</p>
<p>Responsable: {e(CONFIG['responsable'])}. Contacto: {e(CONFIG['contacto'])}.</p>
<p>Este proxecto non ten relación con ningunha empresa nin marca doutros sectores que poida usar un nome parecido.</p>
<p>Esta web non usa cookies de seguimento.</p>
""", ruta="/sobre/"))

    escribe("/propon/", paxina("Propón un carballo", f"""
<h1>Propón un carballo</h1>
<p>Coñeces un carballo singular que non está no mapa? Cóntanos onde está e envía unha foto túa.</p>
<form method="post" action="{e(CONFIG['n8n_formulario_url'])}" enctype="multipart/form-data">
  <label for="nome">Nome co que se coñece a árbore</label><input id="nome" name="nome" required>
  <label for="especie">Especie, se a sabes</label>
  <select id="especie" name="especie"><option value="">Non sei</option><option>Quercus robur</option><option>Quercus petraea</option><option>Quercus pyrenaica</option><option>Quercus suber</option><option>Quercus ilex</option></select>
  <label for="concello">Concello</label><input id="concello" name="concello" required>
  <label for="lat">Latitude</label><input id="lat" name="lat" inputmode="decimal" required placeholder="42.88">
  <label for="lon">Lonxitude</label><input id="lon" name="lon" inputmode="decimal" required placeholder="-8.54">
  <label for="historia">Que sabes del? (historia, lendas, quen o plantou...)</label><textarea id="historia" name="historia" rows="5"></textarea>
  <label for="foto">Foto feita por ti</label><input id="foto" name="foto" type="file" accept="image/*" required>
  <label for="autor">Nome para o crédito da foto</label><input id="autor" name="autor" required>
  <label class="caixa"><input type="checkbox" name="terreo_privado" value="1"> Está en terreo privado ou é fráxil: mostrade só unha localización aproximada.</label>
  <label class="caixa"><input type="checkbox" name="licenza" value="CC BY-SA 4.0" required> A foto é miña e publícoa baixo licenza CC BY-SA 4.0.</label>
  <p class="trampa" aria-hidden="true"><label for="web">Deixa isto baleiro</label><input id="web" name="web" tabindex="-1" autocomplete="off"></p>
  <p><button class="boton" type="submit">Enviar proposta</button></p>
</form>
<p id="estado-envio" role="status"></p>
<script>
const q = new URLSearchParams(location.search), m = document.getElementById("estado-envio");
if (q.has("grazas")) m.textContent = "Grazas! Recibimos a proposta. Aparecerá no mapa cando pase as comprobacións do ciclo semanal.";
if (q.has("erro")) m.textContent = "Non puidemos recibir a proposta: revisa que as coordenadas estean en Galicia e que engadiches a foto e o teu nome.";
</script>
""", ruta="/propon/"))

    # Sitemap, robots e dominio
    rutas = ["/", "/carballos/", "/mapa/", "/fenoloxia/", "/en-cifras/", "/como-se-fai/", "/creditos/", "/rexistro/", "/sobre/", "/propon/"]
    rutas += [f"/carballos/{a['slug']}/" for a in publicadas]
    (SITE_OUT / "sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
                                          + "".join(f"<url><loc>{URL}{r}</loc><lastmod>{hoxe()}</lastmod></url>" for r in rutas)
                                          + "</urlset>\n", encoding="utf-8")
    (SITE_OUT / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {URL}/sitemap.xml\n", encoding="utf-8")
    (SITE_OUT / "CNAME").write_text(URL.split("//", 1)[1] + "\n", encoding="utf-8")
    return {"paxinas": len(publicadas), "no_mapa": len(no_mapa)}


if __name__ == "__main__":
    print(construe())
