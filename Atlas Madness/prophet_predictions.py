from datetime import date, timedelta
import pandas as pd
import numpy as np
import ee
import matplotlib.pyplot as plt
from prophet import Prophet

def make_pred(original_date, long, lat):

    date_of_policy = date.fromisoformat(original_date)

    delta = timedelta(days=150)


    lst = ee.ImageCollection('COPERNICUS/S5P/NRTI/L3_NO2').select('NO2_column_number_density').filterDate((date_of_policy - delta).isoformat(), (date_of_policy + delta).isoformat())


    u_poi = ee.Geometry.Point(long, lat) #long, lat

    scale = 25 * 1000 # scale in meters, average area of a county used to get calc radius

    lst_u_poi = lst.getRegion(u_poi, scale).getInfo()
    measurements = np.array(lst_u_poi[1:])

    time_series = pd.DataFrame()
    #time_series['id'] = measurements[:,0]
    #time_series['longitude'] = measurements[:,1]
    #time_series['latitude'] = measurements[:,2]
    time_series['ds'] = measurements[:,3]
    time_series['ds'] = pd.to_datetime(time_series['ds'], unit='ms')


    time_series['y'] = np.array(measurements[:,4]).astype(float)

    time_series = time_series.replace(to_replace='None', value=np.nan).dropna()
    train = time_series[time_series['ds'] <= original_date]
    test = time_series[time_series['ds'] > original_date]

    model = Prophet()

    # Fit the model
    model.fit(train)

    # create date to predict
    future_dates = model.make_future_dataframe(periods=150)

    # Make predictions
    predictions = model.predict(future_dates)

    plt.figure(figsize=(10,6))
    plt.plot(train['ds'], train['y'], color='red', label='Before Policy Measurements')
    plt.plot(test['ds'], test['y'], color='orange', label='After Policy Measurements')
    plt.plot(predictions[predictions['ds'] > original_date]['ds'], predictions[predictions['ds'] > original_date]['yhat'], label='Prophet Model Prediction')
    plt.ylabel('NO2_column_number_density')
    plt.xlabel('Date')
    plt.title('NO2_column_number_density vs. Time')
    leg = plt.legend(loc='upper center')
    plt.savefig('prophet_prediction')