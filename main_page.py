import ast
import datetime
import os
import shutil

import newspaper
import streamlit as st
from dotenv import load_dotenv
from gnews import GNews
from lyzr_automata import Agent, Task
from lyzr_automata.ai_models.openai import OpenAIModel
from lyzr_automata.ai_models.perplexity import PerplexityModel
from lyzr_automata.tasks.task_literals import InputType, OutputType

from database import base_research_collection, competitors_list_collection

st.sidebar.markdown(
    """ 
    # Main Page
    1. Get a list of your competitors
    2. Gather base research data for them
"""
)

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PASSWORD = os.getenv("PASSWORD")
EMAIL = os.getenv("EMAIL")
PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")

FOLDER_NAME = "raw_data_files"
AGENTS_FILE = "assistant_ids.json"


# FUNCTIONS
@st.cache_data
def create_folder():
    if os.path.exists(FOLDER_NAME):
        shutil.rmtree(FOLDER_NAME)

    os.makedirs(FOLDER_NAME)

    if os.path.exists(AGENTS_FILE):
        os.remove(AGENTS_FILE)


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
        "model": "pplx-7b-online",
    },
)


def search_for_competitors(company_name):
    search_task = Task(
        name="Competitors search",
        output_type=OutputType.TEXT,
        input_type=InputType.TEXT,
        model=perplexity_model_text,
        instructions=f"Return only a dictionary of 5 competitors for the company {company_name} with names and website URLs in the format: {{'CompanyA': 'www.companya.com', 'CompanyB': 'www.companyb.com'}}. RETURN ONLY THE DICTIONARY.",
        log_output=True,
    ).execute()

    return search_task["choices"][0]["message"]["content"]


def search_competitor_analysis(company_name, website_name):
    search_task = Task(
        name="Website data search",
        output_type=OutputType.TEXT,
        input_type=InputType.TEXT,
        model=perplexity_model_text,
        instructions=f"""I need a comprehensive search for the most recent news regarding the company {company_name} with website {website_name}. Please focus on the following areas:
        1. Strategic Developments
        2. Financial Performance
        3. Product Innovations and Launches
        4. Regulatory and Legal Changes
        5. Leadership Changes
        6. Industry Trends and Analysis
        """,
        log_output=True,
    ).execute()

    return search_task["choices"][0]["message"]["content"]


def remove_www(url):
    if url.startswith("www."):
        return url[4:]
    return url


def scrape_competitor_analysis(company_name, website_name):
    scraped_data = ""
    i = 1
    google_news = GNews(period="7d", max_results=10)
    company_news = google_news.get_news(company_name)

    # website_name = remove_www(website_name)
    # website_news = google_news.get_news_by_site(website_name)

    for c_news in company_news:
        scraped_data += str(i) + ". " + c_news["title"] + "\n"
        i += 1

    # for w_news in website_news:
    #     scraped_data += str(i) + ". " + w_news["title"] + "\n"
    #     i += 1

        # try:
        #     article = google_news.get_full_article(news["url"])
        #     scraped_data += article.title + article.text + "\n"
        # except:
        #     print("Couldn't scrape article")
    return scraped_data


def save_raw_data_database(
    competitor_name, competitors_list_document_id, search_results="", scrape_results=""
):
    raw_data = search_results + f"\n\nRecent Headlines about {competitor_name}:\n" + scrape_results
    base_research_document = {
        "competitor_name": competitor_name,
        "competitors_list_document_id": competitors_list_document_id,
        "raw_data": raw_data,
        "created_at": datetime.datetime.now(datetime.UTC),
    }

    base_research_collection.insert_one(base_research_document)


def save_raw_data_file(competitor_name, search_results="", scrape_results=""):
    FILE_NAME = os.path.join(FOLDER_NAME, competitor_name + ".txt")
    with open(FILE_NAME, "w") as my_file:
        my_file.write(search_results)
        my_file.write(f"\n\nRecent Headlines about {competitor_name}:\n")
        my_file.write(scrape_results)


def save_competitors_list_databse(company_name_input, competitors):
    competitors_list_document = {
        "company_name": company_name_input,
        "generated_competitors_list": competitors,
        "created_at": datetime.datetime.now(datetime.UTC),
    }
    new_competitor_list = competitors_list_collection.insert_one(
        competitors_list_document
    )
    document_id = st.session_state["document_id"] = new_competitor_list.inserted_id

    return document_id


