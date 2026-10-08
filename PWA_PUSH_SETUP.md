# PWA, WeatherKit e Web Push

## O que já está no projeto

- `manifest.webmanifest` com nome, ícone, escopo e modo standalone.
- `service-worker.js` com cache básico, tratamento de `push` e clique na notificação.
- Registro automático do Service Worker no `index.html`.
- Ícones do PWA em `icons/`.
- Botão de alertas preparado para criar `PushSubscription` quando as configurações do backend forem preenchidas.
- Fallback atual para notificações locais enquanto o backend não estiver configurado.

## O que ainda falta para alertas com o site fechado

O frontend não deve conter a chave privada VAPID nem as credenciais do WeatherKit. É preciso publicar um pequeno backend HTTPS com:

1. endpoint `POST /push/subscribe` para receber e armazenar assinaturas;
2. tarefa agendada a cada 5 ou 15 minutos;
3. consulta ao feed `https://nivelguaiba.com.br/feed`;
4. comparação com as cotas de São Leopoldo e Campo Bom;
5. envio Web Push usando VAPID;
6. armazenamento do último estado para não repetir alertas.

Depois de publicar o backend, preencher no `index.html` (ou injetar durante o deploy):

```js
const PUSH_PUBLIC_KEY = 'CHAVE_PUBLICA_VAPID';
const PUSH_SUBSCRIPTION_ENDPOINT = 'https://api.exemplo.com/push/subscribe';
```

A chave privada VAPID fica somente como segredo no backend.

## Regras recomendadas

- São Leopoldo ≥ 3,50 m: atenção.
- São Leopoldo ≥ 4,50 m: inundação.
- Campo Bom ≥ 7,20 m: inundação.
- Enviar uma notificação apenas na transição abaixo → acima da cota.
- Remover assinaturas que retornarem HTTP 404 ou 410.

## WeatherKit

A integração WeatherKit também deve ocorrer no backend. Ela exige credenciais da Apple e token assinado. Não colocar a chave privada `.p8` no GitHub nem no JavaScript do navegador.

O backend pode expor ao painel somente os dados necessários, por exemplo:

```json
{
  "current": {},
  "forecast": [],
  "alerts": []
}
```

## Teste local

O Service Worker e as APIs de Push exigem HTTPS, exceto em `localhost`. Em produção, o site precisa ser servido por HTTPS, como no GitHub Pages.

No celular Apple, o usuário deve adicionar o site à Tela de Início antes de conceder notificações push. No Android/Chrome, a instalação pode ser oferecida diretamente pelo navegador.
