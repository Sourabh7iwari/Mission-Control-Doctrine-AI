import streamlit as st
import mysql.connector

st.set_page_config(page_title="🧠 Wartime Strategy Chatbot")
st.title("🧠 Wartime Strategy Chatbot")
st.write("Ask about military doctrines and strategies")

# Connect to MindsDB
def connect_mindsdb():
    return mysql.connector.connect(
        host="localhost",
        port=47335,
        user="mindsdb",
        password=""
    )

# Query KB
def query_kb(question, country):
    conn = connect_mindsdb()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute(f"""
            SELECT * FROM military_kb 
            WHERE strategy_text = '{question}' 
              AND country = '{country}'
        """)
        results = cursor.fetchall()
    except Exception as e:
        results = []
        st.error(f"Query failed: {e}")
    finally:
        cursor.close()
        conn.close()

    return results

# UI Inputs
question = st.text_input("Enter your question:", "What is hybrid warfare?")
country_filter = st.selectbox("Filter by Country", ["Russia", "India", "China"])

if st.button("Search"):
    response = query_kb(question, country_filter)

    st.subheader("Results:")
    if response:
        for row in response:
            st.markdown(f"**Country:** {row['metadata']['country']}")
            st.markdown(f"**Strategy:** {row['chunk_content']}")
            st.markdown(f"**Relevance:** {row['relevance']}")
            st.markdown("---")
    else:
        st.warning("No matching strategy found.")