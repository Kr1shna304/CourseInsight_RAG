import gradio as gr
from ingest import load_documents, build_chunks
from retriever import embed_and_store, retrieve, get_collection
from generator import generate_response


# ---------------------------------------------------------------------------
# Ingestion — runs once on startup
# ---------------------------------------------------------------------------

def run_ingestion():
    collection = get_collection()

    if collection.count() > 0:
        print(
            f"Vector store already populated "
            f"({collection.count()} chunks)."
        )
        return

    print("Starting ingestion...")

    documents = load_documents()

    all_chunks = build_chunks(documents)

    embed_and_store(all_chunks)

    print(
        f"Ingestion complete. "
        f"{len(all_chunks)} chunks stored."
    )


# ---------------------------------------------------------------------------
# Chat handler
# ---------------------------------------------------------------------------

def chat(message, history):
    if not message.strip():
        return ""
    result = retrieve(message)

    if isinstance(result, tuple) and len(result) == 2:
        retrieved, query_type = result
    else:
        # retrieve() may return an empty string or None when nothing valid
        retrieved, query_type = None, None

    return generate_response(message, retrieved, query_type)


# ---------------------------------------------------------------------------
# Gradio UI
# ---------------------------------------------------------------------------


with gr.Blocks(
    theme=gr.themes.Soft(primary_hue="red"),
    title="CourseInsight"
) as demo:

    # Header
    gr.HTML("""
        <div style="text-align:center; padding:1.25rem 0 0.5rem;">
            <h1 style="font-size:2rem; font-weight:700; margin:0;">
    <span style="color:#782F40;">🎓 Course</span><span style="color:#CEB888;">Insight</span>
     </h1>
            <p style="color:#6B7280; font-size:1rem; margin:0.4rem 0 0;">
                Your unofficial guide to choosing professors and courses — grounded in real student reviews.
            </p>
        </div>
    """)

    with gr.Row():

        # MAIN CHAT COLUMN
        with gr.Column(scale=3):

            gr.ChatInterface(
                fn=chat,
                type="messages",
                chatbot=gr.Chatbot(
                    height=440,
                    type="messages",
                    placeholder=(
                        "<div style='text-align:center; color:#782f40; margin-top:3rem; font-size:1.05rem;'>"
                        "Ask about CS professors, workloads, and courses before rolling the semester dice. 🎲"
                        "</div>"
                    ),
                ),

                textbox=gr.Textbox(
                    placeholder=(
                        "e.g. who takes care of students in COP3330?"
                        "Who is easier for COP3330?"
                    ),
                    container=False,
                    scale=7,
                    show_label=False,
                ),

                examples=[
                    "How is Xin Yuan for COP4530?",
                    "Who is better for COP3330, Andy Wang or Xin Yuan?",
                    "Which professor is easiest for COP4710?",
                    "How heavy is workload in CEN4020?",
                    "What are ratings for David Whalley?",
                    "Which professor has the best reviews overall?"
                ],

                cache_examples=False,
            )

        # SIDEBAR
        with gr.Column(scale=1, min_width=220):

            gr.HTML("""
                <div style="
                    background:#CEB888;
                    border:1px solid #CEB888;
                    border-radius:12px;
                    padding:1rem;
                    margin-top:0.5rem;
                    box-shadow:0 2px 6px rgba(0,0,0,0.05);
                ">

                    <p style="
                        font-size:0.8rem;
                        font-weight:700;
                        color:#782F40;
                        margin:0 0 0.5rem;
                        letter-spacing:0.05em;
                    ">
                        📚 DATASET COVERAGE
                    </p>

                    <ul style="
                        font-size:0.85rem;
                        color:#000000 !important;
                        list-style:none;
                        padding:0;
                        margin:0;
                        line-height:1.9;
                    ">
                        <li>👨‍🏫 FSU CS Professors</li>
                        <li>📘 Course Reviews</li>
                        <li>⭐ Ratings & Difficulty</li>
                        <li>💬 Student Feedback</li>
                        <li>📊 Professor-Course Insights</li>
                    </ul>

                    <hr style="
                        border:none;
                        border-top:1px solid #CEB888;
                        margin:0.9rem 0;
                    ">

                    <p style="
                        font-size:0.75rem;
                        color:#782F40 !important;
                        margin:0;
                        line-height:1.5;
                    ">
                        Answers are generated only from retrieved student reviews.
                        This system summarizes student experiences and does not use official university grading data.
                    </p>
                </div>
            """)



if __name__ == "__main__":
    print("\n" + "="*50)
    print("  CourseInsight — starting up")
    print("="*50 + "\n")
    run_ingestion()
    demo.launch()
