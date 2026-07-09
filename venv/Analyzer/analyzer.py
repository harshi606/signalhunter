import json
import os

from dotenv import load_dotenv
from groq import Groq

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))


def analyze_conversation(
    title: str,
    text: str,
    source: str,
    url: str,
) -> dict:
    """Analyze a public conversation for B2B customer-service buying intent."""

    prompt = f"""
You are an AI growth intelligence analyst for Typewise.

Typewise is an enterprise AI customer service platform.
It helps customer service teams automate and resolve customer
requests across channels such as email, chat, and social.

Analyze the following public conversation.

SOURCE:
{source}

TITLE:
{title}

CONVERSATION:
{text}

Your task is to identify whether this conversation represents
a real organic growth opportunity for Typewise.

Return ONLY valid JSON with these exact keys:

{{
    "intent_score": 0,
    "buying_stage": "",
    "pain_point": "",
    "competitors_mentioned": [],
    "typewise_fit": "",
    "reasoning": "",
    "recommended_action": "",
    "suggested_angle": ""
}}

Scoring guidance:

0-20:
No commercial or customer-service relevance.

21-40:
General AI or customer-service discussion.

41-60:
User has a customer-service operational pain point.

61-80:
User is researching solutions or mentioning vendors.

81-100:
User is actively comparing, replacing, evaluating,
or requesting recommendations for AI customer-service tools.

buying_stage must be one of:
"Awareness"
"Problem Aware"
"Research"
"Active Evaluation"
"Purchase Intent"

typewise_fit must be:
"Low"
"Medium"
"High"

recommended_action must be one of:
"Ignore"
"Monitor"
"Educational Response"
"Founder Response"
"Create Content"
"Direct Outreach"

Do not recommend spam.
Do not automatically recommend mentioning Typewise.
Prefer useful, channel-native participation.
"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": (
                    "You analyze organic B2B growth signals. "
                    "Return valid JSON only."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        response_format={"type": "json_object"},
        temperature=0.2,
    )

    result = json.loads(response.choices[0].message.content)

    result["title"] = title
    result["source"] = source
    result["url"] = url
    result["conversation"] = text

    return result