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
# Assuming you added TEST_NUMBER as recommended for good practice
TEST_NUMBER = os.getenv("TEST_NUMBER")


@app.get("/webhook", response_class=PlainTextResponse)
async def verify(request: Request):
    """
    Meta calls this GET endpoint once when you configure the Webhook.
    """
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    print(f"--- Webhook Verification Request: Mode={mode}, Token={token}, Challenge={challenge} ---")

    if mode == "subscribe" and token == VERIFY_TOKEN and challenge:
        print("WEBHOOK VERIFIED. Sending challenge back.")
        return PlainTextResponse(content=challenge, status_code=200)

    print("Verification failed: Token mismatch or invalid mode.")
    return PlainTextResponse(content="Verification token mismatch", status_code=403)


@app.get("/test-send")
def test_send():
    if not TEST_NUMBER:
        print("Error: TEST_NUMBER environment variable is not set.")
        return {"status": "error", "message": "TEST_NUMBER environment variable is not set."}

    print(f"Initiating test message send to: {TEST_NUMBER}")
    send_whatsapp_message(TEST_NUMBER, "Test from FastAPI")
    return {"status": "sent_test_message"}

# ----------------------------------------------------------------------

@app.post("/webhook")
async def receive_message(request: Request):
    """
    WhatsApp sends all incoming messages here as JSON (POST).
    """
    data = await request.json()
    print("\n--- INCOMING WHATSAPP PAYLOAD START ---")
    print(data)
    print("--- INCOMING WHATSAPP PAYLOAD END ---")

    try:
        entry = data["entry"][0]["changes"][0]["value"]

        # Only handle messages (ignore status updates, etc.)
        if "messages" in entry:
            message = entry["messages"][0]
            sender = message["from"]        # WhatsApp number
            msg_type = message["type"]

            if msg_type == "text":
                text = message["text"]["body"]
                
                # Log the extracted incoming message
                print(f"--- Incoming Text Message from {sender}: {text} ---")

                # Pass to AI Customer Service Agent
                result = run_support_agent("WhatsApp", text)

                print("AI Classification:")
                print(f"  Urgency: {result.urgency}")
                print(f"  Intent: {result.intent}")

                reply_text = result.reply
                
                # Log the outgoing message before sending
                print(f"--- Outgoing Reply to {sender}: {reply_text} ---")
                
                send_whatsapp_message(sender, reply_text)
            
            else:
                print(f"Non-text message received: {msg_type}. Skipping agent processing.")


    except Exception as e:
        print(f"ERROR handling incoming message: {e}")

    return {"status": "received"}

# ----------------------------------------------------------------------

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

    print("\n--- SENDING MESSAGE VIA API START ---")
    # print("URL:", url) # Keep this commented out unless needed for security/clean logs
    # print("Payload:", payload) # Keep this commented out unless needed for security/clean logs
    
    response = requests.post(url, headers=headers, json=payload)
    print(f"WhatsApp API Response Status: {response.status_code}")
    print(f"Response Text: {response.text}")
    print("--- SENDING MESSAGE VIA API END ---\n")


if __name__ == "__main__":
    # For local dev only:
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)