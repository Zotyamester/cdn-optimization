FROM python:3.12-slim

WORKDIR /code

# Copy resources of built-in data models.
COPY ./datasource /code/datasource

# Install required packages.
COPY ./requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir -r /code/requirements.txt

# Copy source files.
COPY ./app /code/app

CMD ["fastapi", "run", "app/api.py", "--port", "80"]
