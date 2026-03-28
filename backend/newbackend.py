import json
import os
import re
from pathlib import Path
from typing import Any
from uuid import uuid4

import pandas as pd
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from google import genai
from pydantic import BaseModel, Field
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

load_dotenv()

app = FastAPI(title="Memphis Booking AI - Hybrid Recommender")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class HybridRecommendRequest(BaseModel):
    query: str = Field(..., min_length=1)
    top_k: int = Field(default=7, ge=1, le=20)
    candidate_pool: int = Field(default=15, ge=7, le=50)


class ChatRecommendRequest(BaseModel):
    message: str = Field(..., min_length=1)
    session_id: str | None = None
    reset_session: bool = False
    top_k: int = Field(default=7, ge=1, le=20)
    candidate_pool: int = Field(default=15, ge=7, le=50)


class AddArtistRequest(BaseModel):
    name: str = Field(..., min_length=1)
    genre: str = Field(..., min_length=1)
    descriptors: str = ""
    resources: str = ""
    social: str = ""


data_path = Path(__file__).with_name("memphisbanddata.csv")
df = pd.read_csv(data_path)

required_columns = {"Artist Name", "Genre"}
optional_columns = {"Descriptors", "Resources", "Social"}
missing_columns = required_columns - set(df.columns)
if missing_columns:
    raise ValueError(
        f"CSV is missing required columns: {sorted(missing_columns)}")

for column in optional_columns:
    if column not in df.columns:
        df[column] = ""

for column in required_columns.union(optional_columns):
    df[column] = df[column].fillna("").astype(str).str.strip()


def _normalize_text(value: str) -> str:
    cleaned = str(value).lower().strip()
    cleaned = re.sub(r"https?://\S+", " ", cleaned)
    cleaned = re.sub(r"[^a-z0-9\s,\-/&]", " ", cleaned)
    cleaned = cleaned.replace(",", " ")
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()


def _rebuild_match_content() -> None:
    genre_signal = df["Genre"].map(_normalize_text)
    descriptor_signal = df["Descriptors"].map(_normalize_text)

    # Weight genre and descriptors more heavily for stronger overlap between similar artists.
    df["MatchContent"] = (
        genre_signal
        + " "
        + genre_signal
        + " "
        + descriptor_signal
        + " "
        + descriptor_signal
    ).str.strip()


_rebuild_match_content()

artist_lookup = {name.strip().lower(): idx for idx,
                 name in enumerate(df["Artist Name"])}

tfidf = None
tfidf_matrix = None
cosine_sim = None


def _rebuild_similarity_index() -> None:
    global artist_lookup, tfidf, tfidf_matrix, cosine_sim
    artist_lookup = {name.strip().lower(): idx for idx,
                     name in enumerate(df["Artist Name"])}
    _rebuild_match_content()
    tfidf = TfidfVectorizer(
        stop_words="english",
        ngram_range=(1, 2),
        sublinear_tf=True,
    )
    tfidf_matrix = tfidf.fit_transform(df["MatchContent"])
    cosine_sim = cosine_similarity(tfidf_matrix, tfidf_matrix)


_rebuild_similarity_index()

chat_sessions: dict[str, list[dict[str, str]]] = {}
MAX_CHAT_MESSAGES = 8

gemini_client = None
if os.getenv("GEMINI_API_KEY"):
    gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
elif os.getenv("GOOGLE_API_KEY"):
    gemini_client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
else:
    try:
        gemini_client = genai.Client()
    except Exception:
        gemini_client = None


def _frame_from_indices(indices: list[int], scores: list[float]) -> pd.DataFrame:
    recommendations = df.loc[indices, [
        "Artist Name", "Genre", "Descriptors", "Resources", "Social"]].copy()

    raw_scores = [float(score) for score in scores]
    if raw_scores:
        min_score = min(raw_scores)
        max_score = max(raw_scores)
        score_range = max_score - min_score
        if score_range <= 1e-9:
            normalized_scores = [1.0 for _ in raw_scores]
        else:
            normalized_scores = [(score - min_score) /
                                 score_range for score in raw_scores]
    else:
        normalized_scores = []

    recommendations["raw_match_score"] = [
        round(score, 4) for score in raw_scores]
    recommendations["match_score"] = [
        round(score, 4) for score in normalized_scores]
    recommendations["reason"] = "Local similarity match."
    return recommendations


