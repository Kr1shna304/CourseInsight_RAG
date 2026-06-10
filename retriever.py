import chromadb
from chromadb.utils import embedding_functions
from config import CHROMA_COLLECTION, CHROMA_PATH, EMBEDDING_MODEL, N_RESULTS
import re, os
from config import DOCS_PATH
from groq import Groq
from config import GROQ_API_KEY, LLM_MODEL
DATA_DIR = DOCS_PATH

INITIAL_RETRIEVAL = 10
FINAL_CONTEXT_SIZE = 5

MAX_COURSE_CHUNKS = 5
MAX_PROFESSOR_SUMMARIES = 10



# Embedding function and ChromaDB client are initialized once at module load.
# sentence-transformers downloads the model on first use — this may take
# 30–60 seconds the very first time. Subsequent runs use a local cache.
_ef = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name=EMBEDDING_MODEL
)
_client = chromadb.PersistentClient(path=CHROMA_PATH)
_collection = _client.get_or_create_collection(
    name=CHROMA_COLLECTION,
    embedding_function=_ef,
    metadata={"hnsw:space": "cosine"},
)


def get_collection():
    """Return the ChromaDB collection. Used by app.py during ingestion."""
    return _collection


def embed_and_store(chunks):
    """
    Embed a list of chunks and store them in the vector database.

    This function is already implemented — read through it before moving on.

    _collection.add() takes three parallel lists built from the chunks
    returned by chunk_document():
      - documents : raw text strings — ChromaDB's embedding function converts
                    these to vectors automatically using sentence-transformers
      - metadatas : one dict per chunk, stored alongside the vector so that
                    retrieve() can surface which game a result came from
      - ids       : the unique chunk_id strings used to identify each entry

    You don't generate embeddings manually here — you hand over the text
    and ChromaDB handles the vector math.
    """
    _collection.add(
        documents=[
            chunk["text"]
            for chunk in chunks
        ],

        metadatas=[
            chunk["metadata"]
            for chunk in chunks
        ],

        ids=[
            chunk["id"]
            for chunk in chunks
        ]
    )

    print(
        f"Stored {_collection.count()} chunks in vector database."
    )

client = Groq(api_key=GROQ_API_KEY)

def classify_query(query):
    professors = get_professor_names()
    courses = get_all_courses()

    prompt = f"""

      Query:
        {query}

        You are a query classifier for CourseInsight.

        Classify the user query into EXACTLY ONE category.

        ----------------------------------------
        professor_course
        ----------------------------------------

        The user mentions BOTH:

        - a professor
        AND
        - a course
        professor should be in {professors}
        course should be in {courses}
        The question is about that specific professor teaching that specific course.

        Examples:

        How is Xin Yuan for COP4530?
        Should I take COP3330 with Andy Wang?
        How difficult is COP4610 with Weikuan Yu?
        What do students think of Grigory Fedyukovich in CEN4020?

        ----------------------------------------
        professor
        ----------------------------------------

        The user is asking about a professor overall,
        across all courses and he should be in {professors}.

        Examples:

        Tell me about Xin Yuan.
        How is Andy Wang?
        Is David Whalley a good professor?
        What are students saying about Grigory Fedyukovich?

        ----------------------------------------
        course
        ----------------------------------------

        The user is asking about a course overall among many professors,
        but the course should be in {courses}.

        Examples:

        How hard is COP3330?
        What is COP4710 like?
        What should I expect from COP4530?
        Is COP5621 difficult?

        Also use this category for:
        - Best professor for a course
        - Easiest professor for a course
        - Who teaches a course
        - Recommendations for a course

        Examples:

        Who is best for COP3330?
        Who teaches COP4530?
        Who should I take for COP4710?
        Who is easiest for COP3330?

        ----------------------------------------
        comparison
        ----------------------------------------

        The user wants to compare two or more professors.
        The professors should be in {professors}.
        courses should be in {courses}
        Examples:

        Andy Wang vs Xin Yuan.
        Compare Xin Yuan and Weikuan Yu.
        Who is better, Andy Wang or Xin Yuan?
        Which professor should I choose between David Whalley and Gary Tyson?

        ----------------------------------------
        global_professor_analysis
        ----------------------------------------

        The user wants analysis across ALL professors.

        Examples:

        Who is the best professor overall?
        Who is the worst professor overall?
        Rank all professors.
        Who is the toughest grader?
        Who gives the most homework?
        Which professor explains concepts best?
        Which professor has the hardest exams?

        ----------------------------------------
        list_professors
        ----------------------------------------

        The user wants to see available professor names.

        Examples:

        List all professors.
        Which professors are available?
        Show all professors.
        What professors do you have data for?

        ----------------------------------------
        list_courses
        ----------------------------------------

        The user wants to see available course names.

        Examples:

        List all courses.
        Which courses are covered?
        Show available courses.
        What classes do you have information on?

        ----------------------------------------
        general
        ----------------------------------------

        Everything else.

        Examples:

        What data do you use?
        How does this application work?
        What is bioinformatics?
        Can you help me register for classes?
        What are the graduation requirements?

        Also use GENERAL when the query references a course,
        subject, professor, or topic that does not exist in the dataset.

        Examples:

        Suggest a professor for Bioinformatics.
        Who teaches Machine Learning?
        How is Artificial Intelligence at FSU?

        if those subjects are not present in the dataset.

        ----------------------------------------

        Return ONLY ONE category name.

        Do not explain.
        Do not provide reasoning.
        Return only the category itself.

      
        """

    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    return response.choices[0].message.content.strip()


