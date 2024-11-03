from django.core.management.base import BaseCommand
from walletservice.models import Currency, ExchangeRate


class Command(BaseCommand):
    help = (
        "Populates the Currency model and creates currency pairs in ExchangeRate model."
    )

    def handle(self, *args, **kwargs):
        self.populate_currencies()
        self.create_currency_pairs()

    def populate_currencies(self):
        wallet_choices = [
            "NGN",
            "GHS",
            "KES",
            "XOF",
            "XAF",
            "CDF",
            "GNF",
            "LRD",
            "MZN",
            "SLL",
            "TZS",
            "UGX",
            "ZMW",
            "USD",
            "EUR",
            "GBP",
            "AED",
        ]

        for code in wallet_choices:
            Currency.objects.get_or_create(code=code)
        self.stdout.write(self.style.SUCCESS("Successfully populated currencies."))

    def create_currency_pairs(self):
        currencies = Currency.objects.all()

        for from_currency in currencies:
            for to_currency in currencies:
                if from_currency != to_currency:
                    ExchangeRate.objects.get_or_create(
                        from_currency=from_currency,
                        to_currency=to_currency,
                        defaults={"rate": 1.0},
                    )
        self.stdout.write(self.style.SUCCESS("Successfully created currency pairs."))
