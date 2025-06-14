// Function to toggle the RH input method display
function toggleRhInputMethod() {
    const rhMethodSelect = document.getElementById('rh_method_embed');
    const rhInputContainer = document.getElementById('rh-input-container');
    const selectedMethod = rhMethodSelect.value;

    // Clear previous content
    rhInputContainer.innerHTML = '';

    if (selectedMethod === 'enter_rh') {
        // Add input field for RH value
        rhInputContainer.innerHTML = `
            <div class="form-group">
                <label for="rh_value_embed">Enter RH (%):</label> <!-- Label is visible when input is shown -->
                <input type="number" id="rh_value_embed" name="rh_value" placeholder="Enter RH %" required class="form-control" step="0.1">
            </div>
        `;
    } else if (selectedMethod === 'use_season') {
        // Add Season dropdown for RH lookup
         rhInputContainer.innerHTML = `
             <div class="form-group">
                 <label for="season_embed_rh">Season for RH Lookup:</label> <!-- More descriptive label -->
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
    }
    // If selectedMethod is empty ('-- Select RH Method --'), the container remains empty.
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

     // Ensure the main Season and other selects are reset
    document.getElementById('days_passed_embed').value = '';
    document.getElementById('season_embed').value = '';
    document.getElementById('moisture_embed').value = '';
    document.getElementById('packing_embed').value = '';
     document.getElementById('rh_method_embed').value = ''; // Reset RH method select
}


document.getElementById('prediction-form').addEventListener('submit', function(event) {
    event.preventDefault(); // Prevent the default form submission

    // Collect input data from the form
    const temperature = document.getElementById('temp_embed').value;
    const rhMethod = document.getElementById('rh_method_embed').value;
    let rhValueToSend; // Value to send to the Flask app
    let seasonForRhLookup = null; // To hold the season if used for RH

    if (rhMethod === 'enter_rh') {
        const rhValueInput = document.getElementById('rh_value_embed');
        if (!rhValueInput || rhValueInput.value === '') {
             alert('Please enter the RH value.');
             return;
        }
        rhValueToSend = parseFloat(rhValueInput.value);
    } else if (rhMethod === 'use_season') {
        const seasonForRhSelect = document.getElementById('season_embed_rh');
        if (!seasonForRhSelect || seasonForRhSelect.value === '') {
            alert('Please select a season for RH lookup.');
            return;
        }
        rhValueToSend = 'not Known'; // Send 'not Known' string
        seasonForRhLookup = seasonForRhSelect.value; // Capture the season for RH lookup
    } else {
        alert('Please select a method for providing RH.');
        return;
    }

     const daysPassedSelect = document.getElementById('days_passed_embed');
     if (!daysPassedSelect || daysPassedSelect.value === '') {
          alert('Please select Days Passed after Milling.');
          return;
     }
    const daysPassedValue = daysPassedSelect.value;


    const mainSeasonSelect = document.getElementById('season_embed'); // Get the main season select
     if (!mainSeasonSelect || mainSeasonSelect.value === '') {
        alert('Please select a season for the prediction.');
        return;
     }
    const mainSeasonValue = mainSeasonSelect.value;


    const moistureSelect = document.getElementById('moisture_embed');
     if (!moistureSelect || moistureSelect.value === '') {
         alert('Please select Moisture.');
         return;
     }
    const moistureValue = moistureSelect.value;


    const packingSelect = document.getElementById('packing_embed');
     if (!packingSelect || packingSelect.value === '') {
         alert('Please select Packing.');
         return;
     }
    const packingValue = packingSelect.value;


    // Prepare data for the API in the format your Flask app expects
    const data = {
        "Storage Temperature in C": parseFloat(temperature),
        "RH in percent": rhValueToSend, // Use the value determined by the method
        "Days passed after milling": daysPassedValue, // Send the selected value (string or number)
        "Season": mainSeasonValue, // Use the value from the main season select
        "Moisture": moistureValue, // Send the selected string value
        "Packing": packingValue // Send the selected string value
    };

    // Define the URL of your deployed Flask application on Render
    const renderUrl = 'https://buckwheat-prediction.onrender.com/predict'; // Your Render URL + endpoint

    // Clear previous results and display loading indicator
     document.getElementById('prediction_results').innerHTML = '<h3>Prediction Results:</h3><p id="shelf_life_prediction">Predicting...</p><p id="ffa_prediction"></p>';
     document.getElementById('prediction_results').style.color = 'black'; // Reset text color


    // Send POST request to your Flask app
    fetch(renderUrl, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(data)
    })
    .then(response => {
        if (!response.ok) {
            // Handle HTTP errors (e.g., 400, 500)
            return response.json().then(error => {
                 // Attempt to get a more specific error message from the server
                 const errorMessage = error.message || (error.error ? error.error : response.statusText);
                 throw new Error(`HTTP error! status: ${response.status}, message: ${errorMessage}`);
            }).catch(() => {
                 // Fallback if response body is not JSON or error structure is different
                 throw new Error(`HTTP error! status: ${response.status}, message: ${response.statusText}`);
            });
        }
        return response.json(); // Parse the JSON response
    })
    .then(result => {
        // Check if the result object has the expected properties
        if (result && typeof result.shelf_life_days !== 'undefined' && typeof result.predicted_free_fatty_acids_percent !== 'undefined') {
             // Display predictions in the designated HTML elements
             document.getElementById('shelf_life_prediction').innerText = `Predicted Shelf Life: ${result.shelf_life_days.toFixed(2)} days`;
             document.getElementById('ffa_prediction').innerText = `Predicted Free Fatty Acids: ${result.predicted_free_fatty_acids_percent.toFixed(2)} %`;
             document.getElementById('prediction_results').style.color = 'green'; // Indicate success
             // Update innerHTML of results area with the values for persistence
             document.getElementById('prediction_results').innerHTML = `<h3>Prediction Results:</h3><p id="shelf_life_prediction">${document.getElementById('shelf_life_prediction').innerText}</p><p id="ffa_prediction">${document.getElementById('ffa_prediction').innerText}</p>`;

        } else {
            // Handle case where response is OK but structure is unexpected
            console.error('Unexpected response format:', result);
            document.getElementById('prediction_results').innerHTML = `<h3 style="color: red;">Prediction Error:</h3><p style="color: red;">Unexpected response from server.</p>`;
        }

    })
    .catch(error => {
        console.error('Error during prediction:', error);
        // Display an error message to the user
        document.getElementById('prediction_results').innerHTML = `<h3 style="color: red;">Prediction Error:</h3><p style="color: red;">${error.message || 'An unknown error occurred.'}</p>`;
        document.getElementById('shelf_life_prediction').innerText = ''; // Clear previous results
        document.getElementById('ffa_prediction').innerText = '';
    });
});


// Initial call to set the correct state for the conditional RH input area when the page loads
document.addEventListener('DOMContentLoaded', function() {
    // No initial call to toggleRhInputMethod needed here as we want the user to select first.
    // The container will be empty initially, which is correct.
});
