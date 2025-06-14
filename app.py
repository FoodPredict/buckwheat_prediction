zimport pandas as pd
import numpy as np
import joblib
import os
from flask import Flask, request, jsonify, render_template # Import Flask components
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler

# --- Configuration ---
# Define the directory where your joblib files are stored
MODELS_DIR = 'models/'

# Define filenames for loading (must match saving filenames)
shelf_life_model_filename = os.path.join(MODELS_DIR, 'shelf_life_model.joblib')
ffa_model_filename = os.path.join(MODELS_DIR, 'ffa_model.joblib')
scaler_shelf_life_filename = os.path.join(MODELS_DIR, 'scaler_shelf_life.joblib')
scaler_ffa_filename = os.path.join(MODELS_DIR, 'scaler_ffa.joblib')
imputer_filename = os.path.join(MODELS_DIR, 'imputer.joblib')
train_feature_columns_shelf_life_filename = os.path.join(MODELS_DIR, 'train_feature_columns_shelf_life.joblib')
train_feature_columns_ffa_filename = os.path.join(MODELS_DIR, 'train_feature_columns_ffa.joblib')
original_features_info_filename = os.path.join(MODELS_DIR, 'original_features_info.joblib')

# --- Load Models and Preprocessing Objects ---
# These variables will hold the loaded objects
shelf_life_model = None
ffa_model = None
scaler_shelf_life = None
scaler_ffa = None
imputer = None
train_feature_columns_shelf_life = None
train_feature_columns_ffa = None
original_input_features = None
original_categorical_cols = None
original_numerical_cols = None

def load_all_objects():
    """Loads all saved models and preprocessing objects."""
    global shelf_life_model, ffa_model, scaler_shelf_life, scaler_ffa, imputer, \
           train_feature_columns_shelf_life, train_feature_columns_ffa, \
           original_input_features, original_categorical_cols, original_numerical_cols

    try:
        shelf_life_model = joblib.load(shelf_life_model_filename)
        ffa_model = joblib.load(ffa_model_filename)
        scaler_shelf_life = joblib.load(scaler_shelf_life_filename)
        scaler_ffa = joblib.load(scaler_ffa_filename)
        imputer = joblib.load(imputer_filename)
        train_feature_columns_shelf_life = joblib.load(train_feature_columns_shelf_life_filename)
        train_feature_columns_ffa = joblib.load(train_feature_columns_ffa_filename)

        original_features_info = joblib.load(original_features_info_filename)
        original_input_features = original_features_info['input_features']
        original_categorical_cols = original_features_info['categorical_input_cols']
        original_numerical_cols = original_features_info['original_numerical_cols']

        print("All required objects loaded successfully.")
        return True # Indicate success
    except FileNotFoundError as e:
        print(f"Error loading objects: File not found - {e}.")
        print(f"Please ensure the '{MODELS_DIR}' directory exists and contains all .joblib files.")
        print("The saving notebook cell must be run before running this application.")
        return False # Indicate failure
    except Exception as e:
        print(f"Error loading objects: {e}")
        return False # Indicate failure

# Load objects when the application starts
objects_loaded_successfully = load_all_objects()

