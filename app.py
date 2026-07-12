import pandas as pd
import streamlit as st

from analyzer import analyze_conversation
from collector import collect_signals
from database import (
    load_opportunities,
    load_product_profile,
    save_opportunities,
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


def normalize_old_results(opportunities: list[dict]) -> list[dict]:
    """
    Backward compatibility for older results that used typewise_fit
    instead of product_fit.
    """

    for opportunity in opportunities:
        if "product_fit" not in opportunity:
            opportunity["product_fit"] = opportunity.get(
                "typewise_fit",
                "Low",
            )

    return opportunities


def run_signal_pipeline(
    product_profile: dict,
    max_videos: int = 3,
) -> list[dict]:
    """
    Run the full SignalHunter pipeline from inside Streamlit.

    Steps:
    1. Collect public signals.
    2. Analyze each signal with the LLM.
    3. Keep opportunities with intent_score >= 40.
    4. Sort by intent_score.
    5. Save results to JSON.
    """

    signals = collect_signals(
        product_profile=product_profile,
        max_videos=max_videos,
    )

    if not signals:
        save_opportunities([])
        return []

    opportunities = []

    progress_bar = st.progress(0)
    status_text = st.empty()

    total_signals = len(signals)

    for index, signal in enumerate(signals, start=1):
        status_text.write(
            f"Analyzing signal {index}/{total_signals}..."
        )

        try:
            result = analyze_conversation(
                title=signal["title"],
                text=signal["text"],
                source=signal["source"],
                url=signal["url"],
                product_profile=product_profile,
            )

            intent_score = int(result.get("intent_score", 0))

            if intent_score >= 40:
                opportunities.append(result)

        except Exception as exc:
            st.warning(
                f"Skipped one signal because analysis failed: {exc}"
            )

        progress_bar.progress(index / total_signals)

    opportunities.sort(
        key=lambda item: int(item.get("intent_score", 0)),
        reverse=True,
    )

    save_opportunities(opportunities)

    status_text.write(
        f"Finished. Saved {len(opportunities)} growth opportunities."
    )

    return opportunities


# ---------------------------------------------------------
# Session state
# ---------------------------------------------------------

if "pipeline_has_run" not in st.session_state:
    st.session_state.pipeline_has_run = False

if "last_run_opportunities" not in st.session_state:
    st.session_state.last_run_opportunities = []


# ---------------------------------------------------------
# Load product profile
# ---------------------------------------------------------

saved_profile = load_product_profile()

if not saved_profile:
    saved_profile = DEFAULT_PRODUCT_PROFILE.copy()


# ---------------------------------------------------------
# Sidebar: Product setup
# ---------------------------------------------------------

with st.sidebar:
    st.header("Tell SignalHunter about your product")

    st.caption(
        "This helps SignalHunter understand what market, competitors, "
        "buyers, and product capabilities to analyze."
    )

    product_name = st.text_input(
        "Product name",
        value=saved_profile["product_name"],
    )

    category = st.text_input(
        "Category",
        value=saved_profile["category"],
        help="Example: AI customer service, project management, CRM, design software",
    )

    description = st.text_area(
        "What does your product do?",
        value=saved_profile["description"],
        height=120,
    )

    target_buyer = st.text_area(
        "Who is your target buyer?",
        value=saved_profile["target_buyer"],
        height=100,
    )

    competitors_text = st.text_area(
        "Competitors",
        value=", ".join(saved_profile["competitors"]),
        help="Enter competitors separated by commas.",
    )

    capabilities_text = st.text_area(
        "Verified capabilities",
        value=", ".join(saved_profile["verified_capabilities"]),
        height=130,
        help=(
            "Only include capabilities your product actually supports. "
            "Separate each capability with a comma."
        ),
    )

    max_videos = st.slider(
        "Videos per search query",
        min_value=1,
        max_value=5,
        value=3,
        help="Lower is faster and cheaper. Higher finds more signals.",
    )

    if st.button(
        "Save product setup",
        width="stretch",
    ):
        product_profile_to_save = {
            "product_name": product_name.strip(),
            "category": category.strip(),
            "description": description.strip(),
            "target_buyer": target_buyer.strip(),
            "competitors": text_to_list(competitors_text),
            "verified_capabilities": text_to_list(capabilities_text),
        }

        save_product_profile(product_profile_to_save)

        st.session_state.pipeline_has_run = False
        st.session_state.last_run_opportunities = []

        st.success("Product setup saved.")
        st.rerun()


product_profile = load_product_profile()

if not product_profile:
    product_profile = DEFAULT_PRODUCT_PROFILE.copy()


# ---------------------------------------------------------
# Main header
# ---------------------------------------------------------

st.title("📡 SignalHunter")

st.subheader(
    "Find buyer-intent conversations your future customers are already having."
)

st.write(
    f"SignalHunter is currently set up for **{product_profile['product_name']}**."
)

st.markdown(
    """
    SignalHunter searches public conversations, detects buying intent,
    identifies competitor mentions and pain points, scores product fit,
    and recommends the next organic growth action.
    """
)

st.divider()


# ---------------------------------------------------------
# How it works section
# ---------------------------------------------------------

with st.container():
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("### 1. Find signals")
        st.write(
            "Searches public conversations where people discuss problems, "
            "competitors, alternatives, pricing, and recommendations."
        )

    with col2:
        st.markdown("### 2. Score intent")
        st.write(
            "Uses AI to classify buying stage, pain point, competitor mentions, "
            "and product fit."
        )

    with col3:
        st.markdown("### 3. Recommend action")
        st.write(
            "Turns strong signals into useful organic growth actions and "
            "fast experiments."
        )


st.divider()


# ---------------------------------------------------------
# Run pipeline button
# ---------------------------------------------------------

st.subheader("Run SignalHunter")

st.write(
    "Click the button below to collect fresh public conversations, "
    "score buyer intent, and update the dashboard."
)

run_clicked = st.button(
    "Analyze Market Signals",
    type="primary",
)

if run_clicked:
    with st.spinner(
        f"Finding buyer-intent signals for {product_profile['product_name']}..."
    ):
        try:
            fresh_opportunities = run_signal_pipeline(
                product_profile=product_profile,
                max_videos=max_videos,
            )

            st.session_state.pipeline_has_run = True
            st.session_state.last_run_opportunities = fresh_opportunities

            st.success(
                f"Pipeline complete. Found "
                f"{len(fresh_opportunities)} growth opportunities."
            )

            st.rerun()

        except Exception as exc:
            st.error(f"Pipeline failed: {exc}")


# ---------------------------------------------------------
# Load opportunities only after pipeline has run
# ---------------------------------------------------------

if st.session_state.pipeline_has_run:
    opportunities = load_opportunities()
    opportunities = normalize_old_results(opportunities)
else:
    opportunities = []


# ---------------------------------------------------------
# Empty/home state
# ---------------------------------------------------------

if not opportunities:
    st.info(
        "Enter your product details in the sidebar, then click "
        "**Analyze Market Signals** to find buyer-intent conversations."
    )

    st.markdown(
        """
        ### What SignalHunter looks for

        SignalHunter tries to find conversations where people are:

        - complaining about a competitor
        - asking for alternatives
        - comparing tools
        - discussing pricing pain
        - describing workflow problems
        - researching solutions
        - asking for recommendations

        After analysis, it ranks opportunities by buyer intent and product fit.
        """
    )

    st.markdown(
        """
        ### Example signal

        > “We currently use Zendesk and are looking at Intercom Fin, but pricing
        gets difficult at our ticket volume. Are there AI support tools that work
        with our existing stack?”

        SignalHunter would detect:

        - Buying stage: Active evaluation
        - Pain point: Pricing and migration concerns
        - Competitors: Zendesk, Intercom Fin
        - Recommended action: Educational response or founder response
        """
    )

    st.stop()


# ---------------------------------------------------------
# Dashboard
# ---------------------------------------------------------

df = pd.DataFrame(opportunities)

if "product_fit" not in df.columns:
    df["product_fit"] = "Low"

if "competitors_mentioned" not in df.columns:
    df["competitors_mentioned"] = [[] for _ in range(len(df))]

if "intent_score" not in df.columns:
    df["intent_score"] = 0


st.divider()

st.subheader("Growth Intelligence Dashboard")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "Signals Found",
        len(df),
    )

