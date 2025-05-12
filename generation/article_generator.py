import os
import json
from pymongo import MongoClient
from dotenv import load_dotenv
import re
from sentence_transformers import SentenceTransformer
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough, RunnableLambda

# Load environment variables (for GROQ_API_KEY)
load_dotenv()

# MongoDB connection details
MONGO_URI = 'mongodb://localhost:27017/'
DB_NAME = 'biaslens'
FACTS_COLLECTION = 'facts'

# Embedding model (consistent with your clustering if desired)
EMBEDDING_MODEL_NAME = 'all-MiniLM-L6-v2'


def get_facts_for_cluster(cluster_id: int) -> list:  # Changed type hint to int
    """
    Retrieves all facts for a given cluster_id from MongoDB.
    """
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    collection = db[FACTS_COLLECTION]
    # Exclude MongoDB's _id from the returned fact documents for cleaner metadata
    # Assuming cluster_id is stored as an int in MongoDB
    facts = list(collection.find({"cluster_id": cluster_id}, {"_id": 0}))
    client.close()
    return facts


# Changed type hint to int
def create_fact_embeddings_and_build_retriever(cluster_id: int, embedding_model_service):
    """
    Fetches facts for a cluster, creates text representations, generates embeddings,
    and builds a Langchain retriever.
    """
    facts = get_facts_for_cluster(cluster_id)
    if not facts:
        print(f"No facts found for cluster {cluster_id}.")
        return None

    fact_texts = []
    fact_metadatas = []

    for fact in facts:
        s = fact.get('subject', '')
        v = fact.get('verb', '')
        o = fact.get('object', '')
        text_representation = f"Subject: {s}, Verb: {v}, Object: {o}."
        if fact.get('source'):
            text_representation += f" Source: {fact.get('source')}."
        if fact.get('timestamp'):
            text_representation += f" Timestamp: {fact.get('timestamp')}."

        fact_texts.append(text_representation)
        fact_metadatas.append(fact)

    if not fact_texts:
        print(f"No fact texts to embed for cluster {cluster_id}.")
        return None

    vectorstore = FAISS.from_texts(
        texts=fact_texts, embedding=embedding_model_service, metadatas=fact_metadatas)
    return vectorstore.as_retriever(search_kwargs={"k": 100})


def format_retrieved_facts_for_article(docs) -> str:
    """Formats retrieved Langchain Document objects for the article prompt context."""
    if not docs:
        return "[]"
    formatted_facts = []
    for doc in docs:
        fact = doc.metadata
        formatted_facts.append(
            json.dumps({
                "subject": fact.get('subject', 'N/A'),
                "verb": fact.get('verb', 'N/A'),
                "object": fact.get('object', 'N/A'),
                "source": fact.get('source', 'N/A'),
                "timestamp": fact.get('timestamp', 'N/A')
            })
        )
    return "[\n  " + ",\n  ".join(formatted_facts) + "\n]"


def format_retrieved_facts_for_timeline(docs) -> str:
    """Formats retrieved Langchain Document objects for the timeline prompt context."""
    if not docs:
        return "[]"
    formatted_facts = []
    for doc in docs:
        fact = doc.metadata
        formatted_facts.append(
            json.dumps({
                "subject": fact.get('subject', 'N/A'),
                "verb": fact.get('verb', 'N/A'),
                "object": fact.get('object', 'N/A'),
                "timestamp": fact.get('timestamp', 'N/A'),
                "source": fact.get('source', 'N/A')
            })
        )
    return "[\n  " + ",\n  ".join(formatted_facts) + "\n]"


# 3.  Source Attribution:
    # *   If multiple sources report a similar fact, synthesize the fact and list all corroborating sources as a single citation (e.g., "[Source A, Source B]").
    # *   If a fact is unique to one source, attribute it directly (e.g., "according to Source C," or "Source C reported...").
    # *   Avoid repetitive source mentions for each detail if a paragraph clearly draws from the same set of cited sources.
