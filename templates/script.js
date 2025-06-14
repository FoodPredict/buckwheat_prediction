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
                <label for="rh_value_embed" class="sr-only">Enter RH %:</label>
                <input type="number" id="rh_value_embed" name="rh_value" placeholder="Enter RH %" required class="form-control">
            </div>
        `;
    } else if (selectedMethod === 'use_season') {
        // Add Season dropdown (assuming it's needed for RH lookup)
         rhInputContainer.innerHTML = `
             <div class="form-group">
                 <label for="season_embed_rh">Season for RH:</label> <!-- New ID to distinguish from the main season select -->
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
         // Note: The main season dropdown (id="season_embed") is still needed for the model input.
         // This "season_embed_rh" is specifically for the conditional RH lookup.
    }
}

// Function to clear the form
function clearForm() {
    const form = document.getElementById('prediction-form');
    form.reset(); // Resets all form elements to their initial state

    // Also clear prediction results
    document.getElementById('shelf_life_prediction').innerText = '';
    document.getElementById('ffa_prediction').innerText = '';
    document.getElementById('prediction_results').innerHTML = '<h3>Prediction Results:</h3><p id="shelf_life_prediction"></p><p id="ffa_prediction"></p>'; // Reset structure
    document.getElementById('prediction_results').style.color = 'black'; // Reset text color

    // Reset the conditional RH input area
    document.getElementById('rh-input-container').innerHTML = '';
}


document.getElementById('prediction-form').addEventListener('submit', function(event) {
    event.preventDefault(); // Prevent the default form submission

    // Collect input data from the form
    const temperature = document.getElementById('temp_embed').value;
    const rhMethod = document.getElementById('rh_method_embed').value;
    let rhValueToSend; // Value to send to the Flask app

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
        rhValueToSend = 'not Known'; // Send 'not Known' string, Flask app will handle the lookup
        // We also need the *main* season for the model input
        const mainSeason = document.getElementById('season_embed').value;
         if (!mainSeason) {
             alert('Please select a season for the prediction.');
             return;
         }
         // Ensure the main season value is collected
         data.Season = mainSeason; // We'll add this to the data object later
    } else {
        alert('Please select a method for providing RH.');
        return;
    }

     const daysPassed = document.getElementById('days_passed_embed').value;
     if (!daysPassed) { // Basic check for days passed
          alert('Please select Days Passed after Milling.');
          return;
     }

    const mainSeason = document.getElementById('season_embed').value; // Get the main season value
     if (!mainSeason) {
        alert('Please select a season for the prediction.');
        return;
     }


    const moisture = document.getElementById('moisture_embed').value;
     if (!moisture) { // Basic check for moisture
         alert('Please select Moisture.');
         return;
     }

    const packing = document.getElementById('packing_embed').value;
     if (!packing) { // Basic check for packing
         alert('Please select Packing.');
         return;
     }


    // Prepare data for the API in the format your Flask app expects
    // Handle 'not_known' for Days passed after milling
    let daysPassedValue;
    if (daysPassed === 'not_known') {
         daysPassedValue = 'not_known'; // Send as string for Flask to handle if needed
         // Consider if your Flask app expects a number and needs imputation for 'not_known'
    } else {
        daysPassedValue = parseInt(daysPassed); // Parse to integer
    }


    // Ensure data types match what your Flask app expects (e.g., numbers as numbers, strings as strings)
    const data = {
        "Storage Temperature in C": parseFloat(temperature),
        "RH in percent": rhValueToSend, // Use the value determined by the method
        "Days passed after milling": daysPassedValue, // Use the handled value
        "Season": mainSeason, // Use the value from the main season select
        "Moisture": parseFloat(moisture.replace('<', '').replace('>', '').replace('-', ' ').split(' ')[0]), // Handle different moisture formats - VERIFY THIS PARSING
        "Packing": packing
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
        // Display predictions in the designated HTML elements
        document.getElementById('shelf_life_prediction').innerText = `Predicted Shelf Life: ${result.shelf_life_days.toFixed(2)} days`;
        document.getElementById('ffa_prediction').innerText = `Predicted Free Fatty Acids: ${result.predicted_free_fatty_acids_percent.toFixed(2)} %`;
        document.getElementById('prediction_results').style.color = 'green'; // Indicate success
        document.getElementById('prediction_results').innerHTML = `<h3>Prediction Results:</h3><p id="shelf_life_prediction">${document.getElementById('shelf_life_prediction').innerText}</p><p id="ffa_prediction">${document.getElementById('ffa_prediction').innerText}</p>`;

    })
    .catch(error => {
        console.error('Error during prediction:', error);
        // Display an error message to the user
        document.getElementById('prediction_results').innerHTML = `<h3 style="color: red;">Prediction Error:</h3><p style="color: red;">${error.message || 'An unknown error occurred.'}</p>`;
        document.getElementById('shelf_life_prediction').innerText = ''; // Clear previous results
        document.getElementById('ffa_prediction').innerText = '';
    });
});


// Initial call to set the correct state when the page loads
document.addEventListener('DOMContentLoaded', function() {
    // No initial call to toggleRhInputMethod needed here as we want the user to select first.
    // We could add a default 'use_season' option if desired.
});