def analyze_competitors():
    company_name_input = st.session_state.company_name
    competitors = st.session_state.competitors

    document_id = save_competitors_list_databse(company_name_input, competitors)

    for to_analyze_competitor, to_analyze_website in competitors.items():
        search_results = search_competitor_analysis(
            to_analyze_competitor, to_analyze_website
        )
        scrape_results = scrape_competitor_analysis(
            to_analyze_competitor, to_analyze_website
        )
        # scrape_results = ""
        # search_results = "Based on the search results, here is a comprehensive summary of the latest news regarding Cohere:\n\n**Strategic Developments:**\n\n* Cohere Health has raised $50 million in equity funding to expand its intelligent prior authorization platform and meet the increasing demand for its solutions. (Source:)\n* Cohere has expanded its partnership with Humana to include diagnostic imaging and sleep services. (Source:)\n\n**Financial Performance:**\n\n* Cohere has raised $500 million in funding, valuing the company at $5 billion. (Source:)\n* The company's annualized revenue run rate has climbed to $22 million, up from $13 million in December. (Source:)\n\n**Product Innovations and Launches:**\n\n* Cohere has launched its new model Command-R, which is designed to compete with ChatGPT. (Source:)\n* The company has also launched its Coral knowledge assistant, a chatbot that can answer employee questions and access internal corporate knowledge bases. (Source:)\n\n**Regulatory and Legal Changes:**\n\n* The Centers for Medicare & Medicaid Services Interoperability and Prior Authorization rule, finalized in January, will require health plans to invest in advanced technology to ensure compliance with federal prior authorization requirements. (Source:)\n\n**Leadership Changes:**\n\n* Aidan Gomez, CEO and co-founder of Cohere, has spoken out against the effective altruism movement, criticizing its dogmatic and self-aggrandizing nature. (Source:)\n\n**Industry Trends and Analysis:**\n\n* Cohere's AI technology is being used to improve patient access to care and reduce prior authorization denial rates. (Source:)\n* The company's focus on scalability and production readiness for enterprises has enabled it to compete with other leading AI companies. (Source:)\n* The use of AI in healthcare is expected to continue to grow, with a focus on improving patient outcomes and reducing costs. (Source:)\n\nOverall, Cohere is making significant strides in the AI and healthcare industries, with a focus on improving patient access to care and reducing prior authorization denial rates. The company's recent funding rounds and product launches have positioned it as a major player in the competitive AI market."
        save_raw_data_database(
            to_analyze_competitor, document_id, search_results, scrape_results
        )
        save_raw_data_file(to_analyze_competitor, search_results, scrape_results)


# STREAMLIT COMPONENTS

create_folder()


def display_competitors():
    if st.session_state.competitors:
        st.write("# List of competitors:")
        for name, website in st.session_state.competitors.items():
            st.write(name + " - " + website)


if "competitors" not in st.session_state:
    st.session_state.competitors = {}

company_name = st.text_input("Enter company name:")
st.session_state.company_name = company_name

if st.button("Fetch Competitors"):
    try:
        competitors_dict = search_for_competitors(company_name)
        competitors_dict_final = ast.literal_eval(competitors_dict)
        st.session_state.competitors.update(competitors_dict_final)
        st.success(f"Fetched competitors for {company_name}")
    except:
        st.error("Error while fetching competitors. Try again or add one manually")
    # competitors_dict_final = {
    #     "Lyzr": "www.lyzr.ai",
    #     "Delineate": "www.delineate.com",
    #     "Lilac": "www.lilac.ai",
    #     "VoyagerAnalytics": "www.voyageranalytics.com",
    # }
    
    

st.write("## Add a competitor")
col1, col2 = st.columns(2)
with col1:
    new_company_name = st.text_input("Enter new company name:")

with col2:
    new_company_website = st.text_input("Enter new company website:")

if st.button("Add Competitor"):
    if new_company_name and new_company_website:
        st.session_state.competitors[new_company_name] = new_company_website
        st.success(f"Added competitor: {new_company_name}")
    else:
        st.error("Missing fields")

st.write("## Delete a competitor")
competitors_options = [key for key in st.session_state.competitors]
options = st.multiselect(
    "Pick competitors to delete",
    competitors_options,
)
if st.button("Delete Competitor"):
    for key in options:
        del st.session_state.competitors[key]
        st.success("Deleted!")

display_competitors()

if st.button("Submit Competitors for Analysis", type="primary"):
    analyze_competitors()
    st.write(
        """
        # Analysis complete! :star:
        ### Go to :red[Base Data Research] Page"""
    )
    st.page_link("pages/base_data_research.py", label="Base Data Research", icon="📊")
