# import os
# import json
# from pymongo import MongoClient
# from dotenv import load_dotenv
# import re
# from langchain_community.vectorstores import FAISS
# from langchain_huggingface import HuggingFaceEmbeddings
# from langchain_groq import ChatGroq
# from langchain_core.prompts import ChatPromptTemplate
# from langchain_core.output_parsers import StrOutputParser
# from langchain_core.runnables import RunnablePassthrough, RunnableLambda
# # FIX: Use the correct import for Document
# from langchain_core.documents import Document

# # Load environment variables (for GROQ_API_KEY)
# load_dotenv()

# # MongoDB connection details
# MONGO_URI = 'mongodb://localhost:27017/'
# DB_NAME = 'biaslens'
# FACTS_COLLECTION = 'facts'

# # Use a valid sentence-transformers model (lightweight, works locally)
# EMBEDDING_MODEL_NAME = 'all-MiniLM-L6-v2'


# def get_facts_for_cluster(cluster_id: int) -> list:
#     """
#     Retrieves all facts for a given cluster_id from MongoDB.
#     """
#     client = MongoClient(MONGO_URI)
#     db = client[DB_NAME]
#     collection = db[FACTS_COLLECTION]
#     facts = list(collection.find({"cluster_id": cluster_id}, {"_id": 0}))
#     client.close()
#     return facts


# def create_fact_embeddings_and_build_retriever(cluster_id: int, embedding_model_service):
#     """
#     Fetches facts for a cluster, creates text representations, generates embeddings,
#     and builds a Langchain retriever.
#     """
#     facts = get_facts_for_cluster(cluster_id)
#     if not facts:
#         print(f"No facts found for cluster {cluster_id}.")
#         return None

#     fact_texts = []
#     fact_metadatas = []

#     for fact in facts:
#         s = fact.get('subject', '')
#         v = fact.get('verb', '')
#         o = fact.get('object', '')
#         text_representation = f"Subject: {s}, Verb: {v}, Object: {o}."
#         if fact.get('source'):
#             text_representation += f" Source: {fact.get('source')}."
#         if fact.get('timestamp'):
#             text_representation += f" Timestamp: {fact.get('timestamp')}."

#         fact_texts.append(text_representation)
#         fact_metadatas.append(fact)

#     if not fact_texts:
#         print(f"No fact texts to embed for cluster {cluster_id}.")
#         return None

#     vectorstore = FAISS.from_texts(
#         texts=fact_texts, embedding=embedding_model_service, metadatas=fact_metadatas)
#     return vectorstore.as_retriever(search_kwargs={"k": 100})


# def format_retrieved_facts_for_article(docs) -> str:
#     """Formats retrieved Langchain Document objects for the article prompt context."""
#     if not docs:
#         return "[]"
#     formatted_facts = []
#     for doc in docs:
#         fact = doc.metadata
#         formatted_facts.append(
#             json.dumps({
#                 "subject": fact.get('subject', 'N/A'),
#                 "verb": fact.get('verb', 'N/A'),
#                 "object": fact.get('object', 'N/A'),
#                 "source": fact.get('source', 'N/A'),
#                 "timestamp": fact.get('timestamp', 'N/A')
#             })
#         )
#     return "[\n  " + ",\n  ".join(formatted_facts) + "\n]"


# def format_retrieved_facts_for_timeline(docs) -> str:
#     """Formats retrieved Langchain Document objects for the timeline prompt context."""
#     if not docs:
#         return "[]"
#     formatted_facts = []
#     for doc in docs:
#         fact = doc.metadata
#         formatted_facts.append(
#             json.dumps({
#                 "subject": fact.get('subject', 'N/A'),
#                 "verb": fact.get('verb', 'N/A'),
#                 "object": fact.get('object', 'N/A'),
#                 "timestamp": fact.get('timestamp', 'N/A'),
#                 "source": fact.get('source', 'N/A')
#             })
#         )
#     return "[\n  " + ",\n  ".join(formatted_facts) + "\n]"


