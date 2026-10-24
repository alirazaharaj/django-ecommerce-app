from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db import models
from django.utils import timezone
from unfold.admin import ModelAdmin, TabularInline, StackedInline
from .models import (
    Category,
    Brand,
    Tag,
    Product,
    ProductVariant,
    Review,
    Wishlist,
    CompareList,
    Cart,
    CartItem,
    Order,
    OrderItem,
    ShippingAddress,
    NewsletterSubscriber,
    ContactInquiry,
    SiteSetting,
    HomeSlider,
)


# Use Unfold's TabularInline instead of admin.TabularInline
class ProductVariantInline(TabularInline):
    model = ProductVariant
    extra = 1
    fields = [
        "size",
        "color",
        "color_code",
        "color_image",
        "price",
        "quantity", 
        "is_active",
        "is_default",
    ]


class CartItemInline(TabularInline):
    model = CartItem
    extra = 0
    readonly_fields = ["product", "variant", "quantity", "price", "item_total"]
    fields = ["product", "variant", "quantity", "price", "item_total"]

    def item_total(self, obj):
        return obj.item_total

    item_total.short_description = "Total"

    def has_add_permission(self, request, obj=None):
        return False


class OrderItemInline(TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ["product_name", "variant_name", "quantity", "price", "total"]
    fields = ["product_name", "variant_name", "quantity", "price", "total"]

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Category)
class CategoryAdmin(ModelAdmin):
    list_display = ["name", "parent", "is_active", "product_count", "created_at"]
    list_filter = ["is_active", "parent"]
    search_fields = ["name", "description"]
    prepopulated_fields = {"slug": ("name",)}
    ordering = ["name"]

    def product_count(self, obj):
        return obj.products.count()

    product_count.short_description = "Products"


@admin.register(Brand)
class BrandAdmin(ModelAdmin):
    list_display = ["name", "is_active", "product_count", "created_at"]
    list_filter = ["is_active"]
    search_fields = ["name"]
    prepopulated_fields = {"slug": ("name",)}

    def product_count(self, obj):
        return obj.products.count()

    product_count.short_description = "Products"


@admin.register(Tag)
class TagAdmin(ModelAdmin):
    list_display = ["name", "product_count"]
    search_fields = ["name"]
    prepopulated_fields = {"slug": ("name",)}

    def product_count(self, obj):
        return obj.products.count()

    product_count.short_description = "Products"


@admin.register(Product)
class ProductAdmin(ModelAdmin):
    list_display = [
        "name",
        "sku",
        "category",
        "brand",
        "price",
        "old_price",
        "total_quantity",
        "stock_status",
        "sale_label",
        "featured",
        "status",
        "created_at",
    ]
    list_filter = [
        "status",
        "stock_status",
        "sale_label",
        "featured",
        "best_selling",
        "new_arrival",
        "on_sale",
        "category",
        "brand",
    ]
    search_fields = ["name", "sku", "description"]
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ["discount_percentage", "average_rating", "total_quantity"]
    inlines = [ProductVariantInline]

    fieldsets = (
        (
            "Basic Information",
            {"fields": ("name", "slug", "sku", "description", "additional_info")},
        ),
        ("Pricing", {"fields": ("price", "old_price", "discount_percentage")}),
        (
            "Stock Management",
            {"fields": ("total_quantity", "stock_status", "low_stock_threshold")},
        ),
        ("Categories & Brand", {"fields": ("category", "brand", "tags")}),
        ("Images", {"fields": ("primary_image", "hover_image")}),
        ("Labels", {"fields": ("sale_label",)}),
        (
            "Status & Features",
            {
                "fields": (
                    "status",
                    "featured",
                    "best_selling",
                    "new_arrival",
                    "on_sale",
                    "sale_end_date",
                )
            },
        ),
    )
    
    def total_quantity(self, obj):
        """Calculate total quantity from variants"""
        from django.db import models
        total = obj.variants.aggregate(total=models.Sum('quantity'))['total'] or 0
        return total
    total_quantity.short_description = "Total Stock"
    
    actions = ["make_active", "make_inactive", "make_featured", "remove_featured"]

    def make_active(self, request, queryset):
        queryset.update(status="active")

    make_active.short_description = "Mark selected products as Active"

    def make_inactive(self, request, queryset):
        queryset.update(status="inactive")

    make_inactive.short_description = "Mark selected products as Inactive"

    def make_featured(self, request, queryset):
        queryset.update(featured=True)

    make_featured.short_description = "Mark selected products as Featured"

    def remove_featured(self, request, queryset):
        queryset.update(featured=False)

    remove_featured.short_description = "Remove Featured from selected products"


