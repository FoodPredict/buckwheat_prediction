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

import pandas as pd
import joblib
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from flask import Flask, request, render_template # Assuming Flask

app = Flask(__name__)

# --- Load the saved model objects ---
try:
    loaded_shelf_life_model = joblib.load('shelf_life_model.joblib')
    loaded_ffa_model = joblib.load('ffa_model.joblib')
    loaded_scaler_shelf_life = joblib.load('scaler_shelf_life.joblib')
    loaded_scaler_ffa = joblib.load('scaler_ffa.joblib')
    loaded_imputer = joblib.load('imputer.joblib')
    loaded_train_feature_columns_shelf_life = joblib.load('train_feature_columns_shelf_life.joblib')
    loaded_train_feature_columns_ffa = joblib.load('train_feature_columns_ffa.joblib')
    loaded_original_features_info = joblib.load('original_features_info.joblib')
    loaded_input_features = loaded_original_features_info['input_features']
    loaded_categorical_input_cols = loaded_original_features_info['categorical_input_cols']
    loaded_original_numerical_cols = loaded_original_features_info['original_numerical_cols']

    print("All model objects loaded successfully.")

except FileNotFoundError as e:
    print(f"Error loading model objects: {e}. Ensure the .joblib files are in the same directory as app.py")
    # You might want to handle this more robustly in a real application
    # For example, raise an error or exit if models can't be loaded.
    loaded_shelf_life_model = None # Indicate that loading failed
    # ... set other loaded objects to None

# --- Define your preprocessing function (similar to the one in your notebook) ---
def preprocess_input_data(raw_input_data, imputer, scaler_shelf_life, scaler_ffa,
                         train_feature_columns_shelf_life, train_feature_columns_ffa,
                         original_input_features, original_categorical_cols, original_numerical_cols,
                         model_type): # Added model_type to use correct scaler and train_feature_columns
    """
    Preprocesses raw input data for prediction.
    """
    # ... (paste the logic from your preprocess_new_data_shelf_life function)
    # IMPORTANT: Modify this function to use the correct scaler and train_feature_columns
    # based on the 'model_type' ('shelf_life' or 'ffa').

    processed_df = None # Initialize processed_df

    if isinstance(raw_input_data, dict):
        # Convert dictionary to DataFrame
        processed_data_dict = {}
        for key, value in raw_input_data.items():
            if not isinstance(value, list):
                processed_data_dict[key] = [value]
            else:
                 processed_data_dict[key] = value
        processed_df = pd.DataFrame(processed_data_dict)

    elif isinstance(raw_input_data, pd.DataFrame):
        processed_df = raw_input_data.copy()
    else:
        print("Invalid input data format.")
        return None


    # Ensure required features are present
    missing_input_cols = [col for col in original_input_features if col not in processed_df.columns]
    if missing_input_cols:
         print(f"Error: Input data is missing required original features: {missing_input_cols}")
         return None

    processed_df = processed_df[original_input_features].copy() # Select required columns

    # Impute numerical features
    cols_to_impute = [col for col in original_numerical_cols if col in processed_df.columns]
    if cols_to_impute:
         processed_df[cols_to_impute] = imputer.transform(processed_df[cols_to_impute])

    # One-hot encode categorical features
    if original_categorical_cols:
        processed_df = pd.get_dummies(processed_df, columns=original_categorical_cols, drop_first=False)

    # Reindex and scale based on model type
    if model_type == 'shelf_life':
        target_cols = train_feature_columns_shelf_life
        scaler_to_use = scaler_shelf_life
    elif model_type == 'ffa':
        target_cols = train_feature_columns_ffa
        scaler_to_use = scaler_ffa
    else:
        print("Invalid model_type provided to preprocess_input_data.")
        return None


    # Reindex columns to match training data
    for col in target_cols:
        if col not in processed_df.columns:
            processed_df[col] = 0

    cols_to_drop = [col for col in processed_df.columns if col not in target_cols]
    if cols_to_drop:
        processed_df = processed_df.drop(columns=cols_to_drop)

    processed_df = processed_df[target_cols] # Ensure correct order

    # Scale numerical features
    processed_numerical_cols_for_scaling = [col for col in original_numerical_cols if col in processed_df.columns]
    if processed_numerical_cols_for_scaling:
        processed_df[processed_numerical_cols_for_scaling] = scaler_to_use.transform(processed_df[processed_numerical_cols_for_scaling])


    return processed_df


