import os
import json
from dataclasses import dataclass
from typing import Literal

from dotenv import load_dotenv
from openai import OpenAI

# Load values from .env
load_dotenv()

# Create OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

Urgency = Literal["URGENT", "NOT URGENT"]
Intent = Literal[
    "FAQ",
    "Order Issue",
    "Refund Request",
    "Complaint",
    "Product Question",
    "General Support",
    "Other",
]


@dataclass
class SupportResult:
    urgency: Urgency
    intent: Intent
    summary: str
    reply: str


INSTRUCTION = """
You are a Customer Service Support Agent.

Your job is to:
1. Classify the message into EXACTLY ONE of:
   - URGENT
   - NOT URGENT

2. Identify the customer's intent. Choose ONE:
   - FAQ
   - Order Issue
   - Refund Request
   - Complaint
   - Product Question
   - General Support
   - Other

3. Write a short, friendly summary (2–3 sentences).

4. Draft a polite reply that the business can send to the customer.
   - Tone: warm, clear, professional.
   - If the customer is upset, apologize first.
   - Always give next steps.

5. If the message is missing important info (like order number, email, photo, etc.),
   politely ask for those details.

IMPORTANT: Respond ONLY in valid JSON using this exact format:

{
  "urgency": "URGENT or NOT URGENT",
  "intent": "one of the intents listed",
  "summary": "short summary here",
  "reply": "full reply text here"
}
"""


def run_support_agent(channel: str, message: str) -> SupportResult:
    """
    Sends the customer message to the AI and returns a SupportResult object.
    """
    
    # 📝 Use the messages list structure for Chat Completions API
    messages = [
        {"role": "system", "content": INSTRUCTION},
        {"role": "user", "content": f"Channel: {channel}\nMessage: {message}"}
    ]

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            # ✨ CRITICAL: Force the model to output valid JSON
            response_format={"type": "json_object"}
        )

        # 📝 Access the content using the new structure
        raw_text = response.choices[0].message.content

        # Attempt to parse the JSON answer
        data = json.loads(raw_text)

    except Exception: # Catch both API errors and JSONDecodeError
        # If something goes wrong, fall back to a safe default
        data = {
            "urgency": "NOT URGENT",
            "intent": "Other",
            "summary": "Could not parse AI response or an API error occurred.",
            "reply": "Hi! Thanks for your message. We’re having a small issue with our assistant. Please try again or contact support directly.",
        }

    return SupportResult(
        urgency=data.get("urgency", "NOT URGENT"),
        intent=data.get("intent", "Other"),
        summary=data.get("summary", ""),
        reply=data.get("reply", ""),
    )


if __name__ == "__main__":
    # Simple CLI test runner
    print("Customer Service Agent Queen")
    channel = input("Channel (WhatsApp / Instagram / Email): ")
    message = input("Customer message: ")

    result = run_support_agent(channel, message)

    print("\n=== RESULT ===")
    print("Urgency:", result.urgency)
    print("Intent:", result.intent)
    print("\nSummary:", result.summary)
    print("\nReply:\n", result.reply)
