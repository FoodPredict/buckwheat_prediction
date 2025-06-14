def full_prediction_pipeline(raw_input_data, imputer, scaler_shelf_life, scaler_ffa,
                             train_feature_columns_shelf_life, train_feature_columns_ffa,
                             shelf_life_model, ffa_model,
                             original_input_features, original_categorical_cols, original_numerical_cols,
                             season_rh_map): # Added season_rh_map as a parameter for the RH lookup

    """
    Processes raw input data from a single instance and makes predictions
    for both Shelf Life and Free Fatty Acids using loaded models and preprocessing objects.

    Args:
        raw_input_data (dict or pd.DataFrame): The raw input data for a single prediction.
                                                Expected to be a dictionary or a DataFrame
                                                with keys/columns matching original_input_features.
        imputer: The fitted SimpleImputer object.
        scaler_shelf_life: The fitted StandardScaler object for the Shelf Life model's numerical features.
        scaler_ffa: The fitted StandardScaler object for the FFA model's numerical features.
        train_feature_columns_shelf_life (list): List of feature columns the Shelf Life model was trained on (after preprocessing).
        train_feature_columns_ffa (list): List of feature columns the FFA model was trained on (after preprocessing).
        shelf_life_model: The loaded Shelf Life model.
        ffa_model: The loaded Free Fatty Acids model.
        original_input_features (list): List of the original input feature column names.
        original_categorical_cols (list): List of the original categorical input column names.
        original_numerical_cols (list): List of the original numerical input column names.
        season_rh_map (dict): Dictionary mapping seasons to RH values for 'Not Known' RH lookup.

    Returns:
        dict: A dictionary containing the prediction results ('predicted_shelf_life_days',
              'predicted_free_fatty_acids_percent') or an error dictionary.
    """
    try:
        # 1. Ensure raw_input_data is a single-row DataFrame with expected original columns
        if isinstance(raw_input_data, dict):
            processed_data_dict = {}
            for key, value in raw_input_data.items():
                 # Wrap single values in a list to create a single-row DataFrame
                if not isinstance(value, list):
                    processed_data_dict[key] = [value]
                else:
                     # If it's already a list, ensure it's a list of one for a single instance
                     processed_data_dict[key] = value[:1] if value else [np.nan] # Handle empty list case
            processed_df = pd.DataFrame(processed_data_dict)

        elif isinstance(raw_input_data, pd.DataFrame):
            processed_df = raw_input_data.copy().iloc[:1] # Ensure single row
        else:
            error_msg = "Invalid input data format. Please provide a dictionary or DataFrame."
            print(error_msg)
            return {'error': error_msg}

        # Ensure all expected original input features are present, even if with NaN
        for col in original_input_features:
            if col not in processed_df.columns:
                processed_df[col] = np.nan # Add missing columns with NaN

        # Select only the input features in the original order defined during training
        processed_df = processed_df[original_input_features].copy()

        print(f"DataFrame after initial processing: {processed_df}") # Debugging


        # --- Apply Specific UI Logic for 'Not Known' Fields ---

        # Handle 'RH in percent' if 'Not Known' is provided
        if 'RH in percent' in processed_df.columns:
            # Check the value in the first row (assuming single row input)
            rh_value = processed_df['RH in percent'].iloc[0]
            season_value = processed_df['Season'].iloc[0] # Get season value from the main Season column

            if isinstance(rh_value, str) and rh_value.strip().lower() == 'not known':
                print(f"RH is 'Not Known', using RH based on Season: {season_value}")
                # Look up the RH value based on the season
                if season_value in season_rh_map:
                    processed_df['RH in percent'] = season_rh_map[season_value]
                    print(f"Assigned RH: {processed_df['RH in percent'].iloc[0]}%")
                else:
                    error_msg = f"Error: Season '{season_value}' not recognized for 'Not Known' RH logic."
                    print(error_msg)
                    return {'error': error_msg} # Return error if Season is unknown when RH is 'Not Known'

            else:
                 try:
                     # Try converting the provided RH value to a number if it's not 'Not Known'
                     # This handles cases where the frontend sent a number
                     processed_df['RH in percent'] = pd.to_numeric(processed_df['RH in percent'])
                     print(f"Using provided RH: {processed_df['RH in percent'].iloc[0]}%")
                 except ValueError:
                     error_msg = f"Error: Provided RH value '{rh_value}' is not a valid number or 'Not Known'."
                     print(error_msg)
                     return {'error': error_msg} # Return error for invalid RH value

        # Handle 'Days passed after milling' if 'Not Known' is provided
        if 'Days passed after milling' in processed_df.columns:
             days_value = processed_df['Days passed after milling'].iloc[0]
             if isinstance(days_value, str) and days_value.strip().lower() == 'not known':
                  print("Days passed after milling is 'Not Known', converting to NaN for imputation.")
                  processed_df['Days passed after milling'] = np.nan # Convert 'not known' string to NaN

        print(f"DataFrame after handling 'Not Known': {processed_df}") # Debugging

        # --- Preprocessing Pipeline ---

        # 2. Separate numerical and categorical columns
        # Ensure these lists only contain columns actually present in processed_df
        current_numerical_cols = [col for col in original_numerical_cols if col in processed_df.columns]
        current_categorical_cols = [col for col in original_categorical_cols if col in processed_df.columns]

        print(f"Current Numerical Cols: {current_numerical_cols}") # Debugging
        print(f"Current Categorical Cols: {current_categorical_cols}") # Debugging


        # 3. Impute missing values (handles NaNs converted from 'not known')
        # The imputer should have been fitted on training data containing NaNs
        if imputer and current_numerical_cols:
            try:
                processed_df[current_numerical_cols] = imputer.transform(processed_df[current_numerical_cols])
                print("Imputation applied to numerical columns.") # Debugging
            except Exception as e:
                 error_msg = f"Error during imputation: {e}"
                 print(error_msg)
                 return {'error': error_msg}
        elif current_numerical_cols:
             print("Warning: Imputer not loaded, but numerical columns exist. Missing values may cause issues.") # Debugging


        print(f"DataFrame after imputation: {processed_df}") # Debugging

        # 4. Apply One-Hot Encoding to categorical features
        # This is the CRITICAL part to match training.
        # Ensure the columns generated match the training data's one-hot encoded columns.
        if current_categorical_cols:
            try:
                # Create dummies for the current categorical columns
                processed_df = pd.get_dummies(processed_df, columns=current_categorical_cols, drop_first=False) # Use drop_first=False unless you did during training

                # --- Separate dataframes for Shelf Life and FFA based on *trained* feature sets ---
                # This assumes Shelf Life and FFA models were trained on potentially different subsets
                # of one-hot encoded features or require different processing steps AFTER one-hot encoding.
                # Based on your provided Reindexing code, it seems you were treating them separately.

                processed_df_shelf_life = processed_df.copy()
                processed_df_ffa = processed_df.copy()

                print(f"DataFrame after One-Hot Encoding: {processed_df}") # Debugging


            except Exception as e:
                 error_msg = f"Error during one-hot encoding: {e}"
                 print(error_msg)
                 return {'error': error_msg}
        else:
            processed_df_shelf_life = processed_df.copy()
            processed_df_ffa = processed_df.copy()
            print("No categorical columns to one-hot encode.") # Debugging


        # 5. Reindex and Scale features for Shelf Life model
        # This section needs to be completed if you scaled/reindexed separately for Shelf Life
        # Based on your provided code for FFA reindexing/scaling, a similar process is needed here.

        print(f"DataFrame for Shelf Life BEFORE reindexing/scaling: {processed_df_shelf_life}") # Debugging

        if scaler_shelf_life and train_feature_columns_shelf_life:
            # Ensure columns match training columns exactly before scaling/prediction
            try:
                 # Reindex columns to match the Shelf Life training data columns exactly
                 # Add missing columns (will be filled with 0)
                 for col in train_feature_columns_shelf_life:
                     if col not in processed_df_shelf_life.columns:
                         processed_df_shelf_life[col] = 0

                 # Drop columns not in training features (if any appeared unexpectedly)
                 cols_to_drop_shelf_life = [col for col in processed_df_shelf_life.columns if col not in train_feature_columns_shelf_life]
                 if cols_to_drop_shelf_life:
                     processed_df_shelf_life = processed_df_shelf_life.drop(columns=cols_to_drop_shelf_life)

                 # Ensure the columns are in the correct order
                 processed_df_shelf_life = processed_df_shelf_life[train_feature_columns_shelf_life]
                 print(f"DataFrame for Shelf Life AFTER reindexing: {processed_df_shelf_life}") # Debugging

                 # Scale the numerical features for Shelf Life using the fitted scaler
                 # You need to identify which columns from train_feature_columns_shelf_life are numerical
                 numerical_cols_in_shelf_life_features = [col for col in original_numerical_cols if col in train_feature_columns_shelf_life]
                 if numerical_cols_in_shelf_life_features:
                     processed_df_shelf_life[numerical_cols_in_shelf_life_features] = scaler_shelf_life.transform(processed_df_shelf_life[numerical_cols_in_shelf_life_features])
                     print("Numerical features scaled for Shelf Life model.") # Debugging
                 else:
                     print("No numerical columns to scale for Shelf Life model.") # Debugging

            except Exception as e:
                 error_msg = f"Error preparing Shelf Life features (reindexing/scaling): {e}"
                 print(error_msg)
                 return {'error': error_msg}
        elif not train_feature_columns_shelf_life:
             error_msg = "Shelf Life training feature columns not loaded."
             print(error_msg)
             return {'error': error_msg}
        elif not scaler_shelf_life:
             print("Warning: Shelf Life scaler not loaded. Numerical features will not be scaled.") # Debugging


        # 6. Reindex and Scale features for FFA model
        # This is the section you provided
        print(f"DataFrame for FFA BEFORE reindexing/scaling: {processed_df_ffa}") # Debugging

        if scaler_ffa and train_feature_columns_ffa:
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
                print(f"DataFrame for FFA AFTER reindexing: {processed_df_ffa}") # Debugging

                # Scale the numerical features for FFA using the fitted scaler
                # You need to identify which columns from train_feature_columns_ffa are numerical
                numerical_cols_in_ffa_features = [col for col in original_numerical_cols if col in train_feature_columns_ffa]
                if numerical_cols_in_ffa_features:
                    processed_df_ffa[numerical_cols_in_ffa_features] = scaler_ffa.transform(processed_df_ffa[numerical_cols_in_ffa_features])
                    print("Numerical features scaled for FFA model.") # Debugging
                else:
                    print("No numerical columns to scale for FFA model.") # Debugging


            except Exception as e:
                 error_msg = f"Error preparing FFA features (reindexing/scaling): {e}"
                 print(error_msg)
                 return {'error': error_msg}
        elif not train_feature_columns_ffa:
             error_msg = "FFA training feature columns not loaded."
             print(error_msg)
             return {'error': error_msg}
        elif not scaler_ffa:
             print("Warning: FFA scaler not loaded. Numerical features will not be scaled.") # Debugging

        print(f"Final features for Shelf Life model prediction: {processed_df_shelf_life.columns.tolist()}") # Debugging
        print(f"Final features for FFA model prediction: {processed_df_ffa.columns.tolist()}") # Debugging


        # 7. Make predictions
        if shelf_life_model and ffa_model:
            try:
                predicted_shelf_life = shelf_life_model.predict(processed_df_shelf_life)
                predicted_ffa = ffa_model.predict(processed_df_ffa)

                # Return predictions in a dictionary
                return {
                    'predicted_shelf_life_days': round(float(predicted_shelf_life[0]), 2), # Round to 2 decimal places
                    'predicted_free_fatty_acids_percent': round(float(predicted_ffa[0]), 4) # Round to 4 decimal places
                }

            except Exception as e:
                error_msg = f"Error during prediction: {e}"
                print(error_msg)
                return {'error': error_msg}
        else:
            error_msg = "Prediction models not loaded."
            print(error_msg)
            return {'error': error_msg}

    except Exception as e:
        # Catch any unexpected errors during the pipeline execution
        error_msg = f"An unexpected error occurred in the prediction pipeline: {e}"
        print(error_msg)
        return {'error': error_msg}


