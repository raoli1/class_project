import logging
import azure.functions as func
import requests
import json
from fredapi import Fred
import pandas as pd
from datetime import datetime
from flask import Flask, request, render_template
import matplotlib.pyplot as plt
from io import BytesIO
import base64
import numpy as np

app = Flask(__name__)

#Query BLS API with given date range
def queryBLS(startyear,endyear):
    startyear = startyear
    endyear = endyear
    headers = {'Content-type': 'application/json'}

    #query National total nonforam Employment data seasonally adjusted
    #query New York total nonforam Employment data seasonally adjusted
    data = json.dumps({"seriesid": ['CES0000000001', 'SMS36000000000000001'],"startyear":startyear, "endyear":endyear,  "registrationkey":"510ada63df934476b797c3e3df9d5cdd"})
    p = requests.post('https://api.bls.gov/publicAPI/v2/timeseries/data/', data=data, headers=headers)
    json_data = json.loads(p.text)
    #print(json_data)
    status = json_data['status']
    result_national = []
    result_New_York = []
    MonthConverter ={
        'January' : 1,
        'February' : 2,
        'March' : 3,
        'April' : 4,
        'May' : 5,
        'June' : 6,
        'July' : 7,
        'August' : 8,
        'September' : 9, 
        'October' : 10,
        'November' : 11,
        'December' : 12}
    seriesIDConverter ={
        'SMS36000000000000001' : 'New York',
        'CES0000000001' : 'National'
    }
    if status == 'REQUEST_SUCCEEDED':
        for series in json_data['Results']['series']:
            area = seriesIDConverter[series['seriesID']]
            if area == 'New York':
                for item in series['data']:
                    year = item['year']
                    period = MonthConverter[item['periodName']]
                    value = item['value']
                    result_New_York.append({'year':int(year) ,'month':period ,'value':float(value)})
            if area == 'National':
                for item in series['data']:
                    year = item['year']
                    period = MonthConverter[item['periodName']]
                    value = item['value']
                    result_national.append({'year':int(year) ,'month':period ,'value':float(value)})
    return (result_national, result_New_York)

def queryFred(startyear, endyear):
    fred = Fred(api_key='26974e04eac3aab16fa7b5d74bd47f93')
    datas_national = fred.get_series('CSUSHPISA')
    datas_New_York = fred.get_series('NYXRSA')
    result_national = []
    result_New_York = []

    for date, data in datas_national.iteritems():

        month = date.date().month
        year = date.date().year
        value = data
        if year >= int(startyear) and year <= int(endyear):
            result_national.append({'year':year,'month':month,'value':data})

    for date, data in datas_New_York.iteritems():

        month = date.date().month
        year = date.date().year
        value = data
        if year >= int(startyear) and year <= int(endyear):
            result_New_York.append({'year':year,'month':month,'value':data})
    
    
    return(result_national,result_New_York)

def getAnnual(result_national, result_New_York):
    annual = {}
    annual_New_York = {}
    
    for record in result_national:
        if record['year'] not in annual:
            annual[record['year']]=[record['value'],1,record['value']]
        else:
            annual[record['year']][0]+=record['value']
            annual[record['year']][1]+=1
            annual[record['year']][2]=annual[record['year']][0]/annual[record['year']][1]

    for record in result_New_York:
        if record['year'] not in annual_New_York:
            annual_New_York[record['year']]=[record['value'],1,record['value']]
        else:
            annual_New_York[record['year']][0]+=record['value']
            annual_New_York[record['year']][1]+=1
            annual_New_York[record['year']][2]=annual_New_York[record['year']][0]/annual_New_York[record['year']][1]

    
    return (annual, annual_New_York)

@app.route('/api/connectToApi')
def home():
    
    return render_template("templates.html")

@app.route('/api/connectToApi/startyear=<startyear>/endyear=<endyear>', methods=['GET'])
def result(startyear,endyear):

    result = queryBLS(startyear,endyear)
    result_annual = getAnnual(result[0],result[1])
    result_housing = queryFred(startyear, endyear)
    result_housing_annual = getAnnual(result_housing[0],result_housing[1])
    x = []
    y = []
    year = []
    corr = []

    for i in range(int(startyear),int(endyear)+1):
        x.append(result_annual[0][i][2])
        y.append(result_housing_annual[0][i][2])
        year.append(str(i))
        
    plt.plot(x, y, 'bo')
    plt.xlabel('Employment')
    plt.ylabel('Case-Shiller Index')
    figfile = BytesIO()
    plt.savefig(figfile, format='png')
    figfile.seek(0)
    figdata_png = base64.b64encode(figfile.getvalue())
    plt.clf()
    corr = np.corrcoef(x,y)[0][1]
    
    
    
    x_NY = []
    y_NY = []

    for i in range(int(startyear),int(endyear)+1):
        x_NY.append(result_annual[1][i][2])
        y_NY.append(result_housing_annual[1][i][2])

    plt.plot(x_NY, y_NY, 'bo')
    plt.xlabel('Employment')
    plt.ylabel('Case-Shiller Index')
    figfile_NY = BytesIO()
    plt.savefig(figfile_NY, format='png')
    figfile_NY.seek(0)
    figdata_png_NY = base64.b64encode(figfile_NY.getvalue())
    plt.clf()
    corr_NY = np.corrcoef(x_NY, y_NY)[0][1]
    
    return render_template("showResult.html", result=result_annual, result_housing= result_housing_annual, startyear=startyear, endyear=endyear,plotData = figdata_png.decode('utf8'), plotData_NY = figdata_png_NY.decode('utf8'), corr = corr, corr_NY = corr_NY)


def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')
    startyear=req.params.get("startyear")
    endyear = req.params.get("endyear")
    uri=''
    if(startyear is None or endyear is None):
        uri='/api/connectToApi'
    elif (startyear is not None and endyear is not None):
        uri='/api/connectToApi/startyear='+startyear+'/endyear='+endyear
    
    with app.test_client() as c:
        doAction = {
            "GET": c.get(uri).data,
            "POST": c.post(uri).data
        }
        resp = doAction.get(req.method).decode()
        #return func.HttpResponse(resp, mimetype='text/html')
        return func.HttpResponse(resp, mimetype='text/html')