# --- Prediction Pipeline Function (Copied from notebook) ---
# This function is essential, copy the complete definition from Cell 15
def full_prediction_pipeline(raw_input_data, imputer, scaler_shelf_life, scaler_ffa,
                             train_feature_columns_shelf_life, train_feature_columns_ffa,
                             shelf_life_model, ffa_model,
                             original_input_features, original_categorical_cols, original_numerical_cols):
    """
    Processes raw input data and makes predictions for both Shelf Life and Free Fatty Acids.
    ... (Copy the full docstring and function body from Cell 15 here) ...
    """
    # Ensure raw_input_data is a DataFrame
    if isinstance(raw_input_data, dict):
        processed_data_dict = {}
        for key, value in raw_input_data.items():
             # Wrap single values in a list to create a single-row DataFrame
            if not isinstance(value, list):
                processed_data_dict[key] = [value]
            else:
                 processed_data_dict[key] = value # Keep list if it's already a list
        processed_df = pd.DataFrame(processed_data_dict)

    elif isinstance(raw_input_data, pd.DataFrame):
        processed_df = raw_input_data.copy()
    else:
        print("Invalid input data format. Please provide a dictionary or DataFrame.")
        return None

    # 1. Use only the relevant original input features and ensure they are present
    required_for_processing = [col for col in original_input_features if col != 'RH in percent' and col != 'Days passed after milling'] + \
                              ['RH in percent', 'Days passed after milling', 'Season'] # Ensure RH, Days, Season are checked

    missing_input_cols = [col for col in required_for_processing if col not in processed_df.columns]
    if missing_input_cols:
         print(f"Error: Input data is missing required original features: {missing_input_cols}")
         return None

    # Select only the input features in the original order defined during training
    processed_df = processed_df[original_input_features].copy()

    # --- Apply Specific UI Logic for 'Not Known' Fields ---

    # Define the RH values for each season based on your requirement
    season_rh_map = {
        'Summer': 50,
        'Spring': 55,
        'Autumn': 60,
        'Winter': 65,
        'Rainy': 90
    }

    # Handle 'RH in percent' if 'Not Known' is provided
    if 'RH in percent' in processed_df.columns:
        # Check the value in the first row (assuming single row input)
        rh_value = processed_df['RH in percent'].iloc[0]
        season_value = processed_df['Season'].iloc[0] # Get season value

        if isinstance(rh_value, str) and rh_value.strip().lower() == 'not known':
            # print(f"RH is 'Not Known', using RH based on Season: {season_value}") # Keep prints minimal in app
            # Look up the RH value based on the season
            if season_value in season_rh_map:
                processed_df['RH in percent'] = season_rh_map[season_value]
                # print(f"Assigned RH: {processed_df['RH in percent'].iloc[0]}%") # Keep prints minimal in app
            else:
                print(f"Warning: Season '{season_value}' not recognized for 'Not Known' RH logic.")
                # Optionally, you could raise an error here if an unknown season is provided when RH is 'Not Known'
                # For now, we'll leave it as 'Not Known' and let imputation potentially handle it if the imputer was trained on NaNs
                # A more robust solution would raise an explicit error.
                pass # Keep 'Not Known' string or convert to NaN if imputer handles strings

        else:
             try:
                 # Try converting the provided RH value to a number if it's not 'Not Known'
                 processed_df['RH in percent'] = pd.to_numeric(processed_df['RH in percent'])
                 # print(f"Using provided RH: {processed_df['RH in percent'].iloc[0]}%") # Keep prints minimal in app
             except ValueError:
                 print(f"Error: Provided RH value '{rh_value}' is not a valid number or 'Not Known'.")
                 return {'error': f"Invalid RH value: '{rh_value}'"} # Return an error dictionary


    # Handle 'Days passed after milling' if 'Not Known' is provided
    if 'Days passed after milling' in processed_df.columns:
         days_value = processed_df['Days passed after milling'].iloc[0]
         if isinstance(days_value, str) and days_value.strip().lower() == 'not known':
             # print("'Days passed after milling' is 'Not Known', treating as missing value (NaN).") # Keep prints minimal in app
             processed_df['Days passed after milling'] = np.nan # Convert 'Not Known' string to NaN
         else:
              try:
                  # Try converting to numeric if it's not 'Not Known'
                  processed_df['Days passed after milling'] = pd.to_numeric(processed_df['Days passed after milling'])
              except ValueError:
                 print(f"Error: Provided 'Days passed after milling' value '{days_value}' is not a valid number or 'Not Known'.")
                 return {'error': f"Invalid 'Days passed after milling' value: '{days_value}'"} # Return an error dictionary


    # 2. Handle missing values in numerical input features using the fitted imputer
    # This will handle any remaining NaNs in numerical columns, including 'Days passed after milling'
    # if it was 'Not Known' and converted to NaN. It will also handle RH if it somehow
    # ended up as NaN (though our logic above tries to prevent this).
    cols_to_impute = [col for col in original_numerical_cols if col in processed_df.columns]
    if cols_to_impute:
        # Use the fitted imputer to transform the numerical columns
        # Note: If RH was left as a string 'Not Known' due to an unknown season, transform will fail
        # Ensure pd.to_numeric handles errors or the 'Not Known' string is correctly converted to NaN
        # before this step. The logic above does convert 'Not Known' to NaN.
        try:
            processed_df[cols_to_impute] = imputer.transform(processed_df[cols_to_impute])
            # print("Missing values in numerical features imputed.") # Keep prints minimal
        except Exception as e:
             print(f"Error during imputation: {e}")
             return {'error': f"Error during imputation: {e}"}

    # 3. Perform one-hot encoding on categorical input features
    if original_categorical_cols:
        try:
            # Using get_dummies and then reindexing to handle potential missing categories
            # Ensure the original_categorical_cols actually exist in the processed_df at this stage
            # (They should if the initial check passed)
            cols_to_encode_present = [col for col in original_categorical_cols if col in processed_df.columns]
            processed_df = pd.get_dummies(processed_df, columns=cols_to_encode_present, drop_first=False)
            # print("One-hot encoding complete.") # Keep prints minimal
        except Exception as e:
            print(f"Error during one-hot encoding: {e}")
            return {'error': f"Error during one-hot encoding: {e}"}

    # --- Prepare data for Shelf Life Model prediction ---
    processed_df_shelf_life = processed_df.copy()

    # Reindex columns to match the Shelf Life training data columns exactly
    try:
        # Add missing columns (will be filled with 0, appropriate for one-hot encoded features)
        for col in train_feature_columns_shelf_life:
            if col not in processed_df_shelf_life.columns:
                processed_df_shelf_life[col] = 0

        # Drop columns not in training features
        cols_to_drop_shelf_life = [col for col in processed_df_shelf_life.columns if col not in train_feature_columns_shelf_life]
        if cols_to_drop_shelf_life:
            processed_df_shelf_life = processed_df_shelf_life.drop(columns=cols_to_drop_shelf_life)

        # Ensure the columns are in the correct order
        processed_df_shelf_life = processed_df_shelf_life[train_feature_columns_shelf_life]
        # print("Shelf Life features reordered.") # Keep prints minimal
    except Exception as e:
        print(f"Error reindexing Shelf Life features: {e}")
        return {'error': f"Error reindexing Shelf Life features: {e}"}


    # 4. Scale the numerical features for Shelf Life using the fitted scaler
    processed_numerical_cols_for_scaling_shelf_life = [col for col in original_numerical_cols if col in processed_df_shelf_life.columns]
    if processed_numerical_cols_for_scaling_shelf_life:
        try:
             processed_df_shelf_life[processed_numerical_cols_for_scaling_shelf_life] = scaler_shelf_life.transform(processed_df_shelf_life[processed_numerical_cols_for_scaling_shelf_life])
             # print("Numerical features scaled for Shelf Life model.") # Keep prints minimal
        except Exception as e:
             print(f"Error scaling Shelf Life features: {e}")
             return {'error': f"Error scaling Shelf Life features: {e}"}


    # --- Prepare data for FFA Model prediction ---
    processed_df_ffa = processed_df.copy()

    # Reindex columns to match the FFA training data columns exactly
    try:
        # Add missing columns (will be filled with 0)
        for col in train_feature_columns_ffa:
            if col not in processed_df_ffa.columns:
                processed_df_ffa[col] = 0

        # Drop columns not in training features
        cols_to_drop_ffa = [col for col in processed_df_ffa.columns if col not in train_feature_columns_ffa]
        if cols_to_drop_ffa:
            processed_df_ffa = processed_df_ffa.drop(columns=cols_to_drop_ffa)

        # Ensure the columns are in the correct order
        processed_df_ffa = processed_df_ffa[train_feature_columns_ffa]
        # print("FFA features reordered.") # Keep prints minimal
    except Exception as e:
         print(f"Error reindexing FFA features: {e}")
         return {'error': f"Error reindexing FFA features: {e}"}


    # 5. Scale the numerical features for FFA using the fitted scaler
    processed_numerical_cols_for_scaling_ffa = [col for col in original_numerical_cols if col in processed_df_ffa.columns]
    if processed_numerical_cols_for_scaling_ffa:
        try:
            processed_df_ffa[processed_numerical_cols_for_scaling_ffa] = scaler_ffa.transform(processed_df_ffa[processed_numerical_cols_for_scaling_ffa])
            # print("Numerical features scaled for FFA model.") # Keep prints minimal
        except Exception as e:
             print(f"Error scaling FFA features: {e}")
             return {'error': f"Error scaling FFA features: {e}"}


    # 6. Make predictions
    try:
        predicted_shelf_life = shelf_life_model.predict(processed_df_shelf_life)
        predicted_ffa = ffa_model.predict(processed_df_ffa)

        # Return predictions in a dictionary
        return {
            'predicted_shelf_life_days': round(float(predicted_shelf_life[0]), 2), # Round to 2 decimal places
            'predicted_free_fatty_acids_percent': round(float(predicted_ffa[0]), 4) # Round to 4 decimal places
        }

    except Exception as e:
        print(f"Error during prediction: {e}")
        return {'error': f"Error during prediction: {e}"}