# --- Flask Application Setup ---
app = Flask(__name__)

# Basic route for the homepage (optional, if you have an index.html)
@app.route('/')
def index():
    # Serve the index.html file from the 'templates' directory if you have one
    # If your front-end is entirely separate, you might not need this route
    return render_template('index.html') # Assuming you have index.html in templates


# Prediction endpoint
@app.route('/predict', methods=['POST'])
def predict():
    # Ensure models and preprocessing objects were loaded successfully on startup
    global objects_loaded_successfully # Access the global flag
    if not objects_loaded_successfully:
        print("Models and preprocessing objects failed to load on startup.") # Debugging
        return jsonify({'error': 'Models and preprocessing objects failed to load. Cannot make predictions.'}), 500

    try:
        # Get the raw input data from the POST request
        raw_input_data = request.json

        if not raw_input_data:
             print("No input data received in the request.") # Debugging
             return jsonify({'error': 'No input data received'}), 400

        print(f"\nReceived raw input data: {raw_input_data}") # Log received data

        # Call the prediction pipeline
        # Pass all necessary objects and the season_rh_map
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
            season_rh_map # Pass the season_rh_map
        )

        print(f"Result from full_prediction_pipeline: {predictions}") # Debugging the pipeline output


        # Check the result from the pipeline
        if predictions and 'error' not in predictions:
            # Pipeline returned the prediction dictionary
            print("Prediction pipeline succeeded.") # Debugging
            return jsonify(predictions), 200 # Return the dictionary as JSON with 200 status

        elif predictions and 'error' in predictions:
             # Pipeline returned an error dictionary
             print(f"Prediction pipeline returned an error: {predictions['error']}") # Debugging
             # Return the error message with a 400 status code
             return jsonify(predictions), 400 # Bad Request if pipeline returned a specific error

        else:
             # Pipeline returned None or an unexpected falsy value
             print("Prediction pipeline returned None or an unexpected value.") # Debugging
             return jsonify({'error': 'Prediction pipeline failed to return results or returned an invalid value.'}), 500 # Internal Server Error

    except Exception as e:
        # Catch any unhandled errors during the request processing in the route itself
        print(f"An unhandled error occurred during prediction request processing in the route: {e}") # Debugging
        return jsonify({'error': f'An unexpected error occurred: {e}'}), 500 # Internal Server Error

# --- Run the Flask app ---
# This part is for local development only.
# Render uses a production WSGI server (like Gunicorn) defined by default
# or specified in a Procfile if needed.
if __name__ == '__main__':
    # Load objects before running the app locally
    if objects_loaded_successfully:
       # Debug mode is useful for local testing, disable for production
       app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
    else:
        print("Application will not start locally due to errors loading necessary objects.") # Debugging
