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

from databricks_pipeline import trigger_lakehouse_pipeline
from databricks_data import load_gold_opportunities_from_databricks


st.set_page_config(
    page_title="SignalHunter",
    page_icon="📡",
    layout="wide",
)


# ---------------------------------------------------------
# Config
# ---------------------------------------------------------

SHOW_TECHNICAL_DETAILS = False


# ---------------------------------------------------------
# Helper functions
# ---------------------------------------------------------

def text_to_list(text: str) -> list[str]:
    """Convert comma-separated text into a cleaned list."""

    return [
        item.strip()
        for item in text.split(",")
        if item.strip()
    ]


def normalize_old_results(opportunities: list[dict]) -> list[dict]:
    """
    Normalize local and Databricks results.

    Handles:
    - typewise_fit -> product_fit
    - source_url -> url
    - missing conversation
    - competitors_mentioned as string/list
    """

    for opportunity in opportunities:
        if "product_fit" not in opportunity:
            opportunity["product_fit"] = opportunity.get(
                "typewise_fit",
                "Low",
            )

        if "url" not in opportunity and "source_url" in opportunity:
            opportunity["url"] = opportunity.get("source_url", "")

        if "conversation" not in opportunity:
            opportunity["conversation"] = opportunity.get(
                "cleaned_text",
                "Conversation text is stored in the source data layer.",
            )

        competitors = opportunity.get("competitors_mentioned", [])

        if isinstance(competitors, str):
            competitors = competitors.strip()

            if competitors.startswith("[") and competitors.endswith("]"):
                competitors = (
                    competitors.replace("[", "")
                    .replace("]", "")
                    .replace("'", "")
                    .replace('"', "")
                )

            opportunity["competitors_mentioned"] = [
                item.strip()
                for item in competitors.split(",")
                if item.strip()
            ]

        if "recommended_action" not in opportunity:
            opportunity["recommended_action"] = "Monitor"

        if "suggested_angle" not in opportunity:
            opportunity["suggested_angle"] = "No suggested angle available."

        if "reasoning" not in opportunity:
            opportunity["reasoning"] = "No reasoning available."

        if "source" not in opportunity:
            opportunity["source"] = "Unknown"

        if "buying_stage" not in opportunity:
            opportunity["buying_stage"] = "Unknown"

        if "pain_point" not in opportunity:
            opportunity["pain_point"] = "Unknown pain point"

        if "intent_score" not in opportunity:
            opportunity["intent_score"] = 0

    return opportunities


