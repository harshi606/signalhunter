import json
import os
from typing import Any

from dotenv import load_dotenv
from groq import Groq

load_dotenv()


def get_groq_client() -> Groq:
    """Create and return the Groq client."""

    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        raise ValueError(
            "GROQ_API_KEY is missing. Add it to the .env file."
        )

    return Groq(api_key=api_key)


def analyze_conversation(
    title: str,
    text: str,
    source: str,
    url: str,
    product_profile: dict[str, Any],
) -> dict[str, Any]:
    """
    Analyze a public conversation for buyer intent
    and product-specific organic growth potential.
    """

    client = get_groq_client()

    product_name = product_profile["product_name"]
    category = product_profile["category"]
    description = product_profile["description"]
    target_buyer = product_profile["target_buyer"]
    competitors = product_profile["competitors"]
    verified_capabilities = product_profile[
        "verified_capabilities"
    ]

    prompt = f"""
You are an AI organic growth intelligence analyst.

Your job is to analyze public online conversations and identify
real buyer-intent and organic growth opportunities for a product.

PRODUCT PROFILE

Product Name:
{product_name}

Category:
{category}

Product Description:
{description}

Target Buyer:
{target_buyer}

Known Competitors:
{competitors}

Verified Product Capabilities:
{verified_capabilities}

PUBLIC CONVERSATION

Source:
{source}

Title:
{title}

Conversation:
{text}

Analyze whether this conversation represents an organic growth
opportunity for the product.

Return ONLY valid JSON with these exact keys:

{{
    "intent_score": 0,
    "buying_stage": "",
    "pain_point": "",
    "competitors_mentioned": [],
    "product_fit": "",
    "reasoning": "",
    "recommended_action": "",
    "suggested_angle": ""
}}

INTENT SCORE RULES

0-20:
No commercial or category relevance.

21-40:
General discussion related to the product category.

41-60:
The person has an operational problem relevant to the category.

61-80:
The person is researching solutions, discussing tools,
or mentioning vendors.

81-100:
The person is actively comparing, replacing, evaluating,
or requesting product recommendations.

BUYING STAGE must be exactly one of:

"Awareness"
"Problem Aware"
"Research"
"Active Evaluation"
"Purchase Intent"

PRODUCT FIT must be exactly one of:

"Low"
"Medium"
"High"

RECOMMENDED ACTION must be exactly one of:

"Ignore"
"Monitor"
"Educational Response"
"Founder Response"
"Create Content"
"Direct Outreach"

IMPORTANT ORGANIC GROWTH RULES

Do not recommend spam.

Do not automatically recommend mentioning or promoting
{product_name}.

The suggested_angle should describe the useful insight,
perspective, or educational topic that could be contributed.

Only recommend a direct product mention when the person explicitly
asks for product recommendations or when a direct product comparison
is clearly appropriate.

For community conversations, prioritize usefulness and credibility
over product promotion.

CRITICAL PRODUCT-GROUNDING RULES

Do not invent or assume product capabilities.

Only treat capabilities listed under VERIFIED PRODUCT CAPABILITIES
as confirmed.

Do not claim that {product_name} supports a feature, integration,
workflow, or technical capability unless it is explicitly listed
in the verified capabilities.

If a buyer pain point appears commercially relevant but the required
product capability is not verified, describe the opportunity as a
positioning hypothesis or research opportunity.

Example of a good suggested angle:

"Explain how customer service leaders should evaluate knowledge
retrieval quality and verify whether the product has a differentiated
capability before positioning it."

Example of a bad suggested angle:

"Explain how the product integrates with knowledge bases"

when knowledge-base integration is not in the verified capabilities.

Separate buyer pain detection from product capability claims.

PRODUCT FIT RULES

High:
The buyer pain strongly aligns with the product description,
target buyer, and verified capabilities.

Medium:
The category is relevant, but product capability alignment
is partial or unclear.

Low:
The conversation is not a realistic fit for this product.

The reasoning must clearly explain why the conversation was scored.

Return JSON only.
"""

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You analyze B2B organic growth signals. "
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

        content = response.choices[0].message.content

        if not content:
            raise ValueError(
                "Groq returned an empty response."
            )

        result = json.loads(content)

    except json.JSONDecodeError as exc:
        raise ValueError(
            f"AI returned invalid JSON: {exc}"
        ) from exc

    except Exception as exc:
        raise RuntimeError(
            f"Conversation analysis failed: {exc}"
        ) from exc

    result["title"] = title
    result["source"] = source
    result["url"] = url
    result["conversation"] = text
    result["product_name"] = product_name

    return result