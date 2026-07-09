from analyzer import analyze_conversation
from collector import collect_signals
from database import (
    load_product_profile,
    save_opportunities,
)
from product_config import DEFAULT_PRODUCT_PROFILE


def main() -> None:
    """Run the SignalHunter growth intelligence pipeline."""

    product_profile = load_product_profile()

    if not product_profile:
        product_profile = DEFAULT_PRODUCT_PROFILE

    product_name = product_profile["product_name"]

    print()
    print("=" * 60)
    print("SIGNALHUNTER")
    print(f"Product: {product_name}")
    print("=" * 60)
    print()

    signals = collect_signals(
        product_profile=product_profile,
        max_videos=3,
    )

    print()
    print(f"Found {len(signals)} possible signals.")
    print()

    opportunities = []

    for index, signal in enumerate(signals, start=1):
        print(f"Analyzing {index}/{len(signals)}...")

        try:
            result = analyze_conversation(
                title=signal["title"],
                text=signal["text"],
                source=signal["source"],
                url=signal["url"],
                product_profile=product_profile,
            )

            intent_score = int(
                result.get(
                    "intent_score",
                    0,
                )
            )

            if intent_score >= 40:
                opportunities.append(result)

        except Exception as exc:
            print(f"Signal analysis failed: {exc}")

    opportunities.sort(
        key=lambda item: int(
            item.get(
                "intent_score",
                0,
            )
        ),
        reverse=True,
    )

    save_opportunities(opportunities)

    print()
    print(
        f"Saved {len(opportunities)} "
        f"growth opportunities."
    )
    print()


if __name__ == "__main__":
    main()