import time
import shap
import numpy as np, pandas as pd

from sklearn.ensemble import (
    RandomForestRegressor,
    ExtraTreesRegressor,
    GradientBoostingRegressor
)
from xgboost import XGBRegressor
from lightgbm import LGBMRegressor 
from statsmodels.tsa.statespace.sarimax import SARIMAX
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score
)
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


def compare_models(df, commodity, state=None, market=None):


    s = series_for(df, commodity, state, market)
    d = features(s)

    if len(d) < 50:
        return []

    split = int(len(d) * 0.8)

    X, y = d[FEATURES], d.target

    X_train = X.iloc[:split]
    X_test = X.iloc[split:]

    y_train = y.iloc[:split]
    y_test = y.iloc[split:]

    models = {
        "Random Forest": RandomForestRegressor(
            n_estimators=200,
            random_state=42,
            n_jobs=-1
        ),

        "Extra Trees": ExtraTreesRegressor(
            n_estimators=200,
            random_state=42,
            n_jobs=-1
        ),

        "Gradient Boosting": GradientBoostingRegressor(
            random_state=42
        ),
        "XGBoost": XGBRegressor(
            n_estimators=200,
            max_depth=4,
            learning_rate=0.05,
            subsample=0.9,
            colsample_bytree=0.9,
            objective="reg:squarederror",
            random_state=42,
            n_jobs=-1
        ),
        "LightGBM": LGBMRegressor(
            n_estimators=200,
            max_depth=4,
            learning_rate=0.05,
            subsample=0.9,
            colsample_bytree=0.9,
            random_state=42,
            n_jobs=-1,
            verbosity=-1
        ),
    }

    result = []

    for name, model in models.items():

        start_time = time.perf_counter()

        model.fit(X_train, y_train)

        predictions = model.predict(X_test)

        training_time = time.perf_counter() - start_time

        mae = mean_absolute_error(
            y_test, predictions
        )

        rmse = np.sqrt(
            mean_squared_error(y_test, predictions)
        )

        r2 = r2_score(
            y_test, predictions
        )

        result.append({
            "model": name,
            "mae": round(float(mae), 2),
            "rmse": round(float(rmse), 2),
            "r2_score": round(float(r2), 4),
            "training_time_seconds": round(
                float(training_time), 4
            )
        })
        # SARIMA Model Evaluation
    try:
        start_time = time.perf_counter()

        sarima_model = SARIMAX(
            y_train,
            order=(1, 1, 1),
            seasonal_order=(1, 1, 1, 7),
            enforce_stationarity=False,
            enforce_invertibility=False
        )

        sarima_fitted = sarima_model.fit(disp=False, maxiter=100)
        sarima_predictions = sarima_fitted.forecast(
            steps=len(y_test)
        )

        training_time = time.perf_counter() - start_time

        sarima_mae = mean_absolute_error(
            y_test, sarima_predictions
        )
        sarima_rmse = np.sqrt(
            mean_squared_error(y_test, sarima_predictions)
        )
        sarima_r2 = r2_score(
            y_test, sarima_predictions
        )

        result.append({
            "model": "SARIMA",
            "mae": round(float(sarima_mae), 2),
            "rmse": round(float(sarima_rmse), 2),
            "r2_score": round(float(sarima_r2), 4),
            "training_time_seconds": round(float(training_time), 4)
        })

    except Exception as e:
        print(f"SARIMA evaluation failed: {e}")

    # LSTM Model Evaluation
    try:
        import tensorflow as tf
        from sklearn.preprocessing import MinMaxScaler
        from tensorflow.keras.models import Sequential
        from tensorflow.keras.layers import Input, LSTM, Dense

        start_time = time.perf_counter()

        tf.keras.utils.set_random_seed(42)

        look_back = 14

        train_values = y_train.to_numpy(dtype=np.float32).reshape(-1, 1)
        test_values = y_test.to_numpy(dtype=np.float32).reshape(-1, 1)

        scaler = MinMaxScaler()
        train_scaled = scaler.fit_transform(train_values)

        X_lstm_train = []
        y_lstm_train = []

        for i in range(look_back, len(train_scaled)):
            X_lstm_train.append(train_scaled[i-look_back:i, 0])
            y_lstm_train.append(train_scaled[i, 0])

        if len(X_lstm_train) < 10:
            raise ValueError("Not enough training sequences for LSTM.")

        history = np.concatenate([train_values, test_values], axis=0)
        history_scaled = scaler.transform(history)

        X_lstm_test = []

        for i in range(len(train_values), len(history)):
            X_lstm_test.append(
                history_scaled[i-look_back:i, 0]
            )

        X_lstm_train = np.array(X_lstm_train).reshape(-1, look_back, 1)
        y_lstm_train = np.array(y_lstm_train)
        X_lstm_test = np.array(X_lstm_test).reshape(-1, look_back, 1)

        lstm_model = Sequential([
            Input(shape=(look_back, 1)),
            LSTM(32),
            Dense(1)
        ])

        lstm_model.compile(
            optimizer="adam",
            loss="mse"
        )

        lstm_model.fit(
            X_lstm_train,
            y_lstm_train,
            epochs=15,
            batch_size=16,
            verbose=0,
            shuffle=False
        )

        lstm_scaled_predictions = lstm_model.predict(
            X_lstm_test, verbose=0
        )

        lstm_predictions = scaler.inverse_transform(
            lstm_scaled_predictions
        ).flatten()

        training_time = time.perf_counter() - start_time

        lstm_mae = mean_absolute_error(y_test, lstm_predictions)
        lstm_rmse = np.sqrt(
            mean_squared_error(y_test, lstm_predictions)
        )
        lstm_r2 = r2_score(y_test, lstm_predictions)

        result.append({
            "model": "LSTM",
            "mae": round(float(lstm_mae), 2),
            "rmse": round(float(lstm_rmse), 2),
            "r2_score": round(float(lstm_r2), 4),
            "training_time_seconds": round(float(training_time), 4)
        })

    except Exception as e:
        print(f"LSTM evaluation failed: {e}")
    
    # TFT (Temporal Fusion Transformer) Model Evaluation
    try:
        from pytorch_forecasting import (
            TimeSeriesDataSet,
            TemporalFusionTransformer
        )
        from pytorch_forecasting.metrics import QuantileLoss
        from lightning.pytorch import Trainer, seed_everything

        start_time = time.perf_counter()
        seed_everything(42, workers=True)

        tft_split = len(s) - len(d) + split

        tft_data = pd.DataFrame({
            "time_idx": np.arange(len(s)),
            "price": s.to_numpy(dtype=np.float32),
            "series": "market"
        })

        training_data = TimeSeriesDataSet(
            tft_data.iloc[:tft_split],
            time_idx="time_idx",
            target="price",
            group_ids=["series"],
            max_encoder_length=14,
            min_encoder_length=14,
            max_prediction_length=1,
            min_prediction_length=1,
            time_varying_known_reals=["time_idx"],
            time_varying_unknown_reals=["price"],
            add_relative_time_idx=True,
            add_target_scales=True,
            add_encoder_length=True
        )

        validation_data = TimeSeriesDataSet.from_dataset(
            training_data,
            tft_data,
            min_prediction_idx=tft_split,
            stop_randomization=True
        )

        train_loader = training_data.to_dataloader(
            train=True, batch_size=32, num_workers=0
        )

        val_loader = validation_data.to_dataloader(
            train=False, batch_size=32, num_workers=0
        )

        tft_model = TemporalFusionTransformer.from_dataset(
            training_data,
            learning_rate=0.03,
            hidden_size=8,
            attention_head_size=2,
            dropout=0.1,
            hidden_continuous_size=4,
            loss=QuantileLoss(),
            log_interval=-1,
            reduce_on_plateau_patience=3
        )

        trainer = Trainer(
            max_epochs=10,
            accelerator="cpu",
            devices=1,
            logger=False,
            enable_checkpointing=False,
            enable_model_summary=False,
            enable_progress_bar=False,
            gradient_clip_val=0.1
        )

        trainer.fit(
    tft_model,
    train_dataloaders=train_loader,
    val_dataloaders=val_loader
)

        tft_predictions = tft_model.predict(
            val_loader, mode="prediction"
        )
        tft_predictions = (
            tft_predictions.detach().cpu().numpy().reshape(-1)
        )

        if len(tft_predictions) != len(y_test):
            raise ValueError("TFT prediction and test data lengths do not match.")

        training_time = time.perf_counter() - start_time

        tft_mae = mean_absolute_error(y_test, tft_predictions)
        tft_rmse = np.sqrt(
            mean_squared_error(y_test, tft_predictions)
        )
        tft_r2 = r2_score(y_test, tft_predictions)

        result.append({
            "model": "TFT",
            "mae": round(float(tft_mae), 2),
            "rmse": round(float(tft_rmse), 2),
            "r2_score": round(float(tft_r2), 4),
            "training_time_seconds": round(float(training_time), 4)
        })

    except Exception as e:
        print(f"TFT evaluation failed: {e}")

    result = sorted(
        result,
        key=lambda x: x["mae"]
    )

    for index, item in enumerate(result):
        item["rank"] = index + 1
        item["best_model"] = index == 0

    return result
def explain_model(df, commodity, state=None, market=None):

    s = series_for(df, commodity, state, market)

    if len(s) < 45:
        return {
            "available": False,
            "reason": "Not enough daily observations for SHAP explanation."
        }

    d = features(s)

    if len(d) < 25:
        return {
            "available": False,
            "reason": "Not enough observations after feature creation."
        }

    X = d[FEATURES]
    y = d.target

    model = RandomForestRegressor(
        n_estimators=200,
        min_samples_leaf=2,
        random_state=42,
        n_jobs=-1
    )

    model.fit(X, y)

    sample = X.tail(min(100, len(X)))

    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(sample)

    mean_values = np.abs(shap_values).mean(axis=0)

    explanations = []

    for feature, value in zip(FEATURES, mean_values):
        explanations.append({
            "feature": feature,
            "mean_shap_value": round(float(value), 4)
        })

    explanations.sort(
        key=lambda x: x["mean_shap_value"],
        reverse=True
    )

    return {
        "available": True,
        "model": "Random Forest + SHAP",
        "observations": int(len(X)),
        "explained_samples": int(len(sample)),
        "top_features": explanations[:10],
        "explanation_note": (
            "SHAP values show each feature's contribution "
            "to model predictions. They do not prove causation."
        )
    }