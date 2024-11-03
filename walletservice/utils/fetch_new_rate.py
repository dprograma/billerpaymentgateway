import requests
import logging
from django.conf import settings
from decimal import Decimal, InvalidOperation

logger = logging.getLogger(__name__)


def fetch_new_rate(from_currency, to_currency):
    logger.debug(f"FROM CURRENCY: {from_currency}")
    logger.debug(f"TO CURRENCY: {to_currency}")
    api_key = settings.EXCHANGE_RATE_API_KEY
    url = f"https://v6.exchangerate-api.com/v6/{api_key}/pair/{from_currency}/{to_currency}"

    logger.info(f"Fetching rate from {url}")
    try:
        response = requests.get(url)
        logger.info(f"Received response status: {response.status_code}")
    except requests.RequestException as e:
        logger.error(f"Request failed for URL {url}. Error: {e}")
        raise Exception("Failed to fetch exchange rate due to request error") from e

    if response.status_code == 200:
        try:
            data = response.json()
            logger.info(f"Received response data: {data}")
            conversion_rate = data.get("conversion_rate")
            if conversion_rate is None:
                logger.error("conversion_rate not found in response data")
                raise KeyError("conversion_rate not found in response data")
            # Convert to Decimal for precision
            try:
                rate = Decimal(str(conversion_rate))
                logger.debug(f"Parsed conversion_rate: {rate}")
                return rate
            except (InvalidOperation, ValueError) as e:
                logger.error(
                    f"Invalid conversion_rate format: {conversion_rate}. Error: {e}"
                )
                raise
        except ValueError as e:
            logger.error(f"JSON decoding failed for response from {url}. Error: {e}")
            raise Exception("Failed to decode JSON response") from e
    else:
        logger.error(
            f"Failed to fetch exchange rate: {response.status_code} {response.text}"
        )
        raise Exception("Failed to fetch exchange rate due to non-200 response")