# UNBIASED_ARTICLE_PROMPT_TEMPLATE = """System: You are a highly precise and experienced article writer. Your sole function is to synthesize provided facts into a neutral, objective news report. Adhere strictly to journalistic neutrality.

# User: Generate a detailed, unbiased news article based ONLY on the facts below for Cluster ID {cluster_id}.
# Key Directives:
# 1.  Factual Purity: Report ONLY information explicitly stated in the provided 'Context' facts. NO inference, speculation, or external information.
# 2.  Neutral Language: Employ strictly objective terminology. Avoid emotive, loaded, or biased phrasing.
# 3.  Focus: Prioritize facts that are corroborated by multiple sources. If facts conflict, present the differing accounts neutrally, attributing each.

# Context (Facts for Cluster ID {cluster_id}):
# {context}

# Generate the unbiased news article:"""


# TIMELINE_JSON_PROMPT_TEMPLATE = """System: You are an AI assistant that creates structured JSON timelines from factual data. Your response MUST be a single, valid JSON array of event objects and nothing else. Do not include any explanatory text or markdown formatting outside of the JSON itself.

# User: Based ONLY on the facts below for Cluster ID {cluster_id}, generate a JSON array for a chronological timeline.
# Schema for each timeline event object: {{ "timestamp": "YYYY-MM-DDTHH:MM:SSZ", "event_summary": "Concise SVO fact summary", "sources": ["Source A", "Source B"] }}
# Guidelines:
# 1.  Chronological Order: Strictly by timestamp (earliest to latest).
# 2.  Event Summary: A brief subject-verb-object summary of the event.
# 3.  Sources: List all sources that reported this specific event/fact in the "sources" array.
# 4.  Timestamp Handling: If a timestamp is missing/invalid, use "null" as the value for the "timestamp" key, or a placeholder like "Timestamp N/A".
# 5.  Validity: Ensure the output is a single, valid JSON array of event objects. Adhere strictly to the schema.

# Context (Facts for Cluster ID {cluster_id}):
# {context}

# Generate ONLY the JSON array:"""


# def generate_report_for_cluster_langchain_groq(cluster_id: int) -> tuple[str | None, str | None]:
#     """
#     Generates an unbiased article and a timeline JSON for a given cluster_id
#     using Langchain and Groq.
#     Returns a tuple: (article_text, timeline_json_string)
#     """
#     groq_api_key = os.getenv("GROQ_API_KEY")
#     if not groq_api_key:
#         return "Error: GROQ_API_KEY not found in environment variables.", None

#     try:
#         # Initialize Groq LLM
#         llm = ChatGroq(model_name="llama-3.1-8b-instant",
#                        groq_api_key=groq_api_key, temperature=0.0)
        
#         # Initialize embeddings with a valid model
#         print(f"Loading embedding model: {EMBEDDING_MODEL_NAME}...")
#         embedding_model_service = HuggingFaceEmbeddings(
#             model_name=EMBEDDING_MODEL_NAME,
#             model_kwargs={'device': 'cpu'},
#             encode_kwargs={'normalize_embeddings': True}
#         )

#         # Build retriever from facts
#         retriever = create_fact_embeddings_and_build_retriever(
#             cluster_id, embedding_model_service)
#         if not retriever:
#             return f"No facts found or could not build retriever for cluster {cluster_id}.", None

#         # Helper functions to invoke the scoped retriever with a generic string query
#         def get_article_context(_input_from_chain):
#             docs = retriever.invoke("all relevant facts for article generation")
#             return format_retrieved_facts_for_article(docs)

#         def get_timeline_context(_input_from_chain):
#             docs = retriever.invoke("all relevant facts for timeline generation")
#             return format_retrieved_facts_for_timeline(docs)

#         # --- Generate Unbiased Article ---
#         print("Generating unbiased article...")
#         article_prompt = ChatPromptTemplate.from_template(
#             UNBIASED_ARTICLE_PROMPT_TEMPLATE)

