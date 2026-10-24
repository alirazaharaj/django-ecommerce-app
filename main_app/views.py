from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Avg, Count, Min, Max
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import JsonResponse
from django.contrib.auth import logout
from django.template.loader import render_to_string
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from datetime import date
from django.utils import timezone
from django.contrib.auth.hashers import check_password, make_password
import hashlib
from django.urls import reverse
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


@login_required
def custom_logout(request):
    """Custom logout function"""
    logout(request)
    messages.success(request, "You have been successfully logged out!")
    return redirect('home')

def home(request):
    """Home page with dynamic data"""
    from django.db.models import Avg, Count
    
    # Get site settings
    site_settings = SiteSetting.load()

    # Get categories for navigation
    categories = Category.objects.filter(is_active=True, parent=None)

    # Get cart for the current user/session
    cart = get_cart(request)

    # New Arrivals - Women Products (with review annotations)
    women_category = Category.objects.filter(
        name__iexact="Women", is_active=True
    ).first()
    if women_category:
        women_products = Product.objects.filter(
            status="active", new_arrival=True, category=women_category
        ).annotate(
            avg_rating=Avg('reviews__rating'),
            review_count=Count('reviews')
        )[:10]
    else:
        women_products = Product.objects.filter(status="active", new_arrival=True).annotate(
            avg_rating=Avg('reviews__rating'),
            review_count=Count('reviews')
        )[:10]

    # Men Products (with review annotations)
    men_category = Category.objects.filter(name__iexact="Men", is_active=True).first()
    if men_category:
        men_products = Product.objects.filter(
            status="active", new_arrival=True, category=men_category
        ).annotate(
            avg_rating=Avg('reviews__rating'),
            review_count=Count('reviews')
        )[:10]
    else:
        men_products = Product.objects.filter(status="active", new_arrival=True).annotate(
            avg_rating=Avg('reviews__rating'),
            review_count=Count('reviews')
        )[:10]

    # Sale Products (with review annotations)
    sale_products = Product.objects.filter(status="active", on_sale=True).annotate(
        avg_rating=Avg('reviews__rating'),
        review_count=Count('reviews')
    )[:10]

    # Featured Products (with review annotations)
    featured_products = Product.objects.filter(status="active", featured=True).annotate(
        avg_rating=Avg('reviews__rating'),
        review_count=Count('reviews')
    )[:6]

    # Collection categories (categories with images for collection box slider)
    collection_categories = Category.objects.filter(
        is_active=True, image__isnull=False
    )[:6]

    # If no categories with images, get parent categories
    if not collection_categories:
        collection_categories = Category.objects.filter(is_active=True, parent=None)[:6]

    # Brands for logo slider
    brands = Brand.objects.filter(is_active=True)[:6]

    # Get cart count for header
    cart_count = 0
    if cart:
        cart_count = cart.total_items 

    context = {
        "site_settings": site_settings,
        "categories": categories,
        "women_products": women_products,
        "men_products": men_products,
        "sale_products": sale_products,
        "featured_products": featured_products,
        "collection_categories": collection_categories,
        "brands": brands,
        "cart": cart,
        "cart_count": cart_count,
        'sliders': HomeSlider.objects.filter(is_active=True).order_by('order'),
    }
    return render(request, "index.html", context)

def shop(request):
    """Shop page with filtering and pagination"""
    # Get filter parameters
    category_slug = request.GET.get("category")
    brand_slug = request.GET.get("brand")
    min_price = request.GET.get("min_price")
    max_price = request.GET.get("max_price")
    search_query = request.GET.get("q")
    sort_by = request.GET.get("sort_by", "title-ascending")
    size = request.GET.get("size")
    color = request.GET.get("color")
    page = request.GET.get("page", 1)

    # Start with all active products - USE DIFFERENT NAMES for annotations
    from django.db.models import Avg, Count, F, Value
    
    products = Product.objects.filter(status="active").annotate(
        avg_rating=Avg('reviews__rating'),  # Changed from 'average_rating'
        review_count=Count('reviews')       # Changed from 'total_reviews'
    )

    # Apply category filter
    if category_slug:
        products = products.filter(
            Q(category__slug=category_slug) | Q(category__parent__slug=category_slug)
        )

    # Apply brand filter
    if brand_slug:
        products = products.filter(brand__slug=brand_slug)

    # Apply price range
    if min_price:
        products = products.filter(price__gte=min_price)
    if max_price:
        products = products.filter(price__lte=max_price)

    # Apply size filter
    if size:
        products = products.filter(
            variants__size__iexact=size, variants__is_active=True
        )

    # Apply color filter
    if color:
        products = products.filter(
            variants__color__iexact=color, variants__is_active=True
        )

    # Apply search
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query)
            | Q(description__icontains=search_query)
            | Q(sku__icontains=search_query)
            | Q(category__name__icontains=search_query)
            | Q(brand__name__icontains=search_query)
            | Q(tags__name__icontains=search_query)
        ).distinct()

    # Apply sorting - UPDATED with rating sort option using annotation names
    sort_mapping = {
        "title-ascending": "name",
        "title-descending": "-name",
        "price-ascending": "price",
        "price-descending": "-price",
        "best-selling": "-best_selling",  
        "created-descending": "-created_at",
        "created-ascending": "created_at",
        "rating-descending": "-avg_rating",  # Use annotation name
        "rating-ascending": "avg_rating",     # Use annotation name
    }

    if sort_by in sort_mapping:
        # Handle null values for rating (products without reviews go to the end)
        if sort_by in ["rating-descending", "rating-ascending"]:
            from django.db.models import F
            if sort_by == "rating-descending":
                products = products.order_by(F('avg_rating').desc(nulls_last=True))
            else:
                products = products.order_by(F('avg_rating').asc(nulls_last=True))
        else:
            products = products.order_by(sort_mapping[sort_by])

    # Pagination
    paginator = Paginator(products, 12)
    try:
        products_page = paginator.page(page)
    except PageNotAnInteger:
        products_page = paginator.page(1)
    except EmptyPage:
        products_page = paginator.page(paginator.num_pages)

    # Get all categories for sidebar
    categories = Category.objects.filter(is_active=True, parent=None)

    # Get all brands for sidebar
    brands = Brand.objects.filter(is_active=True)

    # Get all available sizes
    sizes = (
        ProductVariant.objects.filter(is_active=True)
        .exclude(size="")
        .values_list("size", flat=True)
        .distinct()
    )

    # Get all available colors
    colors = (
        ProductVariant.objects.filter(is_active=True)
        .exclude(color="")
        .values_list("color", flat=True)
        .distinct()
    )

    # Get popular products - USE DIFFERENT NAMES for annotations
    popular_products = Product.objects.filter(
        status="active", featured=True
    ).annotate(
        avg_rating=Avg('reviews__rating'),
        review_count=Count('reviews')
    )[:4]

    # Get price range
    price_range = Product.objects.filter(status="active").aggregate(
        min_price=Min("price"), max_price=Max("price")
    )

    # Get cart for the current user/session
    cart = get_cart(request)

    view = request.GET.get('view', 'grid')

    context = {
        "products": products_page,
        "categories": categories,
        "brands": brands,
        "sizes": sizes,
        "colors": colors,
        "popular_products": popular_products,
        "price_range": price_range,
        "cart": cart,
        "current_filters": {
            "category": category_slug,
            "brand": brand_slug,
            "min_price": min_price,
            "max_price": max_price,
            "sort_by": sort_by,
            "size": size,
            "color": color,
            "search": search_query,
        },
        "view": view, 
        "cart_count": get_cart_count(request),
        "site_settings": SiteSetting.load(),
    }
    return render(request, "shop.html", context)