def _local_candidates_from_artist(artist_name: str, candidate_pool: int) -> pd.DataFrame:
    idx = artist_lookup[artist_name.strip().lower()]
    sim_scores = list(enumerate(cosine_sim[idx]))
    sim_scores.sort(key=lambda x: x[1], reverse=True)
    sim_scores = sim_scores[1: candidate_pool + 1]
    indices = [index for index, _ in sim_scores]
    scores = [score for _, score in sim_scores]
    return _frame_from_indices(indices, scores)


def _local_candidates_from_query(query: str, candidate_pool: int) -> pd.DataFrame:
    query_text = _normalize_text(query)
    query_vec = tfidf.transform([query_text])
    sims = cosine_similarity(query_vec, tfidf_matrix).flatten()
    sorted_pairs = sorted(enumerate(sims), key=lambda x: x[1], reverse=True)[
        :candidate_pool]
    indices = [index for index, _ in sorted_pairs]
    scores = [score for _, score in sorted_pairs]
    return _frame_from_indices(indices, scores)


def _extract_json(text: str) -> dict[str, Any]:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}", text)
        if not match:
            raise ValueError("Gemini response did not contain JSON")
        return json.loads(match.group(0))


def _gemini_rerank(query: str, candidates: pd.DataFrame, top_k: int) -> list[dict[str, Any]]:
    if gemini_client is None:
        raise RuntimeError("Gemini client is not configured")

    candidate_rows = candidates.to_dict(orient="records")
    prompt = (
        "You are reranking local music artist recommendations for booking.\n"
        "User query: "
        f"{query}\n"
        "Return ONLY valid JSON with this exact schema:\n"
        "{\"recommendations\":[{\"artist\":string,\"score\":number,\"reason\":string}]}\n"
        f"Choose at most {top_k} artists. Use only artists from this candidate list.\n"
        "Do not invent artists. Do not include markdown.\n"
        f"Candidates: {json.dumps(candidate_rows, ensure_ascii=False)}"
    )

    response = gemini_client.models.generate_content(
        model="gemini-3-flash-preview",
        contents=prompt,
    )
    parsed = _extract_json(response.text or "")
    recommendations = parsed.get("recommendations")
    if not isinstance(recommendations, list):
        raise ValueError("Gemini output missing recommendations list")
    return recommendations


def _finalize_recommendations(
    local_candidates: pd.DataFrame,
    gemini_items: list[dict[str, Any]] | None,
    top_k: int,
) -> list[dict[str, Any]]:
    candidate_map = {
        row["Artist Name"]: row
        for row in local_candidates.to_dict(orient="records")
    }

    output = []
    used = set()

    if gemini_items:
        for item in gemini_items:
            artist = str(item.get("artist", "")).strip()
            if not artist or artist in used or artist not in candidate_map:
                continue
            candidate = candidate_map[artist]
            reason = str(item.get("reason", "")).strip(
            ) or "Gemini reranked candidate."
            try:
                score = float(item.get("score", candidate["match_score"]))
            except (TypeError, ValueError):
                score = float(candidate["match_score"])

            output.append(
                {
                    "artist": artist,
                    "genre": candidate["Genre"],
                    "descriptors": candidate.get("Descriptors", ""),
                    "resources": candidate["Resources"],
                    "social": candidate["Social"],
                    "match_score": round(max(0.0, min(score, 1.0)), 4),
                    "raw_match_score": round(float(candidate.get("raw_match_score", 0.0)), 4),
                    "reason": reason,
                }
            )
            used.add(artist)
            if len(output) == top_k:
                return output

    for _, candidate in local_candidates.iterrows():
        artist = candidate["Artist Name"]
        if artist in used:
            continue
        output.append(
            {
                "artist": artist,
                "genre": candidate["Genre"],
                "descriptors": candidate.get("Descriptors", ""),
                "resources": candidate["Resources"],
                "social": candidate["Social"],
                "match_score": round(float(candidate["match_score"]), 4),
                "raw_match_score": round(float(candidate.get("raw_match_score", 0.0)), 4),
                "reason": "Local similarity match.",
            }
        )
        used.add(artist)
        if len(output) == top_k:
            break

    return output


def _should_skip_gemini(local_candidates: pd.DataFrame, top_k: int) -> bool:
    if local_candidates.empty or len(local_candidates) < top_k:
        return False
    top_score = float(local_candidates.iloc[0]["raw_match_score"])
    return top_score >= 0.55


