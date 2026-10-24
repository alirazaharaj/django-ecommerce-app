from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.urls import reverse
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.text import slugify


class Category(models.Model):
    """Product categories like Clothing, Jewellery, Shoes, etc."""

    name = models.CharField(max_length=200, unique=True)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to="categories/", blank=True, null=True)
    parent = models.ForeignKey(
        "self", on_delete=models.CASCADE, null=True, blank=True, related_name="children"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Category"
        verbose_name_plural = "Categories"
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("category_detail", kwargs={"slug": self.slug})


class Brand(models.Model):
    """Product brands like Allen Vela, Oxymat, etc."""

    name = models.CharField(max_length=200, unique=True)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    description = models.TextField(blank=True)
    logo = models.ImageField(upload_to="brands/", blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Brand"
        verbose_name_plural = "Brands"
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Tag(models.Model):
    """Product tags for filtering"""

    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True, blank=True)

    class Meta:
        verbose_name = "Tag"
        verbose_name_plural = "Tags"
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Product(models.Model):
    """Main product model"""

    STATUS_CHOICES = (
        ("draft", "Draft"),
        ("active", "Active"),
        ("inactive", "Inactive"),
    )

    STOCK_STATUS = (
        ("in_stock", "In Stock"),
        ("out_of_stock", "Out of Stock"),
        ("pre_order", "Pre Order"),
    )

    SALE_LABEL_CHOICES = (
        ("none", "None"),
        ("sale", "Sale"),
        ("new", "New"),
        ("hot", "Hot"),
        ("popular", "Popular"),
    )

    # Basic Information
    name = models.CharField(max_length=300)
    slug = models.SlugField(max_length=300, unique=True, blank=True)
    sku = models.CharField(max_length=100, unique=True)
    description = models.TextField()
    additional_info = models.TextField(
        blank=True, help_text="Additional product details"
    )

    # Pricing
    price = models.DecimalField(max_digits=10, decimal_places=2)
    old_price = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True
    )

    # Stock Management
    stock_status = models.CharField(
        max_length=20, choices=STOCK_STATUS, default="in_stock"
    )
    quantity = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    low_stock_threshold = models.IntegerField(default=5)

    # Relationships
    category = models.ForeignKey(
        Category, on_delete=models.CASCADE, related_name="products"
    )
    brand = models.ForeignKey(
        Brand, on_delete=models.SET_NULL, null=True, blank=True, related_name="products"
    )
    tags = models.ManyToManyField(Tag, blank=True, related_name="products")

    # Labels and Badges
    sale_label = models.CharField(
        max_length=20, choices=SALE_LABEL_CHOICES, default="none"
    )
    discount_percentage = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(99)],
        help_text="Enter number only (e.g., 16 for 16%)",
    )

    # Images
    primary_image = models.ImageField(upload_to="products/")
    hover_image = models.ImageField(upload_to="products/", blank=True, null=True)

    # Reviews
    total_reviews = models.IntegerField(default=0)
    average_rating = models.FloatField(default=0.0)

    # Product Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")
    featured = models.BooleanField(default=False)
    best_selling = models.BooleanField(default=False)
    new_arrival = models.BooleanField(default=False)
    on_sale = models.BooleanField(default=False)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    sale_end_date = models.DateTimeField(blank=True, null=True)

    class Meta:
        verbose_name = "Product"
        verbose_name_plural = "Products"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["slug"]),
            models.Index(fields=["sku"]),
            models.Index(fields=["status"]),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)

        # Auto-calculate discount percentage if old price is set
        if self.old_price and self.old_price > self.price:
            self.discount_percentage = int(
                ((self.old_price - self.price) / self.old_price) * 100
            )
            self.on_sale = True

        # Don't auto-update stock_status here - let it be calculated from variants
        # But ensure quantity is not negative
        if self.quantity < 0:
            self.quantity = 0
            
        super().save(*args, **kwargs)
        
        # After saving, update quantity from variants
        self.update_total_quantity()

    def update_total_quantity(self):
        """Update total quantity from all variants"""
        total = self.variants.aggregate(total=models.Sum('quantity'))['total'] or 0
        
        # Update stock status based on total quantity
        if total <= 0:
            self.stock_status = "out_of_stock"
        elif total <= self.low_stock_threshold:
            self.stock_status = "in_stock"
        else:
            self.stock_status = "in_stock"
        
        # Only save if changed (avoid recursion)
        if self.pk:
            super(Product, self).save(update_fields=['stock_status'])

    def get_default_variant(self):
        """Get the default variant (first available with stock)"""
        # Try to get is_default variant
        default = self.variants.filter(is_default=True, is_active=True).first()
        if default and default.quantity > 0:
            return default
        
        # Get any variant with stock
        in_stock = self.variants.filter(is_active=True, quantity__gt=0).first()
        if in_stock:
            return in_stock
        
        # Get any active variant
        return self.variants.filter(is_active=True).first()

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("product_detail", kwargs={"slug": self.slug})

    @property
    def is_in_stock(self):
        """Check if any variant is in stock or if product has quantity"""
        # First check if product has direct quantity
        if self.quantity > 0:
            return True
        # Then check variants
        return self.variants.filter(is_active=True, quantity__gt=0).exists()
    
    @property
    def is_low_stock(self):
        """Check if product is low stock (based on variants or direct quantity)"""
        if 0 < self.quantity <= self.low_stock_threshold:
            return True
        # Check if any variant has low stock
        return self.variants.filter(is_active=True, quantity__lte=5, quantity__gt=0).exists()

    @property
    def total_stock(self):
        """Get total stock from variants or direct quantity"""
        variant_total = self.variants.aggregate(total=models.Sum('quantity'))['total'] or 0
        if variant_total > 0:
            return variant_total
        return self.quantity
    
    @property
    def first_variant_price(self):
        """Get the lowest variant price"""
        variants = self.variants.filter(is_active=True)
        if variants.exists():
            return variants.order_by("price").first().price
        return self.price


