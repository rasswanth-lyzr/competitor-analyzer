import ast
import datetime
import os
import re
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
def create_folder():
    if os.path.exists(FOLDER_NAME):
        shutil.rmtree(FOLDER_NAME)

    os.makedirs(FOLDER_NAME)

    if os.path.exists(AGENTS_FILE):
        os.remove(AGENTS_FILE)


open_ai_model_text = OpenAIModel(
    api_key=OPENAI_API_KEY,
    parameters={
        "model": "gpt-4o",
        "temperature": 0.2,
        "max_tokens": 1500,
    },
)

# perplexity_model_text = PerplexityModel(
#     api_key=PERPLEXITY_API_KEY,
#     parameters={
#         "model": "pplx-7b-online",
#     },
# )


# def search_for_competitors(company_name):
#     search_task = Task(
#         name="Competitors search",
#         output_type=OutputType.TEXT,
#         input_type=InputType.TEXT,
#         model=perplexity_model_text,
#         instructions=f"Find 5 competitors for the company {company_name} with names and website URLs. Output Format - {{'CompanyA': 'www.companya.com', 'CompanyB': 'www.companyb.com'}}. Return ONLY the dictionary.",
#         log_output=True,
#     ).execute()

#     return search_task["choices"][0]["message"]["content"]


def remove_www(url):
    if url.startswith("www."):
        return url[4:]
    return url


def format_key(title):
    # Remove non-alphanumeric characters and convert to lowercase
    key = re.sub(r"\W+", "_", title).lower()
    return key


def scrape_competitor_analysis(company_name, website_name):
    scraped_data = ""
    google_news = GNews(period="7d", max_results=25)
    company_news = google_news.get_news(company_name)
    website_name = remove_www(website_name)
    website_news = google_news.get_news_by_site(website_name)

    news_article_list = []
    news_dict = {}
    for news in company_news:
        news_article_list.append(news["title"])
        key = format_key(news["title"])
        value = news["url"]
        news_dict[key] = value

    for news in website_news:
        news_article_list.append(news["title"])
        key = format_key(news["title"])
        value = news["url"]
        news_dict[key] = value

    news_picker_agent = Agent(
        prompt_persona="""You are an expert news analyst. You have been given a list of news article headlines about a company. Your task is to identify and return the top 10 headlines that are the most important and impactful.
Consider the following criteria when evaluating each headline:
- Uniqueness: Avoid selecting multiple headlines that discuss the same event or topic. Each of the top 5 headlines should cover a distinct and different event or aspect.
- Relevance: How directly the headline pertains to significant events or developments related to the company (e.g., major financial moves, significant product launches, legal issues, executive changes, etc.).
- Impact: The potential effect of the news on the company's operations, stock price, public perception, or industry standing.

OUTPUT FORMAT - A list containing the headlines - [Headline 1, Headline 2, ...]

Please return the top 10 headlines. If the input has less than 10 headlines, return all.
""",
        role="News picker",
    )

    news_picker_task = Task(
        name="Filter News Task",
        agent=news_picker_agent,
        output_type=OutputType.TEXT,
        input_type=InputType.TEXT,
        model=open_ai_model_text,
        instructions="Filter the news results and give top 10 headlines in a list. Return ONLY the list",
        log_output=True,
        enhance_prompt=False,
        default_input=news_article_list,
    ).execute()

    headlines_list = ast.literal_eval(news_picker_task)
    cleaned_headlines = [format_key(headline.strip()) for headline in headlines_list]

    for title in cleaned_headlines:
        url = news_dict[title]
        try:
            full_article = google_news.get_full_article(url)
            article_title = full_article.title
            article_text = full_article.text
            scraped_data += "Title: " + article_title + "\n" + article_text + "\n"
        except:
            print("Error")

    return scraped_data


def save_raw_data_database(
    competitor_name, competitors_list_document_id, scrape_results=""
):
    raw_data = f"Recent Articles about {competitor_name}:\n" + scrape_results
    base_research_document = {
        "competitor_name": competitor_name,
        "competitors_list_document_id": competitors_list_document_id,
        "raw_data": raw_data,
        "created_at": datetime.datetime.now(datetime.UTC),
    }

    base_research_collection.insert_one(base_research_document)


def save_raw_data_file(competitor_name, scrape_results=""):
    FILE_NAME = os.path.join(FOLDER_NAME, competitor_name + ".txt")
    with open(FILE_NAME, "w") as my_file:
        my_file.write(f"Recent Articles about {competitor_name}:\n")
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
        scrape_results = scrape_competitor_analysis(
            to_analyze_competitor, to_analyze_website
        )
        save_raw_data_database(to_analyze_competitor, document_id, scrape_results)
        save_raw_data_file(to_analyze_competitor, scrape_results)


# STREAMLIT COMPONENTS


def display_competitors():
    if st.session_state.competitors:
        st.write("# List of competitors:")
        for name, website in st.session_state.competitors.items():
            st.write(name + " - " + website)


if "competitors" not in st.session_state:
    st.session_state.competitors = {}

company_name = st.text_input("Enter company name:")
st.session_state.company_name = company_name

# if st.button("Fetch Competitors"):
#     # try:
#     #     competitors_dict = search_for_competitors(company_name)
#     #     competitors_dict_final = ast.literal_eval(competitors_dict)
#     #     st.session_state.competitors.update(competitors_dict_final)
#     #     st.success(f"Fetched competitors for {company_name}")
#     # except:
#     #     st.error("Error while fetching competitors. Try again or add one manually")
#     competitors_dict_final = {"OpenAI": "www.openai.com"}
#     st.session_state.competitors.update(competitors_dict_final)
#     st.success(f"Fetched competitors for {company_name}")


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
    create_folder()
    analyze_competitors()
    st.write(
        """
        # Analysis complete! :star:
        ### Go to :red[Base Data Research] Page"""
    )
    st.page_link("pages/base_data_research.py", label="Base Data Research", icon="📊")
