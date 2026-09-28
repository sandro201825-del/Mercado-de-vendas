import os
from flask import Flask, redirect, request, session, jsonify
from urllib.parse import urlencode
import requests

app = Flask(__name__)

# Chave da sessão
app.secret_key = os.getenv(
    "SESSION_SECRET",
    "troque-esta-chave-no-render"
)

# URL de autorização do Mercado Livre
ML_AUTH_URL = "https://auth.mercadolivre.com.br/authorization"

# URL para obter o token
ML_TOKEN_URL = os.getenv(
    "ML_TOKEN_URI",
    "https://api.mercadolibre.com/oauth/token"
)


@app.get("/")
def home():
    return """
    <h1>Mercado de Vendas V1.6</h1>
    <p>Backend ativo.</p>

    <p>
        <a href="/oauth/mercadolivre">
            Conectar Mercado Livre
        </a>
    </p>

    <p>
        <a href="/health">
            Verificar saúde
        </a>
    </p>
    """


@app.get("/health")
def health():
    return jsonify({
        "status": "ok",
        "version": "1.6"
    })


@app.route("/notifications", methods=["POST"])
def notifications():
    data = request.get_json(silent=True) or {}

    print("Notificação Mercado Livre recebida:", data)

    return jsonify({
        "ok": True,
        "received": True
    }), 200


@app.get("/oauth/mercadolivre")
def oauth_start():

    client_id = os.getenv("ML_CLIENT_ID")
    redirect_uri = os.getenv("ML_REDIRECT_URI")

    if not client_id:
        return jsonify({
            "ok": False,
            "error": "ML_CLIENT_ID não configurado no Render."
        }), 500

    if not redirect_uri:
        return jsonify({
            "ok": False,
            "error": "ML_REDIRECT_URI não configurado no Render."
        }), 500

    # Gera um estado de segurança para o OAuth
    state = os.urandom(16).hex()
    session["oauth_state"] = state

    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "state": state
    }

    authorization_url = (
        ML_AUTH_URL + "?" + urlencode(params)
    )

    print("Iniciando OAuth Mercado Livre")
    print("Redirect URI:", redirect_uri)

    return redirect(authorization_url)


@app.get("/oauth/callback")
def oauth_callback():

    # Verifica se o Mercado Livre retornou algum erro
    error = request.args.get("error")

    if error:
        return jsonify({
            "ok": False,
            "error": error,
            "error_description": request.args.get(
                "error_description"
            )
        }), 400

    # Verifica o state de segurança
    received_state = request.args.get("state")
    saved_state = session.get("oauth_state")

    if not received_state or received_state != saved_state:
        return jsonify({
            "ok": False,
            "error": "state_invalido"
        }), 400

    # Código recebido do Mercado Livre
    code = request.args.get("code")

    if not code:
        return jsonify({
            "ok": False,
            "error": "codigo_oauth_ausente"
        }), 400

    # Variáveis configuradas no Render
    client_id = os.getenv("ML_CLIENT_ID")
    client_secret = os.getenv("ML_CLIENT_SECRET")
    redirect_uri = os.getenv("ML_REDIRECT_URI")

    if not client_id:
        return jsonify({
            "ok": False,
            "error": "ML_CLIENT_ID não configurado."
        }), 500

    if not client_secret:
        return jsonify({
            "ok": False,
            "error": "ML_CLIENT_SECRET não configurado."
        }), 500

    if not redirect_uri:
        return jsonify({
            "ok": False,
            "error": "ML_REDIRECT_URI não configurado."
        }), 500

    # Dados usados para trocar o código pelo access token
    payload = {
        "grant_type": "authorization_code",
        "client_id": client_id,
        "client_secret": client_secret,
        "code": code,
        "redirect_uri": redirect_uri
    }

    print("Solicitando token ao Mercado Livre...")
    print("Token URI:", ML_TOKEN_URL)

    try:
        response = requests.post(
            ML_TOKEN_URL,
            data=payload,
            timeout=30
        )

    except requests.RequestException as e:
        return jsonify({
            "ok": False,
            "error": "falha_na_comunicacao_com_mercado_livre",
            "detalhes": str(e)
        }), 502

    # Mercado Livre recusou a troca do código
    if not response.ok:

        try:
            data = response.json()

        except ValueError:
            data = {
                "error": response.text
            }

        print("Erro Mercado Livre:", data)

        return jsonify({
            "ok": False,
            "mercado_livre": data
        }), response.status_code

    # Tenta ler o token recebido
    try:
        token = response.json()

    except ValueError:
        return jsonify({
            "ok": False,
            "error": "resposta_invalida_do_mercado_livre"
        }), 502

    # Guarda temporariamente o token na sessão
    session["ml_token"] = token

    # Remove o state que já foi utilizado
    session.pop("oauth_state", None)

    print("Mercado Livre conectado com sucesso.")

    return jsonify({
        "ok": True,
        "mensagem": "Mercado Livre conectado com sucesso.",
        "token_recebido": True
    })


if __name__ == "__main__":

    port = int(
        os.getenv("PORT", "3000")
    )

    app.run(
        host="0.0.0.0",
        port=port
    )
