# Inventario Forestal Nacional (IFN)

O IFN non ten unha API: os datos de Galicia publícanse como táboas e bases de datos descargables en MITECO.
Para activar a páxina «En cifras» coas cifras do IFN, crea `ifn-galicia.json` con este formato
(copiando os valores das táboas oficiais, nunca estimándoos):

```json
{
  "fonte": "Inventario Forestal Nacional (IFN4), Galicia. MITECO",
  "fonte_url": "https://www.miteco.gob.es/es/biodiversidad/temas/inventarios-nacionales/inventario-forestal-nacional.html",
  "filas": [
    {"nome": "Superficie de carballeiras (Quercus robur)", "valor": 0, "unidade": "ha"}
  ]
}
```

Comprobar as condicións de reutilización de MITECO antes de publicar.
