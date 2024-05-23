import streamlit as st

from database import metrics_collection, news_collection

st.sidebar.markdown(
    """ 
    **Reports Page**

    1. View all generated reports
"""
)

document_id = st.session_state["document_id"]


pipeline = [
    {"$match": {"competitors_list_document_id": document_id}},
    {
        "$lookup": {
            "from": "news",
            "let": {
                "base_id": "$base_research_document_id",
                "comp_name": "$competitor_name",
            },
            "pipeline": [
                {
                    "$match": {
                        "$expr": {
                            "$and": [
                                {"$eq": ["$base_research_document_id", "$$base_id"]},
                                {"$eq": ["$competitor_name", "$$comp_name"]},
                            ]
                        }
                    }
                },
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

for result in results:
    with st.expander(result["competitor_name"]):
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
