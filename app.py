from flask import Flask, render_template, request, jsonify
import joblib
import pandas as pd
import numpy as np
import os

# --- Load your models and preprocessing objects here ---
# Example:
# imputer = joblib.load('imputer.joblib')
# scaler_shelf_life = joblib.load('scaler_shelf_life.joblib')
# scaler_ffa = joblib.load('scaler_ffa.joblib')
# shelf_life_model = joblib.load('shelf_life_model.joblib')
# ffa_model = joblib.load('ffa_model.joblib')
# train_feature_columns_shelf_life = [...]
# train_feature_columns_ffa = [...]
# original_input_features = [...]
# original_categorical_cols = [...]
# original_numerical_cols = [...]
# season_rh_map = {...}

# Set this flag after loading all objects successfully
objects_loaded_successfully = True  # Set to False if any loading fails

def full_prediction_pipeline(raw_input_data, imputer, scaler_shelf_life, scaler_ffa,
                             train_feature_columns_shelf_life, train_feature_columns_ffa,
                             shelf_life_model, ffa_model,
                             original_input_features, original_categorical_cols, original_numerical_cols,
                             season_rh_map):
    """
    Processes raw input data from a single instance and makes predictions
    for both Shelf Life and Free Fatty Acids using loaded models and preprocessing objects.
    """
    try:
        if isinstance(raw_input_data, dict):
            processed_data_dict = {}
            for key, value in raw_input_data.items():
                if not isinstance(value, list):
                    processed_data_dict[key] = [value]
                else:
                    processed_data_dict[key] = value[:1] if value else [np.nan]
            processed_df = pd.DataFrame(processed_data_dict)
        elif isinstance(raw_input_data, pd.DataFrame):
            processed_df = raw_input_data.copy().iloc[:1]
        else:
            return {'error': "Invalid input data format. Please provide a dictionary or DataFrame."}

        for col in original_input_features:
            if col not in processed_df.columns:
                processed_df[col] = np.nan

        processed_df = processed_df[original_input_features].copy()

        # Handle 'RH in percent'
        if 'RH in percent' in processed_df.columns:
            rh_value = processed_df['RH in percent'].iloc[0]
            season_value = processed_df['Season'].iloc[0]
            if isinstance(rh_value, str) and rh_value.strip().lower() == 'not known':
                if season_value in season_rh_map:
                    processed_df['RH in percent'] = season_rh_map[season_value]
                else:
                    return {'error': f"Error: Season '{season_value}' not recognized for 'Not Known' RH logic."}
            else:
                try:
                    processed_df['RH in percent'] = pd.to_numeric(processed_df['RH in percent'])
                except ValueError:
                    return {'error': f"Error: Provided RH value '{rh_value}' is not a valid number or 'Not Known'."}

        # Handle 'Days passed after milling'
        if 'Days passed after milling' in processed_df.columns:
            days_value = processed_df['Days passed after milling'].iloc[0]
            if isinstance(days_value, str) and days_value.strip().lower() == 'not known':
                processed_df['Days passed after milling'] = np.nan

        current_numerical_cols = [col for col in original_numerical_cols if col in processed_df.columns]
        current_categorical_cols = [col for col in original_categorical_cols if col in processed_df.columns]

        if imputer and current_numerical_cols:
            try:
                processed_df[current_numerical_cols] = imputer.transform(processed_df[current_numerical_cols])
            except Exception as e:
                return {'error': f"Error during imputation: {e}"}

        if current_categorical_cols:
            try:
                processed_df = pd.get_dummies(processed_df, columns=current_categorical_cols, drop_first=False)
                processed_df_shelf_life = processed_df.copy()
                processed_df_ffa = processed_df.copy()
            except Exception as e:
                return {'error': f"Error during one-hot encoding: {e}"}
        else:
            processed_df_shelf_life = processed_df.copy()
            processed_df_ffa = processed_df.copy()

        # Shelf Life
        if scaler_shelf_life and train_feature_columns_shelf_life:
            try:
                for col in train_feature_columns_shelf_life:
                    if col not in processed_df_shelf_life.columns:
                        processed_df_shelf_life[col] = 0
                cols_to_drop = [col for col in processed_df_shelf_life.columns if col not in train_feature_columns_shelf_life]
                if cols_to_drop:
                    processed_df_shelf_life = processed_df_shelf_life.drop(columns=cols_to_drop)
                processed_df_shelf_life = processed_df_shelf_life[train_feature_columns_shelf_life]
                numerical_cols_in_shelf_life_features = [col for col in original_numerical_cols if col in train_feature_columns_shelf_life]
                if numerical_cols_in_shelf_life_features:
                    processed_df_shelf_life[numerical_cols_in_shelf_life_features] = scaler_shelf_life.transform(
                        processed_df_shelf_life[numerical_cols_in_shelf_life_features]
                    )
            except Exception as e:
                return {'error': f"Error preparing Shelf Life features (reindexing/scaling): {e}"}
        elif not train_feature_columns_shelf_life:
            return {'error': "Shelf Life training feature columns not loaded."}

        # FFA
        if scaler_ffa and train_feature_columns_ffa:
            try:
                for col in train_feature_columns_ffa:
                    if col not in processed_df_ffa.columns:
                        processed_df_ffa[col] = 0
                cols_to_drop = [col for col in processed_df_ffa.columns if col not in train_feature_columns_ffa]
                if cols_to_drop:
                    processed_df_ffa = processed_df_ffa.drop(columns=cols_to_drop)
                processed_df_ffa = processed_df_ffa[train_feature_columns_ffa]
                numerical_cols_in_ffa_features = [col for col in original_numerical_cols if col in train_feature_columns_ffa]
                if numerical_cols_in_ffa_features:
                    processed_df_ffa[numerical_cols_in_ffa_features] = scaler_ffa.transform(
                        processed_df_ffa[numerical_cols_in_ffa_features]
                    )
            except Exception as e:
                return {'error': f"Error preparing FFA features (reindexing/scaling): {e}"}
        elif not train_feature_columns_ffa:
            return {'error': "FFA training feature columns not loaded."}

        if shelf_life_model and ffa_model:
            try:
                predicted_shelf_life = shelf_life_model.predict(processed_df_shelf_life)
                predicted_ffa = ffa_model.predict(processed_df_ffa)
                return {
                    'predicted_shelf_life_days': round(float(predicted_shelf_life[0]), 2),
                    'predicted_free_fatty_acids_percent': round(float(predicted_ffa[0]), 4)
                }
            except Exception as e:
                return {'error': f"Error during prediction: {e}"}
        else:
            return {'error': "Prediction models not loaded."}

    except Exception as e:
        return {'error': f"An unexpected error occurred in the prediction pipeline: {e}"}

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/predict', methods=['POST'])
def predict():
    global objects_loaded_successfully
    if not objects_loaded_successfully:
        return jsonify({'error': 'Models and preprocessing objects failed to load. Cannot make predictions.'}), 500
    try:
        raw_input_data = request.json
        if not raw_input_data:
            return jsonify({'error': 'No input data received'}), 400
        predictions = full_prediction_pipeline(
            raw_input_data,
            imputer,
            scaler_shelf_life,
            scaler_ffa,
            train_feature_columns_shelf_life,
            train_feature_columns_ffa,
            shelf_life_model,
            ffa_model,
            original_input_features,
            original_categorical_cols,
            original_numerical_cols,
            season_rh_map
        )
        if predictions and 'error' not in predictions:
            return jsonify(predictions), 200
        elif predictions and 'error' in predictions:
            return jsonify(predictions), 400
        else:
            return jsonify({'error': 'Prediction pipeline failed to return results or returned an invalid value.'}), 500
    except Exception as e:
        return jsonify({'error': f'An unexpected error occurred: {e}'}), 500

if __name__ == '__main__':
    if objects_loaded_successfully:
        app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
    else:
        print("Application will not start locally due to errors loading necessary objects.")
