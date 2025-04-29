# Use Python 3.8 slim base image
FROM python:3.8-slim

# Set working directory in container
WORKDIR /app

# Copy requirements file
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install additional required packages that aren't in requirements.txt
RUN pip install numpy pandas scikit-learn matplotlib

# Copy the entire application
COPY . .

# Train the model before running the app
RUN python model.py

# Set environment variables
ENV FLASK_APP=application.py
ENV FLASK_ENV=production

# Expose port 8080
EXPOSE 8080

# Run the application
CMD ["python", "application.py"]
