import os
import chromadb
from dotenv import load_dotenv
from chromadb.utils import embedding_functions
from flask import Flask, render_template, request, jsonify

# Azure Inference API Client SDK
from azure.ai.inference import ChatCompletionsClient
from azure.ai.inference.models import SystemMessage, UserMessage
from azure.core.credentials import AzureKeyCredential

load_dotenv()  # Load environment variables from .env file

app = Flask(__name__)

# --- STEP 2: ChromaDB Path Configuration ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CHROMA_PATH = os.path.join(BASE_DIR, "chroma_storage")
chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)


# --- GitHub Inference Client Configuration ---
ENDPOINT = "https://models.github.ai/inference"
MODEL_NAME = "meta/Llama-4-Maverick-17B-128E-Instruct-FP8"
TOKEN = os.getenv("GITHUB_TOKEN")

client = ChatCompletionsClient(
    endpoint=ENDPOINT,
    credential=AzureKeyCredential(TOKEN),
)

def extract_course_code(text):
    """Extract a likely course code from the user's query."""
    import re
    pattern = re.compile(r"\b([A-Za-z]{2,4})\s*(\d{2,4}[A-Za-z]?)\b")
    match = pattern.search(text)
    if match:
        return (match.group(1) + match.group(2)).upper()
    return None


def retrieve_course_info(user_query):
    """Semantic Retrieval Engine: Fetches relevant course documents from ChromaDB."""
    chroma_db_dir = "chroma_storage"
    if not os.path.exists(chroma_db_dir):
        print("⚠️ Chroma DB folder missing! Run ingest.py first.")
        return ""

    try:
        chroma_client = chromadb.PersistentClient(path=chroma_db_dir)
        default_ef = embedding_functions.DefaultEmbeddingFunction()
        collection = chroma_client.get_collection(name="course_syllabi", embedding_function=default_ef)

        combined_context = ""
        course_code = extract_course_code(user_query)

        if course_code:
            print(f"🔎 Detected course code for filter: {course_code}")
            results = collection.query(
                query_texts=[user_query],
                n_results=5,
                where={"course_code": course_code}
            )
            if results and results.get("documents") and results["documents"][0]:
                combined_context += "\n--- Retrieved Course-specific Documents ---\n"
                for doc in results["documents"][0]:
                    combined_context += f"{doc}\n"
                return combined_context

        # Fallback: general semantic search across all courses
        results = collection.query(
            query_texts=[user_query],
            n_results=4
        )

        if results and results.get("documents"):
            combined_context += "\n--- Retrieved Relevant Course Documents ---\n"
            for doc in results["documents"][0]:
                combined_context += f"{doc}\n"
        return combined_context
    except Exception as e:
        print(f"Error querying ChromaDB: {e}")
        return ""

# =====================================================================
# Flask Routing Layer
# =====================================================================

@app.route("/")
def home():
    """Serves the front-end chat webpage interface."""
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    """Core RAG Pipeline execution endpoint."""
    user_data = request.json
    user_query = user_data.get("message", "")
    
    if not user_query:
        return jsonify({"response": "Please enter a valid question."})

    # 🎯 Step 1: Query Optimization to prevent missing course codes (e.g., EE214 vs EE 214)
    try:
        routing_check = client.complete(
            messages=[
                SystemMessage(
                    "You are an intent classifier and database search optimizer.\n"
                    "If the user is saying hello or small talk, reply exactly with: GREETING\n\n"
                    "If they are asking about a course, reply with just the query that has to be used in searching and nothing else. " 
                    "We want to embed and use the query to search in the vector DB where the course information is embedded."
                    "Use the course code and/or other keywords that the user provides to create a query for the vector DB such that we are able to accurately retrieve the relevant course information."
                    "Do not make up any course codes yourself."
                    "Provide variations of the code if necessary, with and without spaces, plus topic keywords to optimize vector search.\n"
                    "If the user asks for a department, class type, or credit details, still produce a query using the subject keywords."
                    "Prefer exact course code matches when present, but include fallback keywords when the code alone may not be enough."
                    "If the question contains a strong course-related phrase, output that phrase plus the normalized code."
                    # "Example: 'tell me about mm152' -> 'MM152 MM 152 Materials Technology Metallurgy structure properties'\n"
                    # "Example: 'tell me about structure of materials' -> 'MM201 MM 201 Structure of Materials Crystallography'"
                ),
                UserMessage(user_query),
            ],
            temperature=0.1,
            model=MODEL_NAME
        )
        intent_result = routing_check.choices[0].message.content.strip()
    except Exception as e:
        print(f"Routing expansion failed, fallback to raw query. Error: {e}")
        intent_result = user_query

    # 🎯 Step 2: Handle Greetings without reaching into the Vector DB
    if "GREETING" in intent_result:
        try:
            response = client.complete(
                messages=[
                    SystemMessage("You are a friendly university Course Chatbot. Greet the student nicely and ask how you can help them with their curriculum questions today. Do not mention specific courses yet."),
                    UserMessage(user_query),
                ],
                temperature=0.7,
                model=MODEL_NAME
            )
            return jsonify({"response": response.choices[0].message.content})
        except Exception as e:
            return jsonify({"response": f"Error: {str(e)}"})

    # 🎯 Step 3: Retrieval & Augmentation
    print(f"🔍 Optimised Query passed to ChromaDB: '{intent_result}'")
    retrieved_context = retrieve_course_info(intent_result)
    print(f"📄 Retrieved Context:\n{retrieved_context}")

    # 🎯 Step 4: Final Answer Generation Grounded on Your Custom Data
    try:
        response = client.complete(
            messages=[
                SystemMessage(
                    "You are a helpful university Course Chatbot. Use the provided context containing "
                    "the relevant course reviews and syllabus documents to answer the student's question accurately. "
                    "Rely strictly on the text facts provided. If the answer cannot be found in the context, "
                    "say 'I don't have that information.'\n\n"
                    f"CONTEXT:\n{retrieved_context}"
                ),
                UserMessage(user_query),
            ],
            temperature=0.3,
            max_tokens=2048,
            model=MODEL_NAME
        )
        bot_reply = response.choices[0].message.content
    except Exception as e:
        bot_reply = f"Error communicating with Llama-4 engine: {str(e)}"

    return jsonify({"response": bot_reply})

if __name__ == "__main__":
    app.run(debug=True)
