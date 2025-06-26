import streamlit as st
import plotly.express as px
import pandas as pd
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from chatbot.handler import handle_query  # chatbot logic

# Load data
DATA_PATH = "data"
df_311 = pd.read_csv(f"{DATA_PATH}/311_Data_Cleaned.csv")
df_311['OPENEDDATETIME'] = pd.to_datetime(df_311['OPENEDDATETIME'], errors='coerce')
df_311['Year'] = df_311['OPENEDDATETIME'].dt.year

st.set_page_config(layout="wide")  # Allow wide layout

# Title
st.title("🚧 San Antonio Pothole Assistant")

# Side-by-side layout
col1, col2 = st.columns([1, 2])  # 1/3 for chatbot, 2/3 for dashboard

# -------------------------------
# 💬 Chatbot
# -------------------------------
with col1:
    st.subheader("💬 Chatbot")
    query = st.text_input("Ask something like:")
    st.caption("e.g., 'Top 10 streets with potholes', 'How long does it take to fix?', 'UTSA potholes'")
    if query:
        with st.spinner("Thinking..."):
            response = handle_query(query)
            st.success(response)

# -------------------------------
# 📊 Dashboard
# -------------------------------
with col2:
    st.subheader("📊 Pothole Complaint Dashboard")

    # Filter by year
    years = sorted(df_311['Year'].dropna().unique())
    selected_year = st.selectbox("Select Year", years, key="year_select")
    df_filtered = df_311[df_311['Year'] == selected_year]

    # Top 10 streets
    top_streets = df_filtered['SUBJECTNAME'].value_counts().head(10).reset_index()
    top_streets.columns = ['Street', 'Complaints']
    fig = px.bar(top_streets, x='Street', y='Complaints', title=f"Top 10 Streets with Most Complaints ({selected_year})")
    st.plotly_chart(fig, use_container_width=True)

    # Complaint trend
    trend = df_311['Year'].value_counts().sort_index().reset_index()
    trend.columns = ['Year', 'Total Complaints']
    fig2 = px.line(trend, x='Year', y='Total Complaints', markers=True, title="Pothole Complaint Trend Over Years")
    st.plotly_chart(fig2, use_container_width=True)
