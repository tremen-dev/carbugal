# Carballos Únicos de Galiza

Catálogo aberto e sen ánimo de lucro dos carballos senlleiros de Galiza, en
[carbugal.com](https://carbugal.com). A web actualízase soa cada semana a partir de fontes
abertas, e só se publica o que pasa os controis automáticos.

## Como funciona

```
Fontes ──► Recoller ──► Xerar ──► Controis ──► Publicar (GitHub Pages)
                                     └── non ──► Retido (reinténtase o luns) + aviso a n8n
```

| Peza | Ficheiro |
| --- | --- |
| Fontes: Xunta (CSV), Wikidata, Commons, iNaturalist, GBIF, propostas | `scripts/collect.py` |
| Textos con Claude, cunha segunda chamada que verifica cada frase | `scripts/generate.py` |
| Controis: licenzas, contido mínimo, números, duplicados, lingua | `scripts/qa.py` |
| Web estática | `scripts/build.py`, `site/static/` |
| Ciclo completo | `scripts/weekly.py` |
| Programación | `.github/workflows/semanal.yml` (luns 05:00 UTC) |
| Formulario, DOG, avisos e capturas | `n8n/README.md` |
| Parámetros (tope semanal, mínimos, modelo) | `config.json` |

## Posta en marcha

1. Segredos do repositorio: `ANTHROPIC_API_KEY` e, cando estea o fluxo 3 de n8n, `N8N_WEBHOOK_URL`.
   Desde un equipo con `gh`:
   `gh secret set ANTHROPIC_API_KEY -R tremen-dev/carbugal`
2. Settings › Pages › Source: **GitHub Actions**. Dominio personalizado: `carbugal.com`.
   No DNS de carbugal.com, os rexistros A/AAAA de GitHub Pages; carbugal.es redirixe con 301.
3. Encher `config.json` (`responsable`, `contacto`, `n8n_formulario_url`).
4. Opcional pero recomendado: encher `data/seed/catalogo-xunta.csv` co Anexo I do
   Decreto 67/2007 (redacción do Decreto 10/2015 e resolucións posteriores). Sen el, as
   árbores descóbrense só desde Wikidata e das propostas.
5. Actions › Ciclo semanal › Run workflow, para a primeira execución.

## Analíticas de visitas

Usamos **Cloudflare Web Analytics**: mide visitas agregadas, sen cookies nin identificar a
ninguén (por iso non fai falta banner de consentimento; está dito en `/sobre/`).

- **Onde velas:** dash.cloudflare.com › Analytics & Logs › **Web Analytics** › sitio `carbugal.com`
  (páxinas vistas, visitantes, referrers, países, Core Web Vitals). Non confundir co panel
  *Analytics › Traffic* do dominio: ese só mide tráfico que pasa polo proxy de Cloudflare e aquí
  sempre estará a 0.
- **Como funciona:** un script JS (`beacon.min.js`) inserido en todas as páxinas por
  `scripts/build.py`. O token está en `config.json` › `cloudflare_analytics_token` (non é un
  segredo: vai no HTML público). Se o campo está baleo, non se inclúe o script.
- **DNS:** a zona `carbugal.com` está en Cloudflare (plan Free) cos rexistros de GitHub Pages
  (4 `A`, 4 `AAAA` en `@` e `CNAME www` → `tremen-dev.github.io`), todos en **DNS only**
  (nube gris). Non activar o proxy (nube laranxa) sen revisar antes o certificado HTTPS de
  GitHub Pages. O rexistrador é Dinahosting (só apunta os nameservers a Cloudflare);
  `carbugal.es` segue en Dinahosting e redirixe con 301.
- **Límites:** os bloqueadores de publicidade poden impedir o script, así que as cifras son
  algo inferiores ás reais. Os datos tardan uns minutos en aparecer.
- **Outras estatísticas:** GitHub Pages non ofrece ningunha. *Insights › Traffic* do repositorio
  só conta visitas ao repo (14 días), non á web.

## Probas

```
pip install -r requirements.txt
python -m unittest discover -s tests
python scripts/weekly.py --sen-rede --sen-claude   # constrúe o sitio cos datos actuais
```

## Licenzas

Textos: CC BY-SA 4.0. Fotos: as de cada autor (só CC0, CC BY e CC BY-SA), con
crédito na propia foto e en `/creditos/`.
