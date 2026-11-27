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
LICENZA_URL = {
    "CC0": "https://creativecommons.org/publicdomain/zero/1.0/",
    "Dominio público": "https://creativecommons.org/publicdomain/mark/1.0/",
    "CC BY": "https://creativecommons.org/licenses/by/4.0/",
    "CC BY 2.0": "https://creativecommons.org/licenses/by/2.0/",
    "CC BY 3.0": "https://creativecommons.org/licenses/by/3.0/",
    "CC BY 4.0": "https://creativecommons.org/licenses/by/4.0/",
    "CC BY-SA": "https://creativecommons.org/licenses/by-sa/4.0/",
    "CC BY-SA 2.0": "https://creativecommons.org/licenses/by-sa/2.0/",
    "CC BY-SA 3.0": "https://creativecommons.org/licenses/by-sa/3.0/",
    "CC BY-SA 4.0": "https://creativecommons.org/licenses/by-sa/4.0/",
}


def json_ld_script(datos: dict | list[dict]) -> str:
    bruto = json.dumps(datos, ensure_ascii=False, separators=(",", ":"))
    seguro = bruto.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    return f'<script type="application/ld+json">{seguro}</script>'


def migas_json_ld(elementos: list[tuple[str, str]]) -> dict:
    return {
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": i, "name": nome, "item": url}
            for i, (nome, url) in enumerate(elementos, start=1)
        ],
    }


def paxina(titulo: str, corpo: str, descricion: str = "", ruta: str = "/", extra_head: str = "", *,
           titulo_completo: str | None = None, og_type: str = "website", og_image: str | None = None,
           og_image_alt: str | None = None, json_ld: dict | list[dict] | None = None,
           noindex: bool = False) -> str:
    desc = descricion or CONFIG["lema"]
    tit = titulo_completo or f"{titulo} · {CONFIG['nome']}"
    img_og = og_image or f"{URL}/static/icona-512.png"
    img_og_alt = og_image_alt or CONFIG["nome"]
    tw_card = "summary_large_image" if og_image else "summary"
    robots = '<meta name="robots" content="noindex, follow">\n' if noindex else ""
    canon = f'<link rel="canonical" href="{URL}{ruta}">\n' if ruta else ""
    og_url = f'<meta property="og:url" content="{URL}{ruta}">\n' if ruta else ""
    ld = json_ld_script(json_ld) + "\n" if json_ld is not None else ""
    return f"""<!doctype html>
<html lang="gl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(tit)}</title>
<meta name="description" content="{e(desc)}">
{robots}{canon}<link rel="icon" href="/static/simbolo.svg" type="image/svg+xml">
<link rel="icon" href="/static/favicon-48.png" sizes="48x48" type="image/png">
<link rel="icon" href="/static/icona-192.png" sizes="192x192" type="image/png">
<link rel="apple-touch-icon" href="/static/apple-touch-icon.png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="{FONTES_GOOGLE}">
<link rel="stylesheet" href="/static/estilo.css">
<meta property="og:site_name" content="{e(CONFIG['nome'])}">
<meta property="og:locale" content="gl_ES">
<meta property="og:type" content="{e(og_type)}">
<meta property="og:title" content="{e(tit)}">
<meta property="og:description" content="{e(desc)}">
{og_url}<meta property="og:image" content="{e(img_og)}">
<meta property="og:image:alt" content="{e(img_og_alt)}">
<meta name="twitter:card" content="{tw_card}">
<meta name="twitter:title" content="{e(tit)}">
<meta name="twitter:description" content="{e(desc)}">
<meta name="twitter:image" content="{e(img_og)}">
{ld}{extra_head}
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
  <p class="pe-tremen">Un proxecto de <a class="tremen" href="https://tremen.dev" target="_blank" rel="noopener noreferrer"><svg class="br" viewBox="7 9 18 46" width="7" height="18" aria-hidden="true"><path d="M22 12 C16 12 14 16 14 22 L14 28 C14 30 13 32 10 32 C13 32 14 34 14 36 L14 42 C14 48 16 52 22 52" fill="none" stroke="currentColor" stroke-width="5" stroke-linecap="square" stroke-linejoin="miter"/></svg><span>tremen<span class="dev">.dev</span></span><svg class="br" viewBox="39 9 18 46" width="7" height="18" aria-hidden="true"><path d="M42 12 C48 12 50 16 50 22 L50 28 C50 30 51 32 54 32 C51 32 50 34 50 36 L50 42 C50 48 48 52 42 52" fill="none" stroke="currentColor" stroke-width="5" stroke-linecap="square" stroke-linejoin="miter"/></svg></a></p>
</div></footer>
</body>
</html>
"""


