# Ferramenta de Vendas V1.6

Backend Node.js para OAuth 2.0 do Mercado Livre + busca MLB + motor de análise.

## Requisitos
Node.js 18+.

## Configuração
1. Copie `.env.example` para `.env`.
2. Preencha `ML_CLIENT_ID`, `ML_CLIENT_SECRET` e `ML_REDIRECT_URI`.
3. No Mercado Livre, cadastre exatamente a mesma Redirect URI. Para criação de aplicação, o Mercado Livre exige HTTPS.
4. Rode com `npm start`.

## Observação importante
O arquivo HTML sozinho não é suficiente para OAuth seguro. O Secret fica somente no backend. Para usar com uma aplicação do Mercado Livre, publique este backend em um domínio HTTPS e use esse endereço como Redirect URI.

Endpoints:
- GET /oauth/start
- GET /oauth/callback
- GET /api/status
- GET /api/me
- GET /api/search?q=...
- GET /api/analyze?q=...&cost=20&freight=5&commission=15&tax=0&other=0&fixed=0&minMargin=20&maxDays=10
