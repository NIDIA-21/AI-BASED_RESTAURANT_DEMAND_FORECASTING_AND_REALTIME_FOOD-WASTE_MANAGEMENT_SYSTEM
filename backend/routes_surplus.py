"""
Surplus Food Management & NGO Coordination Module:
Logs unsold surplus food nearing shelf-life expiration and connects with local food rescue NGOs.
"""

from datetime import datetime, timezone
from flask import (
    Blueprint, render_template, request, redirect,
    url_for, flash, jsonify
)
from backend.models import (
    db, ProductMenu, SurplusRedistribution, InventoryStock, InventoryLog,
    FoodWasteLog, FoodDonation, DailyFoodPrep
)
from backend.auth import login_required, role_required
from backend.config import Config
from flask import session

surplus_bp = Blueprint('surplus', __name__, url_prefix='/surplus')


@surplus_bp.route('/', methods=['GET'])
@login_required
@role_required('admin', 'restaurant_manager', 'inventory_staff')
def index():
    """
    Staff / Manager Food Waste Management View:
    Log surplus food and track redistribution lifecycle.
    """
    menu_items = ProductMenu.query.order_by(ProductMenu.category, ProductMenu.item_name).all()

    # Active surplus listings
    available_listings = SurplusRedistribution.query.filter_by(
        status='available_for_ngo'
    ).order_by(SurplusRedistribution.logged_at.desc()).all()

    # Claimed food donations
    claimed_listings = SurplusRedistribution.query.filter_by(
        status='claimed'
    ).order_by(SurplusRedistribution.claimed_at.desc()).limit(50).all()

    # High-level environmental & social impact metrics
    all_donations = SurplusRedistribution.query.all()
    total_portions_saved = sum(s.surplus_qty for s in all_donations)
    claimed_portions = sum(s.surplus_qty for s in claimed_listings)
    total_co2_kg_saved = round(total_portions_saved * 2.5, 1)
    total_value_recovered = sum(s.estimated_value_recovered for s in all_donations)

    # Food waste logs, community donations & overproduction audit
    waste_logs = FoodWasteLog.query.order_by(FoodWasteLog.log_date.desc()).all()
    community_donations = FoodDonation.query.order_by(FoodDonation.donation_date.desc()).all()
    daily_preps = DailyFoodPrep.query.order_by(DailyFoodPrep.prep_date.desc()).all()
    total_waste_loss = sum(w.cost_loss for w in waste_logs)

    return render_template(
        'surplus/index.html',
        menu_items=menu_items,
        available_listings=available_listings,
        claimed_listings=claimed_listings,
        waste_logs=waste_logs,
        community_donations=community_donations,
        daily_preps=daily_preps,
        total_waste_loss=total_waste_loss,
        total_portions_saved=total_portions_saved,
        claimed_portions=claimed_portions,
        total_co2_kg_saved=total_co2_kg_saved,
        total_value_recovered=total_value_recovered,
        currency=Config.CURRENCY_SYMBOL
    )


