import streamlit as st
import json
from pymongo import MongoClient
from dotenv import load_dotenv

# Import the updated generation function from article_generator
from article_generator import (
    generate_report_for_cluster,  # Updated function name
    get_all_facts_for_cluster,    # New function to show facts
    MONGO_URI,
    DB_NAME,
    FACTS_COLLECTION
)

# Load environment variables
load_dotenv()


def get_available_cluster_ids() -> list:
    """
    Retrieves all unique, sorted integer cluster_ids from MongoDB.
    """
    try:
        client = MongoClient(MONGO_URI)
        db = client[DB_NAME]
        facts_collection = db[FACTS_COLLECTION]
        distinct_cluster_ids = facts_collection.distinct("cluster_id")
        available_ids = sorted([
            int(cid) for cid in distinct_cluster_ids
            if isinstance(cid, (int, float, str)) and cid is not None
        ])
        client.close()
        return available_ids
    except Exception as e:
        st.sidebar.error(f"Error fetching cluster IDs: {e}")
        return []


def get_cluster_facts_summary(cluster_id: int) -> str:
    """
    Retrieves a summary of facts for a cluster.
    """
    try:
        facts = get_all_facts_for_cluster(cluster_id)
        if facts and facts != "No facts available.":
            # Limit to first 20 facts for display
            fact_lines = facts.split('\n')
            if len(fact_lines) > 20:
                fact_lines = fact_lines[:20] + ["... and more"]
            return '\n'.join(fact_lines)
        return "No facts available for this cluster."
    except Exception as e:
        return f"Error loading facts: {e}"


def main():
    st.set_page_config(layout="wide", page_title="BiasLens Article & Timeline Viewer")
    st.title("📰 BiasLens: Generated Article and Timeline Viewer")
    st.markdown("---")

    st.sidebar.header("🔍 Cluster Selection")

    available_cluster_ids = get_available_cluster_ids()

    if not available_cluster_ids:
        st.sidebar.warning("No cluster IDs found in the database.")
        cluster_id_input = st.sidebar.number_input(
            "Enter Cluster ID manually:",
            min_value=0,
            value=0,
            step=1,
            help="Enter the Cluster ID to generate a report for."
        )
    else:
        cluster_id_input = st.sidebar.selectbox(
            "Select Cluster ID:",
            options=available_cluster_ids,
            index=0,
            help="Select the Cluster ID to generate a report for."
        )
    
    st.sidebar.markdown("---")
    st.sidebar.info("💡 **Tip:** Reports are cached after generation. Select a cluster ID and click 'Generate Report' below.")
    
    # Generate button
    if st.sidebar.button("🚀 Generate Report", type="primary", key="generate_report_button"):
        if cluster_id_input is not None:
            st.session_state.cluster_id_to_process = int(cluster_id_input)
            # Clear any existing cached data for this cluster to force regeneration
            if f"article_{cluster_id_input}" in st.session_state:
                del st.session_state[f"article_{cluster_id_input}"]
            if f"timeline_{cluster_id_input}" in st.session_state:
                del st.session_state[f"timeline_{cluster_id_input}"]
        else:
            st.sidebar.error("Please select or enter a Cluster ID.")

    # Main content area
    if 'cluster_id_to_process' in st.session_state and st.session_state.cluster_id_to_process is not None:
        current_cluster_id = st.session_state.cluster_id_to_process
        
        # Display cluster info
        st.info(f"📌 **Current Cluster ID:** {current_cluster_id}")
        
        # Create tabs for better organization
        tab1, tab2, tab3 = st.tabs(["📝 Generated Article", "⏱️ Timeline JSON", "📊 Source Facts"])
        
        with tab1:
            st.subheader("Generated Unbiased Article")
            
            if f"article_{current_cluster_id}" not in st.session_state:
                with st.spinner(f"🔄 Generating article for cluster {current_cluster_id}... (this may take a moment)"):
                    article, timeline_json_str = generate_report_for_cluster(current_cluster_id)
                    st.session_state[f"article_{current_cluster_id}"] = article
                    st.session_state[f"timeline_{current_cluster_id}"] = timeline_json_str
            
            article = st.session_state[f"article_{current_cluster_id}"]
            
            if article:
                if "Error" in article or "No facts found" in article:
                    st.error(article)
                else:
                    st.markdown(article)
                    # Add download button for article
                    st.download_button(
                        label="📥 Download Article",
                        data=article,
                        file_name=f"article_cluster_{current_cluster_id}.md",
                        mime="text/markdown"
                    )
            else:
                st.error("Failed to generate article.")
        
        with tab2:
            st.subheader("Generated Timeline (JSON)")
            
            timeline_json_str = st.session_state.get(f"timeline_{current_cluster_id}")
            
            if timeline_json_str:
                try:
                    timeline_data = json.loads(timeline_json_str)
                    st.json(timeline_data)
                    
                    # Download button for timeline
                    st.download_button(
                        label="📥 Download Timeline JSON",
                        data=timeline_json_str,
                        file_name=f"timeline_cluster_{current_cluster_id}.json",
                        mime="application/json"
                    )
                except json.JSONDecodeError:
                    st.error("The generated timeline is not valid JSON.")
                    with st.expander("View Raw Output"):
                        st.code(timeline_json_str, language="text")
            else:
                st.warning("No timeline generated for this cluster.")
        
        with tab3:
            st.subheader("Source Facts Used for Generation")
            
            if f"facts_{current_cluster_id}" not in st.session_state:
                facts_summary = get_cluster_facts_summary(current_cluster_id)
                st.session_state[f"facts_{current_cluster_id}"] = facts_summary
            
            facts_summary = st.session_state[f"facts_{current_cluster_id}"]
            st.text_area("Extracted Facts:", facts_summary, height=400)
            
            # Also show raw fact count
            try:
                client = MongoClient(MONGO_URI)
                db = client[DB_NAME]
                facts_collection = db[FACTS_COLLECTION]
                fact_count = facts_collection.count_documents({"cluster_id": current_cluster_id})
                client.close()
                st.caption(f"📊 Total facts in this cluster: {fact_count}")
            except:
                pass
    
    else:
        st.info("👈 **Select a Cluster ID from the sidebar and click 'Generate Report' to view the article and timeline.**")
        
        # Show available clusters if any
        if available_cluster_ids:
            st.markdown("### 📋 Available Clusters")
            st.write(f"Cluster IDs with facts: {available_cluster_ids}")
            st.caption(f"Total clusters available: {len(available_cluster_ids)}")


if __name__ == '__main__':
    main()