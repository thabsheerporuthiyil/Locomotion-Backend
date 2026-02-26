from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from django.conf import settings
from django.db.models import Sum
from .models import RideRequest
from drivers.models import DriverProfile
import razorpay
import logging

logger = logging.getLogger(__name__)

razorpay_client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

@shared_task
def auto_cancel_stale_rides():
    """
    Cancels any ride requests that have been pending for more than 5 minutes.
    This frees up the rider's map and cleans out the driver's request queue.
    """
    five_minutes_ago = timezone.now() - timedelta(minutes=5)
    
    stale_rides = RideRequest.objects.filter(status='pending', created_at__lte=five_minutes_ago)
    count = stale_rides.count()
    
    if count > 0:
        stale_rides.update(status='cancelled')
        return f"Auto-cancelled {count} stale ride requests"
    return "No stale rides to cancel"


@shared_task
def process_weekly_driver_payouts():
    """
    Finds all drivers who have completed, paid rides that have not been settled yet.
    Calculates their cut and marks the rides as 'settled'. 
    In a real system, this would generate a report for manual bank transfers.
    """
    
    # 1. Get all drivers who have unsettled rides
    drivers = DriverProfile.objects.all()
    
    total_transfers_calculated = 0
    total_amount_calculated = 0
    
    for driver in drivers:
        # 2. Get all unsettled rides for this driver
        unsettled_rides = RideRequest.objects.filter(
            driver=driver,
            status='completed',
            payment_status='completed',
            is_paid=True,
            payout_status='pending'
        )
        
        if unsettled_rides.count() == 0:
            continue
            
        # Calculate total earnings for this driver
        # Ensure we don't hit None values
        total_fare_decimal = unsettled_rides.aggregate(Sum('estimated_fare'))['estimated_fare__sum']
        total_service_charge_decimal = unsettled_rides.aggregate(Sum('service_charge'))['service_charge__sum']
        
        if not total_fare_decimal:
            continue
            
        total_fare = float(total_fare_decimal)
        total_service_charge = float(total_service_charge_decimal) if total_service_charge_decimal else 0.0
        
        # 4. Calculate Driver's cut (Platform takes the sum of all service charges)
        driver_amount = total_fare - total_service_charge
        
        driver_amount_in_paise = int(driver_amount * 100)
        
        if driver_amount_in_paise <= 0:
            continue
            
        try:
            # 5. Mark these rides as settled
            unsettled_rides.update(payout_status='settled')
            
            total_transfers_calculated += 1
            total_amount_calculated += driver_amount
            
            # 6. Log the payout for the admin to process manually
            logger.info(f"Payout Ready: Driver {driver.user.name} (ID: {driver.id}) is owed {driver_amount} INR for {unsettled_rides.count()} rides. (Platform kept {total_service_charge} INR as fee)")
            
        except Exception as e:
            logger.error(f"Unexpected error processing payout for driver ID {driver.id}: {str(e)}")
            
    return f"Calculated {total_transfers_calculated} manual payouts amounting to {total_amount_calculated} INR"
