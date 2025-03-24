from flask import Flask, request, redirect, url_for

app = Flask(__name__)

# Temporary storage for the last submission (in memory, resets on restart)
last_submission = {}

@app.route('/webhook', methods=['POST'])
def webhook():
    global last_submission
    data = request.form.to_dict()
    last_submission = data  # Store the submission data
    # Redirect to the thank-you page on Render
    return redirect(url_for('thank_you'))

@app.route('/thank-you')
def thank_you():
    # Display the submission data
    if last_submission:
        return f"Thank you! Response from Render: Got your submission! You sent: {last_submission}"
    return "Thank you! No submission data available."

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