# --- Flask Application Setup ---
app = Flask(__name__)

# Basic route for the homepage
@app.route('/')
def index():
    # Serve the index.html file from the 'templates' directory
    return render_template('index.html')

@app.route('/predict', methods=['POST'])
def predict():
    data = request.get_json(force=True)

    # ... (Your code to process incoming data, handle RH lookup, etc.) ...
    # Ensure 'data' dictionary contains the processed numerical and string values
    # needed to create the DataFrame for prediction.

    # Example of handling incoming string values for Moisture and Packing
    # if they need mapping to trained categories before one-hot encoding.
    # (You would need to implement the mapping logic here if necessary)
    # Example:
    # packing_mapping = {'Open to air': 'BOPP bag', ...}
    # if data.get('Packing') in packing_mapping:
    #     data['Packing'] = packing_mapping[data['Packing']]

    # Create DataFrame for prediction - ensure column names and data types match training
    # You might need to handle 'not_known' for Days passed after milling here.
    input_df = pd.DataFrame([data])

    # Perform one-hot encoding - ensure this matches how you trained the model
    # The column names generated here MUST match the columns in original_columns.pkl
    input_df = pd.get_dummies(input_df, columns=['Season', 'Packing']) # Add other categorical columns if necessary

    # Reindex input_df to match the training columns, filling missing with 0
    # This is CRUCIAL to ensure the model receives inputs in the correct order and number
    with open('original_columns.pkl', 'rb') as f:
         trained_columns = pickle.load(f)

    input_df = input_df.reindex(columns=trained_columns, fill_value=0)


    # Make predictions
    shelf_life_prediction = shelf_life_model.predict(input_df)[0] # Get the single prediction value
    ffa_prediction = ffa_model.predict(input_df)[0]         # Get the single prediction value

    # *** Construct the correct response dictionary ***
    response_data = {
        'shelf_life_days': float(shelf_life_prediction), # Ensure they are float/number types
        'predicted_free_fatty_acids_percent': float(ffa_prediction)
    }
    # *** End of constructing response dictionary ***

    return jsonify(response_data) # Return the dictionary as JSON