def product_detail(request, slug):
    """Product detail page - only primary image and color images from variants"""
    product = get_object_or_404(Product, slug=slug, status="active")
    
    # Get product images - ONLY primary + color images (no hover, no variant product images)
    product_images = []
    
    # Add primary image only
    if product.primary_image:
        product_images.append({
            'url': product.primary_image.url,
            'alt': product.name,
            'type': 'primary'
        })
    
    # Get product variants
    variants = product.variants.filter(is_active=True)
    
    # Track processed color images to avoid duplicates
    processed_color_images = set()
    
    # Add ONLY color images from variants (NOT variant product images)
    for variant in variants:
        if variant.color_image and variant.color_image.url:
            # Check if this color image is already added
            if variant.color_image.url not in processed_color_images:
                processed_color_images.add(variant.color_image.url)
                product_images.append({
                    'url': variant.color_image.url,
                    'alt': f"{product.name} - {variant.color} Color",
                    'type': 'color',
                    'color': variant.color
                })
    
    # Get variant colors and sizes
    colors = variants.exclude(color="").values_list("color", flat=True).distinct()
    sizes = variants.exclude(size="").values_list("size", flat=True).distinct()
    
    # Build colors with swatch data
    colors_with_swatch = []
    for color in colors:
        variant = variants.filter(color=color).first()
        if variant:
            colors_with_swatch.append({
                'name': color,
                'color_code': variant.color_code,
                'color_image': variant.color_image.url if variant.color_image else None,
            })
    
    # Build sizes with availability
    sizes_with_availability = []
    for size in sizes:
        # Check if size is in stock across any variant
        has_stock = variants.filter(size=size, quantity__gt=0).exists()
        sizes_with_availability.append({
            'name': size,
            'in_stock': has_stock
        })
    
    # Get approved reviews with annotations
    from django.db.models import Avg, Count
    reviews = product.reviews.filter(is_approved=True)
    avg_rating = reviews.aggregate(Avg('rating'))['rating__avg'] or 0
    review_count = reviews.count()
    
    # Check if in wishlist
    in_wishlist = False
    if request.user.is_authenticated:
        in_wishlist = Wishlist.objects.filter(
            user=request.user, product=product
        ).exists()
    
    # Check if in compare list
    in_compare = False
    if request.user.is_authenticated:
        in_compare = CompareList.objects.filter(
            user=request.user, product=product
        ).exists()
    
    # Get related products
    related_products = Product.objects.filter(
        category=product.category, status="active"
    ).exclude(id=product.id).annotate(
        avg_rating=Avg('reviews__rating'),
        review_count=Count('reviews')
    )[:10]
    
    # Get recently viewed products from session
    recently_viewed = []
    if "recently_viewed" in request.session:
        recently_viewed_ids = request.session["recently_viewed"]
        recently_viewed = Product.objects.filter(
            id__in=recently_viewed_ids, status="active"
        ).exclude(id=product.id).annotate(
            avg_rating=Avg('reviews__rating'),
            review_count=Count('reviews')
        )[:8]
    
    # Add current product to recently viewed
    if "recently_viewed" not in request.session:
        request.session["recently_viewed"] = []
    
    if product.id not in request.session["recently_viewed"]:
        request.session["recently_viewed"].insert(0, product.id)
        request.session["recently_viewed"] = request.session["recently_viewed"][:20]
        request.session.modified = True
    categories = Category.objects.filter(is_active=True, parent=None)
    
    context = {
        "product": product,
        "product_images": product_images, 
        "variants": variants,
        "colors": colors,
        "colors_with_swatch": colors_with_swatch,
        "sizes": sizes,
        "sizes_with_availability": sizes_with_availability,
        "reviews": reviews,
        "avg_rating": avg_rating,
        "review_count": review_count,
        "in_wishlist": in_wishlist,
        "in_compare": in_compare,
        "related_products": related_products,
        "recently_viewed": recently_viewed,
        "site_settings": SiteSetting.load(),
        "categories": categories, 
        "cart_count": get_cart_count(request),
    }
    return render(request, "product.html", context)

def add_to_cart(request):
    """Add product to cart with variant handling"""
    if request.method == "POST":
        product_id = request.POST.get("product_id")
        variant_id = request.POST.get("variant_id")
        quantity = int(request.POST.get("quantity", 1))

        try:
            product = Product.objects.get(id=product_id, status="active")
            variant = None
            price = float(product.price)  # Default price from product
            
            # Handle variant selection
            if variant_id and variant_id != 'null' and variant_id != '':
                try:
                    variant = ProductVariant.objects.get(id=variant_id, is_active=True)
                    # Use variant price if available, otherwise use product price
                    price = float(variant.price) if variant.price else float(product.price)
                except ProductVariant.DoesNotExist:
                    pass
            else:
                # Try to get default variant
                default_variant = product.get_default_variant()
                if default_variant:
                    variant = default_variant
                    price = float(variant.price) if variant.price else float(product.price)
            
            # Check if enough stock when variant exists
            if variant and variant.quantity < quantity:
                return JsonResponse({
                    "success": False, 
                    "message": f"Only {variant.quantity} items available in stock for {variant.size} - {variant.color}"
                })
            
            # Get or create cart
            cart = get_or_create_cart(request)

            # Check if item already in cart
            cart_item = CartItem.objects.filter(
                cart=cart, product=product, variant=variant
            ).first()

            if cart_item:
                new_quantity = cart_item.quantity + quantity
                if variant and variant.quantity < new_quantity:
                    return JsonResponse({
                        "success": False, 
                        "message": f"Only {variant.quantity} items available in stock"
                    })
                cart_item.quantity = new_quantity
                cart_item.price = price
                cart_item.save()
            else:
                CartItem.objects.create(
                    cart=cart,
                    product=product,
                    variant=variant,
                    quantity=quantity,
                    price=price,  # Ensure price is always set
                )

            return JsonResponse({
                "success": True,
                "cart_count": cart.total_items,
                "cart_total": str(cart.subtotal),
                "message": f"{product.name} added to cart."
            })

        except ProductVariant.DoesNotExist:
            return JsonResponse({"success": False, "message": "Variant not found"})
        except Product.DoesNotExist:
            return JsonResponse({"success": False, "message": "Product not found"})
        except Exception as e:
            return JsonResponse({"success": False, "message": str(e)})

    return JsonResponse({"success": False, "message": "Invalid request"})


