import streamlit as st
from lyzr import ChatBot

FOLDER_NAME = "raw_data_files"

st.sidebar.markdown(
    """
    # Chatbot Page
    ## Chat with base research data of all competitors
    Powered by [Lyzr Chatbot](https://lyzrinc.mintlify.app/pre-built-agents/rag-powered-agents/chat-agent/quick-start)
"""
)

chatbot = ChatBot.txt_chat(input_dir=FOLDER_NAME, recursive=True)

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

prompt = st.chat_input("Ask a question")
if prompt:
    st.chat_message("user").markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})
    response = chatbot.chat(prompt).response
    with st.chat_message("assistant"):
        st.markdown(response)
    st.session_state.messages.append({"role": "assistant", "content": response})
