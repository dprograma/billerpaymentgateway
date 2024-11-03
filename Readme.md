# This is a readme file for setting up the Aggregated Merchant Acquiring and Payment Gateway System (AMAPS) Application

## 1. Install python on your device (MacOs, Windows, Linux)

## 2. Clone the amaps repository, create virtual environment and install django

```bash
git clone https://kenegwuda@bitbucket.org/siliconharbourng/amaps.git

cd amaps

python3 -m venv venv

source venv/bin/activate

pip install django` # if django is not already installed
```

## 3. setup postgres database and set the login credentials

## 4. start the server

####################################################################
## Code Analysis, sorting and static type checking
####################################################################


## 5. Run static validation comprising black, isort, pylint, mypy and pytest

```bash
chmod +x static_validation.sh     # may require `sudo` for admin permission

DJANGO_SETTINGS_MODULE=amaps.dev ./static_validation.sh
```



