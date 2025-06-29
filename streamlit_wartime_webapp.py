import streamlit as st
import requests
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)



def query_chatbot(question):
    """Query chatbot via direct HTTP call."""
    url = "http://127.0.0.1:47334/api/projects/mindsdb/agents/military_doctrine_chatbot/completions"
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


st.set_page_config(page_title="Military Doctrine Chatbot", layout="wide")
st.title("🪖 Military Strategy Analyst")

# Right now simple defualt options later dynamically load from database
with st.sidebar:
    st.header("🔍 Context Filters")
    country = st.selectbox("Country Focus", ['All', 'America', 'Russia', 'China', 'India', 'Japan'])
    warfare_type = st.selectbox("Warfare Type", ['All', 'Naval', 'Air', 'Cyber', 'Hybrid'])

question = st.text_input(
    "Ask about military doctrines, strategies, or comparisons:",
    "Compare the naval strategies of China and America"
)

COUNTRY_ALIASES = {
    "USA": "America",
    "United States": "America",
    "United States of America": "America"
}

for alias, real_name in COUNTRY_ALIASES.items():
    if alias.lower() in question.lower():
        question = question.replace(alias, real_name)

if st.button("Analyze"):
    with st.spinner("Consulting military databases..."):
        
        if country != 'All':
            question += f" (Focus on {country})"
        if warfare_type != 'All':
            question += f" regarding {warfare_type} warfare"
        
        response = query_chatbot(question)

    st.subheader("📘 Strategic Analysis")
    st.markdown(response)

    st.caption("Data and strategy powered by MindsDB + Streamlit.")
