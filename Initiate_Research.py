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

st.set_page_config(layout="wide")

st.sidebar.markdown(
    """ 
    # Meet Alan! :sunglasses:
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

perplexity_model_text = PerplexityModel(
    api_key=PERPLEXITY_API_KEY,
    parameters={
        "model": "pplx-7b-online",
    },
)


def remove_www(url):
    if url.startswith("www."):
        return url[4:]
    return url


def format_key(title):
    # Remove non-alphanumeric characters and convert to lowercase
    key = re.sub(r"\W+", "_", title).lower()
    return key


def search_competitor_analysis(company_name, website_name):
    search_task = Task(
        name="Website data search",
        output_type=OutputType.TEXT,
        input_type=InputType.TEXT,
        model=perplexity_model_text,
        instructions=f"Tell me about the company {company_name} - {website_name}",
        log_output=True,
    ).execute()

    return search_task["choices"][0]["message"]["content"]


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
        news_dict[key] = news

    for news in website_news:
        news_article_list.append(news["title"])
        key = format_key(news["title"])
        news_dict[key] = news

    news_picker_agent = Agent(
        prompt_persona=f"""You are an expert news analyst. You have been given a list of news article headlines about the company {company_name}. Your task is to identify and return the top 10 headlines that are the most important and impactful.
Consider the following criteria when evaluating each headline:
- Uniqueness: Avoid selecting multiple headlines that discuss the same event or topic. Each of the top 10 headlines should cover a distinct and different event or aspect.
- Relevance: How directly the headline pertains to significant events or developments related to the company (e.g., major financial moves, significant product launches, legal issues, executive changes, etc.).
- Impact: The potential effect of the news on the company's operations, stock price, public perception, or industry standing.

OUTPUT FORMAT - A list containing the headlines - [Headline 1, Headline 2, ...]

Please return the top 10 headlines. If the input has less than 10 headlines, return all. Make sure all the headlines are returned in the same format as input.
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

    breakpoint()

    headlines_list = ast.literal_eval(news_picker_task)
    cleaned_headlines = [format_key(headline.strip()) for headline in headlines_list]

    for title in cleaned_headlines:
        url = news_dict[title]["url"]
        date = news_dict[title]["published date"]
        try:
            full_article = google_news.get_full_article(url)
            article_title = full_article.title
            article_text = full_article.text
            scraped_data += (
                "Title: "
                + article_title
                + "\nPublished Date: "
                + date
                + "\n"
                + article_text
                + "\n"
            )
        except:
            print("Error")

    return scraped_data


def specific_research_analysis(company_name, website_name, specific_research_area):
    search_task = Task(
        name="Specific data search",
        output_type=OutputType.TEXT,
        input_type=InputType.TEXT,
        model=perplexity_model_text,
        instructions=f"Find detailed information about {specific_research_area} of the company {company_name} - {website_name}",
        log_output=True,
    ).execute()

    return search_task["choices"][0]["message"]["content"]


def save_raw_data_database(
    competitor_name,
    competitors_list_document_id,
    search_results="",
    scrape_results="",
    specific_research_results="",
):
    raw_data = (
        f"Specific Research:\n{specific_research_results}\nGeneral Research:\n{search_results}\nRecent Articles about {competitor_name}:\n"
        + scrape_results
    )
    base_research_document = {
        "competitor_name": competitor_name,
        "competitors_list_document_id": competitors_list_document_id,
        "raw_data": raw_data,
        "created_at": datetime.datetime.now(datetime.UTC),
    }

    base_research_collection.insert_one(base_research_document)


def save_raw_data_file(
    competitor_name, search_results="", scrape_results="", specific_research_results=""
):
    raw_data = (
        f"Specific Research:\n{specific_research_results}\nGeneral Research:\n{search_results}\nRecent Articles about {competitor_name}:\n"
        + scrape_results
    )
    FILE_NAME = os.path.join(FOLDER_NAME, competitor_name + ".txt")
    with open(FILE_NAME, "w") as my_file:
        my_file.write(raw_data)


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


def analyze_competitors(specific_research_area=""):
    company_name_input = st.session_state.company_name
    competitors = st.session_state.competitors

    document_id = save_competitors_list_databse(company_name_input, competitors)

    for to_analyze_competitor, to_analyze_website in competitors.items():
        specific_research_results = ""
        if specific_research_area != "":
            specific_research_results = specific_research_analysis(
                to_analyze_competitor, to_analyze_website, specific_research_area
            )
        search_results = search_competitor_analysis(
            to_analyze_competitor, to_analyze_website
        )
        scrape_results = scrape_competitor_analysis(
            to_analyze_competitor, to_analyze_website
        )
        save_raw_data_database(
            to_analyze_competitor,
            document_id,
            search_results,
            scrape_results,
            specific_research_results,
        )
        save_raw_data_file(
            to_analyze_competitor,
            search_results,
            scrape_results,
            specific_research_results,
        )


# STREAMLIT COMPONENTS


def display_competitors():
    if st.session_state.competitors:
        st.write("# List of competitors:")
        for name, website in st.session_state.competitors.items():
            st.write(name + " - " + website)


if "competitors" not in st.session_state:
    st.session_state.competitors = {}

st.image("Alan.png")

company_name = st.text_input("Enter your company name:")
st.session_state.company_name = company_name

st.write("## Add a competitor")
col1, col2 = st.columns(2)
with col1:
    new_company_name = st.text_input("Enter competitor name:")

with col2:
    new_company_website = st.text_input("Enter competitor website:")

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

specific_research_area = st.text_input(
    "Specific area to focus for research *(OPTIONAL)*",
    value="",
    placeholder="Eg. Sales Strategy",
)

display_competitors()

if st.button("Submit Competitors for Analysis", type="primary"):
    create_folder()
    analyze_competitors(specific_research_area.strip())
    st.write(
        """
        # Analysis complete! :star:
        ### Go to :red[Generate Report] Page"""
    )
    st.page_link("pages/1_Generate_Report.py", label="Generate Report", icon="📊")
