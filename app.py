import pandas as pd
import streamlit as st

from database import (
    load_opportunities,
    load_product_profile,
    save_product_profile,
)
from agent import generate_experiment
from product_config import DEFAULT_PRODUCT_PROFILE


st.set_page_config(
    page_title="SignalHunter",
    page_icon="📡",
    layout="wide",
)


def text_to_list(text: str) -> list[str]:
    """Convert comma-separated text into a cleaned list."""

    return [
        item.strip()
        for item in text.split(",")
        if item.strip()
    ]


saved_profile = load_product_profile()

if not saved_profile:
    saved_profile = DEFAULT_PRODUCT_PROFILE.copy()


with st.sidebar:
    st.header("Product Configuration")

    product_name = st.text_input(
        "Product Name",
        value=saved_profile["product_name"],
    )

    category = st.text_input(
        "Category",
        value=saved_profile["category"],
    )

    description = st.text_area(
        "Product Description",
        value=saved_profile["description"],
        height=120,
    )

    target_buyer = st.text_area(
        "Target Buyer",
        value=saved_profile["target_buyer"],
        height=100,
    )

    competitors_text = st.text_area(
        "Competitors",
        value=", ".join(
            saved_profile["competitors"]
        ),
        help=(
            "Enter competitors separated by commas."
        ),
    )

    capabilities_text = st.text_area(
        "Verified Capabilities",
        value=", ".join(
            saved_profile[
                "verified_capabilities"
            ]
        ),
        height=130,
        help=(
            "Only include capabilities that have been "
            "verified. Separate with commas."
        ),
    )

    if st.button(
        "Save Product Profile",
        width="stretch",
    ):
        product_profile = {
            "product_name": product_name.strip(),
            "category": category.strip(),
            "description": description.strip(),
            "target_buyer": target_buyer.strip(),
            "competitors": text_to_list(
                competitors_text
            ),
            "verified_capabilities": text_to_list(
                capabilities_text
            ),
        }

        save_product_profile(product_profile)

        st.success(
            "Product profile saved."
        )

        st.info(
            "Run `python run_pipeline.py` "
            "to collect signals for this product."
        )

        st.rerun()


product_profile = load_product_profile()

if not product_profile:
    product_profile = DEFAULT_PRODUCT_PROFILE


st.title("📡 SignalHunter")

st.caption(
    "AI-powered buyer intent and "
    "organic growth intelligence"
)

st.write(
    f"Analyzing organic growth signals for "
    f"**{product_profile['product_name']}**"
)

st.divider()


opportunities = load_opportunities()

if not opportunities:
    st.warning(
        "No growth opportunities found."
    )

    st.code(
        "python run_pipeline.py"
    )

    st.stop()


df = pd.DataFrame(opportunities)


col1, col2, col3, col4 = st.columns(4)


with col1:
    st.metric(
        "Signals Found",
        len(df),
    )


with col2:
    high_intent = len(
        df[
            df["intent_score"] >= 80
        ]
    )

    st.metric(
        "High Intent",
        high_intent,
    )


with col3:
    average_intent = int(
        df["intent_score"].mean()
    )

    st.metric(
        "Average Intent",
        average_intent,
    )


with col4:
    high_fit = len(
        df[
            df["product_fit"] == "High"
        ]
    )

    st.metric(
        "High Product Fit",
        high_fit,
    )


st.divider()


st.subheader(
    "Top Growth Opportunities"
)


display_columns = [
    "intent_score",
    "source",
    "buying_stage",
    "pain_point",
    "competitors_mentioned",
    "product_fit",
    "recommended_action",
]


st.dataframe(
    df[display_columns],
    width="stretch",
    hide_index=True,
)


st.divider()


st.subheader(
    "Opportunity Intelligence"
)


selected_index = st.selectbox(
    "Select an opportunity",
    options=range(
        len(opportunities)
    ),
    format_func=lambda index: (
        f'{opportunities[index]["intent_score"]}'
        f'/100 — '
        f'{opportunities[index]["pain_point"]}'
    ),
)


opportunity = opportunities[
    selected_index
]


left, right = st.columns(2)


with left:
    st.metric(
        "Intent Score",
        opportunity["intent_score"],
    )

    st.write(
        "**Buying Stage:**",
        opportunity["buying_stage"],
    )

    st.write(
        "**Pain Point:**",
        opportunity["pain_point"],
    )

    competitors = (
        opportunity.get(
            "competitors_mentioned",
            [],
        )
    )

    st.write(
        "**Competitors Mentioned:**",
        ", ".join(competitors)
        if competitors
        else "None detected",
    )

    st.write(
        "**Product Fit:**",
        opportunity["product_fit"],
    )


with right:
    st.write(
        "**Recommended Action**"
    )

    st.info(
        opportunity[
            "recommended_action"
        ]
    )

    st.write(
        "**Suggested Angle**"
    )

    st.write(
        opportunity["suggested_angle"]
    )


with st.expander(
    "Why SignalHunter flagged this"
):
    st.write(
        opportunity["reasoning"]
    )

    st.write(
        "**Original Conversation**"
    )

    st.write(
        opportunity["conversation"]
    )

    st.link_button(
        "Open Original Source",
        opportunity["url"],
    )


st.divider()


if st.button(
    "Generate Growth Experiment",
    type="primary",
):
    try:
        with st.spinner(
            "Designing a rapid growth experiment..."
        ):
            experiment = generate_experiment(
                opportunity=opportunity,
                product_profile=product_profile,
            )

        st.subheader(
            "Growth Experiment"
        )

        st.write(
            "### Hypothesis"
        )

        st.write(
            experiment["hypothesis"]
        )

        st.write(
            "### Channel"
        )

        st.write(
            experiment["channel"]
        )

        st.write(
            "### Experiment"
        )

        st.write(
            experiment["experiment"]
        )

        st.write(
            "### Success Metric"
        )

        st.write(
            experiment["success_metric"]
        )

        st.write(
            "### Duration"
        )

        st.write(
            experiment["duration"]
        )

        st.write(
            "### Next Action"
        )

        st.success(
            experiment["next_action"]
        )

    except Exception as exc:
        st.error(
            f"Experiment generation failed: {exc}"
        )