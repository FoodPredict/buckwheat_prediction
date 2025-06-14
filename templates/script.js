// The toggleRhInputMethod function is no longer needed with the simplified RH input.

// Function to clear the form
function clearForm() {
    const form = document.getElementById('prediction-form');
    form.reset(); // Resets all form elements to their initial state

    // Clear prediction results and reset the results area
    document.getElementById('prediction_results').innerHTML = '<h3>Prediction Results:</h3><p id="shelf_life_prediction"></p><p id="ffa_prediction"></p>';
    document.getElementById('prediction_results').style.color = 'black'; // Reset text color

     // Reset specific selects to their default option
    document.getElementById('rh_embed').value = ''; // Reset the new RH dropdown
    document.getElementById('days_passed_embed').value = '';
    document.getElementById('season_embed').value = '';
    document.getElementById('moisture_embed').value = '';
    document.getElementById('packing_embed').value = '';

    console.log('Form cleared.');
}


document.getElementById('prediction-form').addEventListener('submit', function(event) {
    event.preventDefault();
    console.log('Form submitted.');

    // Collect input data from the form
    const temperature = document.getElementById('temp_embed').value;
    const rhValue = document.getElementById('rh_embed').value; // Get value from the single RH dropdown


    // Basic validation
    if (!temperature || temperature === '' || rhValue === '' || document.getElementById('days_passed_embed').value === '' || document.getElementById('season_embed').value === '' || document.getElementById('moisture_embed').value === '' || document.getElementById('packing_embed').value === '') {
        alert('Please fill in all required fields.');
        console.log('Validation failed: Required fields missing.');
        return;
    }

    const daysPassedValue = document.getElementById('days_passed_embed').value;
    const mainSeasonValue = document.getElementById('season_embed').value;
    const moistureValue = document.getElementById('moisture_embed').value;
    const packingValue = document.getElementById('packing_embed').value;


    // Prepare data for the API in the format your Flask app expects
    // Handle the 'not_known' RH value
    let rhValueToSend;
    if (rhValue === 'not_known') {
        rhValueToSend = 'not Known'; // Send the string 'not Known' to Flask
    } else {
        rhValueToSend = parseFloat(rhValue); // Send the numerical value as a number
    }


    const data = {
        "Storage Temperature in C": parseFloat(temperature),
        "RH in percent": rhValueToSend, // Use the value from the simplified RH dropdown
        "Days passed after milling": daysPassedValue, // Send the selected value (string 'not_known' or number as string)
        "Season": mainSeasonValue, // Send the main Season value
        "Moisture": moistureValue, // Send the selected string value
        "Packing": packingValue // Send the selected string value
    };

    // If RH is 'not Known', the Flask app will need to use the main Season for the lookup.
    // We don't need a separate 'Season for RH Lookup' field in the data object anymore
    // because the Flask app can use the 'Season' field that's already required for the model.


    console.log('Data being sent to Flask:', data);


    // Define the URL of your deployed Flask application on Render
    const renderUrl = 'https://buckwheat-prediction.onrender.com/predict'; // Your Render URL + endpoint

    // Clear previous results and display loading indicator
     document.getElementById('prediction_results').innerHTML = '<h3>Prediction Results:</h3><p id="shelf_life_prediction">Predicting...</p><p id="ffa_prediction"></p>';
     document.getElementById('prediction_results').style.color = 'black';


    // Send POST request to your Flask app
    fetch(renderUrl, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(data)
    })
    .then(response => {
        console.log('Received raw response:', response);
        if (!response.ok) {
             return response.json().then(error => {
                 console.error('Error response body (parsed):', error);
                 const errorMessage = error.message || (error.error ? error.error : response.statusText);
                 throw new Error(`HTTP error! status: ${response.status}, message: ${errorMessage}`);
             }).catch(() => {
                 console.error('Error response body (non-JSON):', response.statusText);
                 throw new Error(`HTTP error! status: ${response.status}, message: ${response.statusText}`);
             });
        }
        return response.json();
    })
    .then(result => {
        console.log('Parsed JSON result:', result);

        // Check if the result object has the expected properties and they are numbers
        if (result && typeof result.shelf_life_days === 'number' && typeof result.predicted_free_fatty_acids_percent === 'number') {
             document.getElementById('shelf_life_prediction').innerText = `Predicted Shelf Life: ${result.shelf_life_days.toFixed(2)} days`;
             document.getElementById('ffa_prediction').innerText = `Predicted Free Fatty Acids: ${result.predicted_free_fatty_acids_percent.toFixed(2)} %`;
             document.getElementById('prediction_results').style.color = 'green';
             document.getElementById('prediction_results').innerHTML = `<h3>Prediction Results:</h3><p id="shelf_life_prediction">${document.getElementById('shelf_life_prediction').innerText}</p><p id="ffa_prediction">${document.getElementById('ffa_prediction').innerText}</p>`;

        } else {
            console.error('Unexpected response format or data types:', result);
            document.getElementById('prediction_results').innerHTML = `<h3 style="color: red;">Prediction Error:</h3><p style="color: red;">Unexpected prediction data received from server. Check console for details.</p>`;
        }

    })
    .catch(error => {
        console.error('Error during prediction (fetch or processing):', error);
        document.getElementById('prediction_results').innerHTML = `<h3 style="color: red;">Prediction Error:</h3><p style="color: red;">${error.message || 'An unknown error occurred. Check console for details.'}</p>`;
        document.getElementById('shelf_life_prediction').innerText = '';
        document.getElementById('ffa_prediction').innerText = '';
    });
});


document.addEventListener('DOMContentLoaded', function() {
     console.log('DOM fully loaded and parsed.');
});
