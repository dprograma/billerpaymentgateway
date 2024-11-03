import logging
from celery import shared_task
from .utils.fetch_new_rate import fetch_new_rate

logger = logging.getLogger(__name__)


@shared_task
def update_exchange_rates():
    from .models import ExchangeRate

    logger.debug("Starting update_exchange_rates task...")
    exchange_rates = ExchangeRate.objects.all()

    for exchange_rate in exchange_rates:
        try:
            new_rate = fetch_new_rate(
                exchange_rate.from_currency.code, exchange_rate.to_currency.code
            )
            logger.debug(
                f"Fetched new rate: {new_rate} for {exchange_rate.from_currency.code} to {exchange_rate.to_currency.code}"
            )
            exchange_rate.rate = new_rate
            exchange_rate.save()
            logger.debug(
                f"Updated exchange rate for {exchange_rate.from_currency.code} to {exchange_rate.to_currency.code}"
            )
        except Exception as e:
            logger.error(
                f"Failed to update exchange rate for {exchange_rate.from_currency.code} to {exchange_rate.to_currency.code}. Error: {e}",
                exc_info=True,
            )
