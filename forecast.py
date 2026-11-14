import numpy as np, pandas as pd
from sklearn.ensemble import RandomForestRegressor, ExtraTreesRegressor, GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error
FEATURES=["lag_1","lag_2","lag_3","lag_7","lag_14","rolling_7","rolling_14","dow","month","doy"]

def series_for(df, commodity, state=None, market=None):
    x=df[df.commodity.str.casefold()==commodity.casefold()].copy()
    if state and state!='All': x=x[x.state.str.casefold()==state.casefold()]
    if market and market!='All': x=x[x.market.str.casefold()==market.casefold()]
    if x.empty: return pd.Series(dtype=float)
    return x.groupby('date').modal_price.mean().sort_index().asfreq('D').interpolate(limit=3).dropna()

def features(s):
    x=pd.DataFrame(index=s.index)
    for lag in [1,2,3,7,14]: x[f'lag_{lag}']=s.shift(lag)
    x['rolling_7']=s.shift(1).rolling(7).mean(); x['rolling_14']=s.shift(1).rolling(14).mean()
    x['dow']=x.index.dayofweek; x['month']=x.index.month; x['doy']=x.index.dayofyear; x['target']=s
    return x.dropna()

def make_forecast(df, commodity, horizon, state=None, market=None):
    s=series_for(df,commodity,state,market)
    if len(s)<45:
        return {"available":False,"reason":f"Only {len(s)} daily observations are available after filtering. At least 45 continuous daily observations are required for this baseline model. No forecast was fabricated."}
    d=features(s)
    if len(d)<25: return {"available":False,"reason":"Not enough observations after lag feature creation."}
    split=max(20,int(len(d)*.8)); X,y=d[FEATURES],d.target
    model=RandomForestRegressor(n_estimators=300,min_samples_leaf=2,random_state=42,n_jobs=-1)
    model.fit(X.iloc[:split],y.iloc[:split]); pred=model.predict(X.iloc[split:])
    mae=float(mean_absolute_error(y.iloc[split:],pred)); rmse=float(np.sqrt(mean_squared_error(y.iloc[split:],pred)))
    model.fit(X,y); hist=list(s.values); rows=[]
    for i in range(horizon):
        dt=s.index[-1]+pd.Timedelta(days=i+1)
        r={"lag_1":hist[-1],"lag_2":hist[-2],"lag_3":hist[-3],"lag_7":hist[-7],"lag_14":hist[-14],"rolling_7":np.mean(hist[-7:]),"rolling_14":np.mean(hist[-14:]),"dow":dt.dayofweek,"month":dt.month,"doy":dt.dayofyear}
        val=max(0,float(model.predict(pd.DataFrame([r],columns=FEATURES))[0])); hist.append(val)
        spread=max(mae,float(s.iloc[-1])*.03)
        rows.append({"date":dt.date().isoformat(),"predicted_modal_price":round(val,2),"lower_estimate":round(max(0,val-spread),2),"upper_estimate":round(val+spread,2)})
    out=pd.DataFrame(rows); latest=float(s.iloc[-1]); end=float(out.predicted_modal_price.iloc[-1])
    importance=sorted([{"feature":f,"importance":round(float(v),4)} for f,v in zip(FEATURES,model.feature_importances_)],key=lambda x:x['importance'],reverse=True)
    return {"available":True,"model":"Random Forest (recursive baseline)","training_observations":int(len(d)),"holdout_observations":int(len(y)-split),"mae":round(mae,2),"rmse":round(rmse,2),"latest_observed":round(latest,2),"change_pct":round((end-latest)/latest*100,2) if latest else 0,"forecast":out.to_dict(orient='records'),"feature_importance":importance,"confidence_note":"Empirical error band from chronological holdout MAE; not a calibrated probability interval."}

def compare_models(df,commodity,state=None,market=None):
    s=series_for(df,commodity,state,market); d=features(s)
    if len(d)<50:return []
    split=int(len(d)*.8); X,y=d[FEATURES],d.target; result=[]
    models={"Random Forest":RandomForestRegressor(n_estimators=200,random_state=42),"Extra Trees":ExtraTreesRegressor(n_estimators=200,random_state=42),"Gradient Boosting":GradientBoostingRegressor(random_state=42)}
    for name,m in models.items():
        m.fit(X.iloc[:split],y.iloc[:split]); p=m.predict(X.iloc[split:]); result.append({"model":name,"mae":round(float(mean_absolute_error(y.iloc[split:],p)),2),"rmse":round(float(np.sqrt(mean_squared_error(y.iloc[split:],p))),2)})
    return sorted(result,key=lambda z:z['mae'])