UNBIASED_ARTICLE_PROMPT_TEMPLATE = """System: You are a highly precise and experienced article writer. Your sole function is to synthesize provided facts into a neutral, objective news report. Adhere strictly to journalistic neutrality.

User: Generate a detailed, unbiased news article based ONLY on the facts below for Cluster ID {cluster_id}.
Key Directives:
1.  Factual Purity: Report ONLY information explicitly stated in the provided 'Context' facts. NO inference, speculation, or external information.
2.  Neutral Language: Employ strictly objective terminology. Avoid emotive, loaded, or biased phrasing.
5.  Focus: Prioritize facts that are corroborated by multiple sources. If facts conflict, present the differing accounts neutrally, attributing each.

Context (Facts for Cluster ID {cluster_id}):
{context}

Generate the unbiased news article:"""

TIMELINE_JSON_PROMPT_TEMPLATE = """System: You are an AI assistant that creates structured JSON timelines from factual data. Your response MUST be a single, valid JSON array of event objects and nothing else. Do not include any explanatory text or markdown formatting outside of the JSON itself.

User: Based ONLY on the facts below for Cluster ID {cluster_id}, generate a JSON array for a chronological timeline.
Schema for each timeline event object: {{ "timestamp": "YYYY-MM-DDTHH:MM:SSZ", "event_summary": "Concise SVO fact summary", "sources": ["Source A", "Source B"] }}
Guidelines:
1.  Chronological Order: Strictly by timestamp (earliest to latest).
2.  Event Summary: A brief subject-verb-object summary of the event.
3.  Sources: List all sources that reported this specific event/fact in the "sources" array.
4.  Timestamp Handling: If a timestamp is missing/invalid, use "null" as the value for the "timestamp" key, or a placeholder like "Timestamp N/A".
5.  Validity: Ensure the output is a single, valid JSON array of event objects. Adhere strictly to the schema.

Context (Facts for Cluster ID {cluster_id}):
{context}

Generate ONLY the JSON array:"""


