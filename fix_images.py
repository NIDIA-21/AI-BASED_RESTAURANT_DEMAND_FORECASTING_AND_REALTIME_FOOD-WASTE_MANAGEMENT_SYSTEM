"""
Fix stored image_url values for dishes that had wrong photos.
Clear the image_url so the corrected display_image property logic runs.
Run once then delete.
"""
from backend import create_app
from backend.models import db, ProductMenu

app = create_app()
with app.app_context():
    # These 4 dishes need corrected images - clear stored URL so property logic runs
    dishes_to_fix = ['Poori', 'Chapati and Curry', 'Veg Meals', 'Paneer Rice']
    
    for dish_name in dishes_to_fix:
        item = ProductMenu.query.filter(
            db.func.lower(ProductMenu.item_name) == dish_name.lower()
        ).first()
        if item:
            old_url = item.image_url
            item.image_url = None  # Clear so display_image property returns correct URL
            print(f"Fixed: {item.item_name} (old: {old_url}) -> now uses corrected logic")
            print(f"  New URL will be: {item.display_image}")
        else:
            print(f"Not found: {dish_name}")
    
    db.session.commit()
    print("\nAll image fixes committed!")
    
    # Verify all 10 items
    print("\nAll menu items and their images:")
    for item in ProductMenu.query.order_by(ProductMenu.id).all():
        print(f"  {item.id}. {item.item_name}: {item.display_image[:60]}...")
