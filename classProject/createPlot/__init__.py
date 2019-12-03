import logging
import azure.functions as func
from flask import Flask, render_template
import plotly.graph_objects as go, plotly
import numpy as np, pandas as pd, matplotlib.pyplot as plt, seaborn as sns
import json
from fredapi import Fred
import quandl
import pathlib

fred = Fred(api_key="a02df0a22c57860f5f7cf25edc70ffb3")
quandl.ApiConfig.api_key = "QZLZXdHDDPZna9Yw48NP"

app = Flask(__name__)


@app.route('/api/createPlot')
def index():
    
    return render_template("home.html")

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')
    
    uri='/api/createPlot'
    with app.test_client() as c:
        doAction = {
            "GET": c.get(uri).data,
            "POST": c.post(uri).data
        }
        resp = doAction.get(req.method).decode()
    
    return func.HttpResponse(resp, mimetype='text/html')

