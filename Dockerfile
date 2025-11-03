# Base Image
FROM python:3.11-slim-bookworm

# Python environment setup
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Setting working directory
ENV PROJECT=/home/app
RUN mkdir -p ${PROJECT}/logs ${PROJECT}/media ${PROJECT}/staticfiles ${PROJECT}/static
WORKDIR ${PROJECT}

# Installing system dependencies (Removed redis-server)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libc-dev \
    python3-dev \
    && apt-get clean && rm -rf /var/lib/apt/lists/*


# Upgrading pip and installing Python dependencies
RUN python -m pip install --upgrade pip setuptools

# Installing requirements, including Daphne
COPY ./requirements.txt ${PROJECT}/requirements.txt
RUN pip install -r ${PROJECT}/requirements.txt

# Copying project files
COPY . ${PROJECT}

# # Running migrations
# RUN python manage.py makemigrations
# RUN python manage.py migrate

# # Collect static
# RUN python manage.py collectstatic --noinput

# Exposing the application port
EXPOSE 8000

# Running the application using Daphne
# CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "project.asgi:application"]
