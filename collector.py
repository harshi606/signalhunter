import os
from typing import Any

from dotenv import load_dotenv
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

load_dotenv()


BUYER_KEYWORDS = [
    "alternative",
    "alternatives",
    "recommend",
    "recommendation",
    "looking for",
    "currently use",
    "currently using",
    "using",
    "pricing",
    "price",
    "expensive",
    "cheaper",
    "migrate",
    "migration",
    "replace",
    "switch",
    "comparison",
    "compare",
    "better than",
    "automation",
    "tool",
    "platform",
    "software",
]


def get_youtube_client():
    """Create the YouTube API client."""

    api_key = os.getenv("YOUTUBE_API_KEY")

    if not api_key:
        raise ValueError(
            "YOUTUBE_API_KEY is missing. Add it to .env."
        )

    return build(
        "youtube",
        "v3",
        developerKey=api_key,
    )


def build_search_queries(
    product_profile: dict[str, Any],
) -> list[str]:
    """
    Build product-specific YouTube search queries.
    """

    category = product_profile["category"]
    competitors = product_profile["competitors"]

    queries = [
        f"best {category} platform",
        f"best {category} software",
        f"{category} alternatives",
        f"{category} recommendations",
        f"{category} comparison",
    ]

    for competitor in competitors:
        queries.append(
            f"{competitor} alternative"
        )

        queries.append(
            f"{competitor} review"
        )

        queries.append(
            f"{competitor} problems"
        )

    return list(dict.fromkeys(queries))


def is_possible_signal(
    text: str,
    product_profile: dict[str, Any],
) -> bool:
    """
    Apply a deterministic keyword filter before LLM analysis.
    """

    normalized = text.lower()

    dynamic_keywords = [
        product_profile["category"].lower(),
        product_profile["product_name"].lower(),
    ]

    dynamic_keywords.extend(
        competitor.lower()
        for competitor in product_profile["competitors"]
    )

    all_keywords = (
        BUYER_KEYWORDS + dynamic_keywords
    )

    return any(
        keyword in normalized
        for keyword in all_keywords
    )


def collect_youtube_comments(
    video_id: str,
    query: str,
    youtube,
    max_results: int = 20,
) -> list[dict[str, str]]:
    """
    Retrieve top-level YouTube comments.
    """

    try:
        response = (
            youtube.commentThreads()
            .list(
                part="snippet",
                videoId=video_id,
                maxResults=max_results,
                textFormat="plainText",
                order="relevance",
            )
            .execute()
        )

    except HttpError:
        return []

    comments = []

    for item in response.get("items", []):
        snippet = (
            item["snippet"]
            ["topLevelComment"]
            ["snippet"]
        )

        text = snippet.get(
            "textDisplay",
            "",
        ).strip()

        if not text:
            continue

        comments.append(
            {
                "title": "YouTube comment",
                "text": text,
                "source": "YouTube",
                "url": (
                    "https://www.youtube.com/watch?v="
                    f"{video_id}"
                ),
                "query": query,
            }
        )

    return comments


def collect_signals(
    product_profile: dict[str, Any],
    max_videos: int = 3,
) -> list[dict[str, str]]:
    """
    Search YouTube and collect potential buyer signals.
    """

    youtube = get_youtube_client()

    search_queries = build_search_queries(
        product_profile
    )

    signals = []
    seen_comments = set()

    for query in search_queries:
        print(f"Searching YouTube: {query}")

        try:
            response = (
                youtube.search()
                .list(
                    part="snippet",
                    q=query,
                    type="video",
                    maxResults=max_videos,
                    order="relevance",
                )
                .execute()
            )

        except HttpError as exc:
            print(
                f"YouTube search failed for "
                f"'{query}': {exc}"
            )
            continue

        for item in response.get("items", []):
            video_id = item["id"].get(
                "videoId"
            )

            if not video_id:
                continue

            comments = collect_youtube_comments(
                video_id=video_id,
                query=query,
                youtube=youtube,
                max_results=20,
            )

            for comment in comments:
                text = comment["text"]

                normalized_text = (
                    " ".join(
                        text.lower().split()
                    )
                )

                if normalized_text in seen_comments:
                    continue

                if not is_possible_signal(
                    text,
                    product_profile,
                ):
                    continue

                seen_comments.add(
                    normalized_text
                )

                signals.append(comment)

    return signals