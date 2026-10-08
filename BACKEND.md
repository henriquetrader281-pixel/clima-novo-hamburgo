# Backend do Clima Novo Hamburgo

Implementação em **Vercel Functions (Node 20)**, compatível com o site estático/GitHub Pages.

## Endpoints

| Endpoint | Uso |
|---|---|
| `GET /api/config` | Expõe somente a chave pública VAPID e as URLs de inscrição. |
| `POST /api/push/subscribe` | Valida e armazena um `PushSubscription` no Redis/Upstash. |
| `DELETE /api/push/subscribe` | Remove uma inscrição. |
| `GET /api/river` | Consulta o feed Nível Guaíba e normaliza Taquara, Campo Bom e São Leopoldo. |
| `GET /api/weather?lat=-29.6783&lon=-51.1308` | Proxy autenticado para WeatherKit; credenciais Apple ficam no servidor. |
| `GET /api/cron/river` | Consulta o rio, detecta transições de cota e envia Web Push. Protegido por `CRON_SECRET`. |

## Configuração

1. Crie um projeto Vercel apontando para este repositório.
2. Crie um Redis REST (Upstash ou Vercel KV compatível) e informe `KV_REST_API_URL` e `KV_REST_API_TOKEN`.
3. Gere as chaves VAPID com `npx web-push generate-vapid-keys`. Configure `VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY` e `VAPID_SUBJECT`.
4. Configure um `CRON_SECRET` forte. A Vercel envia `Authorization: Bearer <CRON_SECRET>` ao cron.
5. Para WeatherKit, crie uma chave WeatherKit na Apple Developer e configure `WEATHERKIT_TEAM_ID`, `WEATHERKIT_KEY_ID`, `WEATHERKIT_SERVICE_ID` e `WEATHERKIT_PRIVATE_KEY`. A chave `.p8` deve ficar apenas nas variáveis secretas da Vercel.
6. Configure `FRONTEND_ORIGIN` com a origem do PWA (por exemplo `https://henriquetrader281-pixel.github.io`) em produção. Em desenvolvimento, deixe ausente para permitir `*`.

O `vercel.json` agenda o cron a cada 5 minutos. Verifique o limite do plano Vercel escolhido antes de publicar: em planos com frequência mínima maior, use um cron externo protegido chamando o mesmo endpoint.

## Desenvolvimento local

```bash
npm install
vercel dev
```

O frontend procura `window.CLIMA_API_BASE`; para GitHub Pages, defina-o antes do carregamento em uma configuração de deploy ou altere a constante indicada no `index.html` para a URL do projeto Vercel. Em uma publicação conjunta na Vercel, a API relativa `/api` é usada automaticamente.

## Regras de alerta

- São Leopoldo: atenção a partir de `3,50 m`, inundação a partir de `4,50 m`.
- Campo Bom: inundação a partir de `7,20 m`.
- O envio ocorre somente na transição de normalidade para atenção/inundação.
- Assinaturas que retornam HTTP 404/410 são removidas automaticamente.
- O navegador fechado é suportado pelo Service Worker e pelo cron do backend; a permissão Push precisa ser concedida previamente.
