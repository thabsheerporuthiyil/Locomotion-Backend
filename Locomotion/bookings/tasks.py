from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from .models import RideRequest

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
