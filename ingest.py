from collections import Counter
import os
from config import DOCS_PATH
import re
DATA_DIR = DOCS_PATH

def parse_professor_document(text):

    professor_match = re.search(r"Professor:\s*(.*)", text)
    rating_match = re.search(r"Overall Rating:\s*([\d.]+)", text)
    difficulty_match = re.search(r"Overall Difficulty:\s*([\d.]+)", text)

    professor = professor_match.group(1).strip()
    overall_rating = float(rating_match.group(1))
    overall_difficulty = float(difficulty_match.group(1))

    course_sections = re.split(r"\n={10,}\n", text)

    courses = {}

    for section in course_sections:

        course_match = re.search(r"Course:\s*([A-Z]+\d+)", section)

        if not course_match:
            continue

        course_name = course_match.group(1)

        reviews = re.split(r"\n---\n", section)

        parsed_reviews = []

        for review_text in reviews:

            quality = re.search(r"Quality:\s*([\d.]+)", review_text)
            difficulty = re.search(r"Difficulty:\s*([\d.]+)", review_text)
            attendance = re.search(r"Attendance:\s*(.*)", review_text)
            would_take_again = re.search(
                r"Would Take Again:\s*(.*)", review_text
            )
            grade = re.search(
                r"Grade Received:\s*(.*)", review_text
            )
            textbook = re.search(
                r"Textbook:\s*(.*)", review_text
            )

            review_body = re.search(
                r"Review:\s*(.*?)\n\s*Tags:",
                review_text,
                re.DOTALL
            )

            parsed_reviews.append({
                "quality":
                    float(quality.group(1)) if quality else None,
                "difficulty":
                    float(difficulty.group(1)) if difficulty else None,
                "attendance":
                    attendance.group(1).strip() if attendance else "Unknown",
                "would_take_again":
                    would_take_again.group(1).strip()
                    if would_take_again else "Unknown",
                "grade":
                    grade.group(1).strip()
                    if grade else "Unknown",
                "textbook":
                    textbook.group(1).strip()
                    if textbook else "Unknown",
                "review":
                    review_body.group(1).strip()
                    if review_body else ""
            })

        courses[course_name] = parsed_reviews

    return {
        "professor": professor,
        "overall_rating": overall_rating,
        "overall_difficulty": overall_difficulty,
        "courses": courses
    }


def build_course_chunk(
    professor,
    overall_rating,
    overall_difficulty,
    course,
    reviews
):

    review_count = len(reviews)

    avg_quality = round(
        sum(r["quality"] for r in reviews if r["quality"])
        / review_count,
        2
    )

    avg_difficulty = round(
        sum(r["difficulty"] for r in reviews if r["difficulty"])
        / review_count,
        2
    )

    attendance_counter = Counter(
        r["attendance"] for r in reviews
    )

    take_again_counter = Counter(
        r["would_take_again"] for r in reviews
    )

    textbook_counter = Counter(
        r["textbook"] for r in reviews
    )

    grade_counter = Counter(
        r["grade"] for r in reviews
    )

    review_text = "\n\n".join(
        r["review"] for r in reviews
    )

    chunk_text = f"""
        Professor: {professor}

        Course: {course}

        Overall Professor Rating: {overall_rating}/5
        Overall Professor Difficulty: {overall_difficulty}/5

        Review Count: {review_count}

        Average Quality: {avg_quality}
        Average Difficulty: {avg_difficulty}

        Attendance:
        {dict(attendance_counter)}

        Would Take Again:
        {dict(take_again_counter)}

        Textbook:
        {dict(textbook_counter)}

        Grades:
        {dict(grade_counter)}

        Student Reviews:
        {review_text}
        """

    return {
        "id": f"{professor}_{course}".lower().replace(" ", "_"),
        "text": chunk_text,
        "metadata": {
            "professor": professor,
            "course": course,
            "chunk_type": "course_summary",
            "overall_rating": overall_rating,
            "overall_difficulty": overall_difficulty
        }
    }

def build_professor_summary(parsed_doc):

    professor = parsed_doc["professor"]

    summary = f"""
            Professor: {professor}

            Overall Rating: {parsed_doc['overall_rating']}/5
            Overall Difficulty: {parsed_doc['overall_difficulty']}/5

            Courses:
            """

    total_reviews = 0

    for course, reviews in parsed_doc["courses"].items():

        total_reviews += len(reviews)

        avg_quality = round(
            sum(r["quality"] for r in reviews if r["quality"])
            / len(reviews),
            2
        )

        avg_difficulty = round(
            sum(r["difficulty"] for r in reviews if r["difficulty"])
            / len(reviews),
            2
        )

        summary += f"""

        {course}
        Average Quality: {avg_quality}
        Average Difficulty: {avg_difficulty}
        Review Count: {len(reviews)}
        """

    summary += f"\n\nTotal Reviews: {total_reviews}"

    return {
        "id": f"{professor}_summary".lower().replace(" ", "_"),
        "text": summary,
        "metadata": {
            "professor": professor,
            "course": "ALL",
            "chunk_type": "professor_summary",
            "overall_rating": parsed_doc["overall_rating"],
            "overall_difficulty": parsed_doc["overall_difficulty"]
        }
    }

def load_documents():
    """
    Loads all professor documents from data folder.
    """

    documents = []

    for filename in os.listdir(DATA_DIR):

        if not filename.endswith(".txt"):
            continue

        filepath = os.path.join(DATA_DIR, filename)

        with open(filepath, "r", encoding="utf-8") as f:

            documents.append(
                {
                    "filename": filename,
                    "text": f.read()
                }
            )

    print(f"Loaded {len(documents)} professor files.")

    return documents


def build_chunks(documents):
    all_chunks = []

    for doc in documents:

        parsed = parse_professor_document(
            doc["text"]
        )

        for course, reviews in parsed["courses"].items():

            course_chunk = build_course_chunk(
                parsed["professor"],
                parsed["overall_rating"],
                parsed["overall_difficulty"],
                course,
                reviews
            )

            all_chunks.append(course_chunk)

        professor_chunk = build_professor_summary(
            parsed
        )

        all_chunks.append(professor_chunk)

    return all_chunks