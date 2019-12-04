import logging
import azure.functions as func
from flask import Flask, render_template, request
import numpy as np, pandas as pd, matplotlib.pyplot as plt, seaborn as sns
import json
from fredapi import Fred
from datetime import datetime, timedelta
import quandl
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly




fred = Fred(api_key="a02df0a22c57860f5f7cf25edc70ffb3")
quandl.ApiConfig.api_key = "QZLZXdHDDPZna9Yw48NP"
app = Flask(__name__)

def get_info(names):
    data = []
    for i in range(len(names)):
        data.append(fred.get_series(names[i]).to_frame().rename(columns={0:names[i]}))
        data[i] = data[i].groupby(data[i].index.year).mean().dropna()
    return data

sp500 = quandl.get('MULTPL/SP500_REAL_PRICE_MONTH').rename(columns={'Value':'SP500'})
names = ["GDP", "SPPOPDPNDOLUSA", "LNU00000036", "LNU00000060", "LNU00024230", "UNRATE", "RHORUSQ156N", "USHVAC"]
sp500 = sp500.groupby(sp500.index.year).mean().dropna()
us_data_series = get_info(names) + [sp500]

usHPI = fred.get_series('CSUSHPINSA').to_frame().rename(columns={0:'CSUSHPINSA'})
usHPI_annual = usHPI.groupby(usHPI.index.year).mean().dropna()
us_annual = usHPI_annual.copy()
for df in us_data_series:
    us_annual = us_annual.merge(df, left_index=True, right_index=True)

# Create figure with secondary y-axis
fig = make_subplots(specs=[[{"secondary_y": True}]])

# Add traces
fig.add_trace(
    go.Scatter(x=us_annual.index, y=us_annual['CSUSHPINSA'], name="HPI"),
    secondary_y=False,
)

fig.add_trace(
    go.Scatter(x=us_annual.index, y=us_annual['GDP'], name="GDP"),
    secondary_y=True,
)

# Add figure title
fig.update_layout(
    title_text="National Housing Price Index"
)

# Set x-axis title
fig.update_xaxes(title_text="Year")

# Set y-axes titles
fig.update_yaxes(title_text="</b> HPI", secondary_y=False)
fig.update_yaxes(title_text="</b> GDP", secondary_y=True)

hpi_df = pd.read_csv('https://raw.githubusercontent.com/raoli1/class_project/raoli/classProject/All-Transaction%20HPI.csv', index_col=0)
states = pd.read_csv('https://raw.githubusercontent.com/plotly/datasets/master/2011_us_ag_exports.csv')['state']
fig = go.Figure(data=go.Choropleth(locations=hpi_df.columns.to_series(),
                                    locationmode='USA-states',
                                    colorscale='RdBu',
                                    autocolorscale=False,
                                    z=hpi_df.loc[2019],
                                    text=states,
                                    marker_line_color='white'))
fig.update_layout(title_text="2019 All-Transaction Housing Price Index",
                 geo_scope='usa')

def national_map():
    data = [dict(type='choropleth',
                     locations=hpi_df.columns.to_series(),
                                    locationmode='USA-states',
                                    colorscale = "Viridis",
                                    autocolorscale=False,
                                    z=hpi_df.loc[2019],
                                    text=states,
                                    marker_line_color='white')]
    layout = dict(geo=dict(scope='usa'))

    graphJSON = json.dumps(dict(data=data, layout=layout), cls=plotly.utils.PlotlyJSONEncoder)

    return graphJSON

def create_plot(feature):
    if feature == 'National':
        trace1 = go.Scatter(
            x=us_annual.index, 
            y=us_annual['CSUSHPINSA'], 
            name="HPI")
        trace2 = go.Scatter(
            x=us_annual.index, 
            y=us_annual['GDP'], 
            name="GDP",
            yaxis='y2')
        data = [trace1, trace2]
        layout = dict(title="National Housing Price Index vs. GDP over Time",
                yaxis=dict(title='Housing Price Index'),
                yaxis2=dict(
                    title='Gross Domestic Product',
                    titlefont=dict(
                        color='rgb(148, 103, 189)'
                    ),
                    tickfont=dict(
                        color='rgb(148, 103, 189)'
                    ),
                    overlaying='y',
                    side='right'))

    else:
        # gotta extract data from fred
        suffix = "STHPI"
        series = fred.get_series(feature+suffix).to_frame().rename(columns={0:feature})
        series = series.groupby(series.index.year).mean()
        data = [go.Scatter(x=series.index, y=series[feature], name=feature)]
        layout = dict(title=feature+' Housing Price Index over Time',
                     xaxis=dict(title='Year'),
                     yaxis=dict(title='Index'))

    graphJSON = json.dumps(dict(data=data, layout=layout), cls=plotly.utils.PlotlyJSONEncoder)

    return graphJSON

@app.route('/api/createPlot')
def index():
    feature = 'National'
    national = national_map()
    bar = create_plot(feature)
    regional = hpi_df.columns.to_series().tolist()
    return render_template('index.html', codelst=regional, usamap=national, plot=bar)

@app.route('/api/createPlot/bar/selected=<state>', methods=['GET', 'POST'])
def change_features(state):
    feature = str(state)
    graphJSON= create_plot(feature)
    return graphJSON


def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')
    uri = ''
    state = req.params.get("selected")
    if not state:
        uri='/api/createPlot'
    else:
        uri='/api/createPlot/bar/selected='+state

    #state = req.params.get("selected")
    #if state:
        #uri='/api/createPlot?selected='+state
   
    with app.test_client() as c:
        doAction = {
            "GET": c.get(uri).data,
            "POST": c.post(uri).data
        }
        resp = doAction.get(req.method).decode()
    
    return func.HttpResponse(resp, mimetype='text/html')

