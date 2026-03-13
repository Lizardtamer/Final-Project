import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

app = FastAPI(title="Memphis Booking AI")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173",
                   "http://127.0.0.1:5173",
                   "http://localhost:5174",
                   "http://127.0.0.1:5174"],  # Vite ports
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic model for adding artists


class Artist(BaseModel):
    name: str
    genre: str


# Load your manually cleaned data
# Ensure the file 'memphisbanddata.csv' is in your project directory
try:
    df = pd.read_csv("memphisbanddata.csv")
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
    Output: Top 7 local Memphis matches based on cosine similarity
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

    # Return top 7 recommendations
    top_indices = [i[0] for i in sim_scores[:7]]
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


@app.post("/add_artist")
def add_artist(artist: Artist):
    """
    Add a new artist to the database
    Input: Artist name and genre
    Output: Success message
    """
    global df

    try:
        # Create new row
        new_artist = pd.DataFrame({
            'Artist Name': [artist.name],
            'Genre': [artist.genre]
        })

        # Append to dataframe
        df = pd.concat([df, new_artist], ignore_index=True)

        # Save to CSV
        df.to_csv("memphisbanddata.csv", index=False)

        return {
            "success": True,
            "message": f"Successfully added {artist.name} to the database!",
            "artist": {
                "name": artist.name,
                "genre": artist.genre
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error adding artist: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
