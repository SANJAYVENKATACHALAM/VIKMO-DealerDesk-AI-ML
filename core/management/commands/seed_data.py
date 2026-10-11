import csv

from django.conf import settings
from django.core.management.base import BaseCommand

from core.models import Product, Inventory, Dealer


class Command(BaseCommand):
    help = "Load catalogue and dealer data into the database."

    def handle(self, *args, **options):
        data_dir = settings.DATA_DIR

        catalogue_file = data_dir / "catalogue.csv"
        dealers_file = data_dir / "dealers.csv"

        # Load products and inventory
        with open(catalogue_file, "r", encoding="utf-8-sig", newline="") as file:
            reader = csv.DictReader(file)

            for row in reader:
                product, _ = Product.objects.update_or_create(
                    sku=row["sku"],
                    defaults={
                        "name": row["name"],
                        "category": row["category"],
                        "brand": row["brand"],
                        "vehicle_fitment": row["vehicle_fitment"],
                        "price": row["price"],
                        "description": row["description"],
                    },
                )

                Inventory.objects.update_or_create(
                    product=product,
                    defaults={
                        "quantity": int(row["stock"]),
                    },
                )

        # Load dealers
        with open(dealers_file, "r", encoding="utf-8-sig", newline="") as file:
            reader = csv.DictReader(file)

            for row in reader:
                Dealer.objects.update_or_create(
                    dealer_code=row["dealer_code"],
                    defaults={
                        "name": row["name"],
                        "city": row["city"],
                        "phone": row["phone"],
                        "email": row["email"],
                        "gstin": row["gstin"],
                        "credit_limit": row["credit_limit"],
                    },
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"Seed complete: {Product.objects.count()} products, "
                f"{Dealer.objects.count()} dealers."
            )
        )