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
            "GROQ_API_KEY is missing."
        )

    return Groq(api_key=api_key)


def generate_experiment(
    opportunity: dict[str, Any],
    product_profile: dict[str, Any],
) -> dict[str, Any]:
    """
    Convert one buyer signal into a fast,
    measurable organic growth experiment.
    """

    client = get_groq_client()

    product_name = product_profile[
        "product_name"
    ]

    verified_capabilities = product_profile[
        "verified_capabilities"
    ]

    prompt = f"""
You are an AI-native organic growth engineer.

You are working on:

Product:
{product_name}

Category:
{product_profile["category"]}

Target Buyer:
{product_profile["target_buyer"]}

Verified Product Capabilities:
{verified_capabilities}

You discovered ONE real public buyer-intent signal.

SIGNAL

Source:
{opportunity["source"]}

Original Conversation:
{opportunity["conversation"]}

Intent Score:
{opportunity["intent_score"]}

Buying Stage:
{opportunity["buying_stage"]}

Pain Point:
{opportunity["pain_point"]}

Competitors Mentioned:
{opportunity["competitors_mentioned"]}

Product Fit:
{opportunity["product_fit"]}

Recommended Action:
{opportunity["recommended_action"]}

Suggested Angle:
{opportunity["suggested_angle"]}

Turn this signal into a FAST and TESTABLE organic growth experiment.

Return ONLY valid JSON:

{{
    "hypothesis": "",
    "channel": "",
    "experiment": "",
    "success_metric": "",
    "duration": "",
    "next_action": ""
}}

STRICT RULES

1. The experiment must launch within 48 hours.

2. The experiment must be executable by one growth engineer.

3. Use the SAME channel as the discovered signal unless there
is a strong reason to use another channel.

4. The experiment must directly test the detected buyer pain point.

5. Do not generate generic marketing strategies.

BAD EXPERIMENTS:

"Write three blog posts."

"Post regularly on LinkedIn."

"Improve SEO."

"Create an email campaign."

"Build a content strategy."

6. Prefer small tests such as:

- Respond educationally to 5 relevant conversations.

- Test 3 educational response angles.

- Find 10 similar high-intent discussions.

- Create one pain-point-specific comparison asset.

- Test founder participation versus brand participation.

- Turn repeated buyer language into one focused content asset.

7. Never recommend spam.

8. Never recommend mass automated posting.

9. Do not invent product capabilities.

10. Only make product claims using the verified capabilities.

11. If the required product capability is not verified, frame the
experiment as a positioning hypothesis that must first be validated.

12. The success metric must contain concrete numbers.

BAD:

"Increase engagement."

GOOD:

"Publish 5 educational responses and generate at least
2 meaningful replies or 1 qualified product inquiry."

13. Duration must be between 2 and 7 days.

14. next_action must explain what to do depending on the outcome.

Example:

"If at least 2 conversations generate meaningful replies,
test the same pain-point angle on Reddit. Otherwise change
the response framing and rerun the experiment."

The goal is rapid learning, not content volume.

Return JSON only.
"""

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You design rapid organic growth "
                        "experiments. Return valid JSON only."
                    ),
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            response_format={
                "type": "json_object"
            },
            temperature=0.3,
        )

        content = (
            response
            .choices[0]
            .message
            .content
        )

        if not content:
            raise ValueError(
                "Groq returned an empty response."
            )

        return json.loads(content)

    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Experiment agent returned "
            f"invalid JSON: {exc}"
        ) from exc

    except Exception as exc:
        raise RuntimeError(
            f"Experiment generation failed: {exc}"
        ) from exc