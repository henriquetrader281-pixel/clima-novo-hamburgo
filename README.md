# Clima Novo Hamburgo

Painel meteorológico local para Novo Hamburgo — Centro e Lomba Grande.

## Arquitetura

O site mantém o layout PWA estático e usa **Vercel Functions** para:

- consultar Apple WeatherKit sem expor credenciais Apple;
- consultar níveis do Rio dos Sinos em estações próximas;
- armazenar inscrições Web Push em Redis REST;
- enviar alertas automáticos por cron, inclusive com o navegador fechado.

Consulte [`BACKEND.md`](BACKEND.md) para o deploy e [`PWA_PUSH_SETUP.md`](PWA_PUSH_SETUP.md) para os detalhes da integração.

## Publicação

Este site pode ser publicado através do GitHub Pages. Para usar WeatherKit e Web Push, publique também o backend na Vercel, configure `window.CLIMA_API_BASE` no deploy estático e preencha as variáveis secretas descritas na documentação.
