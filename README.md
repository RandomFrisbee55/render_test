# Recovery Support Program – Recommendation Algorithm

## Overview
The Eating Disorder (ED) Recovery Framework forms the backbone of the module recommendation algorithm. It was developed using:
- Client feedback  
- Scientific literature on ED recovery  
- Body Brave’s existing Recovery Support Session programming  

This framework structures personalization by assessing a user’s interest across four key domains of recovery and uses this information to recommend the most relevant sessions.

---

## Recovery Framework Categories

Each user is assessed across the following four domains:

1. **Learning About EDs**  
   Understanding the basics of eating disorders, treatment, and recovery  

2. **Emotional Support**  
   Developing self-compassion and managing emotions during recovery  

3. **Social Support**  
   Building and communicating with a personal support network  

4. **Nutrition for Recovery**  
   Practical strategies for approaching eating and nutrition during recovery  

---

## Goal
Recommend the **top 6 most relevant recovery sessions** for each user based on their personalized recovery profile.

---

## Data Sources

### 1. User Input
- Users rate their interest in each recovery category on a **scale from 1 to 5**
- This creates a **user preference vector** used for similarity comparison  

### 2. Scored Session Matrix
- Each recovery session is pre-scored (1–5) across the same four categories  
- Scores are assigned based on expert review  


## Scoring Mechanisms

### 1. Similarity Scoring
Uses a hybrid approach:
- **Cosine similarity** → captures relational similarity between preferences  
- **Euclidean distance** → captures absolute differences  

These metrics identify sessions most aligned with the user’s recovery priorities.

### 2. Popularity Scoring
- Based on **average views per year** (e.g., YouTube engagement)  
- Serves as a proxy for usefulness and user engagement  


## Adaptive Hybrid Ranking Algorithm

The algorithm dynamically adjusts based on how clear a user’s preferences are:

### High Preference Clarity (High Variance)
**Example:** `[1, 5, 2, 3]`  
- Strong differences between categories  
- **Strategy:** Use similarity scoring only  
- Output reflects highly personalized recommendations  


### Low Preference Clarity (Low Variance)
**Example:** `[2, 3, 2, 3]`  
- Preferences are relatively uniform  
- **Strategy:**  
  - Primarily use popularity scoring  
  - Apply light similarity-based boosting  


## Additional Algorithm Considerations

### 1. Diversity of Recommendations
- First 4 recommendations: highest ranked overall  
- Final 2 recommendations:
  - Prioritize **second or third highest-rated categories**  
  - Ensures broader recovery coverage  

### 2. Contextual Filtering
- Filters out inappropriate content based on user context  
- Example:
  - Removes Family-Based Therapy modules for users > 18 years  

---

## System Architecture

### Frontend: JotForm
- Hosts the personalization quiz  
- Collects user inputs  
- Sends responses via webhook  

**Strengths:**
- User-friendly interface  
- Secure handling of sensitive data (PHI)

**Limitations:**
- No support for complex computation  

### API Layer: Render
- Hosted at: https://bodybrave-1.onrender.com  
- Receives webhook requests from JotForm  
- Routes data to backend  


### Backend: Python (FastAPI)

#### Responsibilities:
- Process user input  
- Run recommendation algorithm  
- Return top session recommendations  

#### Key Components:
- `app.py` → Core logic and request handling  
- `modules3.csv` → Main session dataset  
- `special_modules.csv` → Special interest sessions  
- `requirements.txt` → Dependencies (FastAPI, Jinja2, etc.)  
- `Procfile` → Deployment configuration  
- `thankyou.html` → Displays recommendations to users  

## Workflow Summary

1. User completes quiz on JotForm  
2. Data sent via webhook to Render API  
3. Python backend:
   - Processes input vector  
   - Computes similarity + popularity scores  
   - Applies hybrid ranking logic  
4. Top recommendations returned and displayed via HTML page  

---

## Updating the System

### A. Adding a General Session

1. Go to GitHub  
2. Open: `render_test/modules3.csv`  
3. Add a new row with:
   - Title  
   - Category scores (1–5)  
   - Link  
   - Description  
4. Commit changes  

**Result:**
- Automatically live within ~5 minutes  
- No changes needed in JotForm  


### B. Adding a Special Interest Session

#### Step 1: Update Dataset
- File: `render_test/special_modules.csv`  
- Add new row with all required fields  
- Ensure **Category Name matches quiz exactly**

#### Step 2: Update JotForm
- Add matching option under:
  > “Special interest modules” question  

**Result:**
- Updates live within ~2 minutes (or instantly via manual deploy)


## Key Notes
- Exact text matching between CSV files and JotForm is critical  
- General modules require **no frontend updates**  
- Special modules require **both backend + frontend updates**  