#         article_chain = (
#             {
#                 "context": RunnableLambda(get_article_context),
#                 "cluster_id": RunnablePassthrough()
#             }
#             | article_prompt
#             | llm
#             | StrOutputParser()
#         )
#         generated_article = article_chain.invoke(cluster_id)

#         # --- Generate Timeline JSON ---
#         print("Generating timeline JSON...")
#         timeline_prompt = ChatPromptTemplate.from_template(
#             TIMELINE_JSON_PROMPT_TEMPLATE)

#         timeline_chain = (
#             {
#                 "context": RunnableLambda(get_timeline_context),
#                 "cluster_id": RunnablePassthrough()
#             }
#             | timeline_prompt
#             | llm
#             | StrOutputParser()
#         )
#         generated_timeline_str = timeline_chain.invoke(cluster_id)

#         # Parse and validate timeline JSON
#         timeline_output = None
#         try:
#             # Try to find JSON within backticks (```json ... ``` or ``` ... ```)
#             match = re.search(
#                 r"```(?:json)?\s*([\s\S]*?)\s*```", generated_timeline_str, re.DOTALL)
#             if match:
#                 json_str_to_parse = match.group(1).strip()
#             else:
#                 json_str_to_parse = generated_timeline_str.strip()

#             timeline_data = json.loads(json_str_to_parse)
#             # Re-serialize to ensure clean JSON string
#             timeline_output = json.dumps(timeline_data, indent=2)
#             print(f"✓ Successfully generated timeline with {len(timeline_data)} events")
#         except json.JSONDecodeError as e:
#             print(f"Warning: LLM did not return valid JSON for timeline (cluster {cluster_id}). Error: {e}")
#             timeline_output = json.dumps(
#                 [{"error": "Failed to generate valid timeline JSON from LLM.", "details": generated_timeline_str[:200]}], indent=2)

#         return generated_article, timeline_output

#     except Exception as e:
#         print(f"Error in Langchain/Groq generation for cluster {cluster_id}: {e}")
#         import traceback
#         traceback.print_exc()
#         return f"Error during generation: {e}", None


# def save_report_to_mongodb(cluster_id: int, article: str, timeline: str):
#     """
#     Saves the generated article and timeline to MongoDB.
#     """
#     try:
#         from datetime import datetime
#         client = MongoClient(MONGO_URI)
#         db = client[DB_NAME]
#         collection = db['reports']
        
#         report_data = {
#             "cluster_id": cluster_id,
#             "article": article,
#             "timeline": timeline,
#             "generated_at": datetime.now().isoformat()
#         }
        
#         # Use upsert to update if exists or insert if doesn't
#         collection.update_one(
#             {"cluster_id": cluster_id},
#             {"$set": report_data},
#             upsert=True
#         )
#         print(f"✓ Report saved to MongoDB for cluster {cluster_id}")
#         client.close()
#         return True
#     except Exception as e:
#         print(f"Error saving report to MongoDB: {e}")
#         return False


# def generate_reports_for_all_clusters():
#     """
#     Generates reports for all clusters that have facts.
#     """
#     try:
#         client = MongoClient(MONGO_URI)
#         db = client[DB_NAME]
#         facts_collection = db[FACTS_COLLECTION]
        
#         # Get all unique cluster IDs from facts collection
#         cluster_ids = facts_collection.distinct("cluster_id")
#         print(f"Found {len(cluster_ids)} clusters with facts: {cluster_ids}")
#         client.close()
        
#         reports = {}
#         for cluster_id in cluster_ids:
#             print(f"\n{'='*60}")
#             print(f"Processing Cluster {cluster_id}")
#             print(f"{'='*60}")
            
#             article, timeline = generate_report_for_cluster_langchain_groq(cluster_id)
            
