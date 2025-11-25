import os
import requests

from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
from dotenv import load_dotenv

from agent_queen import run_support_agent

load_dotenv()

app = FastAPI()

WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")


@app.get("/webhook", response_class=PlainTextResponse)
async def verify(request: Request):
    """
    Meta calls this GET endpoint once when you configure the Webhook.
    We must:
    - Check that the verify_token matches
    - If ok, return the hub.challenge as plain text with 200 status
    """
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    print("Webhook verification:", mode, token, challenge)

    if mode == "subscribe" and token == VERIFY_TOKEN and challenge:
        # THIS is what Meta expects to verify the webhook
        return PlainTextResponse(content=challenge, status_code=200)

    # If token doesn't match, return 403
    return PlainTextResponse(content="Verification token mismatch", status_code=403)


@app.get("/test-send")
def test_send():
    # use your WA ID exactly as it appears in the logs, e.g. "2348100251810"
    test_number = "2348100251810"
    send_whatsapp_message(test_number, "Test from FastAPI")
    return {"status": "sent_test_message"}

@app.post("/webhook")
async def receive_message(request: Request):
    """
    WhatsApp sends all incoming messages here as JSON (POST).
    We:
    - Extract sender & message text
    - Pass it to the AI
    - Send reply back via WhatsApp API
    """
    data = await request.json()
    print("Incoming WhatsApp data:", data)

    try:
        entry = data["entry"][0]["changes"][0]["value"]

        # Only handle messages (ignore status updates, etc.)
        if "messages" in entry:
            message = entry["messages"][0]
            sender = message["from"]           # WhatsApp number
            msg_type = message["type"]

            if msg_type == "text":
                text = message["text"]["body"]
                print(f"From {sender}: {text}")

                # Pass to AI Customer Service Agent
                result = run_support_agent("WhatsApp", text)

                print("AI urgency:", result.urgency)
                print("AI intent:", result.intent)

                reply_text = result.reply

                send_whatsapp_message(sender, reply_text)

    except Exception as e:
        print("Error handling incoming message:", e)

    return {"status": "received"}


def send_whatsapp_message(to_number: str, text: str):
    url = f"https://graph.facebook.com/v24.0/{PHONE_NUMBER_ID}/messages"

    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json",
    }

    payload = {
        "messaging_product": "whatsapp",
        "to": to_number,
        "type": "text",
        "text": {"body": text},
    }

    print("Sending to:", to_number)
    print("URL:", url)
    print("Payload:", payload)

    response = requests.post(url, headers=headers, json=payload)
    print("WhatsApp send response:", response.status_code, response.text)


if __name__ == "__main__":
    # For local dev only:
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