@admin.register(ProductVariant)
class ProductVariantAdmin(ModelAdmin):
    list_display = [
        "product",
        "size",
        "color",
        "price",
        "styled_quantity",
        "is_active",
    ]
    
    def styled_quantity(self, obj):
        if obj.quantity == 0:
            return format_html('<span style="color: #ef4444; font-weight: bold; background-color: #fee2e2; padding: 2px 6px; border-radius: 4px;">0 (Out of Stock)</span>')
        elif obj.quantity <= 5:
            return format_html('<span style="color: #d97706; font-weight: bold; background-color: #fef3c7; padding: 2px 6px; border-radius: 4px;">{} (Low Stock)</span>', obj.quantity)
        return format_html('<span style="color: #10b981; font-weight: bold;">{}</span>', obj.quantity)
    
    styled_quantity.short_description = "Inventory Stock"
    list_filter = ["is_active", "color", "size"]
    search_fields = ["product__name", "sku", "size", "color"]


@admin.register(Review)
class ReviewAdmin(ModelAdmin):
    list_display = ["product", "user", "name", "rating", "is_approved", "created_at"]
    list_filter = ["is_approved", "rating"]
    search_fields = ["product__name", "user__username", "name", "title", "body"]
    actions = ["approve_reviews"]

    def approve_reviews(self, request, queryset):
        queryset.update(is_approved=True)

    approve_reviews.short_description = "Approve selected reviews"


@admin.register(Wishlist)
class WishlistAdmin(ModelAdmin):
    list_display = ["user", "product", "added_at"]
    search_fields = ["user__username", "product__name"]


@admin.register(CompareList)
class CompareListAdmin(ModelAdmin):
    list_display = ["user", "product", "added_at"]
    search_fields = ["user__username", "product__name"]


@admin.register(Cart)
class CartAdmin(ModelAdmin):
    list_display = ["id", "user", "total_items", "subtotal", "is_ordered", "updated_at"]
    list_filter = ["is_ordered"]
    search_fields = ["user__username", "user__email"]
    inlines = [CartItemInline]
    readonly_fields = ["total_items", "subtotal"]


@admin.register(Order)
class OrderAdmin(ModelAdmin):
    list_display = [
        "order_number",
        "full_name",
        "email",
        "total",
        "status",
        "payment_status",
        "created_at",
    ]
    list_filter = ["status", "payment_status", "country"]
    search_fields = ["order_number", "first_name", "last_name", "email", "phone"]
    readonly_fields = ["order_number", "subtotal", "total"]
    inlines = [OrderItemInline]
    actions = [
        "mark_as_processing",
        "mark_as_shipped",
        "mark_as_delivered",
        "mark_as_cancelled",
        "mark_as_paid",
    ]

    fieldsets = (
        ("Order Information", {"fields": ("order_number", "status", "payment_status")}),
        (
            "Customer Information",
            {"fields": ("user", "first_name", "last_name", "email", "phone")},
        ),
        (
            "Shipping Information",
            {"fields": ("address", "city", "state", "country", "zip_code")},
        ),
        ("Order Totals", {"fields": ("subtotal", "shipping_cost", "tax", "total")}),
        ("Tracking Information", {"fields": ("tracking_number", "tracking_company", "estimated_delivery")}),
        ("Cancellation Information", {"fields": ("cancelled_at", "cancellation_reason")}),
        ("Notes", {"fields": ("notes",)}),
    )

    def mark_as_processing(self, request, queryset):
        queryset.update(status="processing")
        self.message_user(request, f"{queryset.count()} orders marked as processing.")

    mark_as_processing.short_description = "Mark as Processing"

    def mark_as_shipped(self, request, queryset):
        queryset.update(status="shipped")
        self.message_user(request, f"{queryset.count()} orders marked as shipped.")

    mark_as_shipped.short_description = "Mark as Shipped"

    def mark_as_delivered(self, request, queryset):
        queryset.update(status="delivered")
        self.message_user(request, f"{queryset.count()} orders marked as delivered.")

    mark_as_delivered.short_description = "Mark as Delivered"

    def mark_as_paid(self, request, queryset):
        """Mark order as paid"""
        updated = queryset.update(payment_status="paid")
        self.message_user(request, f"{updated} orders marked as paid.")
    
    mark_as_paid.short_description = "Mark as Paid"

    def mark_as_cancelled(self, request, queryset):
        """Mark order as cancelled and restore stock"""
        restored_count = 0
        for order in queryset:
            if order.status == 'cancelled':
                continue
                
            # Restore stock for each order item
            for item in order.items.all():
                if item.product:
                    # Try to find and restore to variant
                    if item.variant_name:
                        # Try to find variant by name
                        variant = ProductVariant.objects.filter(
                            product=item.product,
                            name=item.variant_name,
                            is_active=True
                        ).first()
                        
                        # If not found by name, try to find by parsing size and color
                        if not variant:
                            parts = item.variant_name.replace(' / ', '/').split('/')
                            if len(parts) >= 2:
                                color_part = parts[0].strip()
                                size_part = parts[1].strip() if len(parts) > 1 else ''
                                variant = ProductVariant.objects.filter(
                                    product=item.product,
                                    color__iexact=color_part,
                                    size__iexact=size_part,
                                    is_active=True
                                ).first()
                        
                        if variant:
                            variant.quantity += item.quantity
                            variant.save()
                            restored_count += 1
                    else:
                        # Restore to product directly if no variant
                        item.product.quantity += item.quantity
                        item.product.save()
                        restored_count += 1
            
            # Update order status
            order.status = 'cancelled'
            order.cancelled_at = timezone.now()
            order.cancellation_reason = 'Cancelled by admin'
            order.save()
        
        self.message_user(
            request, 
            f"{queryset.count()} orders cancelled. Stock restored for {restored_count} items."
        )
    
    mark_as_cancelled.short_description = "Mark as Cancelled & Restore Stock"