with col2:
    high_intent = len(df[df["intent_score"] >= 80])

    st.metric(
        "High Intent",
        high_intent,
    )

with col3:
    average_intent = int(df["intent_score"].mean())

    st.metric(
        "Average Intent",
        average_intent,
    )

with col4:
    high_fit = len(df[df["product_fit"] == "High"])

    st.metric(
        "High Product Fit",
        high_fit,
    )


st.divider()


# ---------------------------------------------------------
# Top opportunities table
# ---------------------------------------------------------

st.subheader("Top Growth Opportunities")

display_columns = [
    "intent_score",
    "source",
    "buying_stage",
    "pain_point",
    "competitors_mentioned",
    "product_fit",
    "recommended_action",
]

available_display_columns = [
    column for column in display_columns if column in df.columns
]

st.dataframe(
    df[available_display_columns],
    width="stretch",
    hide_index=True,
)

csv_data = df.to_csv(index=False).encode("utf-8")

st.download_button(
    label="Download Opportunities as CSV",
    data=csv_data,
    file_name="signalhunter_opportunities.csv",
    mime="text/csv",
)


st.divider()


# ---------------------------------------------------------
# Opportunity details
# ---------------------------------------------------------

st.subheader("Opportunity Intelligence")

selected_index = st.selectbox(
    "Select an opportunity",
    options=range(len(opportunities)),
    format_func=lambda index: (
        f'{opportunities[index].get("intent_score", 0)}/100 — '
        f'{opportunities[index].get("pain_point", "Unknown pain point")}'
    ),
)