def update_cart(request):
    """Update cart item quantity"""
    if request.method == "POST":
        item_id = request.POST.get("item_id")
        quantity = int(request.POST.get("quantity", 1))

        try:
            cart_item = CartItem.objects.get(id=item_id)
            cart = cart_item.cart

            if quantity > 0:
                cart_item.quantity = quantity
                cart_item.save()
            else:
                cart_item.delete()

            return JsonResponse(
                {
                    "success": True,
                    "cart_count": cart.total_items,
                    "cart_subtotal": str(cart.subtotal),
                    "item_total": str(cart_item.item_total) if quantity > 0 else "0",
                }
            )

        except CartItem.DoesNotExist:
            return JsonResponse({"success": False, "message": "Cart item not found"})

    return JsonResponse({"success": False, "message": "Invalid request"})


def remove_from_cart(request):
    """Remove item from cart"""
    if request.method == "POST":
        item_id = request.POST.get("item_id")

        try:
            cart_item = CartItem.objects.get(id=item_id)
            cart = cart_item.cart
            cart_item.delete()

            return JsonResponse(
                {
                    "success": True,
                    "cart_count": cart.total_items,
                    "cart_subtotal": str(cart.subtotal),
                }
            )

        except CartItem.DoesNotExist:
            return JsonResponse({"success": False, "message": "Cart item not found"})

    return JsonResponse({"success": False, "message": "Invalid request"})


def cart(request):
    """Cart page"""
    cart = get_cart(request)
    categories = Category.objects.filter(is_active=True, parent=None)   
    
    context = {
        "cart": cart,
        "cart_count": get_cart_count(request),
        "categories": categories, 
        "site_settings": SiteSetting.load(),  
    }
    return render(request, "cart.html", context)


@login_required
def add_to_wishlist(request, product_id):
    """Add product to wishlist"""
    product = get_object_or_404(Product, id=product_id)

    wishlist_item, created = Wishlist.objects.get_or_create(
        user=request.user, product=product
    )

    if created:
        messages.success(request, f"{product.name} added to wishlist.")
    else:
        messages.info(request, f"{product.name} already in your wishlist.")

    return redirect(request.META.get("HTTP_REFERER", "home"))


@login_required
def remove_from_wishlist(request, product_id):
    """Remove product from wishlist"""
    product = get_object_or_404(Product, id=product_id)

    Wishlist.objects.filter(user=request.user, product=product).delete()
    messages.success(request, f"{product.name} removed from wishlist.")

    return redirect(request.META.get("HTTP_REFERER", "home"))


@login_required
def add_to_compare(request, product_id):
    """Add product to compare list"""
    product = get_object_or_404(Product, id=product_id)

    # Limit compare to 5 products
    compare_count = CompareList.objects.filter(user=request.user).count()
    if compare_count >= 5:
        messages.warning(request, "You can compare up to 5 products at a time.")
        return redirect(request.META.get("HTTP_REFERER", "home"))

    compare_item, created = CompareList.objects.get_or_create(
        user=request.user, product=product
    )

    if created:
        messages.success(request, f"{product.name} added to compare list.")
    else:
        messages.info(request, f"{product.name} already in your compare list.")

    return redirect(request.META.get("HTTP_REFERER", "home"))


@login_required
def remove_from_compare(request, product_id):
    """Remove product from compare list"""
    product = get_object_or_404(Product, id=product_id)

    CompareList.objects.filter(user=request.user, product=product).delete()
    messages.success(request, f"{product.name} removed from compare list.")

    return redirect("compare")


@login_required
def compare(request):
    """Compare products page"""
    import json
    compare_items = CompareList.objects.filter(user=request.user).select_related('product')
    categories = Category.objects.filter(is_active=True, parent=None) 
    
    # Build product data for template
    compare_products = []
    for item in compare_items:
        product = item.product
        compare_products.append({
            'id': product.id,
            'name': product.name,
            'slug': product.slug,
            'price': float(product.price),
            'old_price': float(product.old_price) if product.old_price else None,
            'primary_image': product.primary_image.url if product.primary_image else '',
            'description': product.description or '',
            'short_description': (product.additional_info or product.description or '')[:200],
            'is_in_stock': product.is_in_stock,
            'quantity': product.quantity,
            'avg_rating': float(getattr(product, 'avg_rating', 0)) or float(product.average_rating or 0),
            'review_count': product.total_reviews or 0,
            'url': product.get_absolute_url(),
        })
    
    # Get cart for the current user/session
    cart = get_cart(request)
    
    context = {
        "compare_items": compare_items,
        "compare_products_json": json.dumps(compare_products),
        "cart": cart,
        "cart_count": get_cart_count(request),
        "categories": categories,
        "site_settings": SiteSetting.load(),
    }
    return render(request, "compare.html", context)

@login_required
def get_compare_items(request):
    """AJAX endpoint to get compare items as JSON"""
    compare_items = CompareList.objects.filter(user=request.user).select_related('product')
    
    items_data = []
    for item in compare_items:
        product = item.product
        items_data.append({
            'id': product.id,
            'name': product.name,
            'slug': product.slug,
            'price': float(product.price),
            'old_price': float(product.old_price) if product.old_price else None,
            'primary_image': product.primary_image.url if product.primary_image else '',
            'description': product.description,
            'short_description': product.additional_info or product.description[:200],
            'is_in_stock': product.is_in_stock,
            'quantity': product.quantity,
            'avg_rating': float(product.avg_rating) if hasattr(product, 'avg_rating') else 0,
            'review_count': product.total_reviews or 0,
            'url': product.get_absolute_url(),
        })
    
    return JsonResponse({
        'success': True,
        'items': items_data,
        'count': len(items_data)
    })


@login_required
def remove_from_compare_ajax(request):
    """AJAX endpoint to remove product from compare list"""
    if request.method == 'POST':
        product_id = request.POST.get('product_id')
        
        if product_id:
            CompareList.objects.filter(user=request.user, product_id=product_id).delete()
            return JsonResponse({'success': True, 'message': 'Product removed from compare'})
        
        return JsonResponse({'success': False, 'message': 'Product ID required'})
    
    return JsonResponse({'success': False, 'message': 'Invalid request method'})