class ProductVariant(models.Model):
    """Product variants like Size, Color"""

    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="variants"
    )
    sku = models.CharField(max_length=100, unique=True, blank=True)
    name = models.CharField(max_length=200, help_text="e.g., Black / XL, Red / M")
    color = models.CharField(max_length=50, blank=True)
    color_code = models.CharField(max_length=20, blank=True, help_text="Hex color code")
    color_image = models.ImageField(upload_to="variants/colors/", blank=True, null=True)
    size = models.CharField(max_length=20, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    quantity = models.IntegerField(default=0)
    image = models.ImageField(upload_to="variants/", blank=True, null=True)
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Product Variant"
        verbose_name_plural = "Product Variants"
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.sku:
            # Generate SKU from size and color
            size_part = self.size if self.size else "NOSIZE"
            color_part = self.color if self.color else "NOCOLOR"
            self.sku = f"{self.product.sku}-{size_part}-{color_part}"
        
        super().save(*args, **kwargs)
        
        # Update parent product quantity
        self.product.update_total_quantity()
    
    def delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)
        self.product.update_total_quantity()

    def __str__(self):
        return f"{self.product.name} - {self.name}"

    @property
    def is_in_stock(self):
        return self.quantity > 0


class Review(models.Model):
    """Product reviews"""

    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="reviews"
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    email = models.EmailField()
    title = models.CharField(max_length=200)
    body = models.TextField()
    rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    is_approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Review"
        verbose_name_plural = "Reviews"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username} - {self.product.name} - {self.rating} Stars"


class Wishlist(models.Model):
    """User wishlist"""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="wishlists")
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "product")
        verbose_name = "Wishlist"
        verbose_name_plural = "Wishlists"

    def __str__(self):
        return f"{self.user.username} - {self.product.name}"


class CompareList(models.Model):
    """Product comparison list"""

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="compare_lists"
    )
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "product")
        verbose_name = "Compare List"
        verbose_name_plural = "Compare Lists"

    def __str__(self):
        return f"{self.user.username} - {self.product.name}"


