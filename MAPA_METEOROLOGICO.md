# Mapa meteorológico

O painel agora possui um mapa Leaflet atualizado automaticamente a cada 10 minutos.

A camada **Vento local** consulta `/api/wind-map`, que agrega velocidade, direção, rajadas, temperatura e código meteorológico do Open-Meteo para uma grade de nove pontos em torno de Novo Hamburgo. As setas apontam para a direção de deslocamento do vento e a cor representa a intensidade: azul normal, amarelo a partir de 40 km/h, laranja a partir de 60 km/h e vermelho a partir de 80 km/h.

A camada **Avisos INMET** consulta `/api/inmet-alerts`. Ela mostra avisos oficiais classificados como tornado, granizo, vento, vendaval e tempestade. Quando o feed do INMET não fornece geometria municipal, o marcador é aproximado pelo município ou pelo centroide estadual; ele não deve ser interpretado como o ponto exato do fenômeno.

A camada **El Niño / ENOS** carrega as imagens mensais publicadas pelo CPTEC/INPE a partir de `/api/enso`, incluindo anomalia de temperatura da superfície do mar e anomalia de vento em 850 hPa. A imagem é atualizada quando o CPTEC publica um novo boletim. O mapa não representa observação oceânica minuto a minuto: ENOS é um fenômeno climático acompanhado por índices e mapas mensais.

Fontes oficiais: [INMET Alert-AS](https://avisos.inmet.gov.br/), [CPTEC/INPE ENOS](https://clima.cptec.inpe.br/enos) e [Open-Meteo](https://open-meteo.com/en/docs). A camada de vento é uma previsão/modelagem, não uma medição de estação no local exato.