@login_required
def checkout(request):
    """Checkout page with immediate stock deduction"""
    cart = get_cart(request)

    if not cart or cart.items.count() == 0:
        messages.warning(request, "Your cart is empty.")
        return redirect("cart")
    
    # Check stock before checkout
    for cart_item in cart.items.all():
        if cart_item.variant:
            if cart_item.variant.quantity < cart_item.quantity:
                messages.error(
                    request, 
                    f"{cart_item.product.name} ({cart_item.variant.size} - {cart_item.variant.color}) only has {cart_item.variant.quantity} items in stock."
                )
                return redirect("cart")
    
    site_settings = SiteSetting.load()
    
    # Handle AJAX POST request (for order placement)
    if request.method == "POST" and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        try:
            # Get form data from POST
            first_name = request.POST.get('first_name', '')
            last_name = request.POST.get('last_name', '')
            email = request.POST.get('email', '')
            phone = request.POST.get('phone', '')
            address = request.POST.get('address', '')
            city = request.POST.get('city', '')
            state = request.POST.get('state', '')
            country = request.POST.get('country', '')
            zip_code = request.POST.get('zip_code', '')
            notes = request.POST.get('notes', '')
            payment_method = request.POST.get('payment_method', 'bank_transfer')
            
            # Validate required fields
            required_fields = [first_name, last_name, email, phone, address, city, state, country, zip_code]
            if not all(required_fields):
                return JsonResponse({
                    'success': False,
                    'message': 'Please fill in all required fields'
                }, status=400)
            
            # Calculate totals
            subtotal = float(cart.subtotal)
            shipping_cost = 0 if subtotal >= float(site_settings.free_shipping_threshold) else 10.00
            tax = 0
            total = subtotal + shipping_cost + tax
            
            # Create order
            order = Order.objects.create(
                user=request.user,
                first_name=first_name,
                last_name=last_name,
                email=email,
                phone=phone,
                address=address,
                city=city,
                state=state,
                country=country,
                zip_code=zip_code,
                subtotal=subtotal,
                shipping_cost=shipping_cost,
                tax=tax,
                total=total,
                notes=notes,
                status='pending',
                payment_status='pending'
            )
            
            # Create order items and DEDUCT STOCK IMMEDIATELY
            for cart_item in cart.items.all():
                # Deduct stock from variant
                if cart_item.variant:
                    cart_item.variant.quantity -= cart_item.quantity
                    cart_item.variant.save()
                
                OrderItem.objects.create(
                    order=order,
                    product=cart_item.product,
                    product_name=cart_item.product.name,
                    variant_name=cart_item.variant.name if cart_item.variant else '',
                    quantity=cart_item.quantity,
                    price=float(cart_item.price),
                    total=float(cart_item.item_total)
                )
            
            # Mark cart as ordered
            cart.is_ordered = True
            cart.save()
            
            # Prepare response data
            response_data = {
                'success': True,
                'message': 'Order placed successfully!',
                'redirect_url': reverse('order_confirmation', args=[order.id]),
                'order_id': order.id,
                'payment_method': payment_method,
            }
            
            # Add payment details if needed
            if payment_method == 'jazzcash' and site_settings.jazzcash_account:
                response_data['jazzcash_number'] = site_settings.jazzcash_account
            elif payment_method == 'bank_transfer':
                response_data['bank_details'] = {
                    'account_name': site_settings.bank_account_name or 'Belle Store',
                    'account_number': site_settings.bank_account_number or '1234567890',
                    'bank_name': site_settings.bank_name or 'Bank of America',
                    'ifsc': site_settings.bank_ifsc or 'BOFA123456'
                }
            
            return JsonResponse(response_data)
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return JsonResponse({
                'success': False,
                'message': f'Error placing order: {str(e)}'
            }, status=500)
    
    # Handle regular POST request (fallback)
    elif request.method == "POST":
        try:
            first_name = request.POST.get('first_name')
            last_name = request.POST.get('last_name')
            email = request.POST.get('email')
            phone = request.POST.get('phone')
            address = request.POST.get('address')
            city = request.POST.get('city')
            state = request.POST.get('state')
            country = request.POST.get('country')
            zip_code = request.POST.get('zip_code')
            notes = request.POST.get('notes', '')
            
            # Validate required fields
            if not all([first_name, last_name, email, phone, address, city, state, country, zip_code]):
                messages.error(request, 'Please fill in all required fields')
                return redirect('checkout')
            
            # Calculate totals
            subtotal = float(cart.subtotal)
            shipping_cost = 0 if subtotal >= float(site_settings.free_shipping_threshold) else 10.00
            tax = 0
            total = subtotal + shipping_cost + tax
            
            # Create order
            order = Order.objects.create(
                user=request.user,
                first_name=first_name,
                last_name=last_name,
                email=email,
                phone=phone,
                address=address,
                city=city,
                state=state,
                country=country,
                zip_code=zip_code,
                subtotal=subtotal,
                shipping_cost=shipping_cost,
                tax=tax,
                total=total,
                notes=notes,
                status='pending',
                payment_status='pending'
            )
            
            # Create order items and DEDUCT STOCK IMMEDIATELY
            for cart_item in cart.items.all():
                # Deduct stock from variant
                if cart_item.variant:
                    cart_item.variant.quantity -= cart_item.quantity
                    cart_item.variant.save()
                
                OrderItem.objects.create(
                    order=order,
                    product=cart_item.product,
                    product_name=cart_item.product.name,
                    variant_name=cart_item.variant.name if cart_item.variant else '',
                    quantity=cart_item.quantity,
                    price=cart_item.price,
                    total=cart_item.item_total
                )
            
            # Mark cart as ordered
            cart.is_ordered = True
            cart.save()
            
            messages.success(request, 'Order placed successfully!')
            return redirect('order_confirmation', order_id=order.id)
            
        except Exception as e:
            messages.error(request, f'Error placing order: {str(e)}')
            return redirect('checkout')
    categories = Category.objects.filter(is_active=True, parent=None)  
    # GET request - show checkout page
    context = {
        "cart": cart,
        "cart_count": get_cart_count(request),
        "site_settings": site_settings,
        "categories": categories, 
    }
    return render(request, "checkout.html", context)




@login_required
def order_confirmation(request, order_id):
    """Order confirmation page"""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    site_settings = SiteSetting.load()
    
    context = {
        "order": order,
        "cart_count": get_cart_count(request),
        "site_settings": site_settings,
    }
    return render(request, "order_confirmation.html", context)