def _run_hybrid(query: str, top_k: int, candidate_pool: int) -> dict[str, Any]:
    candidate_pool = max(candidate_pool, top_k)
    query_key = query.lower()

    if query_key in artist_lookup:
        local_candidates = _local_candidates_from_artist(query, candidate_pool)
    else:
        local_candidates = _local_candidates_from_query(query, candidate_pool)

    local_candidates = local_candidates.reset_index(drop=True)

    used_gemini = False
    gemini_error = None
    gemini_items = None

    if not _should_skip_gemini(local_candidates, top_k):
        try:
            gemini_items = _gemini_rerank(query, local_candidates, top_k)
            used_gemini = True
        except Exception as exc:
            gemini_error = str(exc)

    recommendations = _finalize_recommendations(
        local_candidates, gemini_items, top_k)

    return {
        "query": query,
        "top_k": top_k,
        "source": "hybrid" if used_gemini else "local",
        "gemini_error": gemini_error,
        "recommendations": recommendations,
    }


def _chat_session_history(session_id: str) -> list[dict[str, str]]:
    if session_id not in chat_sessions:
        chat_sessions[session_id] = []
    return chat_sessions[session_id]


def _interpret_chat_query(message: str, history: list[dict[str, str]]) -> str:
    if gemini_client is None:
        return message

    compact_history = history[-MAX_CHAT_MESSAGES:]
    prompt = (
        "Convert this booking chat context into one concise recommendation query.\n"
        "Return ONLY plain text. No markdown, no JSON.\n"
        "Keep key constraints like genres, vibe, exclusions, and artist references.\n"
        f"History: {json.dumps(compact_history, ensure_ascii=False)}\n"
        f"Latest user message: {message}"
    )
    try:
        response = gemini_client.models.generate_content(
            model="gemini-3-flash-preview",
            contents=prompt,
        )
        interpreted = (response.text or "").strip()
        return interpreted if interpreted else message
    except Exception:
        return message


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "rows": int(len(df)),
        "gemini_configured": gemini_client is not None,
    }


@app.post("/recommend_hybrid")
def recommend_hybrid(request: HybridRecommendRequest):
    query = request.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="query is required")

    return _run_hybrid(query, request.top_k, request.candidate_pool)


@app.post("/chat_recommend")
def chat_recommend(request: ChatRecommendRequest):
    message = request.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="message is required")

    session_id = request.session_id or str(uuid4())
    if request.reset_session:
        chat_sessions[session_id] = []

    history = _chat_session_history(session_id)
    history.append({"role": "user", "content": message})
    history[:] = history[-MAX_CHAT_MESSAGES:]

    interpreted_query = _interpret_chat_query(message, history)
    hybrid_result = _run_hybrid(
        interpreted_query, request.top_k, request.candidate_pool)

    top_names = [item["artist"]
                 for item in hybrid_result["recommendations"][:3]]
    assistant_message = (
        f"Here are {request.top_k} matches based on your request. "
        f"Top picks: {', '.join(top_names)}."
    )
    history.append({"role": "assistant", "content": assistant_message})
    history[:] = history[-MAX_CHAT_MESSAGES:]

    return {
        "session_id": session_id,
        "message": assistant_message,
        "interpreted_query": interpreted_query,
        "result": hybrid_result,
        "history": history,
    }


@app.post("/add_artist")
def add_artist(request: AddArtistRequest):
    global df

    artist_name = request.name.strip()
    artist_genre = request.genre.strip()
    artist_descriptors = request.descriptors.strip()
    artist_resources = request.resources.strip()
    artist_social = request.social.strip()

    if not artist_name or not artist_genre:
        raise HTTPException(
            status_code=400, detail="name and genre are required")

    normalized_name = artist_name.lower()
    if normalized_name in artist_lookup:
        raise HTTPException(
            status_code=409, detail="Artist already exists in the database")

    new_row = pd.DataFrame(
        [
            {
                "Artist Name": artist_name,
                "Genre": artist_genre,
                "Descriptors": artist_descriptors,
                "Resources": artist_resources,
                "Social": artist_social,
            }
        ]
    )

    df = pd.concat([df, new_row], ignore_index=True)

    csv_columns = ["Artist Name", "Genre",
                   "Descriptors", "Resources", "Social"]
    csv_frame = df[[column for column in csv_columns if column in df.columns]]
    csv_frame.to_csv(data_path, index=False)

    _rebuild_similarity_index()

    return {
        "success": True,
        "message": f"Successfully added {artist_name} to the database!",
        "artist": {
            "name": artist_name,
            "genre": artist_genre,
            "descriptors": artist_descriptors,
            "resources": artist_resources,
            "social": artist_social,
        },
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8001)
