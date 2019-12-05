import logging

import azure.functions as func
from flask import Flask, request, render_template

app = Flask(__name__)

@app.route('/api/homepage')
def home():
    
    return render_template("home.html")

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    uri='/api/homepage'
    with app.test_client() as c:
        doAction = {
            "GET": c.get(uri).data,
            "POST": c.post(uri).data
        }
        resp = doAction.get(req.method).decode()

    return func.HttpResponse(resp, mimetype='text/html')
