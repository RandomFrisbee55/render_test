import csv
import math
import os
import numpy as np
import datetime
from fastapi import FastAPI, Form, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from typing import List

# Define the FastAPI app
app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Define categories
categories = ["Emotional & Psychological Insights", "Social Support", "Nutrition for Recovery", "Becoming Eating Disorder Informed"]
category_keys = ["emotional_psychological_insights", "social_support", "nutrition_for_recovery", "becoming_eating_disorder_informed"]

# Load special modules from CSV
def load_special_modules(csv_file_path):
    special_modules = {}
    try:
        with open(csv_file_path, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                category = row["Category"].strip()
                special_modules[category] = {
                    "title": row["Title"].strip(),
                    "description": row["Description"].strip(),
                    "link": row["Link"].strip()
                }
                print(f"Loaded special module: {category} -> {row['Title']}")
    except FileNotFoundError:
        print(f"Special modules CSV file {csv_file_path} not found")
    except Exception as e:
        print(f"Unexpected error while loading special modules CSV: {e}")
    return special_modules

# Helper function to filter holiday modules based on the current month
def filter_holiday_modules(all_modules):
    current_month = datetime.datetime.now().month
    print(f"Current month: {current_month}")
    print("Modules before filtering:", [module["name"] for module in all_modules])
    
    if current_month in [11, 12]:
        print("Including all modules (November or December)")
        return all_modules
    
    holiday_modules = ["navigating the holidays in recovery", "thriving through the holidays"]
    filtered_modules = [
        module for module in all_modules 
        if module["name"].lower() not in holiday_modules
    ]
    
    print("Modules after filtering:", [module["name"] for module in filtered_modules])
    return filtered_modules

# Load modules from CSV
def load_modules(csv_file_path):
    all_modules = []
    try:
        with open(csv_file_path, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            reader.fieldnames = [name.strip() for name in reader.fieldnames]  # Strip whitespace from field names
            for row in reader:
                try:
                    module = {
                        "name": row["Title"].strip(),
                        "features": [float(row[category.strip()]) for category in categories],
                        "link": row.get("Link", ""),
                        "description": row.get("Description", "")  # Load the description
                    }
                    print(f"Loaded module: {module['name']}")
                    all_modules.append(module)
                except (ValueError, KeyError) as e:
                    print(f"Error processing row {row}: {e}")
    except FileNotFoundError:
        print(f"CSV file {csv_file_path} not found")
    except Exception as e:
        print(f"Unexpected error while loading CSV: {e}")
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
    # Filter holiday modules
    filtered_modules = filter_holiday_modules(all_modules)
    
    # Euclidean
    euclidean_scores = []
    for module in filtered_modules:
        euclidean_score = euclidean_distance(user_vector, module["features"])
        euclidean_scores.append((module["name"], euclidean_score, module["features"], module["link"], module["description"]))
    euclidean_scores.sort(key=lambda x: x[1])
    
    # Hierarchical
    hierarchical_scores = hierarchical_ranking(user_preferences, filtered_modules)
    return euclidean_scores[:5], hierarchical_scores

# Load modules at startup
csv_path = os.path.join(os.path.dirname(__file__), "modules3.csv")
print(f"Attempting to load modules from: {csv_path}")
all_modules = load_modules(csv_path)
if not all_modules:
    print("Warning: No modules loaded from CSV")

# Load special modules at startup
special_csv_path = os.path.join(os.path.dirname(__file__), "special_modules.csv")
print(f"Attempting to load special modules from: {special_csv_path}")
special_modules = load_special_modules(special_csv_path)
if not special_modules:
    print("Warning: No special modules loaded from CSV")

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/webhook")
async def webhook(request: Request):
    form_data = await request.form()
    print(f"Webhook received: {dict(form_data)}")
    return JSONResponse(content={"status": "received"}, status_code=200)

@app.post("/submit", response_class=HTMLResponse)
async def submit_form(request: Request):
    # Log the raw form data for debugging
    form_data = await request.form()
    print("Raw form data:", dict(form_data))

    # Extract preference fields with their new names
    emotional_psychological_insights = float(form_data.get("emotional_psychological_insights[0]", 1.0))
    social_support = float(form_data.get("social_support[0]", 1.0))
    nutrition_for_recovery = float(form_data.get("nutrition_for_recovery[0]", 1.0))
    becoming_eating_disorder_informed = float(form_data.get("becoming_eating_disorder_informed[0]", 1.0))

    # Extract niche interests (multiple values: niche_interests[0], niche_interests[1], etc.)
    niche_interests = []
    for key, value in form_data.items():
        if key.startswith("niche_interests["):
            niche_interests.extend([interest.strip() for interest in value.split(",") if interest.strip()])

    print("Processing preferences and niche interests")
    user_preferences = [
        emotional_psychological_insights,
        social_support,
        nutrition_for_recovery,
        becoming_eating_disorder_informed
    ]
    print("Parsed preferences:", user_preferences)
    
    user_niche_interests = niche_interests
    print("Parsed niche interests:", user_niche_interests)
    
    user_vector = user_preferences.copy()

    if not all_modules:
        raise HTTPException(status_code=500, detail="Modules data not available")

    top_5_euclidean, top_5_hierarchical = recommend_modules(user_vector, user_preferences, all_modules)

    # Match niche interests to special modules using the CSV data
    recommended_niche_modules = []
    for interest in user_niche_interests:
        # Handle case sensitivity by converting both to lowercase for comparison
        interest_lower = interest.lower()
        matched_category = next((category for category in special_modules if category.lower() == interest_lower), None)
        if matched_category:
            module_info = special_modules[matched_category]
            print(f"Matched niche interest '{interest}' to category '{matched_category}' with title '{module_info['title']}'")
            recommended_niche_modules.append({
                "name": module_info["title"],
                "link": module_info["link"],
                "description": module_info["description"]
            })
        else:
            print(f"No match found for niche interest '{interest}' in special_modules")

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
