import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error

# --- 1. Page Configuration & Theme ---
st.set_page_config(
    page_title="Kenya Economic Intelligence Engine",
    page_icon="📈",
    layout="wide"
)

st.title("📈 Kenya Economic Intelligence & Forecasting Engine")
st.markdown("""
This interactive web application forecasts Kenyan retail maize prices using macroeconomic indicators 
(CPI, USD/KES Exchange Rate, Central Bank Rate) and autoregressive price lags. 
Select models and adjust economic scenario inputs in the sidebar to simulate forecast dynamics.
""")
st.divider()

# --- 2. Data Loading & Pipeline Execution (Cloud-Optimized CSV Loader) ---
@st.cache_data
def load_and_preprocess_data():
    # Read from preprocessed dataset exported for cloud deployment
    df_model_ready = pd.read_csv("economic_data_ready.csv")
    df_model_ready['observation_month'] = pd.to_datetime(df_model_ready['observation_month'])
    return df_model_ready

try:
    df_model_ready = load_and_preprocess_data()
except Exception as e:
    st.error(f"Failed to load dataset: {e}. Please ensure 'economic_data_ready.csv' is uploaded to your repository.")
    st.stop()

# --- 3. Feature Selection & Chronological Train/Test Split ---
feature_cols = [
    'MAIZE_RETAIL_PRICE_KG_lag1', 
    'CPI_INDEX_lag1', 
    'EXCHANGE_RATE_USD_KES_lag1', 
    'CENTRAL_BANK_RATE_lag1'
]

X = df_model_ready[feature_cols]
y = df_model_ready['MAIZE_RETAIL_PRICE_KG']
dates = df_model_ready['observation_month']

split_index = len(df_model_ready) - 24

X_train, X_test = X.iloc[:split_index], X.iloc[split_index:]
y_train, y_test = y.iloc[:split_index], y.iloc[split_index:]
dates_test = dates.iloc[split_index:]

# --- 4. Sidebar Controls ---
st.sidebar.header("⚙️ Model & Scenario Controls")

selected_model_name = st.sidebar.selectbox(
    "Select Forecasting Model",
    ["Linear Regression Baseline", "Ridge Regularization", "Tuned Random Forest"]
)

st.sidebar.subheader("🔮 Macroeconomic Scenario Adjustments")
st.sidebar.caption("Simulate small percentage shifts in the most recent indicator values:")

latest_row = X_test.iloc[-1].copy()
adj_cpi = st.sidebar.slider("CPI Index Shift (%)", -10.0, 10.0, 0.0, 0.5)
adj_fx = st.sidebar.slider("USD/KES Exchange Rate Shift (%)", -10.0, 10.0, 0.0, 0.5)
adj_cbr = st.sidebar.slider("Central Bank Rate Shift (%)", -5.0, 5.0, 0.0, 0.25)

# Adjust scenario input vector
scenario_input = latest_row.copy()
scenario_input['CPI_INDEX_lag1'] *= (1 + adj_cpi / 100.0)
scenario_input['EXCHANGE_RATE_USD_KES_lag1'] *= (1 + adj_fx / 100.0)
scenario_input['CENTRAL_BANK_RATE_lag1'] *= (1 + adj_cbr / 100.0)

# --- 5. Model Instantiation & Training ---
models = {
    "Linear Regression Baseline": LinearRegression(),
    "Ridge Regularization": Ridge(alpha=10.0),
    "Tuned Random Forest": RandomForestRegressor(n_estimators=150, max_depth=5, random_state=42)
}

active_model = models[selected_model_name]
active_model.fit(X_train, y_train)

# Generate out-of-sample test predictions
y_pred_test = active_model.predict(X_test)

# Calculate metrics
mae = mean_absolute_error(y_test, y_pred_test)
rmse = np.sqrt(mean_squared_error(y_test, y_pred_test))

# Scenario prediction
scenario_pred = active_model.predict(pd.DataFrame([scenario_input]))[0]

# --- 6. Top Metric Cards ---
col1, col2, col3 = st.columns(3)
col1.metric("Out-of-Sample MAE", f"KES {mae:.2f}")
col2.metric("Out-of-Sample RMSE", f"KES {rmse:.2f}")
col3.metric("Simulated Next-Month Price", f"KES {scenario_pred:.2f}", delta=f"{(scenario_pred - y_test.iloc[-1]):.2f} KES vs Last")

st.divider()

# --- 7. Main Plots Layout ---
tab1, tab2, tab3 = st.tabs(["📉 Forecast Dashboard", "📊 Feature Importances", "🔍 Residual Analysis"])

with tab1:
    st.subheader(f"Out-of-Sample Evaluation: {selected_model_name}")
    
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(dates_test, y_test, label='Actual Retail Price', color='#1f77b4', marker='o', linewidth=2)
    ax.plot(dates_test, y_pred_test, label=f'Predicted ({selected_model_name})', color='#ff7f0e', linestyle='--', marker='x', linewidth=1.5)
    ax.set_title("Kenyan Retail Maize Prices (2024–2025 Test Window)")
    ax.set_xlabel("Observation Month")
    ax.set_ylabel("Price (KES per Kg)")
    ax.grid(True, linestyle='--', alpha=0.6)
    ax.legend()
    st.pyplot(fig)

with tab2:
    st.subheader("Random Forest Feature Importance Weights")
    rf_explainer = RandomForestRegressor(n_estimators=100, max_depth=5, random_state=42)
    rf_explainer.fit(X_train, y_train)
    
    importances = pd.DataFrame({
        'Feature': feature_cols,
        'Importance': rf_explainer.feature_importances_
    }).sort_values('Importance', ascending=True)
    
    fig_imp, ax_imp = plt.subplots(figsize=(9, 4))
    ax_imp.barh(importances['Feature'], importances['Importance'], color='#2ca02c')
    ax_imp.set_xlabel("Importance Score")
    ax_imp.set_title("Relative Feature Weights (Random Forest Regressor)")
    ax_imp.grid(True, linestyle='--', alpha=0.6, axis='x')
    st.pyplot(fig_imp)

with tab3:
    st.subheader("Out-of-Sample Residual Errors over Time")
    residuals = y_test - y_pred_test
    
    fig_res, ax_res = plt.subplots(figsize=(10, 4))
    ax_res.plot(dates_test, residuals, label='Model Residuals (Actual - Predicted)', color='#d62728', marker='s', linestyle=':')
    ax_res.axhline(0, color='black', linestyle='-', linewidth=1)
    ax_res.set_xlabel("Observation Month")
    ax_res.set_ylabel("Error Margin (KES)")
    ax_res.set_title("Residual Variance Check")
    ax_res.grid(True, linestyle='--', alpha=0.6)
    ax_res.legend()
    st.pyplot(fig_res)

# --- 8. Raw Data Table Footer ---
with st.expander("📁 View Recent Model-Ready Dataset"):
    st.dataframe(df_model_ready.tail(15))