def escribe(ruta: str, html: str) -> None:
    destino = SITE_OUT / ruta.strip("/") if ruta.endswith((".xml", ".html")) else SITE_OUT / ruta.strip("/") / "index.html"
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(html, encoding="utf-8")


def coords_publicas(a: dict) -> tuple[float, float]:
    if a.get("coords_privadas") or a.get("coords_aproximadas"):
        paso = CONFIG["arredondar_coords_paso"]
        return round(round(a["lat"] / paso) * paso, 4), round(round(a["lon"] / paso) * paso, 4)
    return round(a["lat"], 5), round(a["lon"], 5)


def foto_html(f: dict, alt: str = "", clase: str = "", principal: bool = False) -> str:
    pe = f"Foto: {e(f['autor'])}, <a href=\"{e(f['orixe'])}\">{e(f['licenza'])}</a> ({e(f.get('fonte', ''))})"
    atributos = 'fetchpriority="high" decoding="async"' if principal else 'loading="lazy" decoding="async"'
    return (f'<figure class="{clase}"><img src="{e(f["url"])}" alt="{e(alt)}" {atributos}>'
            f"<figcaption>{pe}</figcaption></figure>")


def propias(a: dict) -> list[dict]:
    return [f for f in a.get("fotos", []) if not f.get("proxima")]


