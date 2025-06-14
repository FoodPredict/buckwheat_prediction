// Function to toggle the RH input method display
function toggleRhInputMethod() {
    const rhMethodSelect = document.getElementById('rh_method_embed');
    const rhInputContainer = document.getElementById('rh-input-container');
    const selectedMethod = rhMethodSelect.value;

    // Clear previous content
    rhInputContainer.innerHTML = ''; // Clear existing content first

    if (selectedMethod === 'known') { // Value is 'known'
        // Add input field for RH value
        rhInputContainer.innerHTML = `
            <div class="form-group">
                <label for="rh_value_embed">Enter RH (%):</label>
                <input type="number" id="rh_value_embed" name="rh_value" placeholder="Enter RH %" required class="form-control" step="0.1">
            </div>
        `;
        console.log('RH Known selected. Numerical input field added.');
    } else if (selectedMethod === 'not_known') { // Value is 'not_known'
        // Add Season dropdown for RH lookup
         rhInputContainer.innerHTML = `
             <div class="form-group">
                 <label for="season_embed_rh">Season for RH Lookup:</label>
                 <select id="season_embed_rh" name="season_for_rh" required class="form-control">
                     <option value="">-- Select Season --</option>
                     <option value="Summer">Summer</option>
                     <option value="Spring">Spring</option>
                     <option value="Autumn">Autumn</option>
                     <option value="Winter">Winter</option>
                     <option value="Rainy">Rainy</option>
                 </select>
             </div>
         `;
         console.log('RH not known selected. Season dropdown for lookup added.');
    } else {
         console.log('No RH method selected.');
    }
     console.log('toggleRhInputMethod executed. Selected method:', selectedMethod);
}

// Function to clear the form
function clearForm() {
    const form = document.getElementById('prediction-form');
    form.reset(); // Resets all form elements to their initial state

    // Clear prediction results and reset the results area
    document.getElementById('prediction_results').innerHTML = '<h3>Prediction Results:</h3><p id="shelf_life_prediction"></p><p id="ffa_prediction"></p>';
    document.getElementById('prediction_results').style.color = 'black'; // Reset text color

    // Clear the dynamically added RH input/select
    document.getElementById('rh-input-container').innerHTML = '';

     // Reset specific selects to their default option
    document.getElementById('days_passed_embed').value = '';
    document.getElementById('season_embed').value = '';
    document.getElementById('moisture_embed').value = '';
    document.getElementById('packing_embed').value = '';
     document.getElementById('rh_method_embed').value = ''; // Reset RH method select

    console.log('Form cleared.');
}


document.getElementById('prediction-form').addEventListener('submit', function(event) {
    event.preventDefault();
    console.log('Form submitted.');

    // Collect input data from the form
    const temperature = document.getElementById('temp_embed').value;
    const rhMethod = document.getElementById('rh_method_embed').value;
    let rhValueToSend;
    let seasonForRhLookupValue = null;


    if (rhMethod === 'known') { // Value is 'known'
        const rhValueInput = document.getElementById('rh_value_embed');
        // Check if the rhValueInput element exists and has a valid number
        if (!rhValueInput || rhValueInput.value === '' || isNaN(parseFloat(rhValueInput.value))) {
             alert('Please enter a valid numeric RH value.');
             console.log('Validation failed: Invalid RH value.');
             return;
        }
        rhValueToSend = parseFloat(rhValueInput.value);
    } else if (rhMethod === 'not_known') { // Value is 'not_known'
        const seasonForRhSelect = document.getElementById('season_embed_rh');
        // Check if the seasonForRhSelect element exists and a season is selected
        if (!seasonForRhSelect || seasonForRhSelect.value === '') {
            alert('Please select a season for RH lookup.');
             console.log('Validation failed: No season selected for RH lookup.');
            return;
        }
        rhValueToSend = 'not Known'; // Send 'not Known' string to Flask
        seasonForRhLookupValue = seasonForRhSelect.value; // Capture the season value for lookup
    } else {
        alert('Please select a method for providing RH.');
        console.log('Validation failed: No RH method selected.');
        return;
    }

     const daysPassedSelect = document.getElementById('days_passed_embed');
     if (!daysPassedSelect || daysPassedSelect.value === '') {
          alert('Please select Days Passed after Milling.');
           console.log('Validation failed: No Days Passed selected.');
          return;
     }
    const daysPassedValue = daysPassedSelect.value;


    const mainSeasonSelect = document.getElementById('season_embed'); // Get the main season select
     if (!mainSeasonSelect || mainSeasonSelect.value === '') {
        alert('Please select a season for the prediction.');
         console.log('Validation failed: No main Season selected.');
        return;
     }
    const mainSeasonValue = mainSeasonSelect.value;


    const moistureSelect = document.getElementById('moisture_embed');
     if (!moistureSelect || moistureSelect.value === '') {
         alert('Please select Moisture.');
          console.log('Validation failed: No Moisture selected.');
         return;
     }
    const moistureValue = moistureSelect.value;


    const packingSelect = document.getElementById('packing_embed');
     if (!packingSelect || packingSelect.value === '') {
         alert('Please select Packing.');
          console.log('Validation failed: No Packing selected.');
         return;
     }
    const packingValue = packingSelect.value;

     // The season value sent to the Flask app is the main Season selected for the prediction model.
     // The seasonForRhLookupValue is ONLY used in the Flask app if RH is 'not Known'.
     const seasonValueToSend = mainSeasonValue;


    // Prepare data for the API in the format your Flask app expects
    const data = {
        "Storage Temperature in C": parseFloat(temperature),
        "RH in percent": rhValueToSend, // Use the value determined by the method (number or 'not Known')
        "Days passed after milling": daysPassedValue, // Send the selected value (string 'not_known' or number as string)
        "Season": seasonValueToSend, // Always send the main Season for the model
        "Moisture": moistureValue, // Send the selected string value
        "Packing": packingValue // Send the selected string value
    };

    // Add seasonForRhLookupValue to data ONLY if RH method is 'not_known'.
    // The Flask app needs to be updated to look for this key if "RH in percent" is 'not Known'.
    if (rhMethod === 'not_known') {
        data['Season for RH Lookup'] = seasonForRhLookupValue;
    }


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