# Changed type hint to int
def generate_report_for_cluster_langchain_groq(cluster_id: int) -> tuple[str | None, str | None]:
    """
    Generates an unbiased article and a timeline JSON for a given cluster_id
    using Langchain and Groq.
    Returns a tuple: (article_text, timeline_json_string)
    """
    groq_api_key = os.getenv("GROQ_API_KEY")
    if not groq_api_key:
        return "Error: GROQ_API_KEY not found in environment variables.", None

    try:
        llm = ChatGroq(model_name="llama3-8b-8192",
                       groq_api_key=groq_api_key, temperature=0.0)
        embedding_model_service = HuggingFaceEmbeddings(
            model_name=EMBEDDING_MODEL_NAME)

        retriever = create_fact_embeddings_and_build_retriever(
            cluster_id, embedding_model_service)
        if not retriever:
            return f"No facts found or could not build retriever for cluster {cluster_id}.", None

        # Helper functions to invoke the scoped retriever with a generic string query
        def get_article_context(_input_from_chain):
            # _input_from_chain is the cluster_id, not used for query here as retriever is scoped
            docs = retriever.invoke(
                "all relevant facts for article generation")
            return format_retrieved_facts_for_article(docs)

        def get_timeline_context(_input_from_chain):
            docs = retriever.invoke(
                "all relevant facts for timeline generation")
            return format_retrieved_facts_for_timeline(docs)

        # --- Generate Unbiased Article ---
        article_prompt = ChatPromptTemplate.from_template(
            UNBIASED_ARTICLE_PROMPT_TEMPLATE)

        article_chain = (
            {
                "context": RunnableLambda(get_article_context),
                "cluster_id": RunnablePassthrough()
            }
            | article_prompt
            | llm
            | StrOutputParser()
        )
        # The input to invoke (cluster_id) is passed to RunnablePassthrough
        # and as input to RunnableLambda(get_article_context)
        generated_article = article_chain.invoke(cluster_id)

        # --- Generate Timeline JSON ---
        timeline_prompt = ChatPromptTemplate.from_template(
            TIMELINE_JSON_PROMPT_TEMPLATE)

        timeline_chain = (
            {
                "context": RunnableLambda(get_timeline_context),
                "cluster_id": RunnablePassthrough()
            }
            | timeline_prompt
            | llm
            | StrOutputParser()
        )
        generated_timeline_str = timeline_chain.invoke(cluster_id)

        timeline_output = None
        try:
            # Try to find JSON within backticks (```json ... ``` or ``` ... ```)
            match = re.search(
                r"```(?:json)?\s*([\s\S]*?)\s*```", generated_timeline_str, re.DOTALL)
            if match:
                json_str_to_parse = match.group(1).strip()
            else:
                # If no backticks, assume the whole string is JSON (or an attempt at it)
                json_str_to_parse = generated_timeline_str.strip()

            # The LLM might still truncate. We can't easily fix a fundamentally broken JSON string here.
            # The hope is that by asking for ONLY JSON, it's less likely to be truncated badly.
            timeline_data = json.loads(json_str_to_parse)
            # Re-serialize to ensure clean JSON string
            timeline_output = json.dumps(timeline_data)
        except json.JSONDecodeError as e:
            print(
                f"Warning: LLM did not return valid JSON for timeline (cluster {cluster_id}). Error: {e}")
            # Log more of the raw output
            print(
                f"LLM raw output for timeline: {generated_timeline_str[:500]}")
            timeline_output = json.dumps(
                [{"error": "Failed to generate valid timeline JSON from LLM.", "details": generated_timeline_str[:200]}])

        return generated_article, timeline_output

    except Exception as e:
        print(
            f"Error in Langchain/Groq generation for cluster {cluster_id}: {e}")
        # import traceback
        # traceback.print_exc() # For more detailed error logging during development
        return f"Error during generation: {e}", None


if __name__ == '__main__':
    # client = MongoClient(MONGO_URI)
    # db = client[DB_NAME]
    # facts_collection = db[FACTS_COLLECTION]
    # if facts_collection.count_documents({"cluster_id": 0}) == 0: # Assuming cluster_id 0 for testing
    #     print("Inserting dummy facts for cluster_id 0 for testing...")
    #     dummy_facts = [
    #         {"subject": "Company A", "verb": "launched", "object": "a new product", "article_id": "art1", "cluster_id": 0, "source": "Tech News", "timestamp": "2025-05-12T09:00:00Z"},
    #         {"subject": "Analysts", "verb": "predict", "object": "strong sales", "article_id": "art2", "cluster_id": 0, "source": "Finance Weekly", "timestamp": "2025-05-12T11:00:00Z"},
    #         {"subject": "Company B", "verb": "responded", "object": "with a statement", "article_id": "art3", "cluster_id": 0, "source": "Competitor Monitor", "timestamp": "2025-05-12T14:00:00Z"}
    #     ]
    #     facts_collection.insert_many(dummy_facts)
    # client.close()

    test_cluster_id = 54  # Using int as per the error and likely origin
    print(
        f"Generating report for cluster: {test_cluster_id} using Langchain and Groq...")

    article, timeline_json_str = generate_report_for_cluster_langchain_groq(
        test_cluster_id)

    print("\n--- Generated Unbiased Article ---")
    if article:
        print(article)
    else:
        print("Failed to generate article.")

    print("\n--- Generated Timeline (JSON String) ---")
    if timeline_json_str:
        print(timeline_json_str)
        try:
            timeline_data = json.loads(timeline_json_str)
            print("\n--- Parsed Timeline Data (for verification) ---")
            for item in timeline_data:
                print(item)
        except json.JSONDecodeError as e:
            print(f"\nError: Could not parse timeline JSON: {e}")
    else:
        print("Failed to generate timeline.")
