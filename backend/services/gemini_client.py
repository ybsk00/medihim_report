import google.generativeai as genai
from config import GEMINI_API_KEY

genai.configure(api_key=GEMINI_API_KEY)

_model = None
_embedding_model = "models/gemini-embedding-001"


def get_model():
    global _model
    if _model is None:
        _model = genai.GenerativeModel("gemini-2.0-flash")
    return _model


async def generate_text(prompt: str, system_instruction: str = "") -> str:
    model = get_model()
    if system_instruction:
        model = genai.GenerativeModel(
            "gemini-2.0-flash",
            system_instruction=system_instruction,
        )
    response = model.generate_content(prompt)
    return response.text


async def generate_json(prompt: str, system_instruction: str = "") -> str:
    model = genai.GenerativeModel(
        "gemini-2.0-flash",
        system_instruction=system_instruction,
        generation_config=genai.GenerationConfig(
            response_mime_type="application/json",
        ),
    )
    response = model.generate_content(prompt)
    return response.text


async def get_embedding(text: str) -> list[float]:
    result = genai.embed_content(
        model=_embedding_model,
        content=text,
        task_type="retrieval_document",
        output_dimensionality=768,
    )
    return result["embedding"]


async def get_query_embedding(text: str) -> list[float]:
    result = genai.embed_content(
        model=_embedding_model,
        content=text,
        task_type="retrieval_query",
        output_dimensionality=768,
    )
    return result["embedding"]
