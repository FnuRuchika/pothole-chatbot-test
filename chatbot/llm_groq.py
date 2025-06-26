# chatbot/llm_groq.py

import streamlit as st
from groq import Groq

client = Groq(api_key=st.secrets["GROQ_API_KEY"])

def ask_groq(query, context=None):
    messages = [{"role": "system", "content": "You are a helpful chatbot that answers questions about potholes in San Antonio."}]
    if context:
        messages.append({"role": "assistant", "content": context})
    messages.append({"role": "user", "content": query})

    try:
        response = client.chat.completions.create(
            model="llama3-8b-8192",
            messages=messages,
            temperature=0.4,
            max_tokens=300
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"⚠️ Error using Groq: {e}"