class Cart(models.Model):
    """Shopping cart"""

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, null=True, blank=True, related_name="carts"
    )
    session_id = models.CharField(max_length=200, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_ordered = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Cart"
        verbose_name_plural = "Carts"

    def __str__(self):
        return f"Cart {self.id} - {self.user.username if self.user else 'Guest'}"

    @property
    def total_items(self):
        return self.items.aggregate(total=models.Sum("quantity"))["total"] or 0

    @property
    def subtotal(self):
        return (
            self.items.aggregate(
                total=models.Sum(models.F("quantity") * models.F("price"))
            )["total"]
            or 0
        )

    @property
    def total(self):
        # Add shipping calculation logic here
        return self.subtotal


class CartItem(models.Model):
    """Cart items"""

    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    variant = models.ForeignKey(
        ProductVariant, on_delete=models.SET_NULL, null=True, blank=True
    )
    quantity = models.IntegerField(default=1, validators=[MinValueValidator(1)])
    price = models.DecimalField(max_digits=10, decimal_places=2)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Cart Item"
        verbose_name_plural = "Cart Items"

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"

    @property
    def item_total(self):
        return self.quantity * self.price


class Order(models.Model):
    """Customer orders"""

    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("processing", "Processing"),
        ("shipped", "Shipped"),
        ("delivered", "Delivered"),
        ("cancelled", "Cancelled"),
    )

    PAYMENT_STATUS = (
        ("pending", "Pending"),
        ("paid", "Paid"),
        ("failed", "Failed"),
        ("refunded", "Refunded"),
    )

    user = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="orders"
    )
    order_number = models.CharField(max_length=50, unique=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    address = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    country = models.CharField(max_length=100)
    zip_code = models.CharField(max_length=20)

    # Order Details
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=10, decimal_places=2)

    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    payment_status = models.CharField(
        max_length=20, choices=PAYMENT_STATUS, default="pending"
    )

    # Notes
    notes = models.TextField(blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Tracking and Shipping
    tracking_number = models.CharField(max_length=100, blank=True, null=True)
    tracking_company = models.CharField(max_length=100, blank=True, null=True, 
                                        choices=[('dhl', 'DHL'), ('fedex', 'FedEx'), 
                                                ('ups', 'UPS'), ('usps', 'USPS'), 
                                                ('other', 'Other')])
    estimated_delivery = models.DateField(blank=True, null=True)
    delivered_at = models.DateTimeField(blank=True, null=True)
    cancelled_at = models.DateTimeField(blank=True, null=True)
    cancellation_reason = models.TextField(blank=True)

    class Meta:
        verbose_name = "Order"
        verbose_name_plural = "Orders"
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = f"ORD-{timezone.now().strftime('%Y%m%d%H%M%S')}-{self.user.id if self.user else 'G'}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Order {self.order_number}"

    def restore_stock(self):
        """Restore stock for all items in this order"""
        for item in self.items.all():
            if item.product:
                if item.variant_name:
                    variant = ProductVariant.objects.filter(
                        product=item.product,
                        name=item.variant_name
                    ).first()
                    if variant:
                        variant.quantity += item.quantity
                        variant.save()
                else:
                    item.product.quantity += item.quantity
                    item.product.save()
    
    def deduct_stock(self):
        """Deduct stock for all items in this order"""
        for item in self.items.all():
            if item.product:
                if item.variant_name:
                    variant = ProductVariant.objects.filter(
                        product=item.product,
                        name=item.variant_name
                    ).first()
                    if variant:
                        variant.quantity -= item.quantity
                        variant.save()
                else:
                    item.product.quantity -= item.quantity
                    item.product.save()

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"


class OrderItem(models.Model):
    """Order items"""

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    product_name = models.CharField(max_length=300)
    variant_name = models.CharField(max_length=200, blank=True)
    quantity = models.IntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    total = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        verbose_name = "Order Item"
        verbose_name_plural = "Order Items"

    def __str__(self):
        return f"{self.product_name} x {self.quantity}"

    def save(self, *args, **kwargs):
        if not self.total:
            self.total = self.quantity * self.price
        super().save(*args, **kwargs)


class ShippingAddress(models.Model):
    """User shipping addresses"""

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="shipping_addresses"
    )
    full_name = models.CharField(max_length=200)
    address = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    country = models.CharField(max_length=100)
    zip_code = models.CharField(max_length=20)
    phone = models.CharField(max_length=20)
    is_default = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Shipping Address"
        verbose_name_plural = "Shipping Addresses"

    def __str__(self):
        return f"{self.full_name} - {self.address}"

    def save(self, *args, **kwargs):
        if self.is_default:
            # Set all other addresses as non-default
            ShippingAddress.objects.filter(user=self.user, is_default=True).update(
                is_default=False
            )
        super().save(*args, **kwargs)


class NewsletterSubscriber(models.Model):
    """Newsletter subscribers"""

    email = models.EmailField(unique=True)
    is_active = models.BooleanField(default=True)
    subscribed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Newsletter Subscriber"
        verbose_name_plural = "Newsletter Subscribers"

    def __str__(self):
        return self.email