def subscribe_newsletter(request):
    """Newsletter subscription"""
    if request.method == "POST":
        email = request.POST.get("EMAIL")

        if email:
            subscriber, created = NewsletterSubscriber.objects.get_or_create(
                email=email
            )

            if created:
                return JsonResponse(
                    {"success": True, "message": "Thank you for subscribing!"}
                )
            else:
                return JsonResponse(
                    {"success": True, "message": "You are already subscribed."}
                )

    return JsonResponse({"success": False, "message": "Invalid request"})

@login_required
def wishlist(request):
    """Wishlist page"""
    wishlist_items = Wishlist.objects.filter(user=request.user).select_related('product')
    cart = get_cart(request)
    categories = Category.objects.filter(is_active=True, parent=None)   
    
    context = {
        "wishlist_items": wishlist_items,
        "cart": cart,
        "cart_count": get_cart_count(request),
        "site_settings": SiteSetting.load(),
        "categories": categories,   
    }
    return render(request, "wishlist.html", context)


@login_required
def remove_from_wishlist_ajax(request):
    """Remove product from wishlist via AJAX"""
    if request.method == "POST":
        product_id = request.POST.get("product_id")
        
        if product_id:
            deleted, _ = Wishlist.objects.filter(user=request.user, product_id=product_id).delete()
            if deleted:
                return JsonResponse({"success": True, "message": "Product removed from wishlist"})
            else:
                return JsonResponse({"success": False, "message": "Product not found in wishlist"})
        
        return JsonResponse({"success": False, "message": "Product ID required"})
    
    return JsonResponse({"success": False, "message": "Invalid request method"})

def contact_us(request):
    """Contact us page"""
    if request.method == "POST" and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        name = request.POST.get("name")
        email = request.POST.get("email")
        phone = request.POST.get("phone", "")
        subject = request.POST.get("subject", "General Inquiry")
        message = request.POST.get("message")

        if name and email and message:
            ContactInquiry.objects.create(
                name=name, email=email, phone=phone, subject=subject, message=message
            )
            return JsonResponse({"success": True, "message": "Thank you for your message. We will get back to you soon!"})
        else:
            return JsonResponse({"success": False, "message": "Please fill all required fields."})
    
    elif request.method == "POST":
        # Handle non-AJAX POST
        name = request.POST.get("name")
        email = request.POST.get("email")
        phone = request.POST.get("phone", "")
        subject = request.POST.get("subject", "General Inquiry")
        message = request.POST.get("message")

        if name and email and message:
            ContactInquiry.objects.create(
                name=name, email=email, phone=phone, subject=subject, message=message
            )
            messages.success(request, "Thank you for your message. We will get back to you soon!")
        else:
            messages.error(request, "Please fill all required fields.")

        return redirect("contact_us")
    cart = get_cart(request)
    categories = Category.objects.filter(is_active=True, parent=None) 
    context = {
        "cart": cart,
        "cart_count": get_cart_count(request),
        "site_settings": SiteSetting.load(),
        "categories": categories, 
    }
    return render(request, "contact_us.html", context)

def product_search(request):
    """AJAX product search"""
    query = request.GET.get("q", "")

    if query:
        products = (
            Product.objects.filter(
                Q(name__icontains=query)
                | Q(description__icontains=query)
                | Q(sku__icontains=query)
                | Q(category__name__icontains=query)
                | Q(brand__name__icontains=query)
            )
            .filter(status="active")
            .distinct()[:10]
        )

        results = []
        for product in products:
            results.append(
                {
                    "id": product.id,
                    "name": product.name,
                    "price": str(product.price),
                    "old_price": str(product.old_price) if product.old_price else None,
                    "image": product.primary_image.url if product.primary_image else "",
                    "url": product.get_absolute_url(),
                }
            )

        return JsonResponse({"results": results})

    return JsonResponse({"results": []})


def quick_view_product(request, product_id):
    """Quick view product with only primary image and color images from variants"""
    product = get_object_or_404(Product, id=product_id, status="active")

    # Get color variants with their images
    color_variants = []
    color_sizes_data = {}
    variant_images = []
    size_colors_data = {}
    variant_by_size_color = {}
    
    # Store ONLY color images (not variant product images)
    color_images = []  # Store ONLY color images
    processed_colors = set()  # To avoid duplicate color images
    
    variants = product.variants.filter(is_active=True)
    
    # Build data structures for dynamic filtering
    for variant in variants:
        size = variant.size if variant.size else 'One Size'
        color = variant.color if variant.color else 'Default'
        
        # Store variant by size+color combination
        key = f"{size}|{color}"
        variant_by_size_color[key] = {
            'id': variant.id,
            'price': str(variant.price) if variant.price else str(product.price),
            'quantity': variant.quantity,
            'in_stock': variant.quantity > 0,
            'color_image': variant.color_image.url if variant.color_image else None,
            'size': size,
            'color': color
        }
        
        # Add ONLY color image to color_images (avoid duplicates)
        if variant.color_image and variant.color_image.url:
            color_key = f"{color}_{variant.color_image.url}"
            if color_key not in processed_colors:
                processed_colors.add(color_key)
                color_images.append({
                    'url': variant.color_image.url,
                    'alt': f"{product.name} - {color} Color",
                    'color': color,
                    'size': size,
                    'type': 'color_image'
                })
        
        # Build colors by size
        if size not in size_colors_data:
            size_colors_data[size] = []
        
        color_exists = any(c['color'] == color for c in size_colors_data[size])
        if not color_exists:
            size_colors_data[size].append({
                'color': color,
                'color_code': variant.color_code,
                'color_image': variant.color_image.url if variant.color_image else None,
                'in_stock': variant.quantity > 0,
                'variant_id': variant.id,
            })
        
        # Collect color info for color_variants
        color_info = {
            'color': color,
            'color_code': variant.color_code,
            'color_image': variant.color_image.url if variant.color_image else None,
            'price': str(variant.price) if variant.price else str(product.price),
            'variant_id': variant.id,
        }
        
        # Avoid duplicates in color_variants
        if not any(v['color'] == color for v in color_variants):
            color_variants.append(color_info)
    
    # Prepare images - ONLY Color Images (NOT primary image - it's sent separately)
    all_images = []
    
    # Add ONLY color images (no primary, no hover, no variant product images)
    for c_img in color_images:
        all_images.append(c_img)
    
    # Get all unique sizes sorted
    all_sizes = sorted(size_colors_data.keys())
    
    # Get reviews
    reviews = product.reviews.filter(is_approved=True)
    avg_rating = reviews.aggregate(Avg('rating'))['rating__avg'] or 0
    review_count = reviews.count()
    
    data = {
        'id': product.id,
        'name': product.name,
        'sku': product.sku,
        'price': str(product.price),
        'old_price': str(product.old_price) if product.old_price else None,
        'description': product.description,
        'short_description': product.additional_info or product.description[:200],
        'primary_image': product.primary_image.url if product.primary_image else '',  # Primary image sent separately
        'images': all_images,  # Now contains ONLY color images (no duplication)
        'color_variants': color_variants,
        'sizes_by_color': color_sizes_data,
        'colors_by_size': size_colors_data,
        'variant_by_size_color': variant_by_size_color,
        'all_sizes': all_sizes,
        'stock_status': product.stock_status,
        'in_stock': product.is_in_stock,
        'quantity': product.quantity,
        'avg_rating': round(avg_rating, 1),
        'review_count': review_count,
        'url': product.get_absolute_url(),
    }

    return JsonResponse(data)