# Prediction endpoint
@app.route('/predict', methods=['POST'])
def predict():
    if not objects_loaded_successfully:
        return jsonify({'error': 'Models and preprocessing objects failed to load. Cannot make predictions.'}), 500

    try:
        # Get the raw input data from the POST request
        # Assuming the input data is sent as JSON
        raw_input_data = request.json

        if not raw_input_data:
             return jsonify({'error': 'No input data received'}), 400

        print(f"\nReceived input data: {raw_input_data}") # Log received data


        # Call the prediction pipeline
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
            original_numerical_cols
        )

        if predictions and 'error' not in predictions:
            # Return the predictions as JSON
            return jsonify(predictions), 200
        elif predictions and 'error' in predictions:
             # Return the error from the pipeline
             return jsonify(predictions), 400 # Bad Request if pipeline returned a specific error
        else:
             # Generic error if pipeline returned None unexpectedly
             return jsonify({'error': 'Prediction pipeline failed to return results.'}), 500


    except Exception as e:
        # Catch any errors during the request processing
        print(f"Error processing prediction request: {e}")
        return jsonify({'error': 'An error occurred during prediction.'}), 500

# --- Run the Flask app ---
# This part is for local development only.
# Render uses a production WSGI server (like Gunicorn) defined by default
# or specified in a Procfile if needed.
# if __name__ == '__main__':
#     # Debug mode is useful for local testing, disable for production
#     app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
