import json
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# Store the most recent form data for display
last_form_data = {}

@app.post("/submit", response_class=HTMLResponse)
async def capture_submit(request: Request):
    global last_form_data
    form_data = await request.form()
    last_form_data = dict(form_data)
    print("Captured /submit data:", last_form_data)
    
    # Format the data as a string for display
    data_str = "<h2>Received /submit Data:</h2><pre>" + json.dumps(last_form_data, indent=2) + "</pre>"
    return HTMLResponse(content=data_str)

@app.get("/", response_class=HTMLResponse)
async def view_data(request: Request):
    # Display the most recent form data
    if not last_form_data:
        return HTMLResponse(content="<h2>No Data Received Yet</h2><p>Submit a form to see the data.</p>")
    
    data_str = "<h2>Last Received Form Data:</h2><pre>" + json.dumps(last_form_data, indent=2) + "</pre>"
    return HTMLResponse(content=data_str)