@admin.register(ShippingAddress)
class ShippingAddressAdmin(ModelAdmin):
    list_display = ["user", "full_name", "city", "state", "country", "is_default"]
    list_filter = ["country", "state"]
    search_fields = ["user__username", "full_name", "address", "city"]


@admin.register(NewsletterSubscriber)
class NewsletterSubscriberAdmin(ModelAdmin):
    list_display = ["email", "is_active", "subscribed_at"]
    list_filter = ["is_active"]
    search_fields = ["email"]
    actions = ["make_active", "make_inactive"]

    def make_active(self, request, queryset):
        queryset.update(is_active=True)

    make_active.short_description = "Mark as Active"

    def make_inactive(self, request, queryset):
        queryset.update(is_active=False)

    make_inactive.short_description = "Mark as Inactive"


@admin.register(ContactInquiry)
class ContactInquiryAdmin(ModelAdmin):
    list_display = ["name", "email", "subject", "is_read", "created_at"]
    list_filter = ["is_read"]
    search_fields = ["name", "email", "subject", "message"]
    actions = ["mark_as_read"]

    def mark_as_read(self, request, queryset):
        queryset.update(is_read=True)

    mark_as_read.short_description = "Mark as Read"


@admin.register(SiteSetting)
class SiteSettingAdmin(ModelAdmin):
    fieldsets = (
        ('General Settings', {
            'fields': ('site_name', 'site_description', 'logo', 'favicon', 'email', 'phone', 'address')
        }),
        ('Social Media', {
            'fields': ('facebook_url', 'twitter_url', 'instagram_url', 'pinterest_url', 'youtube_url')
        }),
        ('Payment Settings - JazzCash/EasyPaisa', {
            'fields': ('jazzcash_account', 'jazzcash_merchant_id', 'jazzcash_password'),
            'classes': ('collapse',)
        }),
        ('Payment Settings - Bank Transfer', {
            'fields': ('bank_account_name', 'bank_account_number', 'bank_name', 'bank_ifsc'),
            'classes': ('collapse',)
        }),
        ('Shipping Settings', {
            'fields': ('free_shipping_threshold',)
        }),
    )

    def has_add_permission(self, request):
        return not SiteSetting.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
    

@admin.register(HomeSlider)
class HomeSliderAdmin(ModelAdmin):
    list_display = ['title', 'order', 'is_active', 'text_position', 'created_at', 'preview_image']
    list_filter = ['is_active', 'text_position', 'created_at']
    search_fields = ['title', 'subtitle']
    list_editable = ['order', 'is_active']
    
    fieldsets = (
        ('Slide Content', {
            'fields': ('title', 'subtitle', 'button_text')
        }),
        ('Images', {
            'fields': ('image', 'mobile_image'),
            'description': 'Recommended desktop image size: 1920x800px. Mobile image optional.'
        }),
        ('Links & Positioning', {
            'fields': ('button_link', 'linked_category', 'linked_product', 'text_position', 'text_color', 'overlay_opacity')
        }),
        ('Display Settings', {
            'fields': ('order', 'is_active')
        }),
    )
    
    def preview_image(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-height: 50px; max-width: 100px;" />', obj.image.url)
        return "-"
    preview_image.short_description = "Preview"
    
    class Media:
        css = {
            'all': ('unfold/css/custom.css',)
        }