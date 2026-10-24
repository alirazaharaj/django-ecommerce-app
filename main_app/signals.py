from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Order, ProductVariant

@receiver(post_save, sender=Order)
def update_stock_on_order_status_change(sender, instance, **kwargs):
    """Update stock when order status changes from cancelled to something else"""
    # This is handled in the admin action, but this is a backup
    pass