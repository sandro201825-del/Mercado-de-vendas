
import os
from flask import Flask, redirect, request, session, jsonify
from urllib.parse import urlencode
import requests

app = Flask(__name__)
app.secret_key = os.getenv("SESSION_SECRET", "troque-esta-chave")

ML_AUTH_URL = "https://auth.mercadolivre.com.br/authorization"
ML_TOKEN_URL = "https://api.mercadolibre.com/oauth/token"


@app.get("/")
def home():
    return """
    <h1>Mercado de Vendas V1.6</h1>
    <p>Backend ativo.</p>
    <p><a href="/oauth/mercadolivre">Conectar Mercado Livre</a></p>
    <p><a href="/health">Verificar saúde</a></p>
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

    if not client_id or not redirect_uri:
        return "Configure ML_CLIENT_ID e ML_REDIRECT_URI no Render.", 500

    state = os.urandom(16).hex()
    session["oauth_state"] = state

    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "state": state,
    }

    return redirect(
        ML_AUTH_URL + "?" + urlencode(params)
    )


@app.get("/oauth/callback")
def oauth_callback():
    error = request.args.get("error")

    if error:
        return jsonify({
            "ok": False,
            "error": error
        }), 400

    if request.args.get("state") != session.get("oauth_state"):
        return jsonify({
            "ok": False,
            "error": "state_invalido"
        }), 400

    code = request.args.get("code")

    if not code:
        return jsonify({
            "ok": False,
            "error": "codigo_oauth_ausente"
        }), 400

    payload = {
        "grant_type": "authorization_code",
        "client_id": os.getenv("ML_CLIENT_ID"),
        "client_secret": os.getenv("ML_CLIENT_SECRET"),
        "code": code,
        "redirect_uri": os.getenv("ML_REDIRECT_URI"),
    }

    r = requests.post(
        ML_TOKEN_URL,
        data=payload,
        timeout=30
    )

    if not r.ok:
        try:
            data = r.json()
        except ValueError:
            data = {
                "error": r.text
            }

        return jsonify({
            "ok": False,
            "mercado_livre": data
        }), r.status_code

    token = r.json()

    session["ml_token"] = token

    return jsonify({
        "ok": True,
        "mensagem": "Mercado Livre conectado com sucesso.",
        "token_recebido": True
    })


if __name__ == "__main__":
    port = int(os.getenv("PORT", "3000"))

    app.run(
        host="0.0.0.0",
        port=port
    )