#             if article and not article.startswith("Error"):
#                 reports[cluster_id] = {
#                     "article": article,
#                     "timeline": timeline
#                 }
#                 # Save to MongoDB
#                 save_report_to_mongodb(cluster_id, article, timeline)
#             else:
#                 print(f"Failed to generate report for cluster {cluster_id}")
        
#         print(f"\n{'='*60}")
#         print(f"Summary: Generated reports for {len(reports)} clusters")
#         print(f"{'='*60}")
        
#         return reports
        
#     except Exception as e:
#         print(f"Error getting cluster IDs: {e}")
#         return {}


# if __name__ == '__main__':
#     print("="*60)
#     print("ARTICLE AND TIMELINE GENERATOR")
#     print("="*60)
    
#     # Check if GROQ_API_KEY is set
#     if not os.getenv("GROQ_API_KEY"):
#         print("⚠️  WARNING: GROQ_API_KEY not found in environment variables.")
#         print("Please add GROQ_API_KEY to your .env file")
#         exit(1)
    
#     # Option 1: Generate report for a specific cluster
#     test_cluster_id = 23
#     print(f"\nOption 1: Generating report for cluster {test_cluster_id}...")
#     article, timeline_json_str = generate_report_for_cluster_langchain_groq(test_cluster_id)

#     if article and not article.startswith("Error"):
#         print("\n" + "="*60)
#         print("GENERATED UNBIASED ARTICLE")
#         print("="*60)
#         print(article)
        
#         print("\n" + "="*60)
#         print("GENERATED TIMELINE (JSON)")
#         print("="*60)
#         print(timeline_json_str)
        
#         # Save to file
#         with open(f"report_cluster_{test_cluster_id}.json", "w") as f:
#             json.dump({
#                 "cluster_id": test_cluster_id,
#                 "article": article,
#                 "timeline": timeline_json_str
#             }, f, indent=2)
#         print(f"\n✓ Report saved to report_cluster_{test_cluster_id}.json")
#     else:
#         print(f"\n❌ Failed to generate report for cluster {test_cluster_id}")
#         print(f"Error: {article}")
    
#     # Option 2: Generate reports for all clusters (uncomment to use)
#     # print("\n" + "="*60)
#     # print("Option 2: Generating reports for ALL clusters...")
#     # print("="*60)
#     # all_reports = generate_reports_for_all_clusters()

import os
import json
from pymongo import MongoClient
from dotenv import load_dotenv
import re
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough, RunnableLambda

# Load environment variables
load_dotenv()

# MongoDB connection details
MONGO_URI = 'mongodb://localhost:27017/'
DB_NAME = 'biaslens'
FACTS_COLLECTION = 'facts'


def get_facts_for_cluster(cluster_id: int) -> list:
    """Retrieves all facts for a given cluster_id from MongoDB."""
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    collection = db[FACTS_COLLECTION]
    facts = list(collection.find({"cluster_id": cluster_id}, {"_id": 0}))
    client.close()
    return facts


def get_all_facts_for_cluster(cluster_id: int) -> str:
    """Simply returns all facts as formatted text (no embeddings needed)."""
    facts = get_facts_for_cluster(cluster_id)
    
    if not facts:
        return "No facts available."
    
    formatted_facts = []
    for fact in facts:
        s = fact.get('subject', 'N/A')
        v = fact.get('verb', 'N/A')
        o = fact.get('object', 'N/A')
        source = fact.get('source', 'N/A')
        timestamp = fact.get('timestamp', 'N/A')
        
        fact_str = f"- {s} {v} {o} (Source: {source}, Timestamp: {timestamp})"
        formatted_facts.append(fact_str)
    
    return "\n".join(formatted_facts)


