import csv
import math
import os
from fastapi import FastAPI, Form, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from typing import List

# Define the FastAPI app first
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

# Recommendation functions
def euclidean_distance(vector1, vector2):
    if len(vector1) != len(vector2):
        return float("inf")
    squared_distance = 0
    for i in range(len(vector1)):
        squared_distance += (vector1[i] - vector2[i]) ** 2
    return math.sqrt(squared_distance)

def hierarchical_ranking(user_preferences, all_modules):
    if not all_modules:
        return []  # Return empty list if no modules

    category_ranking = [(pref, idx) for idx, pref in enumerate(user_preferences)]
    category_ranking.sort(reverse=True)

    module_scores = []
    for module in all_modules:
        module_scores.append({
            "name": module["name"],
            "features": module["features"],
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
    return [(m["name"], m["primary_score"], m["features"]) for m in module_scores[:5]]

def recommend_modules(user_vector, user_preferences, all_modules):
    euclidean_scores = []
    for module in all_modules:
        euclidean_score = euclidean_distance(user_vector, module["features"])
        euclidean_scores.append((module["name"], euclidean_score, module["features"]))
    euclidean_scores.sort(key=lambda x: x[1])
    print("Euclidean scores:", euclidean_scores[:5])  # Debug

    hierarchical_scores = hierarchical_ranking(user_preferences, all_modules)
    print("Hierarchical scores:", hierarchical_scores)  # Debug

    return euclidean_scores[:5], hierarchical_scores

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
    emotional_psychological_insights: float = Form(...),
    social_support: float = Form(...),
    nutrition_for_recovery: float = Form(...),
    becoming_eating_disorder_informed: float = Form(...),
    niche_interests: str = Form(default="")
):
    form_data = await request.form()
    print("Received form data:", dict(form_data))

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
    print("Top 5 Euclidean:", top_5_euclidean)  # Debug
    print("Top 5 Hierarchical:", top_5_hierarchical)  # Debug

    return templates.TemplateResponse(
        "thankyou.html",
        {
            "request": request,
            "name": "User",
            "email": "N/A",
            "preferences": dict(zip(categories, user_preferences)),
            "niche_interests": user_niche_interests,
            "euclidean_recommendations": top_5_euclidean,
            "hierarchical_recommendations": top_5_hierarchical
        }
    )
