# Fluxos de n8n

O ciclo semanal corre en GitHub Actions. O servidor de n8n encárgase das pezas que precisan
estar sempre acesas. Son catro fluxos pequenos; aquí está cada un nodo a nodo para montalos
no editor de n8n.

## Importar

Os catro fluxos están listos en `n8n/fluxos/`. En n8n: *Workflows › Import from File*, un por
ficheiro. Despois de importar cada un:

1. Abre os nodos de GitHub e escolle a credencial **GitHub carbugal** (tipo *Header Auth*,
   nome `Authorization`, valor `Bearer <token>`). Créala unha vez e vale para todos.
2. Abre os nodos de correo e escolle a credencial **SMTP avisos**; cambia `[REMITENTE]` e
   `[O TEU CORREO]`.
3. Activa o fluxo. Nos fluxos 1 e 3 copia a *Production URL* do webhook:
   - fluxo 1 → `config.json` › `n8n_formulario_url`
   - fluxo 3 → segredo `N8N_WEBHOOK_URL` do repositorio
     (`gh secret set N8N_WEBHOOK_URL -R tremen-dev/carbugal`).

O fluxo 2 vixía a páxina do catálogo na web de Medio Ambiente da Xunta: a primeira execución
só garda as ligazóns que xa hai; a partir de aí avisa das novas.

A descrición nodo a nodo segue embaixo como referencia.

Credenciais que precisa n8n:

- **GitHub**: un token de grano fino só para `tremen-dev/carbugal`, con permisos
  *Contents: read and write*, *Issues: read and write* e *Actions: read and write*.
- **Correo** (SMTP ou Gmail) para os avisos.

Segredos que precisa o repositorio (Settings › Secrets and variables › Actions):

- `DEEPSEEK_API_KEY`: a clave da API de DeepSeek.
- `N8N_WEBHOOK_URL`: a URL do webhook do fluxo 3.

## 1. Propostas da web

Recibe o formulario «Propón un carballo» e convérteo nunha issue que o ciclo semanal le.

1. **Webhook** (POST, `multipart/form-data`, binary property `foto`). Copia a súa URL de
   produción en `config.json` › `n8n_formulario_url`.
2. **IF**: descarta o envío se falta `nome`, `lat`, `lon`, `autor`, a foto ou a caixa de licenza,
   ou se as coordenadas caen fóra de lat 41.80 a 43.80 e lon -9.35 a -6.70.
3. **Code**: crea un nome de ficheiro `data/propostas/fotos/AAAA-MM-DD-<slug>.jpg` e pasa a
   foto a base64.
4. **GitHub › Create file**: sube a foto a esa ruta, rama `main`, mensaxe «Foto de proposta».
5. **GitHub › Create issue**: título `Proposta: <nome>`, etiqueta `proposta`, e no corpo un
   bloque de código json:

   ```json
   {"nome": "...", "especie": "...", "concello": "...", "lat": 42.9, "lon": -8.1,
    "historia": "...", "autor": "...", "licenza": "CC BY-SA 4.0",
    "terreo_privado": false,
    "foto_url": "https://raw.githubusercontent.com/tremen-dev/carbugal/main/data/propostas/fotos/..."}
   ```

   Non gardes o correo de quen envía a proposta na issue: as issues son públicas.
6. **Respond to Webhook**: redirixe a `https://carbugal.com/propon/?grazas=1`.
7. Opcional: **HTTP Request** POST a
   `https://api.github.com/repos/tremen-dev/carbugal/dispatches` co corpo
   `{"event_type": "proposta"}` para non agardar ao luns.

## 2. Vixilancia do DOG

Detecta novas inclusións no Catálogo galego de árbores senlleiras.

1. **Schedule**: cada día ás 08:00.
2. **HTTP Request**: busca no DOG as publicacións do día co texto «árbores senlleiras».
3. **IF**: hai algunha publicación nova (compara co último identificador gardado en
   *Static Data* do fluxo).
4. **Send Email**: avisa coa ligazón. As novas árbores hai que engadilas a
   `data/seed/catalogo-xunta.csv`. Este é o único paso que segue sendo manual, unha ou dúas
   veces ao ano.
5. **HTTP Request** a `/dispatches` con `{"event_type": "dog-novidade"}`.

## 3. Resultado de cada ciclo

O último paso do ciclo semanal envía aquí un JSON con `resultado` (`success` ou `failure`),
`execucion` (ligazón á execución) e `informe` (fichas publicadas, retidas e erros).

1. **Webhook** (POST, JSON).
2. **Code**: garda en *Static Data* o número de fallos seguidos (poño a 0 se `resultado` é
   `success`).
3. **IF fallos seguidos ≥ 2**: **HTTP Request** PUT
   `https://api.github.com/repos/tremen-dev/carbugal/actions/workflows/semanal.yml/disable`
   e envía un correo: «O ciclo parou tras dous fallos seguidos». A web segue publicada coa
   última versión boa. Para retomalo, actívase de novo en GitHub › Actions.
4. **Send Email** unha vez ao mes (o primeiro luns) cun resumo: fichas publicadas, retidas
   e os seus motivos, e fontes que fallaron. Lelo leva uns 10 minutos e é opcional.

## 4. Capturas e vixilancia da web

1. **Schedule**: o día 1 de cada mes.
2. **HTTP Request** GET `https://web.archive.org/save/https://carbugal.com/` e o mesmo para
   `/carballos/`, `/mapa/` e `/como-se-fai/`. Esas capturas son probas datadas de uso
   continuado.
3. **Schedule** cada hora + **HTTP Request** HEAD a `https://carbugal.com/`: se falla tres
   veces seguidas, envía un correo.