class ContactInquiry(models.Model):
    """Contact form inquiries"""

    name = models.CharField(max_length=200)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    subject = models.CharField(max_length=200)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Contact Inquiry"
        verbose_name_plural = "Contact Inquiries"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} - {self.subject}"


class SiteSetting(models.Model):
    """Site-wide settings"""

    site_name = models.CharField(max_length=200, default="Belle")
    site_description = models.TextField(blank=True)
    logo = models.ImageField(upload_to="site/", blank=True, null=True)
    favicon = models.ImageField(upload_to="site/", blank=True, null=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    facebook_url = models.URLField(blank=True)
    twitter_url = models.URLField(blank=True)
    instagram_url = models.URLField(blank=True)
    pinterest_url = models.URLField(blank=True)
    youtube_url = models.URLField(blank=True)
    free_shipping_threshold = models.DecimalField(
        max_digits=10, decimal_places=2, default=199.00
    )
    # Payment Settings
    jazzcash_account = models.CharField(max_length=20, blank=True, help_text="JazzCash/EasyPaisa Account Number")
    jazzcash_merchant_id = models.CharField(max_length=50, blank=True, help_text="JazzCash Merchant ID (if using API)")
    jazzcash_password = models.CharField(max_length=100, blank=True, help_text="JazzCash Password")
    bank_account_name = models.CharField(max_length=200, blank=True, help_text="Bank Account Holder Name")
    bank_account_number = models.CharField(max_length=50, blank=True, help_text="Bank Account Number")
    bank_name = models.CharField(max_length=100, blank=True, help_text="Bank Name")
    bank_ifsc = models.CharField(max_length=20, blank=True, help_text="IFSC/IBAN Code")
    
    class Meta:
        verbose_name = "Site Setting"
        verbose_name_plural = "Site Settings"
 

    def __str__(self):
        return self.site_name

    def save(self, *args, **kwargs):
        # Ensure only one instance exists
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, created = cls.objects.get_or_create(pk=1)
        return obj




class HomeSlider(models.Model):
    """Dynamic home page slider"""
    
    POSITION_CHOICES = (
        ('left', 'Left'),
        ('center', 'Center'),
        ('right', 'Right'),
    )
    
    title = models.CharField(max_length=200, help_text="Main heading text")
    subtitle = models.CharField(max_length=300, blank=True, help_text="Subtitle text")
    button_text = models.CharField(max_length=50, blank=True, default="Shop Now", help_text="Button label")
    button_link = models.CharField(max_length=200, blank=True, default="/shop/", help_text="Button URL (e.g., /shop/, /shop/?category=men)")
    image = models.ImageField(upload_to="slider/", help_text="Slider background image")
    mobile_image = models.ImageField(upload_to="slider/mobile/", blank=True, null=True, help_text="Optional mobile-specific image")
    
    # Positioning and styling
    text_position = models.CharField(max_length=20, choices=POSITION_CHOICES, default='center')
    text_color = models.CharField(max_length=20, default="#ffffff", help_text="Text color (hex code)")
    overlay_opacity = models.IntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(100)], help_text="Dark overlay opacity (0-100)")
    
    # Ordering and status
    order = models.IntegerField(default=0, help_text="Display order (lower numbers appear first)")
    is_active = models.BooleanField(default=True, help_text="Show this slide")
    
    # Optional: link to category or product
    linked_category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True, 
        help_text="Optional: Link to specific category"
    )
    linked_product = models.ForeignKey(
        Product, on_delete=models.SET_NULL, null=True, blank=True,
        help_text="Optional: Link to specific product"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Home Slider"
        verbose_name_plural = "Home Sliders"
        ordering = ["order", "created_at"]
    
    def __str__(self):
        return self.title
    
    @property
    def get_button_url(self):
        """Get button URL from various sources"""
        if self.button_link:
            return self.button_link
        if self.linked_category:
            return reverse('shop') + f'?category={self.linked_category.slug}'
        if self.linked_product:
            return self.linked_product.get_absolute_url()
        return '#'
    
    @property
    def get_image_url(self):
        """Get the appropriate image URL (mobile or desktop)"""
        if self.mobile_image:
            return self.mobile_image.url
        return self.image.url