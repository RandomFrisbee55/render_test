import csv
import math
import os
from fastapi import FastAPI, Form, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from typing import List

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# Define categories and niche topics
categories = ["Emotional & Psychological Insights", "Social Support", "Nutrition for Recovery", "Becoming Eating Disorder Informed"]
category_keys = ["emotional_psychological_insights", "social_support", "nutrition_for_recovery", "becoming_eating_disorder_informed"]
niche_topics = ["Transgender", "Decolonizing Eating Disorders", "Non-Diet Approach to Managing Diabetes & Heart", "Food & Trauma from Sexual Violence", "Neurodivergence", "Type 1 Diabetes", "Athletes"]

# Load modules from CSV
def load_modules(csv_file_path):
    all_modules = []
    try:
        with open(csv_file_path, newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            reader.fieldnames = [name.strip() for name in reader.fieldnames]
            for row in reader:
                try:
                    module = {
                        "name": row["Title"],
                        "features": [float(row[category.strip()]) for category in categories]
                    }
                    all_modules.append(module)
                except (ValueError, KeyError) as e:
                    print(f"Error processing row {row}: {e}")
    except FileNotFoundError:
        print(f"CSV file {csv_file_path} not found")
    return all_modules

# Recommendation functions (unchanged for brevity)
def euclidean_distance(vector1, vector2):
    if len(vector1) != len(vector2):
        return float("inf")
    squared_distance = 0
    for i in range(len(vector1)):
        squared_distance += (vector1[i] - vector2[i]) ** 2
    return math.sqrt(squared_distance)

def hierarchical_ranking(user_preferences, all_modules): ...
def recommend_modules(user_vector, user_preferences, all_modules): ...

# Load modules at startup
csv_path = os.path.join(os.path.dirname(__file__), "modules3.csv")
all_modules = load_modules(csv_path)
if not all_modules:
    print("Warning: No modules loaded from CSV")

@app.get("/", response_class=HTMLResponse)
async def root():
    return "Welcome to the app. Use POST /submit for form submissions."

@app.post("/submit", response_class=HTMLResponse)
async def submit_form(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    emotional_psychological_insights: float = Form(...),
    social_support: float = Form(...),
    nutrition_for_recovery: float = Form(...),
    becoming_eating_disorder_informed: float = Form(...),
    niche_interests: str = Form(default="")
):
    form_data = await request.form()
    print("Received form data:", dict(form_data))  # This should work now
    user_preferences = [
        emotional_psychological_insights,
        social_support,
        nutrition_for_recovery,
        becoming_eating_disorder_informed
    ]
    user_niche_interests = niche_interests.split(",") if niche_interests else []
    user_vector = user_preferences.copy()

    if not all_modules:
        raise HTTPException(status_code=500, detail="Modules data not available")

    top_5_euclidean, top_5_hierarchical = recommend_modules(user_vector, user_preferences, all_modules)

    return templates.TemplateResponse(
        "thankyou.html",
        {
            "request": request,
            "name": name,
            "email": email,
            "preferences": dict(zip(categories, user_preferences)),
            "niche_interests": user_niche_interests,
            "euclidean_recommendations": top_5_euclidean,
            "hierarchical_recommendations": top_5_hierarchical
        }
    )
