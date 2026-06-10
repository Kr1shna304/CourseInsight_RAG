from groq import Groq
from config import GROQ_API_KEY, LLM_MODEL

_client = Groq(api_key=GROQ_API_KEY)


def generate_response(query, retrieved_chunks, chunk_type):
    if not retrieved_chunks or not chunk_type:
        return (
            "I couldn't find anything relevant in the loaded rule books. "
            "Try rephrasing your question — or check that your ingestion pipeline is working."
        )
    context_parts = []

    if chunk_type == "list_professors":
         context = retrieved_chunks['professors']
    elif chunk_type == "list_courses":
         context = retrieved_chunks['courses']
    else:
        for chunk in retrieved_chunks:
          context_parts.append(
                    f"""
            Professor: {chunk['professor']}
            Course: {chunk['course']}
            Type: {chunk['chunk_type']}

            {chunk['text']}
            """
                )
        context = "\n\n".join(context_parts)
    
    system_prompt = """

        You are CourseInsight.

        You answer questions about university professors and courses.

        Use only the provided context.

        Never invent information.

        When information is missing, explicitly state that it is not available and state this - "I could not find enough information from the student reviews to answer that question."
        When comparing professors:
        - Compare ratings
        - Compare difficulty
        - Compare review themes

        When ranking professors:
        - Use available ratings and review summaries
        - Explain reasoning

        Keep answers concise but informative.

        At the end of every answer, include a "Sources" section.

        For Sources:

        List the professor names used to generate the answer.
        If course-specific information was used, include both professor and course.
        Do not invent sources.
        Only cite professors present in the provided context.

        Example:
        Sources:
        Xin Yuan
        Andy Wang

        Keep answers concise but informative.


    """

    user_prompt = f"""

    Context:
    {context}

    Question:
    {query}
    """


    response = _client.chat.completions.create(
       model=LLM_MODEL,
       messages=[
          {"role": "system", "content": system_prompt},
          {"role": "user", "content": user_prompt},
      ],
  )

    
    # Your implementation here.
    return response.choices[0].message.content