# Helper functions
def get_or_create_cart(request):
    """Get or create a cart for the user/session"""
    cart = None

    if request.user.is_authenticated:
        cart, created = Cart.objects.get_or_create(user=request.user, is_ordered=False)
    else:
        session_id = request.session.session_key
        if not session_id:
            request.session.create()
            session_id = request.session.session_key

        cart, created = Cart.objects.get_or_create(
            session_id=session_id, is_ordered=False
        )

    return cart


def get_cart(request):
    """Get current cart"""
    cart = None

    if request.user.is_authenticated:
        cart = Cart.objects.filter(user=request.user, is_ordered=False).first()
    else:
        session_id = request.session.session_key
        if session_id:
            cart = Cart.objects.filter(session_id=session_id, is_ordered=False).first()

    return cart


def get_cart_count(request):
    """Get cart item count"""
    cart = get_cart(request)
    if cart:
        return cart.total_items
    return 0


# Static pages
def about_us(request):
    """About Us page"""
    cart = get_cart(request)
    categories = Category.objects.filter(is_active=True, parent=None)   
    
    context = {
        "cart": cart,
        "cart_count": get_cart_count(request),
        "site_settings": SiteSetting.load(),
        "categories": categories,  
    }
    return render(request, "about_us.html", context)

def faqs(request):
    """FAQs page"""
    cart = get_cart(request)
    categories = Category.objects.filter(is_active=True, parent=None)   
    
    context = {
        "cart": cart,
        "cart_count": get_cart_count(request),
        "site_settings": SiteSetting.load(),
        "categories": categories,  
    }
    return render(request, "faqs.html", context)


def get_variant_sizes(request):
    """Get available sizes for a product color"""
    product_id = request.GET.get('product_id')
    color = request.GET.get('color')
    
    if not product_id or not color:
        return JsonResponse({'sizes': []})
    
    variants = ProductVariant.objects.filter(
        product_id=product_id, 
        color__iexact=color, 
        is_active=True
    )
    
    sizes = []
    for v in variants:
        if v.size:
            sizes.append({
                'name': v.size, 
                'in_stock': v.quantity > 0,
                'variant_id': v.id
            })
    
    return JsonResponse({'sizes': sizes})


def get_variant_id(request):
    """Get variant ID for specific color and size combination"""
    product_id = request.GET.get('product_id')
    color = request.GET.get('color')
    size = request.GET.get('size')
    
    if not all([product_id, color, size]):
        return JsonResponse({'variant_id': None, 'price': None})
    
    variant = ProductVariant.objects.filter(
        product_id=product_id, 
        color__iexact=color, 
        size__iexact=size, 
        is_active=True
    ).first()
    
    return JsonResponse({
        'variant_id': variant.id if variant else None, 
        'price': str(variant.price) if variant and variant.price else None
    })