UNBIASED_ARTICLE_PROMPT_TEMPLATE = """System: You are a highly precise and experienced article writer. Your sole function is to synthesize provided facts into a neutral, objective news report. Adhere strictly to journalistic neutrality.

User: Generate a detailed, unbiased news article based ONLY on the facts below for Cluster ID {cluster_id}.

Key Directives:
1. Factual Purity: Report ONLY information explicitly stated in the provided facts. NO inference, speculation, or external information.
2. Neutral Language: Employ strictly objective terminology. Avoid emotive, loaded, or biased phrasing.
3. Focus: Prioritize facts that are corroborated by multiple sources. If facts conflict, present the differing accounts neutrally, attributing each.
4. Structure: Write a coherent news article with a headline, introduction, body paragraphs, and conclusion.

Facts for Cluster {cluster_id}:
{context}

Generate the unbiased news article:"""


TIMELINE_JSON_PROMPT_TEMPLATE = """System: You are an AI assistant that creates structured JSON timelines from factual data. Your response MUST be a single, valid JSON array of event objects and nothing else. Do not include any explanatory text or markdown formatting outside of the JSON itself.

User: Based ONLY on the facts below for Cluster ID {cluster_id}, generate a JSON array for a chronological timeline.

Schema for each timeline event object:
{{
    "timestamp": "YYYY-MM-DDTHH:MM:SSZ or null",
    "event_summary": "Concise SVO fact summary",
    "sources": ["Source A", "Source B"]
}}

Guidelines:
1. Chronological Order: Strictly by timestamp (earliest to latest).
2. Event Summary: A brief subject-verb-object summary of the event.
3. Sources: List all sources that reported this specific event/fact.
4. Timestamp Handling: If timestamp is missing, use null.

Facts for Cluster {cluster_id}:
{context}

Generate ONLY the JSON array (no other text):"""


def generate_report_for_cluster(cluster_id: int) -> tuple[str | None, str | None]:
    """
    Generates an unbiased article and timeline JSON using Groq (no embeddings).
    """
    groq_api_key = os.getenv("GROQ_API_KEY")
    if not groq_api_key:
        return "Error: GROQ_API_KEY not found in environment variables.", None

    try:
        # Initialize Groq LLM
        llm = ChatGroq(
            model_name="llama-3.1-8b-instant",
            groq_api_key=groq_api_key,
            temperature=0.0
        )
        
        # Get all facts for the cluster
        print(f"Fetching facts for cluster {cluster_id}...")
        facts_text = get_all_facts_for_cluster(cluster_id)
        
        if facts_text == "No facts available.":
            return f"No facts found for cluster {cluster_id}.", None
        
        print(f"Found facts. Generating article...")
        
        # Generate Article
        article_prompt = ChatPromptTemplate.from_template(UNBIASED_ARTICLE_PROMPT_TEMPLATE)
        article_chain = article_prompt | llm | StrOutputParser()
        generated_article = article_chain.invoke({
            "cluster_id": cluster_id,
            "context": facts_text
        })
        
        # Generate Timeline
        print("Generating timeline JSON...")
        timeline_prompt = ChatPromptTemplate.from_template(TIMELINE_JSON_PROMPT_TEMPLATE)
        timeline_chain = timeline_prompt | llm | StrOutputParser()
        generated_timeline_str = timeline_chain.invoke({
            "cluster_id": cluster_id,
            "context": facts_text
        })
        
        # Parse and validate timeline JSON
        timeline_output = None
        try:
            # Extract JSON from response
            match = re.search(r'\[[\s\S]*\]', generated_timeline_str)
            if match:
                json_str_to_parse = match.group(0)
            else:
                json_str_to_parse = generated_timeline_str.strip()
            
            timeline_data = json.loads(json_str_to_parse)
            timeline_output = json.dumps(timeline_data, indent=2)
            print(f"✓ Successfully generated timeline with {len(timeline_data)} events")
        except json.JSONDecodeError as e:
            print(f"Warning: Could not parse timeline JSON: {e}")
            timeline_output = json.dumps([{"error": "Failed to parse timeline", "raw": generated_timeline_str[:200]}], indent=2)
        
        return generated_article, timeline_output
        
    except Exception as e:
        print(f"Error generating report for cluster {cluster_id}: {e}")
        import traceback
        traceback.print_exc()
        return f"Error: {e}", None


