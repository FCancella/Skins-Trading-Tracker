from django.core.management.base import BaseCommand
from trades.models import Trade
from django.utils import timezone
from datetime import timedelta, time

class Command(BaseCommand):
    help = 'Fixes historical trade datetimes that were incorrectly set to 21:00 after migration.'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS("--- Starting Trade Datetime Fix Script ---"))

        trades_to_fix = Trade.objects.filter(
            buy_date__time=time(21, 0)
        ) | Trade.objects.filter(
            sell_date__time=time(21, 0)
        )
        
        # trades_to_fix = trades_to_fix.distinct()

        if not trades_to_fix.exists():
            self.stdout.write(self.style.WARNING("No trades with 21:00 timestamp found to fix."))
            return

        self.stdout.write(f"Found {trades_to_fix.count()} trades to potentially fix.")

        updated_count = 0
        for trade in trades_to_fix:
            updated = False
            
            # Fix buy_date if it's at 21:00
            print(trade.buy_date)
            if trade.buy_date.time() == time(0, 0):
                new_buy_date = (trade.buy_date).replace(hour=3, minute=0, second=0, microsecond=0)
                trade.buy_date = new_buy_date
                updated = True
                self.stdout.write(f"  Fixing buy_date for trade ID {trade.id}...")

            # Fix sell_date if it's at 21:00
            if trade.sell_date and trade.sell_date.time() == time(0, 0):
                new_sell_date = (trade.sell_date).replace(hour=3, minute=0, second=0, microsecond=0)
                trade.sell_date = new_sell_date
                updated = True
                self.stdout.write(f"  Fixing sell_date for trade ID {trade.id}...")

            if updated:
                trade.save()
                updated_count += 1
        
        self.stdout.write(self.style.SUCCESS(f"--- Script Finished. Successfully updated {updated_count} trades. ---"))