import datetime
import json
import os
import re

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from lyzr_automata import Agent, Task
from lyzr_automata.ai_models.openai import OpenAIModel
from lyzr_automata.ai_models.perplexity import PerplexityModel
from lyzr_automata.memory.open_ai import OpenAIMemory
from lyzr_automata.tasks.task_literals import InputType, OutputType

from database import (
    base_research_collection,
    competitors_list_collection,
    metrics_collection,
    news_collection,
)

st.set_page_config(layout="wide", page_title="Alan - The Business Analyst")

st.sidebar.title("Try Alan’s Capabilities")
st.sidebar.markdown(
    "<small>Alan can do a thorough research about your customer or competitor and generate a detailed report, on a daily or weekly basis. Alan looks up information in the internet (powered by Perplexity), news (powered by Google news) and also scraps their website.</small>",
    unsafe_allow_html=True,
)
st.sidebar.markdown(
    "Learn more about [Alan](https://www.lyzr.ai/book-demo/)", unsafe_allow_html=True
)

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")

FOLDER_NAME = "raw_data_files"

# FUNCTIONS
open_ai_model_text = OpenAIModel(
    api_key=OPENAI_API_KEY,
    parameters={
        "model": "gpt-4-turbo-preview",
        "temperature": 0.2,
        "max_tokens": 1500,
    },
)

perplexity_model_text = PerplexityModel(
    api_key=PERPLEXITY_API_KEY,
    parameters={
        "model": "llama-3-sonar-small-32k-online",
    },
)


def process_data(row, competitors_list_document_id):
    metrics_dict = st.session_state.metrics_dict
    metrics_list_keys = list(metrics_dict.keys())
    metrics_list_keys = list(metrics_dict.values())
    competitor_name = row["competitor_name"]
    base_research_document_id = row["id"]
    website = row["website"]
    email_report = write_email_report(competitor_name)
    # email_report = """<!DOCTYPE html> <html> <head> <title>Cohere Competitor Analysis Digest</title> <style> body {font-family: Arial, sans-serif; margin: 0; padding: 20px; color: #333;} h1, h2 {color: #0056b3;} ul {list-style-type: none; padding: 0;} li {margin-bottom: 10px;} .section {margin-bottom: 20px;} </style> </head> <body> <div class="email-content"> <h1>Competitor Analysis Digest: Cohere</h1> <div class="section"> <h2>Topic Overview</h2> <p>This digest provides a comprehensive summary of the latest strategic developments, financial performance, product innovations, regulatory changes, leadership shifts, and industry trends related to Cohere. As a competitor, staying informed of these updates is crucial for strategic planning and market positioning.</p> </div> <div class="section"> <h2>Key Events or Updates</h2> <ul> <li><strong>Strategic Developments:</strong> Cohere Health has successfully raised $50 million in equity funding to expand its intelligent prior authorization platform. Additionally, the company has broadened its partnership with Humana to encompass diagnostic imaging and sleep services.</li> <li><strong>Financial Performance:</strong> Cohere has impressively raised $500 million in funding, reaching a valuation of $5 billion. The company's annual revenue run rate has also seen a significant increase, rising to $22 million from $13 million in December.</li> <li><strong>Product Innovations and Launches:</strong> The launch of Command-R, aimed at competing with ChatGPT, and the Coral knowledge assistant, signifies Cohere's commitment to innovation and addressing market needs.</li> <li><strong>Regulatory and Legal Changes:</strong> The finalized Interoperability and Prior Authorization rule by the Centers for Medicare & Medicaid Services mandates health plans to adopt advanced technology, impacting Cohere's operational focus.</li> <li><strong>Leadership Changes:</strong> CEO Aidan Gomez has publicly criticized the effective altruism movement, indicating a potential shift in the company's cultural or ethical stance.</li> <li><strong>Industry Trends and Analysis:</strong> Cohere's AI technology is not only improving patient access to care but also positioning the company as a formidable competitor in the AI and healthcare sectors.</li> </ul> </div> <div class="section"> <h2>Takeaways</h2> <ul> <li>Cohere's recent funding and strategic partnerships underscore its growth trajectory and expanding market influence.</li> <li>The company's innovation in AI and healthcare solutions, such as Command-R and Coral, highlights its commitment to leading in technology advancements.</li> <li>Regulatory changes and Cohere's response to them may affect the competitive landscape, requiring close monitoring.</li> <li>Leadership perspectives and industry trends suggest a dynamic shift in strategies that could impact competitor approaches.</li> </ul> </div> </div> </body> </html>"""
    save_email_report(
        competitor_name,
        email_report,
        base_research_document_id,
        competitors_list_document_id,
    )
    metrics_data_raw = get_metrics_data(
        competitor_name, website, metrics_list_values, metrics_list_keys
    )
    metrics_data = parse_json_output(metrics_data_raw)
    # metrics_data = {
    #     "website": "http://www.microsoft.com",
    #     "sector": "Technology",
    #     "industry": "Software and Video Games",
    #     "location": "Redmond, Washington, USA",
    #     "number_of_employees": 221000,
    #     "founding_year": 1975,
    #     "company_type": "Public",
    #     "market_cap": None,
    #     "annual_revenue": "US$110.36 billion (2018)",
    #     "linkedin_url": None,
    #     "tagline": "Empower every person and every organization on the planet to achieve more.",
    #     "stock_ticker": "MSFT",
    #     "competitor_name": "Microsoft",
    # }
    save_metrics_data_database(
        metrics_data,
        competitor_name,
        base_research_document_id,
        competitors_list_document_id,
    )
    save_metrics_data_file(metrics_data, competitor_name)
    return None


