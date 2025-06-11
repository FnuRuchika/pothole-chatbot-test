import sys
import os

# Let Streamlit find the chatbot module
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import streamlit as st
from chatbot.handler import handle_query

# Page settings
st.set_page_config(page_title="Chatbot Demo", layout="centered")
st.title("Hi! I’m Patchy the Pothole Bot. How can I help you today?")

# Initialize chat history
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []

# Chat input form
with st.form(key='chat_form', clear_on_submit=True):
    query = st.text_input("Your question:", placeholder="e.g., Are there potholes near UTSA?")
    submit = st.form_submit_button("Send")

# Process user input
if submit and query:
    response = handle_query(query)
    st.session_state.chat_history.append(("You", query))
    st.session_state.chat_history.append(("Bot", response))

# Display chat history
for sender, message in st.session_state.chat_history:
    if sender == "You":
        st.markdown(f"**🧑‍💬 You:** {message}")
    else:
        st.markdown(f"**🤖 Bot:** {message}")
