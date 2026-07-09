from analyzer import analyze_conversation


conversation = """
Our support team currently uses Zendesk.

We've been looking at Intercom Fin but the pricing becomes
difficult at our ticket volume. We also don't want to migrate
our entire customer support stack.

Are there any AI support platforms that work with existing
systems?
"""


result = analyze_conversation(
    title="Alternatives to Intercom Fin?",
    text=conversation,
    source="Reddit",
    url="https://example.com/test",
)

print(result)