from flask import Flask, request

app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.form.to_dict()  # Get JotForm submission data
    return f"Got your submission! You sent: {data}"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
