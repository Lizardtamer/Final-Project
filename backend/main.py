import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

app = FastAPI(title="Memphis Booking AI")

# Load your manually cleaned data
# Ensure the file 'Memphis_Band_Data.csv' is in your project directory
try:
    df = pd.read_csv("Memphis_Band_Data.csv")
    # Basic verification: Ensure required columns exist
    required_cols = {'Artist Name', 'Genre'}
    if not required_cols.issubset(df.columns):
        raise ValueError(f"CSV must contain columns: {required_cols}")
except Exception as e:
    print(f"Error loading CSV: {e}")
    df = pd.DataFrame(columns=['Artist Name', 'Genre'])


@app.get("/recommend")
def recommend_acts(touring_genres: str = Query(..., example="Indie, Rock, Alternative")):
    """
    Input: Genres of the touring artist
    Output: Top 3 local Memphis matches based on cosine similarity
    """
    if df.empty:
        raise HTTPException(
            status_code=500, detail="Database is empty or failed to load.")

    local_genres = df['Genre'].fillna("").tolist()
    all_genres = local_genres + [touring_genres]

    tfidf = TfidfVectorizer(stop_words='english')
    tfidf_matrix = tfidf.fit_transform(all_genres)

    cosine_sim = cosine_similarity(tfidf_matrix[-1], tfidf_matrix[:-1])

    sim_scores = list(enumerate(cosine_sim[0]))
    sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)

    # Return top 3 recommendations
    top_indices = [i[0] for i in sim_scores[:3]]
    recommendations = []
    for i, idx in enumerate(top_indices):
        recommendations.append({
            "artist": df.iloc[idx]['Artist Name'],
            "genre": df.iloc[idx]['Genre'],
            "match_score": round(float(sim_scores[i][1]), 4)
        })

    return {
        "touring_profile": touring_genres,
        "recommendations": recommendations
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
