#!/bin/bash

set -e

# Check for the existence of required tools
required_tools=(black isort python prospector bandit mypy semgrep pytest)
for tool in "${required_tools[@]}"; do
    if ! command -v "$tool" &> /dev/null; then
        echo "$tool could not be found, please install it before running this script."
        exit 1
    fi
done

# Define a list of apps to process
apps=(merchantservice paymentgatewayservice transactions userservice walletservice kyc tests)

# Run black
echo "Running black..."
for app in "${apps[@]}"; do
    black "$app" --line-length=100
done

# Run isort
echo "Running isort..."
for app in "${apps[@]}"; do
    isort "$app"
done

# Run django migrations check to ensure that there are no migrations left to create
echo "Running makemigrations..."
python manage.py makemigrations

echo "Running migrate..."
python manage.py migrate

# Run python static validation
# echo "Running prospector..."
# prospector --profile=.prospector.yml --path=merchantservice


# Run bandit
echo "Running bandit..."
bandit -r "${apps[@]}" --exclude tests

# Run mypy
echo "Running mypy..."
mypy "${apps[@]}"

# Run semgrep
echo "Running semgrep..."
semgrep --timeout 60 --config .semgrep_rules.yml "${apps[@]}"

# Run pytest
echo "Running pytest..."
pytest "${apps[@]}"