def convert_field_name_advanced(field_name):
    field_name = field_name.lower()
    field_name = re.sub(r"[^a-z0-9]", "_", field_name)
    field_name = re.sub(r"__+", "_", field_name)
    field_name = field_name.strip("_")
    return field_name


def parse_json_output(json_object):
    try:
        data_dict = json.loads(json_object.replace("'", '"'))
        return data_dict
    except json.JSONDecodeError:
        return {}


def get_metrics_data(competitor_name, website, metrics_list_values, metrics_list_keys):
    metrics_parsing_agent = Agent(
        prompt_persona="You are intelligent agent that can process raw text data into structured JSON format. Please provide the information in plain JSON format without any additional characters or markdown. Return ONLY the JSON object. If a matching value for a key is not found, let the value be None.",
        role="Metrics Parser",
    )

    search_task = Task(
        name="Metrics data search",
        output_type=OutputType.TEXT,
        input_type=InputType.TEXT,
        model=perplexity_model_text,
        instructions=f"I need recent and updated information about the company {competitor_name} - {website}. Please search and provide comprehensive insights based on the following details required: {metrics_list_values}.",
        log_output=True,
    ).execute()

    metrics_parsing_task = Task(
        name="Metrics Parsing Task",
        agent=metrics_parsing_agent,
        output_type=OutputType.TEXT,
        input_type=InputType.TEXT,
        model=open_ai_model_text,
        instructions=f"Use the company information provided and return the information as a JSON object with keys for : {metrics_list_keys}",
        log_output=True,
        enhance_prompt=False,
        previous_output=search_task,
        input_tasks=[search_task],
    ).execute()

    return metrics_parsing_task


def write_email_report(company_name):
    memory_file_path = f"raw_data_files/{company_name}.txt"
    email_writer_memory = OpenAIMemory(file_path=memory_file_path)

    email_writer_agent = Agent(
        prompt_persona="""You are intelligent agent that can generate a comprehensive summary using the latest information provided about a company. Ensure the summary is organized, succinct, and tailored to the specified audience. Use clear section headings and maintain the requested tone throughout the document.
        Target Audience - Competitor of the company
        Tone and Style - Formal and informative
        Summary Format - 
        1. Company Name: [Name of the Company]
        2. Key Events:
        Article 1: [Title]
        [Published Date]
        [2 bullet points to summarize article 1]
        Article 2: [Title]
        [Published Date]
        [2 bullet points to summarize article 2]
        ...
        3. General Research: [Summary of General Research]
        4. Specific Research: [Summary of Specific Reseach]
        """,
        role="Competitor Analyst",
        memory=email_writer_memory,
    )

    content_writer_task = Task(
        name="Competitor Analyst Task",
        agent=email_writer_agent,
        output_type=OutputType.TEXT,
        input_type=InputType.TEXT,
        model=open_ai_model_text,
        instructions=f"Use the articles provided about the company {company_name} and write a summary for each and every article. Each article starts with 'Title:', followed by the content. If Specific Research or General Research is present, write a summary about them. If Specific Research or General Research is NOT present, do not generate anything. Send the response in text without any markdown. Use bullets for points and beautify it be as creative as you want",
        log_output=True,
        enhance_prompt=False,
    ).execute()

    return content_writer_task