@surplus_bp.route('/log', methods=['POST'])
@login_required
@role_required('admin', 'restaurant_manager', 'inventory_staff')
def log_surplus():
    """
    Records leftover or surplus batches nearing expiration into the NGO recovery network.
    Optionally adjusts physical InventoryStock if logged from remaining prep.
    """
    item_id = request.form.get('item_id', type=int)
    surplus_qty = request.form.get('surplus_qty', 0, type=int)
    notes = request.form.get('notes', '').strip()
    deduct_inventory = request.form.get('deduct_inventory') == 'yes'

    if not item_id or surplus_qty <= 0:
        flash("Please select a valid menu item and positive surplus quantity.", "warning")
        return redirect(url_for('surplus.index'))

    product = db.get_or_404(ProductMenu, item_id)

    # Optional deduction from physical stock
    if deduct_inventory:
        inv = InventoryStock.query.filter_by(item_id=item_id).first()
        if inv:
            prev_stock = inv.current_stock_qty
            inv.current_stock_qty = max(0, inv.current_stock_qty - surplus_qty)
            new_stock = inv.current_stock_qty
            inv_log = InventoryLog(
                item_id=item_id,
                change_qty=-(prev_stock - new_stock),
                previous_stock=prev_stock,
                new_stock=new_stock,
                reason='surplus_deduction',
                logged_at=datetime.now(timezone.utc),
                created_by_user_id=session.get('user_id')
            )
            db.session.add(inv_log)

    surplus_entry = SurplusRedistribution(
        item_id=item_id,
        surplus_qty=surplus_qty,
        status='available_for_ngo',
        logged_at=datetime.now(timezone.utc),
        notes=notes or "Prepared fresh during shift. Safely packed for immediate collection."
    )

    db.session.add(surplus_entry)
    db.session.commit()

    flash(
        f"Logged {surplus_qty} portions of '{product.item_name}' to the NGO Redistribution Portal. "
        f"Estimated {surplus_entry.co2_kg_saved} kg CO2 emission avoided upon claim!",
        "success"
    )
    return redirect(url_for('surplus.index'))


@surplus_bp.route('/ngo', methods=['GET'])
def ngo_portal():
    """
    Public / Community Partner NGO Portal:
    Allows local food recovery organizations (Robin Hood Army, Feeding India, local shelters)
    to browse live surplus food batches and claim donations for immediate pickup.
    """
    available_items = SurplusRedistribution.query.filter_by(
        status='available_for_ngo'
    ).order_by(SurplusRedistribution.logged_at.desc()).all()

    # Filter out expired items if hours_remaining <= 0
    active_items = [item for item in available_items if not item.is_expired]

    claimed_history = SurplusRedistribution.query.filter_by(
        status='claimed'
    ).order_by(SurplusRedistribution.claimed_at.desc()).limit(15).all()

    total_meals_saved = sum(s.surplus_qty for s in SurplusRedistribution.query.filter_by(status='claimed').all())
    total_co2 = round(total_meals_saved * 2.5, 1)

    return render_template(
        'surplus/ngo_portal.html',
        available_items=active_items,
        claimed_history=claimed_history,
        total_meals_saved=total_meals_saved,
        total_co2=total_co2,
        currency=Config.CURRENCY_SYMBOL
    )


@surplus_bp.route('/claim/<int:surplus_id>', methods=['POST'])
def claim_donation(surplus_id):
    """
    NGO donation claim endpoint:
    Records NGO organization identity, contact info, and estimated pickup ETA.
    """
    surplus_entry = db.get_or_404(SurplusRedistribution, surplus_id)

    if surplus_entry.status != 'available_for_ngo':
        flash("This surplus food batch has already been claimed by another organization.", "warning")
        return redirect(url_for('surplus.ngo_portal'))

    ngo_name = request.form.get('ngo_name', '').strip()
    contact_phone = request.form.get('contact_phone', '').strip()
    pickup_eta = request.form.get('pickup_eta', '').strip()

    if not ngo_name or not contact_phone:
        flash("Organization Name and Contact Phone are required to claim food donations.", "danger")
        return redirect(url_for('surplus.ngo_portal'))

    surplus_entry.status = 'claimed'
    surplus_entry.claimed_by_ngo = ngo_name
    surplus_entry.contact_phone = contact_phone
    surplus_entry.pickup_eta = pickup_eta or "Within 60 minutes"
    surplus_entry.claimed_at = datetime.now(timezone.utc)

    db.session.commit()

    flash(
        f"Thank you, {ngo_name}! You have successfully claimed {surplus_entry.surplus_qty} portions of "
        f"'{surplus_entry.product.item_name}'. Please present Claim #{surplus_entry.id} upon arrival.",
        "success"
    )
    return redirect(url_for('surplus.ngo_portal'))
