# PWA, WeatherKit e Web Push

O projeto agora inclui um backend Vercel Functions em `api/`.

## Integração implementada

- `GET /api/config` publica somente a chave pública VAPID.
- `POST /api/push/subscribe` armazena `PushSubscription` em Redis REST.
- `DELETE /api/push/subscribe` remove a assinatura.
- `GET /api/river` consulta o feed público e normaliza as estações próximas.
- `GET /api/weather?lat=...&lon=...` consulta o **Apple WeatherKit** no servidor e normaliza os dados para o mesmo layout do painel.
- `GET /api/cron/river` roda a cada cinco minutos, compara as cotas e envia Web Push quando há transição de status.
- Assinaturas expiradas (HTTP 404/410) são removidas automaticamente.

O `index.html` mantém o layout existente, mas consulta `/api/weather` para temperatura, sensação, umidade, pressão, vento, chuva e previsão horária/diária. As credenciais Apple e a chave VAPID privada não são enviadas ao navegador.

## Configuração

Consulte [`BACKEND.md`](BACKEND.md) para as variáveis Vercel, Redis/Upstash, credenciais WeatherKit e cron.

Para GitHub Pages, defina `window.CLIMA_API_BASE` com a URL da API Vercel antes do script principal. Em um deploy conjunto na Vercel, a URL relativa `/api` funciona sem configuração adicional.

## Regras de cota

- São Leopoldo ≥ 3,50 m: atenção.
- São Leopoldo ≥ 4,50 m: inundação.
- Campo Bom ≥ 7,20 m: inundação.
- O envio ocorre apenas na transição para atenção/inundação.

## Requisitos do navegador

O Service Worker e as APIs Push exigem HTTPS, exceto em `localhost`. No iPhone/iPad, o usuário deve adicionar o site à Tela de Início antes de conceder notificações push. Com a permissão concedida, o Service Worker pode exibir alertas mesmo com o navegador fechado.