def submit_review(request):
    """Submit product review (AJAX)"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid request method'}, status=400)
    
    product_id = request.POST.get('product_id')
    name = request.POST.get('name')
    email = request.POST.get('email')
    title = request.POST.get('title')
    body = request.POST.get('body')
    rating = request.POST.get('rating')
    
    # Validation
    if not all([product_id, name, email, title, body, rating]):
        return JsonResponse({'success': False, 'message': 'All fields are required'})
    
    try:
        product = get_object_or_404(Product, id=product_id)
        rating = int(rating)
        
        if rating < 1 or rating > 5:
            return JsonResponse({'success': False, 'message': 'Rating must be between 1 and 5'})
        
        # Create review
        review = Review.objects.create(
            product=product,
            user=request.user if request.user.is_authenticated else None,
            name=name,
            email=email,
            title=title,
            body=body,
            rating=rating,
            is_approved=True  # Auto-approve for now
        )
        
        # Update product average rating
        from django.db.models import Avg
        avg_rating = Review.objects.filter(product=product, is_approved=True).aggregate(Avg('rating'))['rating__avg']
        review_count = Review.objects.filter(product=product, is_approved=True).count()
        
        product.average_rating = avg_rating or 0
        product.total_reviews = review_count
        product.save(update_fields=['average_rating', 'total_reviews'])
        
        return JsonResponse({
            'success': True,
            'message': 'Review submitted successfully!',
            'avg_rating': float(avg_rating or 0),
            'review_count': review_count
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


def get_cart_data(request):
    """AJAX endpoint to get cart data for mini cart update"""
    
    cart = get_cart(request)
    cart_count = get_cart_count(request)
    subtotal = cart.subtotal if cart else 0
    
    # Build the mini cart HTML directly
    if cart and cart.items.exists():
        cart_items_html = ''
        for item in cart.items.all()[:5]:
            cart_items_html += f'''
            <li class="item" id="cart-item-{item.id}">
                <a class="product-image" href="{item.product.get_absolute_url()}">
                    <img src="{item.product.primary_image.url if item.product.primary_image else '/static/images/product-images/default.jpg'}" alt="{item.product.name}" />
                </a>
                <div class="product-details">
                    <a href="#" class="remove" onclick="removeCartItem(this, {item.id}); return false;">
                        <i class="anm anm-times-l" aria-hidden="true"></i>
                    </a>
                    <a class="pName" href="{item.product.get_absolute_url()}">{item.product.name}</a>
                    {f'<div class="variant-cart">{item.variant.name}</div>' if item.variant else ''}
                    <div class="wrapQtyBtn">
                        <div class="qtyField">
                            <span class="label">Qty:</span>
                            <a class="qtyBtn minus" href="javascript:void(0);" onclick="updateCartItem(this, {item.id}, 'minus')">
                                <i class="fa anm anm-minus-r" aria-hidden="true"></i>
                            </a>
                            <input type="text" value="{item.quantity}" class="product-form__input qty" id="cart-qty-{item.id}" readonly>
                            <a class="qtyBtn plus" href="javascript:void(0);" onclick="updateCartItem(this, {item.id}, 'plus')">
                                <i class="fa anm anm-plus-r" aria-hidden="true"></i>
                            </a>
                        </div>
                    </div>
                    <div class="priceRow">
                        <div class="product-price">
                            <span class="money">₨{item.price}</span>
                        </div>
                    </div>
                </div>
            </li>
            '''
        
        full_html = f'''
        <ul class="mini-products-list">
            {cart_items_html}
        </ul>
        <div class="total">
            <div class="total-in">
                <span class="label">Cart Subtotal:</span>
                <span class="product-price"><span class="money">₨{subtotal}</span></span>
            </div>
            <div class="buttonSet text-center">
                <a href="/cart/" class="btn btn-secondary btn--small">View Cart</a>
                <a href="/checkout/" class="btn btn-secondary btn--small">Checkout</a>
            </div>
        </div>
        '''
    else:
        full_html = '<div class="text-center p-3"><p>Your cart is empty</p></div>'
    
    return JsonResponse({
        'cart_items_html': full_html,
        'cart_count': cart_count,
        'subtotal': float(subtotal),
        'success': True
    })


def calculate_shipping(request):
    """Calculate shipping cost (demo)"""
    subtotal = float(request.GET.get('subtotal', 0))
    # Free shipping over ₨199
    if subtotal >= 199:
        shipping_cost = 0
    else:
        shipping_cost = 10.00
    
    return JsonResponse({
        'shipping_cost': shipping_cost,
        'free_shipping_threshold': 199,
        'remaining_for_free': max(0, 199 - subtotal)
    })


def user_login(request):
    """User login page"""
    if request.user.is_authenticated:
        return redirect('home')
    
    cart = get_cart(request)
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            
            # Merge guest cart with user cart
            session_id = request.session.session_key
            if session_id:
                guest_cart = Cart.objects.filter(session_id=session_id, is_ordered=False).first()
                if guest_cart:
                    user_cart, created = Cart.objects.get_or_create(user=user, is_ordered=False)
                    for item in guest_cart.items.all():
                        existing_item = CartItem.objects.filter(
                            cart=user_cart, product=item.product, variant=item.variant
                        ).first()
                        if existing_item:
                            existing_item.quantity += item.quantity
                            existing_item.save()
                        else:
                            item.cart = user_cart
                            item.save()
                    guest_cart.delete()
            
            messages.success(request, f'Welcome back, {user.username}!')
            
            next_url = request.GET.get('next', 'home')
            return redirect(next_url)
        else:
            messages.error(request, 'Invalid email or password. Please try again.')
    
    categories = Category.objects.filter(is_active=True, parent=None) 
    context = {
        "cart": cart,
        "cart_count": get_cart_count(request),
        "site_settings": SiteSetting.load(),
        "categories": categories,
    }
    return render(request, "login.html", context)


def user_register(request):
    """User registration page"""
    if request.user.is_authenticated:
        return redirect('home')
    
    cart = get_cart(request)
    
    if request.method == 'POST':
        username = request.POST.get('email')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        name = request.POST.get('name', '')
        
        if password != confirm_password:
            messages.error(request, 'Passwords do not match!')
            return render(request, "register.html", context)
        
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Email already registered!')
            return render(request, "register.html", context)
        
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=name
        )
        
        login(request, user)
        messages.success(request, f'Account created successfully! Welcome, {user.username}!')
        return redirect('home')
    
    categories = Category.objects.filter(is_active=True, parent=None)
    context = {
        "cart": cart,
        "cart_count": get_cart_count(request),
        "site_settings": SiteSetting.load(),
        "categories": categories,
    }
    return render(request, "register.html", context)



def track_order(request):
    """Track order page"""
    cart = get_cart(request)
    order = None
    error_message = None
    
    if request.method == 'POST':
        order_number = request.POST.get('order_number', '').strip()
        email_or_phone = request.POST.get('email_or_phone', '').strip()
        
        # Try to find order by order number and email/phone
        order = Order.objects.filter(order_number=order_number).first()
        
        if order:
            # Check if email or phone matches
            if order.email.lower() == email_or_phone.lower() or order.phone == email_or_phone:
                # Order found
                context = {
                    'cart': cart,
                    'cart_count': get_cart_count(request),
                    'site_settings': SiteSetting.load(),
                    'order': order,
                    'tracking_status': get_order_tracking_status(order),
                    'status_history': get_order_status_history(order),
                }
                return render(request, 'track_order_result.html', context)
            else:
                error_message = 'Invalid order number or email/phone combination. Please try again.'
        else:
            error_message = 'Order not found. Please check your order number and try again.'
    
    
    categories = Category.objects.filter(is_active=True, parent=None)
    context = {
        'cart': cart,
        'cart_count': get_cart_count(request),
        'site_settings': SiteSetting.load(), 
        "categories": categories, 
        'error_message': error_message,
        'order': order,
    }
    return render(request, 'track_order.html', context)


def get_order_tracking_status(order):
    """Get tracking status with timeline"""
    statuses = []
    
    # Order Placed
    statuses.append({
        'status': 'Order Placed',
        'date': order.created_at,
        'completed': True,
        'icon': 'fa-check-circle',
        'color': '#4CAF50',
        'description': f'Your order #{order.order_number} has been placed successfully.'
    })
    
    # Payment Confirmed (if paid)
    if order.payment_status == 'paid':
        statuses.append({
            'status': 'Payment Confirmed',
            'date': order.updated_at if order.payment_status == 'paid' else None,
            'completed': True,
            'icon': 'fa-credit-card',
            'color': '#4CAF50',
            'description': 'Your payment has been confirmed.'
        })
    elif order.payment_status == 'pending':
        statuses.append({
            'status': 'Payment Pending',
            'date': None,
            'completed': False,
            'icon': 'fa-clock',
            'color': '#FF9800',
            'description': 'Awaiting payment confirmation.'
        })
    
    # Processing
    if order.status == 'processing' or order.status == 'shipped' or order.status == 'delivered':
        statuses.append({
            'status': 'Processing',
            'date': order.updated_at if order.status in ['processing', 'shipped', 'delivered'] else None,
            'completed': order.status in ['processing', 'shipped', 'delivered'],
            'icon': 'fa-cogs',
            'color': '#4CAF50' if order.status in ['processing', 'shipped', 'delivered'] else '#9E9E9E',
            'description': 'Your order is being processed and prepared for shipping.'
        })
    elif order.status == 'cancelled':
        statuses.append({
            'status': 'Processing',
            'date': None,
            'completed': False,
            'icon': 'fa-ban',
            'color': '#F44336',
            'description': 'Order processing was cancelled.'
        })
    else:
        statuses.append({
            'status': 'Processing',
            'date': None,
            'completed': False,
            'icon': 'fa-clock',
            'color': '#9E9E9E',
            'description': 'Awaiting order processing.'
        })
    
    # Shipped
    if order.status == 'shipped' or order.status == 'delivered':
        statuses.append({
            'status': 'Shipped',
            'date': order.updated_at if order.status in ['shipped', 'delivered'] else None,
            'completed': order.status in ['shipped', 'delivered'],
            'icon': 'fa-truck',
            'color': '#4CAF50' if order.status in ['shipped', 'delivered'] else '#9E9E9E',
            'description': f'Your order has been shipped.{f" Tracking: {order.tracking_number}" if order.tracking_number else ""}'
        })
    elif order.status == 'cancelled':
        statuses.append({
            'status': 'Shipped',
            'date': None,
            'completed': False,
            'icon': 'fa-ban',
            'color': '#F44336',
            'description': 'Shipping was cancelled.'
        })
    else:
        statuses.append({
            'status': 'Shipped',
            'date': None,
            'completed': False,
            'icon': 'fa-clock',
            'color': '#9E9E9E',
            'description': 'Awaiting shipment.'
        })
    
    # Out for Delivery
    if order.status == 'delivered':
        statuses.append({
            'status': 'Out for Delivery',
            'date': order.delivered_at if order.delivered_at else order.updated_at,
            'completed': True,
            'icon': 'fa-truck-moving',
            'color': '#4CAF50',
            'description': 'Your order is out for delivery.'
        })
    elif order.status == 'cancelled':
        statuses.append({
            'status': 'Out for Delivery',
            'date': None,
            'completed': False,
            'icon': 'fa-ban',
            'color': '#F44336',
            'description': 'Delivery was cancelled.'
        })
    else:
        statuses.append({
            'status': 'Out for Delivery',
            'date': None,
            'completed': False,
            'icon': 'fa-clock',
            'color': '#9E9E9E',
            'description': 'Awaiting delivery.'
        })
    
    # Delivered
    if order.status == 'delivered':
        statuses.append({
            'status': 'Delivered',
            'date': order.delivered_at if order.delivered_at else order.updated_at,
            'completed': True,
            'icon': 'fa-home',
            'color': '#4CAF50',
            'description': 'Your order has been delivered successfully.'
        })
    elif order.status == 'cancelled':
        statuses.append({
            'status': 'Delivered',
            'date': None,
            'completed': False,
            'icon': 'fa-ban',
            'color': '#F44336',
            'description': 'Delivery cancelled.'
        })
    else:
        statuses.append({
            'status': 'Delivered',
            'date': None,
            'completed': False,
            'icon': 'fa-clock',
            'color': '#9E9E9E',
            'description': 'Awaiting delivery.'
        })
    
    # Cancelled
    if order.status == 'cancelled':
        statuses.append({
            'status': 'Cancelled',
            'date': order.cancelled_at if order.cancelled_at else order.updated_at,
            'completed': True,
            'icon': 'fa-ban',
            'color': '#F44336',
            'description': order.cancellation_reason or 'Your order has been cancelled.'
        })
    
    return statuses


def get_order_status_history(order):
    """Get order status change history"""
    history = []
    
    # Add order placed
    history.append({
        'status': 'Order Placed',
        'date': order.created_at,
        'icon': 'fa-shopping-cart'
    })
    
    # Add payment status change
    if order.payment_status == 'paid':
        history.append({
            'status': 'Payment Confirmed',
            'date': order.updated_at,
            'icon': 'fa-credit-card'
        })
    
    # Add status changes
    if order.status == 'processing':
        history.append({
            'status': 'Order Processing',
            'date': order.updated_at,
            'icon': 'fa-cogs'
        })
    elif order.status == 'shipped':
        history.append({
            'status': 'Order Shipped',
            'date': order.updated_at,
            'icon': 'fa-truck'
        })
    elif order.status == 'delivered':
        history.append({
            'status': 'Order Delivered',
            'date': order.delivered_at if order.delivered_at else order.updated_at,
            'icon': 'fa-home'
        })
    elif order.status == 'cancelled':
        history.append({
            'status': 'Order Cancelled',
            'date': order.cancelled_at if order.cancelled_at else order.updated_at,
            'icon': 'fa-ban'
        })
    
    return history


def cancel_order_tracking(request, order_number):
    """Cancel order from tracking page"""
    if request.method == 'POST':
        email_or_phone = request.POST.get('email_or_phone', '').strip()
        reason = request.POST.get('cancellation_reason', 'Customer requested cancellation')
        
        order = Order.objects.filter(order_number=order_number).first()
        
        if order and (order.email.lower() == email_or_phone.lower() or order.phone == email_or_phone):
            if order.status == 'cancelled':
                return JsonResponse({'success': False, 'message': 'Order is already cancelled.'})
            
            if order.status in ['shipped', 'delivered']:
                return JsonResponse({'success': False, 'message': 'Cannot cancel order that has already been shipped or delivered.'})
            
            # Restore stock for each order item
            for item in order.items.all():
                if item.product:
                    # Try to find variant by size and color from variant_name
                    variant = None
                    if item.variant_name:
                        # Parse variant_name (format: "Black / XL" or similar)
                        # Try to find variant by product and name
                        variant = ProductVariant.objects.filter(
                            product=item.product,
                            name=item.variant_name,
                            is_active=True
                        ).first()
                        
                        # If not found by name, try to find by parsing size and color
                        if not variant:
                            # Try to split by common separators
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
                    else:
                        # If no variant found, try to restore to product directly
                        item.product.quantity += item.quantity
                        item.product.save()
            
            # Cancel order
            order.status = 'cancelled'
            order.cancelled_at = timezone.now()
            order.cancellation_reason = reason
            order.save()
            
            return JsonResponse({
                'success': True, 
                'message': 'Your order has been cancelled successfully.',
                'redirect_url': reverse('track_order_result', args=[order.order_number])
            })
        
        return JsonResponse({'success': False, 'message': 'Invalid order information.'})
    
    return JsonResponse({'success': False, 'message': 'Invalid request method.'})

def track_order_result(request, order_number):
    """View order tracking result"""
    cart = get_cart(request)
    order = get_object_or_404(Order, order_number=order_number)
    categories = Category.objects.filter(is_active=True, parent=None)
    
    context = {
        'cart': cart,
        'cart_count': get_cart_count(request),
        'site_settings': SiteSetting.load(),
        "categories": categories, 
        'order': order,
        'tracking_status': get_order_tracking_status(order),
        'status_history': get_order_status_history(order),
    }
    return render(request, 'track_order_result.html', context)

@login_required
def my_account(request):
    """User account page"""
    cart = get_cart(request)
    categories = Category.objects.filter(is_active=True, parent=None)
    
    context = {
        'cart': cart,
        'cart_count': get_cart_count(request),
        'site_settings': SiteSetting.load(),
        "categories": categories, 
    }
    return render(request, 'my_account.html', context)