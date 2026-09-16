"""Termux diagnostic for FarmDirect FINAL V20 multi-source mandi sync."""
import market_sync

print("FarmDirect FINAL V20 multi-source market sync")
print("Chain: AGMARKNET 2.0 -> data.gov.in -> Tamil Nadu AgriMarket -> optional e-NAM -> cache")
print("Testing Tomato / Tamil Nadu...\n")
result = market_sync.sync_crop("Tomato", state="Tamil Nadu", force=True, limit=100)
print("Sync result:", result)
reference = market_sync.get_reference_price("Tomato", "Tamil Nadu")
print("\nReference:", reference)
print("\nProvider health:")
for provider in market_sync.status_summary().get("providers", []):
    print(f" - {provider['provider']}: {provider['status']} | {provider.get('message') or ''}")
if reference:
    print(f"\nOK: ₹{reference['modal']}/kg | {reference['provider']} | {reference['arrival_date']}")
else:
    print("\nNo verified market row available yet. The app will keep retrying automatically and never invent an official price.")
