import json
import os
import textwrap
import uuid

import requests
import streamlit as st
from dotenv import load_dotenv
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
CHATBOT_BEARER_TOKEN = os.getenv("CHATBOT_BEARER_TOKEN")
BASE_URL = os.getenv("BASE_URL")
USER_ID = os.getenv("USER_ID")
VECTOR_STORE_URL = os.getenv("VECTOR_STORE_URL")
VECTOR_STORE_API_KEY = os.getenv("VECTOR_STORE_API_KEY")

HEADERS = {"Authorization": f"Bearer {CHATBOT_BEARER_TOKEN}"}

try:
    company_name_input = st.session_state.company_name
except:
    st.error("Please complete Initiate Research and Generate Report step!")
    st.stop()


def generate_new_uuid():
    new_uuid = uuid.uuid4()
    return new_uuid.hex


def create_new_chatbot():
    chatbot_config = {
        "name": f"{company_name_input} Chatbot",
        "description": f"A chatbot for the report for the company {company_name_input}",
        "configuration": {
            "exclude_hidden": True,
            "filename_as_id": True,
            "recursive": True,
            "required_exts": ["string"],
            "system_prompt": "Answer every question in under 100 words",
            "embed_model": {
                "embedding_type": "OpenAIEmbedding",
                "model": "text-embedding-ada-002",
                "api_key": OPENAI_API_KEY,
            },
            "llm_params": {
                "model": "gpt-4-1106-preview",
                "api_key": OPENAI_API_KEY,
                "stream": False,
            },
            "vector_store_params": {
                "vector_store_type": "WeaviateVectorStore",
                "url": VECTOR_STORE_URL,
                "api_key": VECTOR_STORE_API_KEY,
                "index_name": company_name_input.upper() + generate_new_uuid(),
            },
            "service_context_params": {},
            "chat_engine_params": {
                "chat_mode": "context",
                "similarity_top_k": 50,
                "system_prompt": "You are a helpful Assistant",
            },
            "retriever_params": {"retriever_type": "Simple"},
        },
    }
    response = requests.post(
        f"{BASE_URL}/chatbot/", json=chatbot_config, headers=HEADERS
    )
    response.raise_for_status()
    chatbot_info = response.json()
    print(chatbot_info)
    return chatbot_info["details"]["id"]


def find_files(folder_path="raw_data_files"):
    pdf_files = []
    for filename in os.listdir(folder_path):
        if filename.endswith(".pdf"):
            file_path = os.path.join(folder_path, filename)
            pdf_files.append(
                ("files", (filename, open(file_path, "rb"), "application/pdf"))
            )

    return pdf_files


def read_text_file(file_path):
    with open(file_path, "r") as file:
        content = file.read()
    return content


def write_pdf(file_path, text, max_width=80):
    c = canvas.Canvas(file_path, pagesize=letter)
    width, height = letter
    y_position = height - 40
    line_height = 12
    wrapped_text = textwrap.fill(text, max_width)

    for line in wrapped_text.split("\n"):
        if y_position < line_height:
            c.showPage()
            y_position = height - 40
        c.drawString(40, y_position, line)
        y_position -= line_height

    c.save()


def convert_txt_to_pdf(folder_path="raw_data_files"):
    for filename in os.listdir(folder_path):
        if filename.endswith(".txt"):
            text_file_path = os.path.join(folder_path, filename)
            pdf_filename = filename.split(".")[0] + ".pdf"
            pdf_file_path = os.path.join(folder_path, pdf_filename)
            text_content = read_text_file(text_file_path)
            write_pdf(pdf_file_path, text_content)


def train_chatbot(chatbot_id, pdf_files):
    response = requests.post(
        f"{BASE_URL}/train/from-pdf/{chatbot_id}", files=pdf_files, headers=HEADERS
    )
    response.raise_for_status()
    training_status = response.json()
    print(f"Training Status: {training_status}")
    return training_status


def create_user():
    user_data = {"name": "Rasswanth", "email": "rasswanth@lyzr.ai"}

    response = requests.post(f"{BASE_URL}/users/", json=user_data, headers=HEADERS)
    response.raise_for_status()
    user_info = response.json()
    print(f"User Info: {user_info}")

    return user_info["details"]["id"]


def create_conversation(user_id, chatbot_id):
    response = requests.post(
        f"{BASE_URL}/conversations/",
        json={"user_id": user_id, "chatbot_id": chatbot_id},
        headers=HEADERS,
    )
    response.raise_for_status()
    conversation_info = response.json()
    print(f"Conversation Info: {conversation_info}")

    return conversation_info["details"]["id"]


def chat_with_chatbot(conversation_id, user_input=""):
    response = requests.post(
        f"{BASE_URL}/cchat/{conversation_id}",
        params={"input_message": user_input},
        headers=HEADERS,
    )
    response.raise_for_status()
    chat_response = response.json()
    print(f"Chatbot Response: {chat_response}")
    return chat_response["details"]["response"]
