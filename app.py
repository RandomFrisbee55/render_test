import csv
import math
import os
import numpy as np
from fastapi import FastAPI, Form, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from typing import List

# Define the FastAPI app
app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Define categories and niche topics
categories = ["Emotional & Psychological Insights", "Social Support", "Nutrition for Recovery", "Becoming Eating Disorder Informed"]
category_keys = ["emotional_psychological_insights", "social_support", "nutrition_for_recovery", "becoming_eating_disorder_informed"]
niche_topics = [
    "Transgender", 
    "Decolonizing Eating Disorders", 
    "Non-Diet Approach to Managing Diabetes & Heart", 
    "Food & Trauma from Sexual Violence", 
    "Neurodivergence", 
    "Type 1 Diabetes", 
    "Athletes"
]
special_topic_modules = {
    "Transgender": "Every Body’s Journey: Inclusive Recovery for Transgender and Gender Diverse People",
    "Decolonizing Eating Disorders": "Decolonizing Eating Disorders",
    "Non-Diet Approach to Managing Diabetes & Heart": "Non-Diet Approach to Managing Diabetes & Heart Health",
    "Food & Trauma from Sexual Violence": "Food & Trauma from Sexual Violence",
    "Neurodivergence": "Neurodivergence and Eating Disorders",
    "Type 1 Diabetes": "Type 1 Diabetes & Eating Disorders",
    "Athletes": "Athletes and Eating Disorders"
}

# Load modules from CSV
def load_modules(csv_file_path):
    all_modules = []
    try:
        with open(csv_file_path, newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            reader.fieldnames = [name.strip() for name in reader.fieldnames]  # Strip whitespace from field names
            for row in reader:
                try:
                    module = {
                        "name": row["Title"],
                        "features": [float(row[category.strip()]) for category in categories],
                        "link": row.get("Link", ""),
                        "description": row.get("Description", "")  # Load the description
                    }
                    all_modules.append(module)
                except (ValueError, KeyError) as e:
                    print(f"Error processing row {row}: {e}")
    except FileNotFoundError:
        print(f"CSV file {csv_file_path} not found")
    return all_modules

# Recommendation functions
def euclidean_distance(vector1, vector2):
    if len(vector1) != len(vector2):
        return float("inf")
    squared_distance = 0
    for i in range(len(vector1)):
        squared_distance += (vector1[i] - vector2[i]) ** 2
    return math.sqrt(squared_distance)

def weighted_euclidean_distance(user_vector, module_vector, weights):
    if len(user_vector) != len(module_vector) or len(user_vector) != len(weights):
        return float("inf")
    differences = np.array(user_vector) - np.array(module_vector)
    weighted_squared = (differences ** 2) * np.array(weights)
    return np.sqrt(np.sum(weighted_squared))

def hierarchical_ranking(user_preferences, all_modules):
    if not all_modules:
        return []
    category_ranking = [(pref, idx) for idx, pref in enumerate(user_preferences)]
    category_ranking.sort(reverse=True)
    module_scores = []
    for module in all_modules:
        module_scores.append({
            "name": module["name"],
            "features": module["features"],
            "link": module["link"],
            "description": module["description"],
            "sort_keys": []
        })
    for level, (pref, category_idx) in enumerate(category_ranking):
        if level == 0:
            top_categories = [idx for p, idx in category_ranking if p == pref]
            if len(top_categories) == 1:
                for module in module_scores:
                    score = module["features"][category_idx]
                    module["sort_keys"].append(-score)
            else:
                for module in module_scores:
                    avg_score = sum(module["features"][idx] for idx in top_categories) / len(top_categories)
                    module["sort_keys"].append(-avg_score)
        else:
            for module in module_scores:
                score = module["features"][category_idx]
                module["sort_keys"].append(-score)
    for module in module_scores:
        module["sort_keys"].append(module["name"])
        module["primary_score"] = -module["sort_keys"][0] if module["sort_keys"] else 0
    module_scores.sort(key=lambda x: x["sort_keys"])
    return [(m["name"], m["primary_score"], m["features"], m["link"], m["description"]) for m in module_scores[:5]]

def recommend_modules(user_vector, user_preferences, all_modules):
    #euclidean
    euclidean_scores = []
    for module in all_modules:
        euclidean_score = euclidean_distance(user_vector, module["features"])
        euclidean_scores.append((module["name"], euclidean_score, module["features"], module["link"], module["description"]))
    euclidean_scores.sort(key=lambda x: x[1])

    # Weighted Euclidean distance
    weights = [0.5 if pref <= 1 else 1.0 if pref <= 3 else 2.0 for pref in user_preferences]
    weighted_euclidean_scores = []
    for module in all_modules:
        weighted_score = weighted_euclidean_distance(user_vector, module["features"], weights)
        weighted_euclidean_scores.append((module["name"], weighted_score, module["features"].tolist(), module["link"], module["description"]))
    weighted_euclidean_scores.sort(key=lambda x: x[1])

    #hierarchical
    hierarchical_scores = hierarchical_ranking(user_preferences, all_modules)
    return euclidean_scores[:5], weighted_euclidean_scores[:5], hierarchical_scores

# Load modules at startup
csv_path = os.path.join(os.path.dirname(__file__), "modules3.csv")
all_modules = load_modules(csv_path)
if not all_modules:
    print("Warning: No modules loaded from CSV")

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/submit", response_class=HTMLResponse)
async def submit_form(
    request: Request,
    emotional_psychological_insights: float = Form(...),
    social_support: float = Form(...),
    nutrition_for_recovery: float = Form(...),
    becoming_eating_disorder_informed: float = Form(...),
    niche_interests: str = Form(default="")
):
    # Log the raw form data for debugging
    form_data = await request.form()
    print("Raw form data:", dict(form_data))

    print("Processing preferences and niche interests")
    user_preferences = [
        emotional_psychological_insights,
        social_support,
        nutrition_for_recovery,
        becoming_eating_disorder_informed
    ]
    user_niche_interests = [interest.strip() for interest in niche_interests.split(",")] if niche_interests else []
    user_vector = user_preferences.copy()

    if not all_modules:
        raise HTTPException(status_code=500, detail="Modules data not available")

    top_5_euclidean, top_5_hierarchical = recommend_modules(user_vector, user_preferences, all_modules)

    # Match niche interests to special topic modules
    recommended_niche_modules = []
    for interest in user_niche_interests:
        if interest in special_topic_modules:
            module_name = special_topic_modules[interest]
            # Find the module in all_modules to get its link and description
            module = next((m for m in all_modules if m["name"] == module_name), None)
            if module:
                recommended_niche_modules.append({
                    "name": module_name,
                    "link": module["link"],
                    "description": module["description"]
                })

    return templates.TemplateResponse(
        "thankyou.html",
        {
            "request": request,
            "name": "User",
            "email": "N/A",
            "preferences": dict(zip(categories, user_preferences)),
            "niche_interests": user_niche_interests,
            "euclidean_recommendations": top_5_euclidean,
            "hierarchical_recommendations": top_5_hierarchical,
            "niche_recommendations": recommended_niche_modules
        }
    )
