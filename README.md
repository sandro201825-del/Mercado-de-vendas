# Mercado de Vendas — V1.6

Backend Flask com início do fluxo OAuth do Mercado Livre.

## Arquivos
- app.py — servidor e OAuth
- requirements.txt — dependências
- render.yaml — configuração do Render
- .env.example — variáveis necessárias

## Redirect URI
Depois que o serviço estiver publicado no Render, use exatamente:

https://SEU-DOMINIO/oauth/callback

Essa mesma URI deve estar cadastrada no aplicativo do Mercado Livre.

## Variáveis no Render
- ML_CLIENT_ID
- ML_CLIENT_SECRET
- ML_REDIRECT_URI
- SESSION_SECRET

Nunca publique o Client Secret no GitHub.