def tarxeta(a: dict, prioritaria: bool = False) -> str:
    f = (propias(a) or [{}])[0]
    alt = f"{a['nome']} en {a['concello']}" if a.get("concello") else a["nome"]
    atributos = 'fetchpriority="high" decoding="async"' if prioritaria else 'loading="lazy" decoding="async"'
    img = f'<img src="{e(f["url"])}" alt="{e(alt)}" {atributos}>' if f.get("url") else ""
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

    partes_alt = [a["nome"]]
    if a.get("especie"):
        partes_alt[0] += f" ({a['especie']})"
    if a.get("concello"):
        partes_alt.append(f"en {a['concello']}")
    alt_principal = " ".join(partes_alt)

    galeria = ""
    if len(fotos) > 1:
        imgs_gal = "".join(
            foto_html(f, alt=f"{a['nome']} en {a['concello']}, vista {i}" if a.get("concello") else f"{a['nome']}, vista {i}")
            for i, f in enumerate(fotos[1:7], start=2)
        )
        galeria = f'<h2>Máis fotos</h2><div class="galeria">{imgs_gal}</div>'
    arredor = ""
    if proximas:
        alt_prox = (f"Carballo observado nos arredores de {a['nome']} en {a['concello']}"
                    if a.get("concello") else f"Carballo observado nos arredores de {a['nome']}")
        arredor = ("<h2>Carballos observados nos arredores</h2><p class=\"meta\">Fotos doutros carballos a menos de 1 km, "
                   "subidas a iNaturalist. Non son necesariamente esta árbore.</p><div class=\"galeria\">"
                   + "".join(foto_html(f, alt=alt_prox) for f in proximas[:6]) + "</div>")
    fontes = "".join(f'<li><a href="{e(f["url"])}">{e(f["nome"])}</a></li>' for f in a.get("fontes", []))
    corpo = f"""
<nav class="meta" aria-label="Migas de pan"><a href="/">Inicio</a> › <a href="/carballos/">Carballos</a> › {e(a.get('concello') or a['nome'])}</nav>
<h1>{e(a['nome'])}</h1>
<p class="lema">{e(t.get('resumo') or '')}</p>
{aviso}
{foto_html(fotos[0], alt=alt_principal, principal=True) if fotos else ''}
{texto}
<h2>Ficha</h2>
<table class="ficha">{taboa}</table>
<p><a class="boton sec" href="/mapa/#{a['slug']}">Ver no mapa</a></p>
{galeria}
{arredor}
<h2>Fontes</h2><ul>{fontes}</ul>
<p class="meta">Texto xerado automaticamente a partir destas fontes e verificado frase a frase. <a href="/como-se-fai/">Como se fai</a>. Última actualización: {e(a.get('actualizado') or '')}.</p>
"""
    ruta = f"/carballos/{a['slug']}/"
    url_ficha = f"{URL}{ruta}"
    titulo = f"{a['nome']} ({a['concello']})" if a.get("concello") and len(a["nome"]) + len(a["concello"]) <= 42 else a["nome"]
    desc = t.get("resumo") or f"{a['nome']}, exemplar de {a.get('especie') or 'Quercus'} en {a.get('concello') or 'Galiza'}."
    enderezo = {k: v for k, v in (
        ("addressLocality", a.get("concello")),
        ("addressRegion", a.get("provincia")),
        ("addressCountry", "ES"),
    ) if v}
    imaxes_ld = []
    for f in fotos:
        obj = {"@type": "ImageObject", "contentUrl": f["url"], "creditText": f["autor"], "acquireLicensePage": f["orixe"]}
        if f.get("licenza") in LICENZA_URL:
            obj["license"] = LICENZA_URL[f["licenza"]]
        imaxes_ld.append(obj)
    lugar_ld = {
        "@type": "Place",
        "@id": f"{url_ficha}#arbore",
        "name": a["nome"],
        "description": desc,
        "url": url_ficha,
        "geo": {"@type": "GeoCoordinates", "latitude": lat, "longitude": lon},
        "address": {"@type": "PostalAddress", **enderezo},
    }
    if imaxes_ld:
        lugar_ld["image"] = imaxes_ld
    if a.get("wikidata"):
        lugar_ld["sameAs"] = f"https://www.wikidata.org/wiki/{a['wikidata']}"
    pax_ld = {
        "@type": "WebPage",
        "url": url_ficha,
        "name": titulo,
        "description": desc,
        "inLanguage": "gl",
        "license": "https://creativecommons.org/licenses/by-sa/4.0/",
        "mainEntity": {"@id": f"{url_ficha}#arbore"},
    }
    if a.get("publicado_en"):
        pax_ld["datePublished"] = a["publicado_en"]
    mod = a.get("actualizado") or a.get("publicado_en")
    if mod:
        pax_ld["dateModified"] = mod
    ld = {
        "@context": "https://schema.org",
        "@graph": [
            migas_json_ld([("Inicio", f"{URL}/"), ("Carballos", f"{URL}/carballos/"), (a["nome"], url_ficha)]),
            lugar_ld,
            pax_ld,
        ],
    }
    return paxina(
        titulo, corpo, desc, ruta,
        og_type="article",
        og_image=fotos[0]["url"] if fotos else None,
        og_image_alt=alt_principal if fotos else None,
        json_ld=ld,
    )


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
    ultima_pub = max((d for d in (a.get("actualizado") or a.get("publicado_en") for a in publicadas) if d), default=None)
    ultima_mapa = max((d for d in (a.get("actualizado") or a.get("publicado_en") for a in no_mapa) if d), default=None)

    # Portada
    mes = ""
    if do_mes:
        mes = f'<h2>O carballo do mes</h2><div class="grella">{tarxeta(do_mes, prioritaria=True)}</div>'
    ultimas = "".join(tarxeta(a, prioritaria=(not do_mes and i == 0)) for i, a in enumerate(publicadas[:6]))
    foto_mes = (propias(do_mes) or [{}])[0] if do_mes else {}
    og_img_portada = foto_mes.get("url")
    og_alt_portada = (
        (f"{do_mes['nome']} en {do_mes['concello']}" if do_mes.get("concello") else do_mes["nome"])
        if og_img_portada and do_mes else None
    )
    desc_portada = (
        f"Catálogo aberto e mapa de carballos e árbores senlleiras de Galiza: localización, medidas, "
        f"fotos con licenza libre e fenoloxía. {len(publicadas)} fichas e {len(no_mapa)} árbores."
    )
    ld_portada = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "WebSite",
                "@id": f"{URL}/#sitio",
                "url": f"{URL}/",
                "name": CONFIG["nome"],
                "alternateName": CONFIG["nome_curto"],
                "description": desc_portada,
                "inLanguage": "gl",
                "publisher": {"@id": f"{URL}/#organizacion"},
            },
            {
                "@type": "Organization",
                "@id": f"{URL}/#organizacion",
                "name": CONFIG["nome"],
                "url": f"{URL}/",
                "logo": f"{URL}/static/icona-512.png",
                "email": CONFIG["contacto"],
            },
        ],
    }
    escribe("/", paxina(
        "Inicio",
        f"""
<h1>Os carballos senlleiros de Galiza</h1>
<p class="lema">{e(CONFIG['lema'])}</p>
<p>Un catálogo aberto de carballos singulares: onde están, como son e que lles pasa ao longo do ano. {len(publicadas)} fichas e {len(no_mapa)} árbores no mapa.</p>
<p><a class="boton" href="/mapa/">Abrir o mapa</a> <a class="boton sec" href="/propon/">Propón un carballo</a></p>
{mes}
<h2>Últimas fichas</h2><div class="grella">{ultimas or '<p>As primeiras fichas están en preparación.</p>'}</div>
""",
        descricion=desc_portada,
        ruta="/",
        titulo_completo=f"{CONFIG['nome']} · Catálogo e mapa de árbores senlleiras",
        og_image=og_img_portada,
        og_image_alt=og_alt_portada,
        json_ld=ld_portada,
    ))

    # Listado e fichas
    ordenadas = sorted(publicadas, key=lambda a: a["nome"])
    desc_cat = (f"Explora as {len(publicadas)} fichas verificadas de carballos, sobreiras e aciñeiras senlleiras "
                f"de Galiza, con datos oficiais, localización e fotografía libre.")
    foto_cat = ((propias(ordenadas[0]) or [{}])[0]).get("url") if ordenadas else None
    ld_cat = {
        "@context": "https://schema.org",
        "@graph": [
            migas_json_ld([("Inicio", f"{URL}/"), ("Carballos", f"{URL}/carballos/")]),
            {
                "@type": "CollectionPage",
                "url": f"{URL}/carballos/",
                "name": "Catálogo de carballos senlleiros",
                "description": desc_cat,
                "inLanguage": "gl",
                "mainEntity": {
                    "@type": "ItemList",
                    "numberOfItems": len(ordenadas),
                    "itemListElement": [
                        {"@type": "ListItem", "position": i, "name": a["nome"], "url": f"{URL}/carballos/{a['slug']}/"}
                        for i, a in enumerate(ordenadas, start=1)
                    ],
                },
            },
        ],
    }
    escribe("/carballos/", paxina(
        "Catálogo de carballos senlleiros",
        "<h1>Carballos</h1><div class=\"grella\">"
        + "".join(tarxeta(a, prioritaria=i < 2) for i, a in enumerate(ordenadas)) + "</div>",
        descricion=desc_cat,
        ruta="/carballos/",
        og_image=foto_cat,
        json_ld=ld_cat,
    ))
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
               '<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js" defer></script>')
    desc_mapa = (f"Mapa interactivo con {len(no_mapa)} carballos e árbores senlleiras de Galiza: "
                 f"localización xeográfica, especie, concello e acceso ás fichas completas.")
    ld_mapa = {
        "@context": "https://schema.org",
        "@graph": [
            migas_json_ld([("Inicio", f"{URL}/"), ("Mapa", f"{URL}/mapa/")]),
            {
                "@type": "Dataset",
                "name": "Mapa e datos xeográficos dos carballos senlleiros de Galiza",
                "description": desc_mapa,
                "url": f"{URL}/mapa/",
                "license": "https://creativecommons.org/licenses/by-sa/4.0/",
                "spatialCoverage": "Galiza, España",
                "distribution": {
                    "@type": "DataDownload",
                    "contentUrl": f"{URL}/datos/arbores.geojson",
                    "encodingFormat": "application/geo+json",
                },
            },
        ],
    }
    escribe("/mapa/", paxina("Mapa dos carballos senlleiros", """
<h1>Mapa dos carballos</h1>
<div id="mapa" role="region" aria-label="Mapa interactivo"></div>
<p class="meta">As árbores en terreo privado ou fráxiles móstranse cunha localización aproximada.</p>
<script>
window.addEventListener('DOMContentLoaded', () => {
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
});
</script>""", descricion=desc_mapa, ruta="/mapa/", extra_head=leaflet, json_ld=ld_mapa))

    # Fenoloxía
    feno_ruta = DATA / "fenoloxia.json"
    feno_data = None
    if feno_ruta.exists():
        feno = json.loads(feno_ruta.read_text(encoding="utf-8"))
        feno_data = feno.get("actualizado") or None
        escribe("/fenoloxia/", paxina(
            "O ano do carballo en Galiza",
            f"""
<h1>O ano do carballo</h1>
<p>Cando abrocha, florece e dá landras o carballo en Galiza, segundo as observacións anotadas en iNaturalist (todos os anos, por mes).</p>
{grafico_fenoloxia(feno)}
<p class="meta">Fonte: <a href="https://www.inaturalist.org/">iNaturalist</a>, observacións de grao investigación do xénero Quercus en Galiza. Actualizado: {e(feno.get('actualizado', ''))}.</p>
""",
            descricion="Cando abrocha, florece e dá landras o carballo en Galiza: gráfico mensual de fenoloxía do xénero Quercus a partir de observacións de iNaturalist.",
            ruta="/fenoloxia/",
            json_ld={"@context": "https://schema.org", **migas_json_ld([("Inicio", f"{URL}/"), ("O ano do carballo en Galiza", f"{URL}/fenoloxia/")])},
        ))

    # En cifras (GBIF + IFN se existe)
    cifras = ""
    gbif_data = None
    gbif = DATA / "gbif.json"
    if gbif.exists():
        g = json.loads(gbif.read_text(encoding="utf-8"))
        gbif_data = g.get("actualizado") or None
        filas = "".join(f"<tr><th>{e(s['especie'] or '')}</th><td>{s['rexistros']}</td></tr>" for s in g["especies"])
        cifras += (f"<h2>Rexistros en GBIF</h2><p>{g['total']} rexistros de Quercus en Galiza con licenza CC0 ou CC BY.</p>"
                   f'<table class="ficha">{filas}</table><p class="meta">Fonte: <a href="{e(g["consulta"])}">{e(g["fonte"])}</a>, {e(g["actualizado"])}.</p>')
    ifn = DATA / "ifn" / "ifn-galicia.json"
    if ifn.exists():
        d = json.loads(ifn.read_text(encoding="utf-8"))
        if d.get("filas"):
            filas = "".join(f"<tr><th>{e(f['nome'])}</th><td>{e(str(f['valor']))} {e(f.get('unidade', ''))}</td></tr>" for f in d["filas"])
            cifras += (f"<h2>Inventario Forestal Nacional</h2><table class=\"ficha\">{filas}</table>"
                       f'<p class="meta">Fonte: <a href="{e(d["fonte_url"])}">{e(d["fonte"])}</a>.</p>')
    if cifras:
        desc_cifras = "Datos abertos sobre os carballos (xénero Quercus) en Galiza: rexistros de biodiversidade en GBIF e cifras do Inventario Forestal Nacional."
        ld_cifras = {
            "@context": "https://schema.org",
            "@graph": [
                migas_json_ld([("Inicio", f"{URL}/"), ("En cifras", f"{URL}/en-cifras/")]),
                {"@type": "Dataset", "name": "Os carballos de Galiza en cifras", "description": desc_cifras,
                 "url": f"{URL}/en-cifras/", "spatialCoverage": "Galiza, España"},
            ],
        }
        escribe("/en-cifras/", paxina(
            "Os carballos de Galiza en cifras",
            "<h1>Os carballos de Galiza en cifras</h1>" + cifras,
            descricion=desc_cifras,
            ruta="/en-cifras/",
            json_ld=ld_cifras,
        ))

    # Páxinas fixas
    escribe("/como-se-fai/", paxina(
        "Como se fai esta web",
        f"""
<h1>Como se fai esta web</h1>
<p>Esta web actualízase soa cada semana. Un programa recolle datos de fontes abertas (o Catálogo galego de árbores senlleiras da Xunta, Wikidata, Wikimedia Commons, iNaturalist, GBIF e o Inventario Forestal Nacional), constrúe as fichas e o mapa, e redacta os textos coa axuda dun modelo de intelixencia artificial (Claude, de Anthropic).</p>
<p>Os textos só poden usar os datos da propia ficha. Despois, unha segunda revisión automática comproba frase a frase que todo o que se di está nos datos; o que non se pode comprobar elimínase. Tamén se revisan os números, a lingua e que os textos non se repitan entre fichas.</p>
<p>Só se usan fotos con licenzas libres (CC0, CC BY e CC BY-SA), sempre co nome do autor e unha ligazón á orixe. Se unha foto desaparece da súa orixe, retírase.</p>
<p>Publícanse como moito {CONFIG['max_paxinas_novas_semana']} fichas novas por semana. Os cambios quedan no <a href="/rexistro/">rexistro público</a>. Se atopas un erro, escríbenos a {e(CONFIG['contacto'])}.</p>
""",
        descricion="Como funciona Carballos Únicos de Galiza: fontes abertas, actualización semanal automatizada, verificación frase a frase e licenzas libres.",
        ruta="/como-se-fai/",
        json_ld={"@context": "https://schema.org", **migas_json_ld([("Inicio", f"{URL}/"), ("Como se fai esta web", f"{URL}/como-se-fai/")])},
    ))

    creditos = []
    for a in publicadas:
        for f in a.get("fotos", []):
            creditos.append(f'<li><a href="/carballos/{a["slug"]}/">{e(a["nome"])}</a>: {e(f["autor"])}, '
                            f'<a href="{e(f["orixe"])}">{e(f["licenza"])}</a> ({e(f.get("fonte", ""))})</li>')
    escribe("/creditos/", paxina(
        "Créditos e licenzas",
        "<h1>Créditos e licenzas</h1><p>Todas as fotos publicadas, co seu autor, licenza e orixe.</p><ul>"
        + "".join(creditos) + "</ul>",
        descricion="Créditos, autoría e licenzas libres (CC0, CC BY, CC BY-SA) de todas as fotografías e fontes de datos publicadas en Carballos Únicos de Galiza.",
        ruta="/creditos/",
        json_ld={"@context": "https://schema.org", **migas_json_ld([("Inicio", f"{URL}/"), ("Créditos e licenzas", f"{URL}/creditos/")])},
    ))

    rex_ruta = DATA / "rexistro.json"
    rex = json.loads(rex_ruta.read_text(encoding="utf-8")) if rex_ruta.exists() else []
    ultima_rex = rex[-1]["data"] if rex else None
    filas = "".join(f"<tr><th>{e(r['data'])}</th><td>{e(r['texto'])}</td></tr>" for r in reversed(rex[-200:]))
    escribe("/rexistro/", paxina(
        "Rexistro de cambios",
        f'<h1>Rexistro de cambios</h1><table class="ficha">{filas}</table>',
        descricion="Rexistro público de cambios semanais de Carballos Únicos de Galiza: novas fichas publicadas, actualizacións de datos e carballo do mes.",
        ruta="/rexistro/",
        json_ld={"@context": "https://schema.org", **migas_json_ld([("Inicio", f"{URL}/"), ("Rexistro de cambios", f"{URL}/rexistro/")])},
    ))

    escribe("/sobre/", paxina(
        "Sobre o proxecto e aviso legal",
        f"""
<h1>Sobre o proxecto e aviso legal</h1>
<p>{e(CONFIG['nome'])} é un proxecto cultural e divulgativo sen ánimo de lucro sobre os carballos senlleiros de Galiza. Non ten publicidade nin vende nada.</p>
<p>Responsable: {e(CONFIG['responsable'])}. Contacto: {e(CONFIG['contacto'])}.</p>
<p>Este proxecto non ten relación con ningunha empresa nin marca doutros sectores que poida usar un nome parecido.</p>
<p>Esta web non usa cookies de seguimento.</p>
""",
        descricion="Sobre Carballos Únicos de Galiza e aviso legal: proxecto cultural e divulgativo sen ánimo de lucro, sen publicidade e sen cookies de seguimento.",
        ruta="/sobre/",
        json_ld={"@context": "https://schema.org", **migas_json_ld([("Inicio", f"{URL}/"), ("Sobre o proxecto e aviso legal", f"{URL}/sobre/")])},
    ))

    escribe("/propon/", paxina(
        "Propón un carballo",
        f"""
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
if (q.has("erro")) m.textContent = "Non puidemos recibir a proposta: revisa que as coordenadas estean en Galiza e que engadiches a foto e o teu nome.";
</script>
""",
        descricion="Propón un carballo singular de Galiza para o catálogo e o mapa: envía a localización, a historia que coñeces e unha fotografía con licenza libre.",
        ruta="/propon/",
        json_ld={"@context": "https://schema.org", **migas_json_ld([("Inicio", f"{URL}/"), ("Propón un carballo", f"{URL}/propon/")])},
    ))

    # Páxina 404
    escribe("404.html", paxina(
        "Páxina non atopada",
        """
<h1>Páxina non atopada</h1>
<p>A páxina que buscas non existe ou mudou de enderezo.</p>
<p><a class="boton" href="/">Volver ao inicio</a> <a class="boton sec" href="/carballos/">Ver o catálogo</a> <a class="boton sec" href="/mapa/">Abrir o mapa</a></p>
""",
        descricion="A páxina que buscas non existe en Carballos Únicos de Galiza. Accede ao catálogo de carballos ou ao mapa interactivo.",
        ruta="",
        noindex=True,
    ))

    # Sitemap, robots e dominio
    entradas: list[tuple[str, str | None]] = [
        ("/", ultima_pub),
        ("/carballos/", ultima_pub),
        ("/mapa/", ultima_mapa),
    ]
    if feno_ruta.exists():
        entradas.append(("/fenoloxia/", feno_data))
    if cifras:
        entradas.append(("/en-cifras/", gbif_data))
    entradas += [
        ("/como-se-fai/", None),
        ("/creditos/", ultima_pub),
        ("/rexistro/", ultima_rex),
        ("/sobre/", None),
        ("/propon/", None),
    ]
    entradas += [(f"/carballos/{a['slug']}/", a.get("actualizado") or a.get("publicado_en") or None) for a in publicadas]
    urls_xml = "".join(
        f"<url><loc>{URL}{r}</loc>{f'<lastmod>{e(lm)}</lastmod>' if lm else ''}</url>"
        for r, lm in entradas
    )
    (SITE_OUT / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        + urls_xml + "</urlset>\n",
        encoding="utf-8",
    )
    (SITE_OUT / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {URL}/sitemap.xml\n", encoding="utf-8")
    (SITE_OUT / "CNAME").write_text(URL.split("//", 1)[1] + "\n", encoding="utf-8")
    return {"paxinas": len(publicadas), "no_mapa": len(no_mapa)}


if __name__ == "__main__":
    print(construe())
