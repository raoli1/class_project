import logging
import azure.functions as func
from sklearn.linear_model import LinearRegression
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
    
hpi_df = pd.read_csv("https://raw.githubusercontent.com/raoli1/class_project/raoli/classProject/All-Transaction%20HPI.csv", index_col=0)
states = pd.read_csv('https://raw.githubusercontent.com/plotly/datasets/master/2011_us_ag_exports.csv')['state']

### Linear Regression in for national data
X = us_annual.drop(columns=['CSUSHPINSA'], axis=1)
Y = us_annual['CSUSHPINSA']
X_train, X_test, Y_train, Y_test = X.loc[:2010], X.loc[2010:], Y.loc[:2010], Y.loc[2010:]
lin_model = LinearRegression()
lin_model.fit(X_train, Y_train)
y_train_predict = lin_model.predict(X_train)
y_test_predict = lin_model.predict(X_test)

def national_map():
    data = [dict(type='choropleth',
                     locations=hpi_df.columns.to_series(),
                                    locationmode='USA-states',
                                    colorscale = "PRGn",
                                    autocolorscale=False,
                                    z=hpi_df.loc[2019],
                                    text=states,
                                    marker_line_color='white')]
    layout = dict(geo=dict(scope='usa'), title="Statewide All-Transaction Housing Price Index in 2019")

    graphJSON = json.dumps(dict(data=data, layout=layout), cls=plotly.utils.PlotlyJSONEncoder)

    return graphJSON

def create_plot(feature):
    if feature == 'National':
        trace1 = go.Scatter(
            x=us_annual.index, 
            y=us_annual['CSUSHPINSA'], 
            xaxis='x',yaxis='y',
            name="HPI")
        trace2 = go.Scatter(
            x=us_annual.index, 
            y=us_annual['GDP'], name="GDP",
            xaxis='x',yaxis='y3')
        trace3 = go.Scatter(
            x=us_annual.index, 
            y=us_annual['LNU00024230'], name="Population (Age>54)",
            xaxis='x',yaxis='y4')
        trace4 = go.Scatter(
            x=us_annual.index, y=us_annual['SP500'], 
            name="S&P500", xaxis='x',yaxis='y5')
        trace5 = go.Scatter(x=Y.index, y=Y.tolist(), name="Actual Index",
                          xaxis='x2',
                          yaxis='y2')
        trace6 = go.Scatter(x=Y.index, y=list(y_train_predict)+list(y_test_predict), 
                            name="Experimental Index", 
                           xaxis='x2',
                           yaxis='y6')
        
        data = [trace1, trace2, trace3, trace4, trace5, trace6]
        layout = dict(
                legend=dict(x=-.1, y=1.2, orientation="h"),
                grid=dict(rows=1, columns=2, pattern='independent'),
                yaxis=dict(title='Housing Price Index',
                          titlefont=dict(
                                color="#1f77b4"
                            ),
                            tickfont=dict(
                                color="#1f77b4"
                            )),
                yaxis3=dict(
                    title='Gross Domestic Product',
                    titlefont=dict(
                            color="#FFA500"
                        ),
                        tickfont=dict(
                            color="#FFA500"
                        ),
                    overlaying='y',
                    side='right'),
                yaxis4=dict(
                    title='Total Population of Age>54',
                    titlefont=dict(
                            color="#00ff00"
                        ),
                        tickfont=dict(
                            color="#00ff00"
                        ),
                    anchor="free",
                    overlaying="y",
                    side="left",
                    position=0.05),
                yaxis5=dict(
                    title='S&P 500 Index',
                    titlefont=dict(
                            color="#d62728"
                        ),
                        tickfont=dict(
                            color="#d62728"
                        ),
                       anchor="free",
                        overlaying="y",
                        side="right",
                        position=0.40),
                yaxis2=dict(title='Actual'),
                yaxis6=dict(title='Predicted',
                            anchor="free",
                            position=1,
                           overlaying='y2',
                           side='right'),
                annotations=[dict(text='Significant Econ Variables on National HPI', showarrow=False, font=dict(size=14),
                                  align='center', x=0.1, y= 1, xref='paper',yref='paper'), 
                             dict(text='Predicted HPI Using LinRegress on Econ Variables', 
                                  showarrow=False, font=dict(size=14),
                                  align='center', x=0.96, y= 1, xref='paper',yref='paper')])
        
                     

    else:
        # gotta extract data from fred
        suffix = "STHPI"
        pop = 'POP'
        series = fred.get_series(feature+suffix).to_frame().rename(columns={0:feature})
        series = series.groupby(series.index.year).mean()
        series2 = fred.get_series(feature+pop).to_frame().rename(columns={0:pop})
        series = series2.groupby(series2.index.year).mean().merge(series, left_index=True, right_index=True)
        data = [go.Scatter(x=series.index, y=series[feature], name=feature+' HPI'), 
               go.Scatter(x=series.index, y=series[pop], name='State Population', yaxis='y2')]
        layout = dict(title=feature+' Housing Price Index and Population over Time',
                     xaxis=dict(title='Year'),
                     yaxis=dict(title='Housing Index'),
                     yaxis2=dict(title='State Population', anchor="free",
                    overlaying="y", side='right'))

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

    with app.test_client() as c:
        doAction = {
            "GET": c.get(uri).data,
            "POST": c.post(uri).data
        }
        resp = doAction.get(req.method).decode()
    
    return func.HttpResponse(resp, mimetype='text/html')

