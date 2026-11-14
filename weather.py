import requests

def get_weather(place):
    try:
        g=requests.get('https://geocoding-api.open-meteo.com/v1/search',params={'name':place,'count':1,'language':'en','format':'json'},timeout=15); g.raise_for_status()
        found=g.json().get('results',[])
        if not found:return {"available":False,"error":f"Location not found: {place}"}
        loc=found[0]
        params={'latitude':loc['latitude'],'longitude':loc['longitude'],'current':'temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m,cloud_cover','daily':'temperature_2m_max,temperature_2m_min,precipitation_sum,wind_speed_10m_max','hourly':'soil_moisture_0_to_7cm','forecast_days':7,'timezone':'auto'}
        r=requests.get('https://api.open-meteo.com/v1/forecast',params=params,timeout=20); r.raise_for_status(); j=r.json()
        d=j.get('daily',{}); daily=[{'date':d['time'][i],'temp_max':d['temperature_2m_max'][i],'temp_min':d['temperature_2m_min'][i],'rain_sum':d['precipitation_sum'][i],'wind_max':d['wind_speed_10m_max'][i]} for i in range(len(d.get('time',[])))]
        h=j.get('hourly',{}); moist=h.get('soil_moisture_0_to_7cm',[])
        return {'available':True,'location':f"{loc.get('name')}, {loc.get('admin1','')}, {loc.get('country','')}",'current':j.get('current',{}),'daily':daily,'soil_moisture_latest':next((v for v in reversed(moist) if v is not None),None),'source':'Open-Meteo forecast API','note':'Soil moisture is provider model output, not a local sensor measurement.'}
    except Exception as e:return {'available':False,'error':f'Weather provider unavailable: {e}'}
