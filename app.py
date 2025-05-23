import csv
import os
import numpy as np
import datetime
import logging
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import jinja2

# Configure logging
logging.basicConfig(level=logging.WARNING)  # Less verbose for production
logger = logging.getLogger(__name__)

# Define the FastAPI app
app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Define categories
categories = ["Emotional & Psychological Insights", "Social Support", "Nutrition for Recovery", "Becoming Eating Disorder Informed"]

# Load special modules from CSV
def load_special_modules(csv_file_path):
    special_modules = {}
    try:
        with open(csv_file_path, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            required_columns = ["Category", "Title", "Description", "Link"]
            if not all(col in reader.fieldnames for col in required_columns):
                raise ValueError(f"Special modules CSV missing columns: {[col for col in required_columns if col not in reader.fieldnames]}")
            for row in reader:
                category = row["Category"].strip()
                special_modules[category] = {
                    "title": row["Title"].strip(),
                    "description": row["Description"].strip(),
                    "link": row["Link"].strip()
                }
                logger.debug(f"Loaded special module: {category} -> {row['Title']}")
    except FileNotFoundError:
        logger.error(f"Special modules CSV file {csv_file_path} not found")
    except Exception as e:
        logger.error(f"Error loading special modules CSV: {e}")
    return special_modules

# Helper function to filter modules based on month and age
def filter_modules(all_modules, age_over_18):
    filtered_modules = all_modules[:]
    
    if age_over_18:
        filtered_modules = [
            module for module in filtered_modules 
            if module["name"].lower() != "family-based therapy & eating disorders"
        ]
    
    return filtered_modules

# Load modules from CSV
def load_modules(csv_file_path):
    logger.info(f"Loading modules from: {csv_file_path}")
    all_modules = []
    try:
        with open(csv_file_path, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            required_columns = ["Title", "Average Views Per Year"] + categories
            if not all(col in reader.fieldnames for col in required_columns):
                raise ValueError(f"CSV missing columns: {[col for col in required_columns if col not in reader.fieldnames]}")
            for row in reader:
                try:
                    features = [float(row[category.strip()]) for category in categories]
                    max_score = max(features)
                    top_category_idx = features.index(max_score)
                    top_category = categories[top_category_idx]
                    avg_views = float(row.get("Average Views Per Year", 0))
                    module = {
                        "name": row["Title"].strip(),
                        "features": np.array(features),
                        "average_views_per_year": avg_views,
                        "link": row.get("Link", "").strip(),
                        "description": row.get("Description", "").strip(),
                        "top_category": top_category
                    }
                    all_modules.append(module)
                except (ValueError, KeyError) as e:
                    logger.error(f"Error processing row {row}: {e}")
            if all(module["average_views_per_year"] == 0 for module in all_modules):
                logger.warning("All average_views_per_year values are 0")
    except FileNotFoundError:
        logger.error(f"CSV file {csv_file_path} not found")
    except ValueError as e:
        logger.error(f"CSV validation error: {e}")
    return all_modules

# Recommendation algorithms
def combined_cosine_euclidean(user_preferences, all_modules):
    user_vec = np.array(user_preferences)
    user_norm = np.linalg.norm(user_vec)
    user_vec_cosine = user_vec if user_norm == 0 else user_vec / user_norm
    max_magnitude = np.sqrt(len(user_preferences) * 5.0**2)
    user_vec_euclidean = user_vec if user_norm == 0 else user_vec / user_norm * max_magnitude
    
    cosine_distances = []
    euclidean_distances = []
    for module in all_modules:
        module_vec = module["features"]
        module_norm = np.linalg.norm(module_vec)
        cosine_sim = 0.0 if module_norm == 0 or user_norm == 0 else np.dot(user_vec_cosine, module_vec / module_norm)
        cosine_sim = max(min(cosine_sim, 1.0), -1.0)
        cosine_distances.append((module["name"], 1.0 - cosine_sim, module["average_views_per_year"]))
        euclidean_dist = np.linalg.norm(module_vec - user_vec_euclidean)
        euclidean_distances.append((module["name"], euclidean_dist, module["average_views_per_year"]))
    
    cosine_ranks = sorted([(name, i + 1) for i, (name, _, _) in enumerate(sorted(cosine_distances, key=lambda x: x[1]))])
    euclidean_ranks = sorted([(name, i + 1) for i, (name, _, _) in enumerate(sorted(euclidean_distances, key=lambda x: x[1]))])
    
    rank_dict = {module["name"]: [0, 0] for module in all_modules}
    for name, rank in cosine_ranks:
        rank_dict[name][0] = rank
    for name, rank in euclidean_ranks:
        rank_dict[name][1] = rank
    
    return sorted(
        [(name, ranks[0] + ranks[1], views) for name, ranks in rank_dict.items()
         for module in all_modules if module["name"] == name and (views := module["average_views_per_year"])],
        key=lambda x: x[1]
    )

def popularity_ranking(all_modules):
    return sorted(
        [(module["name"], module["average_views_per_year"], module["average_views_per_year"]) for module in all_modules],
        key=lambda x: x[1], reverse=True
    )

def content_boosted_popularity(user_preferences, all_modules):
    relevance_scores = combined_cosine_euclidean(user_preferences, all_modules)
    relevance_dict = {name: 1 / (1 + rank) for name, rank, _ in relevance_scores}
    results = []
    for module in all_modules:
        name = module["name"]
        views = module["average_views_per_year"]
        relevance = relevance_dict.get(name, 0.5)
        boosted_score = views * (0.7 + 0.3 * relevance)
        results.append((module["name"], boosted_score, views))
    return sorted(results, key=lambda x: x[1], reverse=True)

def hybrid_recommendation(user_preferences, all_modules):
    variance = np.var(user_preferences)
    logger.debug(f"Variance: {variance:.2f}")
    
    top_scores = content_boosted_popularity(user_preferences, all_modules)[:4] if variance < 0.5 else combined_cosine_euclidean(user_preferences, all_modules)[:4]
    
    pref_ranking = sorted([(pref, idx) for idx, pref in enumerate(user_preferences)], reverse=True)
    second_rank_score = pref_ranking[1][0]
    second_rank_categories = [categories[idx] for pref, idx in pref_ranking if pref == second_rank_score]
    
    results = top_scores[:]
    top_score_names = [name for name, _, _ in top_scores]
    
    base_scores = combined_cosine_euclidean(user_preferences, all_modules)
    candidates = [
        score for score in base_scores
        if score[0] not in top_score_names and
        any(module["name"] == score[0] and module["top_category"] in second_rank_categories for module in all_modules)
    ]
    
    candidates.sort(key=lambda x: x[1])
    results.extend(candidates[:2])
    
    if len(results) < 6:
        additional = [score for score in base_scores if score[0] not in [name for name, _, _ in results]][:6 - len(results)]
        results.extend(additional)
    
    return results[:6]

def recommend_modules(user_preferences, all_modules, age_over_18):
    logger.info(f"Processing preferences: {user_preferences}, Age Over 18: {age_over_18}")
    filtered_modules = filter_modules(all_modules, age_over_18)
    
    if not filtered_modules:
        logger.warning("No modules available after filtering")
        return []
    
    if not all(1 <= pref <= 5 for pref in user_preferences) or len(user_preferences) != len(categories):
        logger.warning("Invalid preferences: Defaulting to popularity")
        return popularity_ranking(filtered_modules)[:6]
    
    if len(set(user_preferences)) == 1:
        logger.info("Identical preferences: Defaulting to popularity")
        return popularity_ranking(filtered_modules)[:6]
    
    return hybrid_recommendation(user_preferences, filtered_modules)

# Load modules at startup
csv_path = os.path.join(os.path.dirname(__file__), "modules3.csv")
all_modules = load_modules(csv_path)
if not all_modules:
    logger.error("No modules loaded from CSV")

special_csv_path = os.path.join(os.path.dirname(__file__), "special_modules.csv")
special_modules = load_special_modules(special_csv_path)
if not special_modules:
    logger.error("No special modules loaded from CSV")

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    try:
        return templates.TemplateResponse("index.html", {"request": request})
    except jinja2.exceptions.TemplateNotFound:
        logger.error("index.html not found in templates directory")
        return HTMLResponse(content="<h1>Error: Home page template not found</h1>", status_code=500)

@app.post("/webhook", response_class=JSONResponse)
async def webhook(request: Request):
    form_data = await request.form()
    logger.debug(f"Webhook received: {dict(form_data)}")
    return JSONResponse(content={"status": "received"}, status_code=200)

@app.post("/submit", response_class=HTMLResponse)
async def submit_form(request: Request):
    form_data = await request.form()
    logger.debug(f"Raw form data: {dict(form_data)}")
    logger.info(f"Form data keys: {list(form_data.keys())}")

    try:
        # Use confirmed JotForm field names from old code
        field_mapping = {
            "emotional_psychological_insights[0]": "emotional_psychological_insights",
            "social_support[0]": "social_support",
            "nutrition_for_recovery[0]": "nutrition_for_recovery",
            "becoming_eating_disorder_informed[0]": "becoming_eating_disorder_informed"
        }
        user_preferences = [
            float(form_data.get(key, 1.0)) for key in field_mapping
        ]
        if not all(1 <= p <= 5 for p in user_preferences):
            raise ValueError("Preferences must be between 1 and 5")
    except (ValueError, TypeError) as e:
        logger.error(f"Invalid preferences: {str(e)}")
        return templates.TemplateResponse(
            "error.html",
            {"request": request, "error": f"Invalid preferences: {str(e)}"},
            status_code=400
        )

    over_18_str = form_data.get("under_18", "NO")
    over_18 = over_18_str.upper() == "YES"

    niche_interests = []
    for key, value in form_data.items():
        if key.startswith("niche_interests["):
            niche_interests.extend([interest.strip() for interest in value.split(",") if interest.strip()])

    if not all_modules:
        logger.error("Modules data not available")
        return templates.TemplateResponse(
            "error.html",
            {"request": request, "error": "No modules available. Please try again later."},
            status_code=500
        )

    # Format recommendations to match old thankyou.html tuple structure
    top_6_modules = [
        (
            module["name"],
            score,
            module["features"].tolist(),  # Convert numpy array to list for template
            module["link"],
            module["description"]
        )
        for module, score, views in [
            (next(m for m in all_modules if m["name"] == name), score, views)
            for name, score, views in recommend_modules(user_preferences, all_modules, over_18)
        ]
    ]

    # Match niche interests to special modules
    recommended_niche_modules = []
    for interest in niche_interests:
        interest_lower = interest.lower()
        matched_category = next((category for category in special_modules if category.lower() == interest_lower), None)
        if matched_category:
            module_info = special_modules[matched_category]
            recommended_niche_modules.append({
                "name": module_info["title"],
                "link": module_info["link"],
                "description": module_info["description"]
            })

    return templates.TemplateResponse(
        "thankyou.html",
        {
            "request": request,
            "name": "User",  # Static, as old code used
            "email": "N/A",  # Static, as old code used
            "preferences": dict(zip(categories, user_preferences)),
            "niche_interests": niche_interests,
            "general_recommendations": top_6_modules,
            "niche_recommendations": recommended_niche_modules
        }
    )
