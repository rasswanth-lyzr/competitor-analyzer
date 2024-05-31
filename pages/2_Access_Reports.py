import os

import streamlit as st
from fpdf import FPDF

from database import metrics_collection, news_collection

REPORT_FOLDER_NAME = "reports"

st.set_page_config(layout="wide", page_title="Alan - The Business Analyst")

st.sidebar.title("Try Alan’s Capabilities")
st.sidebar.markdown(
    "<small>Alan can do a thorough research about your customer or competitor and generate a detailed report, on a daily or weekly basis. Alan looks up information in the internet (powered by Perplexity), news (powered by Google news) and also scraps their website.</small>",
    unsafe_allow_html=True,
)
st.sidebar.markdown(
    "Learn more about [Alan](https://www.lyzr.ai/book-demo/)", unsafe_allow_html=True
)

try:
    document_id = st.session_state["document_id"]
except:
    st.error("Please complete Generate Report step!")
    st.stop()


pipeline = [
    {"$match": {"competitors_list_document_id": document_id}},
    {
        "$sort": {
            "created_at": -1
        }  # Sort the metrics_collection by 'created_at' in descending order
    },
    {"$limit": 1},
    {
        "$lookup": {
            "from": "news",
            "let": {
                "comp_name": "$competitor_name",
            },
            "pipeline": [
                {
                    "$match": {
                        "$expr": {
                            "$and": [
                                {"$eq": ["$competitor_name", "$$comp_name"]},
                            ]
                        }
                    }
                },
                {
                    "$sort": {"created_at": -1}
                },  # Sort by 'created_at' in descending order
                {"$limit": 1},  # Limit to the latest record
                {"$project": {"email_report": 1, "_id": 0}},
            ],
            "as": "news_data",
        }
    },
    {"$addFields": {"email_report": {"$arrayElemAt": ["$news_data.email_report", 0]}}},
    {
        "$project": {
            "news_data": 0  # Optionally remove the news_data array from the final output
        }
    },
]

results = metrics_collection.aggregate(pipeline)
keys_to_ignore = {
    "_id",
    "base_research_document_id",
    "competitors_list_document_id",
    "created_at",
    "email_report",
}


def save_report(result):
    FILE_NAME = os.path.join(REPORT_FOLDER_NAME, result["competitor_name"] + ".pdf")
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    metrics_text_content = ""
    new_data = {
        key: value for key, value in result.items() if key not in keys_to_ignore
    }
    metrics_dict = st.session_state.metrics_dict
    for key, value in new_data.items():
        if key in list(metrics_dict.keys()):
            metrics_text_content += f"- {metrics_dict[key]}: {value} \n"
        else:
            metrics_text_content += f"- {key}: {value} \n"

    text_content = (
        "Summary\n\n" + result["email_report"] + "\n\nMetrics\n" + metrics_text_content
    )
    pdf.multi_cell(0, 10, text_content)
    pdf.output(FILE_NAME)
    return FILE_NAME


st.header("View all generated reports")
for result in results:
    with st.expander(result["competitor_name"]):
        file_path = save_report(result)
        st.write("# Summary")
        st.write(result["email_report"])
        st.write("# Metrics")
        new_data = {
            key: value for key, value in result.items() if key not in keys_to_ignore
        }
        metrics_dict = st.session_state.metrics_dict
        for key, value in new_data.items():
            if key in list(metrics_dict.keys()):
                st.write(f"- **{metrics_dict[key]}**: {value}")
            else:
                st.write(f"- **{key}**: {value}")

        with open(file_path, "rb") as file:
            st.download_button("Download file", data=file, file_name=file_path, mime='application/octet-stream')