# --- Flask Route to handle predictions ---
@app.route('/', methods=['GET', 'POST'])
def index():
    predicted_shelf_life = "--"
    predicted_ffa = "--"
    error_message = None

    if request.method == 'POST':
        # Get data from the form
        storage_temp = request.form.get('storage_temp')
        rh = request.form.get('rh')
        days_passed = request.form.get('days_passed')
        season = request.form.get('season')
        moisture = request.form.get('moisture')
        packing = request.form.get('packing')

        # Create a dictionary with the raw input data
        raw_input_data = {
            'Storage Temperature in C': float(storage_temp), # Convert to appropriate type
            'RH in percent': float(rh),
            'Days passed after milling': int(days_passed),
            'Season': season,
            'Moisture': moisture,
            'Packing': packing
        }

        try:
            # --- Preprocess for Shelf Life Model ---
            processed_data_shelf_life = preprocess_input_data(
                raw_input_data,
                imputer=loaded_imputer,
                scaler_shelf_life=loaded_scaler_shelf_life,
                scaler_ffa=loaded_scaler_ffa, # Pass both scalers
                train_feature_columns_shelf_life=loaded_train_feature_columns_shelf_life,
                train_feature_columns_ffa=loaded_train_feature_columns_ffa, # Pass both column lists
                original_input_features=loaded_input_features,
                original_categorical_cols=loaded_categorical_input_cols,
                original_numerical_cols=loaded_original_numerical_cols,
                model_type='shelf_life' # Specify model type
            )

            if processed_data_shelf_life is not None and loaded_shelf_life_model is not None:
                predicted_shelf_life = loaded_shelf_life_model.predict(processed_data_shelf_life)[0]
                predicted_shelf_life = f"{predicted_shelf_life:.2f}" # Format output

            # --- Preprocess for FFA Model ---
            processed_data_ffa = preprocess_input_data(
                 raw_input_data,
                imputer=loaded_imputer,
                scaler_shelf_life=loaded_scaler_shelf_life,
                scaler_ffa=loaded_scaler_ffa,
                train_feature_columns_shelf_life=loaded_train_feature_columns_shelf_life,
                train_feature_columns_ffa=loaded_train_feature_columns_ffa,
                original_input_features=loaded_input_features,
                original_categorical_cols=loaded_categorical_input_cols,
                original_numerical_cols=loaded_original_numerical_cols,
                model_type='ffa' # Specify model type
            )

            if processed_data_ffa is not None and loaded_ffa_model is not None:
                predicted_ffa = loaded_ffa_model.predict(processed_data_ffa)[0]
                predicted_ffa = f"{predicted_ffa:.4f}" # Format output

        except Exception as e:
            error_message = f"An unexpected error occurred during prediction: {e}"
            print(error_message) # Log the error

    # Render the HTML template, passing the prediction results and error message
    return render_template('index.html',
                           shelf_life=predicted_shelf_life,
                           ffa=predicted_ffa,
                           error=error_message)

if __name__ == '__main__':
    # When deploying with gunicorn (like on Render), this block is often
    # not the primary entry point, as gunicorn handles starting the app.
    # However, it's useful for local testing.
    # Ensure the host and port are set appropriately for the deployment environment
    # Render typically expects the app to bind to 0.0.0.0 on a specific port (often 10000).
    # You usually don't need app.run() if using gunicorn in production.
    # For local testing: app.run(debug=True)
    pass # Leave this empty if gunicorn is your entry point on Render





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
