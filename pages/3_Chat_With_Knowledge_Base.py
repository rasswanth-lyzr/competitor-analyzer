import os
import time

import streamlit as st
from dotenv import load_dotenv

from chatbot_helper import (
    chat_with_chatbot,
    convert_txt_to_pdf,
    create_conversation,
    create_new_chatbot,
    find_files,
    train_chatbot,
)

load_dotenv()
FOLDER_NAME = "raw_data_files"
USER_ID = os.getenv("USER_ID")

st.set_page_config(layout="wide", page_title="Alan - The Business Analyst")

st.sidebar.markdown(
    """
    ## Chat with research data of all competitors
    Powered by [Lyzr Chatbot](https://lyzrinc.mintlify.app/pre-built-agents/rag-powered-agents/chat-agent/quick-start)
"""
)

st.header("Chat with Research Data")


@st.cache_data
def initialize_chatbot():
    chatbot_id = create_new_chatbot()
    # USER_ID = create_user()
    time.sleep(10)
    pdf_files = find_files()
    time.sleep(10)
    train_chatbot(chatbot_id, pdf_files)
    conversation_id = create_conversation(USER_ID, chatbot_id)
    return chatbot_id, conversation_id


convert_txt_to_pdf()
chatbot_id, conversation_id = initialize_chatbot()

with st.sidebar:
    st.markdown("### *To retrain the chatbot, click here*")
    retrain = st.button("Retrain", type="primary")
    if retrain:
        pdf_files = find_files()
        train_chatbot(chatbot_id, pdf_files)

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

prompt = st.chat_input("Ask a question")
if prompt:
    st.chat_message("user").markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})
    response = chat_with_chatbot(conversation_id, prompt)
    with st.chat_message("assistant"):
        st.markdown(response)
    st.session_state.messages.append({"role": "assistant", "content": response})
