import numpy as np
from flask import Flask, request, jsonify, render_template
import pickle
import os  # Add this import for os.environ

# Fix for sklearn version compatibility
import sklearn

try:
    # For newer scikit-learn versions
    from sklearn.linear_model import LinearRegression
except ImportError:
    # For older scikit-learn versions
    from sklearn.linear_model.base import LinearRegression

application = Flask(__name__)  # Initialize the flask App

# Add error handling for model loading
try:
    model = pickle.load(open("model.pkl", "rb"))
    model_loaded = True
except Exception as e:
    print(f"Error loading model: {e}")
    model_loaded = False
    model = None
    # You might want to add a fallback model here or handle the error differently


@application.route("/")
def home():
    return render_template("index.html")


@application.route("/predict", methods=["POST"])
def predict():
    """
    For rendering results on HTML GUI
    """
    # Check if model is loaded before making predictions
    if not model_loaded:
        return render_template(
            "index.html",
            prediction_text="Error: Model is not available. Please check server logs.",
        )

    int_features = [int(x) for x in request.form.values()]
    final_features = [np.array(int_features)]
    prediction = model.predict(final_features)

    output = round(prediction[0], 2)

    return render_template(
        "index.html", prediction_text="Employee Salary should be $ {}".format(output)
    )


if __name__ == "__main__":
    application.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
