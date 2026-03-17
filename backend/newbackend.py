import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# : https://colab.research.google.com/drive/1extN1hHYR0IVdnpKdGWjKskbb1pLTGHH?usp=drive_link#scrollTo=5w5huLW0VwHJ

# Load the dataset
df = pd.read_csv('memphisbanddata.csv')

df.head()
df.info()

# Combine relevant text columns into a single column for content-based filtering
df['Content'] = df['primary_genres'] + ' ' + \
    df['descriptors'] + ' ' + df['artist_name']
df['Content'] = df['Content'].astype(str)

# Check the new 'Content' column
df[['release_name', 'Content']].head()

# Create a function to get recommendations


def get_recommendations(album_title, cosine_sim=cosine_sim, num_recommendations=5):
    # Get the index of the album that matches the title
    idx = df[df['release_name'] == album_title].index[0]

    # Get the pairwise similarity scores of all albums with that album
    sim_scores = list(enumerate(cosine_sim[idx]))

    # Sort the albums by similarity score (in descending order)
    sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)

    # Get the top n most similar albums (excluding the first one, which is the album itself)
    sim_scores = sim_scores[1:num_recommendations+1]

    # Get the album indices
    album_indices = [i[0] for i in sim_scores]

    # Return the top n recommended album titles
    return df['release_name'].iloc[album_indices]


# Example: Get recommendations for a specific album
recommended_albums = get_recommendations('Loveless', cosine_sim)

# Show the recommended albums
print("Recommended Albums:")
print(recommended_albums)
