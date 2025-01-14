import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import nltk
from nltk.corpus import stopwords
import string
import re
from fastapi import FastAPI

app = FastAPI()

# Download NLTK stopwords
print("Downloading NLTK stopwords...")
nltk.download('stopwords')
stop_words = set(stopwords.words('english'))
print("NLTK stopwords downloaded.")

# Function for text preprocessing
def preprocess_text(text):
    if pd.isna(text):  # Check for NaN values
        return ""
    text = str(text).lower()  # Convert to lowercase and ensure it's a string
    text = text.translate(str.maketrans('', '', string.punctuation))  # Remove punctuation
    text = re.sub(r'[^\x00-\x7F]+', '', text)  # Remove non-ASCII characters
    tokens = text.split()  # Tokenize
    tokens = [word for word in tokens if word not in stop_words]  # Remove stopwords
    return ' '.join(tokens)

@app.get("/{file1}/{input_topic}")
async def read_root(file1: str, input_topic: str):
    
    # Load the extracted content CSV file
    print("Loading extracted content CSV file...")
    df_extracted = pd.read_csv(f"BlogsData/{file1}")
    print("Extracted content CSV file loaded successfully.")

    # Print the first few rows to verify the contents
    print("First few rows of Extracted_content:")
    print(df_extracted.head())

    # Preprocess the texts in 'Title' and 'Meta Description' columns of Extracted_content
    print("Preprocessing text columns in Extracted_content...")
    df_extracted['Processed_Text'] = (df_extracted['Title'].fillna('') + ' ' + df_extracted['Meta Description'].fillna('')).apply(preprocess_text)
    print("Text columns preprocessed.")

    # Vectorize the texts using TF-IDF
    print("Vectorizing texts using TF-IDF...")
    vectorizer = TfidfVectorizer()
    X_extracted = vectorizer.fit_transform(df_extracted['Processed_Text'])
    print("Texts vectorized in Extracted_content.")

    # Accept a single topic as input
    print(f"Processing single topic: {input_topic}")

    # Preprocess the input topic
    processed_input_topic = preprocess_text(input_topic)

    # Transform the processed input topic using the same vectorizer
    X_input_topic = vectorizer.transform([processed_input_topic])
    print("Input topic vectorized.")

    # Calculate cosine similarity between the input topic and the extracted content
    print("Calculating cosine similarity...")
    similarity_matrix = cosine_similarity(X_input_topic, X_extracted)
    print("Cosine similarity calculated.")

    # Find similar content based on a similarity threshold
    print("Finding similar content based on a similarity threshold...")
    threshold = 0.5  # Adjust the threshold as needed
    similar_pairs = []
    used_titles = set()  # To keep track of used titles

    for j in range(similarity_matrix.shape[1]):
        if similarity_matrix[0, j] > threshold and df_extracted.iloc[j]['Title'] not in used_titles:
            used_titles.add(df_extracted.iloc[j]['Title'])
            similar_row = df_extracted.iloc[j].to_dict()
            similar_pairs.append((input_topic, similarity_matrix[0, j], df_extracted.iloc[j]['Title']) + tuple(similar_row.values()))

    # Check if there are any similar pairs found
    if not similar_pairs:
        return {}

    # Save the similar pairs to a new DataFrame
    print("Saving similar content to DataFrame...")
    columns = ['Topic', 'Similarity', 'Similar Title'] + list(df_extracted.columns)
    similar_df = pd.DataFrame(similar_pairs, columns=columns)

    # Return single object if there's only one similar pair found
    if len(similar_df) == 1:
        return similar_df.iloc[0].to_json()  # Return single JSON object
    else:
        return similar_df.to_json(orient='records')  # Return array of JSON objects