def build_chunks(results):

    chunks = []

    for doc, meta in zip(
        results["documents"],
        results["metadatas"]
    ):

        chunks.append({
            "text": doc,
            "professor": meta["professor"],
            "course": meta["course"],
            "chunk_type": meta["chunk_type"]
        })

    return chunks

def semantic_search(query):

    results = _collection.query(
        query_texts=[query],
        n_results=INITIAL_RETRIEVAL,
        include=[
            "documents",
            "metadatas",
            "distances"
        ]
    )

    chunks = []

    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0]
    ):

        chunks.append({
            "text": doc,
            "professor": meta["professor"],
            "course": meta["course"],
            "chunk_type": meta["chunk_type"],
            "distance": dist
        })

    chunks.sort(
        key=lambda x: x["distance"]
    )

    return chunks[:FINAL_CONTEXT_SIZE]


def get_professor_summary(professor):

    results = _collection.get(
        where={
            "$and": [
                {"professor": professor},
                {"chunk_type": "professor_summary"}
            ]
        }
    )

    return build_chunks(results)

def get_course_chunks(course):

    results = _collection.get(
        where={
            "$and": [
                {"course": course},
                {"chunk_type": "course_summary"}
            ]
        }
    )

    return build_chunks(results)[:MAX_COURSE_CHUNKS]

def get_professor_course(professor, course):

    results = _collection.get(
        where={
            "$and": [
                {"professor": professor},
                {"course": course},
                {"chunk_type": "course_summary"}
            ]
        }
    )

    return build_chunks(results)

def get_all_professor_summaries():

    results = _collection.get(
        where={
            "chunk_type": "professor_summary"
        }
    )

    return build_chunks(results)

def get_professor_names():

    professors = []

    for filename in os.listdir(DATA_DIR):

        if filename.endswith(".txt"):

            professor = filename.replace(".txt", "")
            professor = professor.replace("_"," ")

            professors.append(professor)

    return professors


def extract_course(query):
    match = re.search(r"\b[A-Z]{3}\d{4}\b", query.upper())
    return match.group(0) if match else None


def extract_professors(query):
    found = []

    query_lower = query.lower()

    for professor in get_professor_names():
        if professor.lower() in query_lower:
            found.append(professor)

    return found

def get_all_courses():

    results = _collection.get(
        include=["metadatas"]
    )

    courses = set()

    for meta in results["metadatas"]:

        course = meta.get("course")

        if (
            course
            and course != "ALL"
        ):
            courses.add(course)

    return sorted(courses)


def get_course_names():
    return get_all_courses()


def retrieve(query):

    query_type = classify_query(query)

    professors = extract_professors(query)

    course = extract_course(query)

    print(f"\nQuery Type: {query_type}")

    # -------------------
    # List Professors
    # -------------------

    if query_type == "list_professors":

        return {
            "type": "professor_list",
            "professors": get_professor_names()
        }, "list_professors"
    
    # -------------------
    # List Courses
    # -------------------

    if query_type == "list_courses":

        return {
            "type": "course_list",
            "courses": get_course_names()
        }, "list_courses"

    # -------------------
    # Professor + Course
    # -------------------

    if query_type == "professor_course":

        return get_professor_course(
            professors[0],
            course
        ), "professor_course"

    # -------------------
    # Course Queries
    # -------------------

    if query_type == "course":

        return get_course_chunks(course), "course"

    # -------------------
    # Single Professor
    # -------------------

    if query_type == "professor":

        return get_professor_summary(
            professors[0]
        ), "professor"

    # -------------------
    # Comparison
    # -------------------

    if query_type == "comparison":

        chunks = []

        for professor in professors:

            if course:

                chunks.extend(
                    get_professor_course(
                        professor,
                        course
                    )
                )

            else:

                chunks.extend(
                    get_professor_summary(
                        professor
                    )
                )

        return chunks, "comparison"

    # -------------------
    # Global Analysis
    # -------------------

    if query_type == "global_professor_analysis":

        return get_all_professor_summaries(), "global_professor_analysis"

    # -------------------
    # Semantic Search
    # -------------------

    return semantic_search(query),"semantic_search"