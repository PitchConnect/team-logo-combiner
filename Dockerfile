FROM python:3.9-slim-buster

# Install curl for health checks
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

COPY app.py app.py
COPY team_logo_combiner.py team_logo_combiner.py
COPY src/ src/

# Create assets directory and copy default background image
RUN mkdir assets
COPY assets/grass_turf.jpg assets/grass_turf.jpg

EXPOSE 5002

CMD ["python", "app.py"]