def save_report_to_mongodb(cluster_id: int, article: str, timeline: str):
    """Saves the generated report to MongoDB."""
    try:
        from datetime import datetime
        client = MongoClient(MONGO_URI)
        db = client[DB_NAME]
        collection = db['reports']
        
        report_data = {
            "cluster_id": cluster_id,
            "article": article,
            "timeline": timeline,
            "generated_at": datetime.now().isoformat()
        }
        
        collection.update_one(
            {"cluster_id": cluster_id},
            {"$set": report_data},
            upsert=True
        )
        print(f"✓ Report saved to MongoDB for cluster {cluster_id}")
        client.close()
        return True
    except Exception as e:
        print(f"Error saving report: {e}")
        return False


def generate_reports_for_all_clusters():
    """Generates reports for all clusters with facts."""
    try:
        client = MongoClient(MONGO_URI)
        db = client[DB_NAME]
        facts_collection = db[FACTS_COLLECTION]
        
        cluster_ids = facts_collection.distinct("cluster_id")
        print(f"Found {len(cluster_ids)} clusters: {cluster_ids}")
        client.close()
        
        reports = {}
        for cluster_id in cluster_ids:
            print(f"\n{'='*60}")
            print(f"Processing Cluster {cluster_id}")
            print(f"{'='*60}")
            
            article, timeline = generate_report_for_cluster(cluster_id)
            
            if article and not article.startswith("Error"):
                reports[cluster_id] = {"article": article, "timeline": timeline}
                save_report_to_mongodb(cluster_id, article, timeline)
            else:
                print(f"Failed to generate report for cluster {cluster_id}")
        
        print(f"\n✓ Generated reports for {len(reports)} clusters")
        return reports
        
    except Exception as e:
        print(f"Error: {e}")
        return {}
# Add this function to article_generator.py to make it available for import
def get_all_facts_for_cluster(cluster_id: int) -> str:
    """Simply returns all facts as formatted text (no embeddings needed)."""
    facts = get_facts_for_cluster(cluster_id)
    
    if not facts:
        return "No facts available."
    
    formatted_facts = []
    for fact in facts:
        s = fact.get('subject', 'N/A')
        v = fact.get('verb', 'N/A')
        o = fact.get('object', 'N/A')
        source = fact.get('source', 'N/A')
        timestamp = fact.get('timestamp', 'N/A')
        
        fact_str = f"- {s} {v} {o} (Source: {source}, Timestamp: {timestamp})"
        formatted_facts.append(fact_str)
    
    return "\n".join(formatted_facts)

if __name__ == '__main__':
    print("="*60)
    print("ARTICLE AND TIMELINE GENERATOR (No FAISS Required)")
    print("="*60)
    
    if not os.getenv("GROQ_API_KEY"):
        print("⚠️  GROQ_API_KEY not found in .env file")
        print("Please add: GROQ_API_KEY=your_key_here")
        exit(1)
    
    # Generate report for cluster 23
    cluster_id = 23
    print(f"\nGenerating report for cluster {cluster_id}...")
    
    article, timeline = generate_report_for_cluster(cluster_id)
    
    if article and not article.startswith("Error"):
        print("\n" + "="*60)
        print("GENERATED ARTICLE")
        print("="*60)
        print(article)
        
        print("\n" + "="*60)
        print("GENERATED TIMELINE")
        print("="*60)
        print(timeline)
        
        # Save to file
        with open(f"report_cluster_{cluster_id}.json", "w") as f:
            json.dump({
                "cluster_id": cluster_id,
                "article": article,
                "timeline": timeline
            }, f, indent=2)
        print(f"\n✓ Saved to report_cluster_{cluster_id}.json")
        
        # Also save to MongoDB
        save_report_to_mongodb(cluster_id, article, timeline)
    else:
        print(f"\n❌ Failed: {article}")