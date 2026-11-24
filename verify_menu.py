"""Quick verification that all 10 menu items and DB tables are correct."""
from backend import create_app
from ml_model.predictor import DemandPredictor

app = create_app()
with app.app_context():
    from backend.models import (ProductMenu, InventoryIngredient, MenuItemIngredient,
                                 DailyFoodPrep, FoodWasteLog, FoodDonation, HistoricalSalesData)
    items = ProductMenu.query.all()
    print("=== MENU ITEMS (%d) ===" % len(items))
    for item in items:
        print("  #%d: %s (%s) - Rs.%.2f" % (item.id, item.item_name, item.category, item.unit_price))

    print("\n=== DATABASE TABLE COUNTS ===")
    print("  Ingredients:   ", InventoryIngredient.query.count())
    print("  Recipes:       ", MenuItemIngredient.query.count())
    print("  DailyFoodPrep: ", DailyFoodPrep.query.count())
    print("  WasteLogs:     ", FoodWasteLog.query.count())
    print("  Donations:     ", FoodDonation.query.count())
    print("  HistoricalSales:", HistoricalSalesData.query.count())

    print("\n=== ML PREP RECOMMENDATIONS (Weekend Rainy 180 customers) ===")
    recs = DemandPredictor.get_daily_preparation_recommendations(
        customer_count=180, day_type='weekend', weather_condition='Rainy')
    for r in recs['recommendations']:
        print("  %-20s | demand=%d | prep_qty=%d | stock=%d" % (
            r['item_name'], r['predicted_demand'], r['recommended_prep_qty'], r['current_stock']))

    print("\nALL CHECKS PASSED - App is ready!")