def run_signal_pipeline(
    product_profile: dict,
    max_videos: int = 3,
) -> list[dict]:
    """
    Local fallback pipeline.

    This is mainly for development. The public app uses the Databricks-backed
    fresh analysis flow through trigger_lakehouse_pipeline().
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


def get_sample_opportunities() -> list[dict]:
    """
    Sample fallback data for instant demo experience.

    Used when no saved opportunities exist yet.
    """

    return [
        {
            "intent_score": 88,
            "source": "YouTube",
            "buying_stage": "Active Evaluation",
            "pain_point": "Looking for alternatives to existing AI wellbeing tools",
            "competitors_mentioned": ["Wysa", "Woebot"],
            "product_fit": "High",
            "recommended_action": "Create Content",
            "suggested_angle": "Create a comparison-style post about AI burnout detection tools for HR teams.",
            "reasoning": (
                "The conversation suggests interest in AI wellbeing tools and alternatives. "
                "This indicates a strong opportunity to educate users about burnout detection, "
                "voice journaling, and workplace stress signals."
            ),
            "conversation": (
                "We are exploring AI wellbeing tools for employees but most apps feel generic. "
                "Are there better alternatives to Wysa or Woebot for workplace burnout?"
            ),
            "url": "https://youtube.com",
        },
        {
            "intent_score": 76,
            "source": "YouTube",
            "buying_stage": "Research",
            "pain_point": "Concern about employee burnout and workplace stress",
            "competitors_mentioned": [],
            "product_fit": "Medium",
            "recommended_action": "Educational Response",
            "suggested_angle": "Explain how voice journaling can help identify burnout patterns earlier.",
            "reasoning": (
                "The user is discussing workplace stress and employee burnout. "
                "The buying intent is not direct yet, but it is relevant to MochiAI's problem space."
            ),
            "conversation": (
                "Burnout is becoming a big issue in our team. I wish there was a way to understand "
                "stress levels before people completely crash."
            ),
            "url": "https://youtube.com",
        },
        {
            "intent_score": 69,
            "source": "YouTube",
            "buying_stage": "Problem Aware",
            "pain_point": "Managers need better visibility into team stress without invading privacy",
            "competitors_mentioned": [],
            "product_fit": "Medium",
            "recommended_action": "Founder Response",
            "suggested_angle": "Talk about privacy-first burnout signals for teams.",
            "reasoning": (
                "This signal shows a real HR/team management problem. "
                "The person is not asking for a tool yet, but the pain point is aligned with MochiAI."
            ),
            "conversation": (
                "Managers often find out too late that someone is burned out. "
                "But monitoring people directly feels invasive. There should be a better approach."
            ),
            "url": "https://youtube.com",
        },
    ]


def load_demo_results() -> list[dict]:
    """
    Load saved results if available. Otherwise use sample fallback data.
    """

    saved_results = load_opportunities()
    saved_results = normalize_old_results(saved_results)

    if saved_results:
        return saved_results

    return get_sample_opportunities()


# ---------------------------------------------------------
# Session state
# ---------------------------------------------------------

if "pipeline_has_run" not in st.session_state:
    st.session_state.pipeline_has_run = False

if "last_run_opportunities" not in st.session_state:
    st.session_state.last_run_opportunities = []

if "databricks_run_id" not in st.session_state:
    st.session_state.databricks_run_id = None

if "application_run_id" not in st.session_state:
    st.session_state.application_run_id = None

if "analysis_started" not in st.session_state:
    st.session_state.analysis_started = False


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
    st.header("Product Setup")

    st.caption(
        "Tell SignalHunter what you are building so it can find relevant "
        "buyer-intent conversations."
    )

    product_name = st.text_input(
        "Product name",
        value=saved_profile["product_name"],
    )

    category = st.text_input(
        "Category",
        value=saved_profile["category"],
        help=(
            "Example: AI burnout detector, CRM, customer support AI, "
            "project management tool"
        ),
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
        "Search depth",
        min_value=1,
        max_value=5,
        value=1,
        help="Lower is faster. Higher may find more signals.",
    )

    if st.button(
        "Save Product Setup",
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
        st.session_state.databricks_run_id = None
        st.session_state.application_run_id = None
        st.session_state.analysis_started = False

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
    "Find buyer-intent signals before your competitors do."
)

st.write(
    f"Currently analyzing opportunities for **{product_profile['product_name']}**."
)

st.markdown(
    """
    SignalHunter scans public conversations to find people discussing problems,
    comparing competitors, asking for alternatives, or looking for recommendations.
    It turns those conversations into ranked growth opportunities.
    """
)

st.divider()


# ---------------------------------------------------------
# Product flow section
# ---------------------------------------------------------

with st.container():
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("### 1. Enter your product")
        st.write(
            "Add your product, target buyer, competitors, and verified capabilities."
        )

    with col2:
        st.markdown("### 2. Find buyer signals")
        st.write(
            "SignalHunter scans public conversations and detects buyer intent."
        )

    with col3:
        st.markdown("### 3. Take action")
        st.write(
            "Review pain points, competitor mentions, product fit, and suggested growth actions."
        )


st.divider()


# ---------------------------------------------------------
# Optional technical section
# ---------------------------------------------------------

if SHOW_TECHNICAL_DETAILS:
    st.subheader("Technical Architecture")

    st.write(
        "SignalHunter uses a Databricks Lakehouse-style pipeline to process "
        "unstructured public conversations into structured growth intelligence."
    )

    pipeline_col1, pipeline_col2, pipeline_col3 = st.columns(3)

    with pipeline_col1:
        st.markdown("### Bronze")
        st.write("Raw public conversations collected from sources like YouTube.")

    with pipeline_col2:
        st.markdown("### Silver")
        st.write("Cleaned and filtered buyer-intent candidates.")

    with pipeline_col3:
        st.markdown("### Gold")
        st.write("AI-enriched opportunities ready for analytics.")

    st.divider()


# ---------------------------------------------------------
# User-friendly run section
# ---------------------------------------------------------

st.subheader("Find Buyer Signals")

st.write(
    "View demo results instantly, or run a fresh analysis to scan new public conversations."
)

st.warning(
    "Prototype notice: Fresh analysis runs on free/community infrastructure. "
    "It may take a few minutes, and occasional timeouts can happen. "
    "For a faster first look, click **View Demo Results**."
)

run_col1, run_col2 = st.columns([1, 1])

with run_col1:
    if st.button("View Demo Results", type="secondary", width="stretch"):
        demo_opportunities = load_demo_results()
        demo_opportunities = normalize_old_results(demo_opportunities)

        save_opportunities(demo_opportunities)

        st.session_state.pipeline_has_run = True
        st.session_state.last_run_opportunities = demo_opportunities
        st.session_state.analysis_started = False

        st.success(
            f"Loaded {len(demo_opportunities)} demo buyer-intent opportunities."
        )

        st.rerun()

with run_col2:
    if st.button("Run Fresh Analysis", type="primary", width="stretch"):
        with st.spinner(
            "Starting fresh analysis. SignalHunter is scanning conversations..."
        ):
            try:
                databricks_run_id, application_run_id = trigger_lakehouse_pipeline(
                    product_profile=product_profile
                )

                st.session_state.pipeline_has_run = False
                st.session_state.databricks_run_id = databricks_run_id
                st.session_state.application_run_id = application_run_id
                st.session_state.analysis_started = True

                st.success(
                    "Fresh analysis started. Please wait 2–5 minutes, then click Show Results."
                )

            except Exception as exc:
                st.error("SignalHunter could not start fresh analysis.")
                st.exception(exc)


if st.session_state.get("analysis_started"):
    st.info(
        "Fresh analysis is running. This usually takes 2–5 minutes."
    )

    if st.button("Show Results", type="primary"):
        try:
            lakehouse_df = load_gold_opportunities_from_databricks(
                run_id=st.session_state.application_run_id
            )

            if lakehouse_df.empty:
                st.warning(
                    "Results are not ready yet. Please wait a little longer "
                    "and click Show Results again."
                )
            else:
                opportunities = lakehouse_df.to_dict("records")
                opportunities = normalize_old_results(opportunities)

                save_opportunities(opportunities)

                st.session_state.pipeline_has_run = True
                st.session_state.last_run_opportunities = opportunities
                st.session_state.analysis_started = False

                st.success(
                    f"Found {len(opportunities)} buyer-intent opportunities."
                )

                st.rerun()

        except Exception as exc:
            st.error("Could not load results.")
            st.exception(exc)


# ---------------------------------------------------------
# Developer-only local fallback
# ---------------------------------------------------------

if SHOW_TECHNICAL_DETAILS:
    st.divider()

    with st.expander("Developer tools"):
        st.write(
            "Use this only for local testing. Public users should use the main buttons."
        )

        if st.button("Run Local AI Pipeline"):
            with st.spinner("Collecting and analyzing public signals locally..."):
                try:
                    fresh_opportunities = run_signal_pipeline(
                        product_profile=product_profile,
                        max_videos=max_videos,
                    )

                    save_opportunities(fresh_opportunities)

                    st.session_state.pipeline_has_run = True
                    st.session_state.last_run_opportunities = fresh_opportunities

                    st.success(
                        f"Found {len(fresh_opportunities)} opportunities."
                    )

                    st.rerun()

                except Exception as exc:
                    st.error(f"Local pipeline failed: {exc}")


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
        "Set up your product in the sidebar, then click **View Demo Results** "
        "or **Run Fresh Analysis**."
    )

    st.markdown(
        """
        ### What SignalHunter looks for

        SignalHunter searches for conversations where people are:

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

df["intent_score"] = pd.to_numeric(
    df["intent_score"],
    errors="coerce",
).fillna(0).astype(int)


st.divider()

st.subheader("Growth Intelligence Dashboard")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "Opportunities Found",
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

    if isinstance(competitors, str):
        competitors = [
            item.strip()
            for item in competitors.split(",")
            if item.strip()
        ]

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

    source_link = opportunity.get("url") or opportunity.get("source_url")

    if source_link:
        st.link_button(
            "Open Original Source",
            source_link,
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

    except Exception:
        st.error(
            "Could not generate the growth experiment right now. Please try again."
        )