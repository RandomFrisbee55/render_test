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
            "name": name,
            "email": email,
            "preferences": dict(zip(categories, user_preferences)),
            "niche_interests": user_niche_interests,
            "euclidean_recommendations": top_5_euclidean,
            "hierarchical_recommendations": top_5_hierarchical
        }
    )
