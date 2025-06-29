import streamlit as st
import requests
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MINDSDB_API_URL = "http://127.0.0.1:47334"

def query_chatbot(question):
    """Query chatbot via direct HTTP call."""
    url = f"{MINDSDB_API_URL}/api/projects/mindsdb/agents/military_doctrine_chatbot/completions"
    payload = {
        "messages": [
            {"question": question, "answer": None}
        ]
    }
    headers = {"Content-Type": "application/json"}

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=15)
        response.raise_for_status()
        return response.json()["message"]["content"]
    except Exception as e:
        logger.error(f"HTTP chatbot error: {e}")
        return f"❌ Chatbot unavailable. Reason: {e}"

@st.cache_data
def fetch_kb_doctrine_combinations():
    """Fetch (country, warfare_type) combos from military_kb via SDK."""
    try:
        import mindsdb_sdk
        import pandas as pd
        
        server = mindsdb_sdk.connect()
        project = server.get_project()
        results = project.query("""
            SELECT DISTINCT 
                REPLACE(REPLACE(JSON_EXTRACT(metadata, '$.country'), '"', ''), "'", '') AS country,
                REPLACE(REPLACE(JSON_EXTRACT(metadata, '$.warfare_type'), '"', ''), "'", '') AS warfare_type
            FROM military_kb
        """).fetch()

        # Handle DataFrame result
        if isinstance(results, pd.DataFrame):
            if results.empty:
                return []
            return [f"{row['country']} - {row['warfare_type']}" for _, row in results.iterrows()]
        
        # Handle other result types (list/dict) if needed
        elif not results:
            return []
        elif isinstance(results[0], dict):
            return [f"{row['country']} - {row['warfare_type']}" for row in results]
        elif isinstance(results[0], list):
            return [f"{row[0]} - {row[1]}" for row in results]
        else:
            raise ValueError("Unsupported result format.")

    except Exception as e:
        logger.warning(f"Could not load doctrine combos: {e}")
        return []


# Streamlit UI
st.set_page_config(page_title="Military Doctrine Chatbot", layout="wide")
st.title("🪖 Military Strategy Analyst")

# Sidebar with live doctrine filter
with st.sidebar:
    st.title("Manage Doctrines")
    st.header("🔍Check Doctrine")
    kb_combos = fetch_kb_doctrine_combinations()
    doctrine_choice = st.selectbox("Available Doctrines", ['All'] + kb_combos)

# User input
question = st.text_input(
    "Ask about military doctrines, strategies, or comparisons:",
    "Compare the naval strategies of China and America"
)

# Normalize aliases like "USA" → "America"
COUNTRY_ALIASES = {
    "USA": "America",
    "United States": "America",
    "United States of America": "America"
}
for alias, real in COUNTRY_ALIASES.items():
    if alias.lower() in question.lower():
        question = question.replace(alias, real)

# If doctrine selected, append to question
if doctrine_choice != "All":
    question += f" (Focus on {doctrine_choice})"

# Chatbot response
if st.button("Analyze"):
    with st.spinner("Consulting military databases..."):
        response = query_chatbot(question)

    st.subheader("📘 Strategic Analysis")
    st.markdown(response)
    st.caption("Data and strategy powered by MindsDB + Streamlit.")