def save_email_report(
    competitor_name,
    email_report,
    base_research_document_id,
    competitors_list_document_id,
):
    news_document = {
        "competitor_name": competitor_name,
        "email_report": email_report,
        "base_research_document_id": base_research_document_id,
        "competitors_list_document_id": competitors_list_document_id,
        "created_at": datetime.datetime.now(datetime.UTC),
    }

    news_collection.insert_one(news_document)


def save_metrics_data_database(
    metrics_data,
    competitor_name,
    base_research_document_id,
    competitors_list_document_id,
):
    metric_document = metrics_data.copy()
    metric_document["competitor_name"] = competitor_name
    metric_document["base_research_document_id"] = base_research_document_id
    metric_document["competitors_list_document_id"] = competitors_list_document_id
    metric_document["created_at"] = datetime.datetime.now(datetime.UTC)
    metrics_collection.insert_one(metric_document)


def save_metrics_data_file(metrics_data, competitor_name):
    FILE_NAME = os.path.join(FOLDER_NAME, competitor_name + ".txt")
    metrics_dict = st.session_state.metrics_dict
    with open(FILE_NAME, "a") as my_file:
        my_file.write(f"\n\nMetrics about the company {competitor_name}:\n")
        for key, value in metrics_data.items():
            if key in list(metrics_dict.keys()):
                my_file.write(metrics_dict[key] + ": " + str(value) + "\n")
            else:
                my_file.write(key + ": " + str(value) + "\n")


# STREAMLIT COMPONENTS
try:
    document_id = st.session_state["document_id"]
except:
    st.error("Please complete Initiate Research step!")
    st.stop()

st.header("View your research data")

result1 = competitors_list_collection.find_one({"_id": document_id})
competitors_list = result1["generated_competitors_list"]

result2 = base_research_collection.find(
    {"competitors_list_document_id": document_id},
    {"raw_data": 1, "competitor_name": 1},
)

object_id_column = []
competitor_name_column = []
raw_data_column = []
website_column = []

for item in result2:
    object_id_column.append(item["_id"])
    competitor_name_column.append(item["competitor_name"])
    raw_data_column.append(item["raw_data"])
    website_column.append(competitors_list[item["competitor_name"]])

dataframe_dict = {
    "id": object_id_column,
    "competitor_name": competitor_name_column,
    "website": website_column,
    "raw_data": raw_data_column,
}
df = pd.DataFrame(dataframe_dict)
df.index = df.index + 1
st.dataframe(df, column_config={"id": None})

st.write("## Generate report for")
generate_report_list = st.multiselect(
    "Generate Report for", options=competitor_name_column, label_visibility="collapsed"
)

fields = [
    "Website URL",
    "Sector",
    "Industry",
    "Location",
    "Number of Employees",
    "Founding Year",
    "Company Type",
    "Market Cap",
    "Annual Revenue",
    "LinkedIn URL",
    "Tagline",
    "Stock Ticker",
]
st.write("## Select required metrics")
metrics_list_values = [field for field in fields if st.checkbox(field, value=True)]

report_button = st.button("Generate report")
if report_button:
    if metrics_list_values:
        metrics_dict = {}
        for name in metrics_list_values:
            key_value = convert_field_name_advanced(name.strip())
            metrics_dict[key_value] = name.strip()

        st.session_state.metrics_dict = metrics_dict
    else:
        st.error("No fields selected.")
    filtered_dataframe = df[df["competitor_name"].isin(generate_report_list)]
    filtered_dataframe.apply(
        process_data,
        axis=1,
        args=(document_id,),
    )

    st.write(
        """
        # Report generated! :sparkles:
        ### Go to :red[Access Reports] Page"""
    )
    st.page_link("pages/2_Access_Reports.py", label="Access Reports", icon="📁")
    st.write("### To chat with the data, go to :red[Chat With Knowledge Base] page")
    st.page_link(
        "pages/3_Chat_With_Knowledge_Base.py",
        label="Chat With Knowledge Base",
        icon="🤖",
    )
