import streamlit as st
import json
from pymongo import MongoClient
from dotenv import load_dotenv

# Import the generation function and MongoDB details from article_generator
from article_generator import (
    generate_report_for_cluster_langchain_groq,
    MONGO_URI,
    DB_NAME,
    FACTS_COLLECTION
)

# Load environment variables (if not already loaded by article_generator, though it should be)
load_dotenv()


def get_available_cluster_ids() -> list:
    """
    Retrieves all unique, sorted integer cluster_ids from MongoDB.
    """
    try:
        client = MongoClient(MONGO_URI)
        db = client[DB_NAME]
        facts_collection = db[FACTS_COLLECTION]
        # Fetch distinct cluster_ids and sort them. Ensure they are integers.
        # Handle potential non-integer or missing cluster_id fields gracefully.
        distinct_cluster_ids_cursor = facts_collection.distinct("cluster_id")
        available_ids = sorted([
            int(cid) for cid in distinct_cluster_ids_cursor
            if isinstance(cid, (int, float)) and cid is not None
        ])
        client.close()
        return available_ids
    except Exception as e:
        st.sidebar.error(f"Error fetching cluster IDs: {e}")
        return []


def main():
    st.set_page_config(layout="wide", page_title="BiasLens Article Viewer")
    st.title("BiasLens: Generated Article and Timeline Viewer")

    st.sidebar.header("Cluster Selection")

    available_cluster_ids = get_available_cluster_ids()

    if not available_cluster_ids:
        st.sidebar.warning(
            "No cluster IDs found in the database. Please add data or check connection.")
        # Allow manual input if no clusters are found
        cluster_id_input = st.sidebar.number_input(
            "Enter Cluster ID:",
            min_value=0,
            value=0,
            step=1,
            help="Enter the Cluster ID to generate a report for."
        )
    else:
        cluster_id_input = st.sidebar.selectbox(
            "Select Cluster ID:",
            options=available_cluster_ids,
            index=0,  # Default to the first available cluster ID
            help="Select the Cluster ID to generate a report for."
        )

    if st.sidebar.button("Generate Report", key="generate_report_button"):
        if cluster_id_input is not None:
            st.session_state.cluster_id_to_process = int(
                cluster_id_input)  # Ensure int
        else:
            st.sidebar.error("Please select or enter a Cluster ID.")
            st.session_state.cluster_id_to_process = None
            return  # Stop further execution if no ID

    if 'cluster_id_to_process' in st.session_state and st.session_state.cluster_id_to_process is not None:
        current_cluster_id = st.session_state.cluster_id_to_process

        # Display which cluster is being processed or was processed
        st.info(f"Displaying report for Cluster ID: {current_cluster_id}")

        # Use columns for a better layout
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Generated Unbiased Article")
            with st.spinner(f"Generating article for cluster: {current_cluster_id}..."):
                # We call the function once and store results to avoid re-calling on every interaction
                if f"article_{current_cluster_id}" not in st.session_state:
                    article, timeline_json_str = generate_report_for_cluster_langchain_groq(
                        current_cluster_id)
                    st.session_state[f"article_{current_cluster_id}"] = article
                    st.session_state[f"timeline_{current_cluster_id}"] = timeline_json_str

                article = st.session_state[f"article_{current_cluster_id}"]

            if article:
                if "Error:" in article or "No facts found" in article:
                    st.error(article)
                else:
                    st.markdown(article)
            else:
                st.error(
                    "Failed to generate article or no article content returned.")

        with col2:
            st.subheader("Generated Timeline (JSON)")
            with st.spinner(f"Generating timeline for cluster: {current_cluster_id}..."):
                # Timeline was generated with article, retrieve from session state
                timeline_json_str = st.session_state.get(
                    f"timeline_{current_cluster_id}")

            if timeline_json_str:
                try:
                    # Attempt to parse to check validity and pretty-print
                    timeline_data = json.loads(timeline_json_str)
                    st.json(timeline_data)  # st.json handles dicts/lists well
                except json.JSONDecodeError:
                    st.error("The generated timeline string is not valid JSON.")
                    st.text_area("Raw Timeline Output:",
                                 timeline_json_str, height=300)
                except Exception as e:  # Catch other potential errors with the timeline string
                    st.error(f"An error occurred with the timeline data: {e}")
                    st.text_area("Raw Timeline Output:",
                                 timeline_json_str, height=300)

            else:
                st.error(
                    "Failed to generate timeline or no timeline content returned.")
    else:
        st.info(
            "Select a Cluster ID from the sidebar and click 'Generate Report' to view its details.")


if __name__ == '__main__':
    main()