opportunity = opportunities[selected_index]

left, right = st.columns(2)

with left:
    st.metric(
        "Intent Score",
        opportunity.get("intent_score", 0),
    )

    st.write(
        "**Buying Stage:**",
        opportunity.get("buying_stage", "Unknown"),
    )

    st.write(
        "**Pain Point:**",
        opportunity.get("pain_point", "Unknown"),
    )

    competitors = opportunity.get("competitors_mentioned", [])

    st.write(
        "**Competitors Mentioned:**",
        ", ".join(competitors) if competitors else "None detected",
    )

    st.write(
        "**Product Fit:**",
        opportunity.get("product_fit", "Low"),
    )

with right:
    st.write("**Recommended Action**")

    st.info(
        opportunity.get("recommended_action", "Monitor")
    )

    st.write("**Suggested Angle**")

    st.write(
        opportunity.get(
            "suggested_angle",
            "No suggested angle available.",
        )
    )


with st.expander("Why SignalHunter flagged this"):
    st.write(
        opportunity.get("reasoning", "No reasoning available.")
    )

    st.write("**Original Conversation**")

    st.write(
        opportunity.get("conversation", "No conversation text available.")
    )

    if opportunity.get("url"):
        st.link_button(
            "Open Original Source",
            opportunity["url"],
        )


st.divider()


# ---------------------------------------------------------
# Growth experiment generator
# ---------------------------------------------------------

st.subheader("Growth Experiment")

st.write(
    "Generate a small, fast organic growth experiment based on the selected signal."
)

if st.button(
    "Generate Growth Experiment",
    type="secondary",
):
    try:
        with st.spinner("Designing a rapid growth experiment..."):
            experiment = generate_experiment(
                opportunity=opportunity,
                product_profile=product_profile,
            )

        st.write("### Hypothesis")
        st.write(experiment.get("hypothesis", ""))

        st.write("### Channel")
        st.write(experiment.get("channel", ""))

        st.write("### Experiment")
        st.write(experiment.get("experiment", ""))

        st.write("### Success Metric")
        st.write(experiment.get("success_metric", ""))

        st.write("### Duration")
        st.write(experiment.get("duration", ""))

        st.write("### Next Action")
        st.success(experiment.get("next_action", ""))

    except Exception as exc:
        st.error(f"Experiment generation failed: {exc}")