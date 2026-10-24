from django.db import models
from django.db.models import Sum, Count, Q, F, DecimalField, Value
from django.db.models.functions import TruncDay, Coalesce
from django.utils import timezone
from datetime import timedelta
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render
from django.http import JsonResponse 
from .models import Product, Order, OrderItem, Category, Brand, ProductVariant

@staff_member_required
def admin_dashboard(request):
    """Custom admin dashboard with e-commerce metrics"""
    today = timezone.now()
    last_7_days = today - timedelta(days=7)
    last_30_days = today - timedelta(days=30)
    
    # Get counts for active catalog items
    total_products = Product.objects.filter(status='active').count()
    total_categories = Category.objects.filter(is_active=True).count()
    total_brands = Brand.objects.filter(is_active=True).count()
    total_active_items = total_products + total_categories + total_brands
    
    # Count variants that are out of stock (quantity = 0)
    out_of_stock_variants = ProductVariant.objects.filter(
        is_active=True,
        quantity=0
    ).count()
    
    # Count variants that are low stock (quantity between 1 and 5)
    low_stock_variants = ProductVariant.objects.filter(
        is_active=True,
        quantity__gte=1,
        quantity__lte=5
    ).count()
    
    # Also check products without variants
    products_without_variants_out_of_stock = Product.objects.filter(
        status='active',
        variants__isnull=True,
        quantity=0
    ).count()
    
    products_without_variants_low_stock = Product.objects.filter(
        status='active',
        variants__isnull=True,
        quantity__gte=1,
        quantity__lte=5
    ).count()
    
    out_of_stock_count = out_of_stock_variants + products_without_variants_out_of_stock
    low_stock_count = low_stock_variants + products_without_variants_low_stock
    
    # 7-Day Revenue Summary
    orders_last_7_days = Order.objects.filter(
        created_at__gte=last_7_days,
        payment_status='paid'
    )
    
    revenue_last_7_days = orders_last_7_days.aggregate(
        total=Coalesce(Sum('total', output_field=DecimalField()), Value(0, output_field=DecimalField()))
    )['total']
    
    # Daily revenue for chart
    daily_revenue = (
        Order.objects.filter(
            created_at__gte=last_7_days,
            payment_status='paid'
        )
        .annotate(day=TruncDay('created_at'))
        .values('day')
        .annotate(total=Sum('total', output_field=DecimalField()))
        .order_by('day')
    )
    
    # Prepare chart data
    chart_dates = []
    chart_revenues = []
    
    # Fill in missing dates
    for i in range(8):
        date = (today - timedelta(days=7-i)).date()
        chart_dates.append(date.strftime('%b %d'))
        
        revenue = next(
            (float(item['total']) for item in daily_revenue if item['day'].date() == date),
            0
        )
        chart_revenues.append(revenue)
    
    # Top 5 Best Selling Items (last 30 days)
    top_selling_items = (
        OrderItem.objects.filter(
            order__created_at__gte=last_30_days,
            order__payment_status='paid'
        )
        .values('product_name', 'product_id')
        .annotate(
            total_quantity=Sum('quantity'),
            total_revenue=Sum('total', output_field=DecimalField())
        )
        .order_by('-total_quantity')[:5]
    )
    
    # Get product images for top items
    for item in top_selling_items:
        try:
            product = Product.objects.get(id=item['product_id'])
            item['image_url'] = product.primary_image.url if product.primary_image else None
        except Product.DoesNotExist:
            item['image_url'] = None
    
    # Additional metrics
    total_orders = Order.objects.filter(created_at__gte=last_30_days).count()
    total_revenue_30_days = Order.objects.filter(
        created_at__gte=last_30_days,
        payment_status='paid'
    ).aggregate(
        total=Coalesce(Sum('total', output_field=DecimalField()), Value(0, output_field=DecimalField()))
    )['total']
    
    pending_orders = Order.objects.filter(status='pending').count()
    
    avg_order_value = 0
    if total_orders > 0:
        avg_order_value = float(total_revenue_30_days) / total_orders
    
    # Convert Decimal to float for JSON serialization
    revenue_last_7_days = float(revenue_last_7_days) if revenue_last_7_days else 0
    total_revenue_30_days = float(total_revenue_30_days) if total_revenue_30_days else 0
    
    # Total items in stock
    total_items_in_stock = ProductVariant.objects.filter(is_active=True).aggregate(
        total=models.Sum('quantity')
    )['total'] or 0
    
    # Add products without variants stock
    products_without_variants_stock = Product.objects.filter(
        status='active',
        variants__isnull=True
    ).aggregate(total=models.Sum('quantity'))['total'] or 0
    
    total_items_in_stock = total_items_in_stock + products_without_variants_stock
    
    context = {
        'total_items_in_stock': total_items_in_stock,
        'total_active_items': total_active_items,
        'total_products': total_products,
        'total_categories': total_categories,
        'total_brands': total_brands,
        'low_stock_count': low_stock_count,
        'out_of_stock_count': out_of_stock_count,
        'revenue_last_7_days': revenue_last_7_days,
        'chart_dates': chart_dates,
        'chart_revenues': chart_revenues,
        'top_selling_items': top_selling_items,
        'total_orders_30_days': total_orders,
        'total_revenue_30_days': total_revenue_30_days,
        'pending_orders': pending_orders,
        'avg_order_value': round(avg_order_value, 2),
    }
    
    return render(request, 'admin/dashboard.html', context)


@staff_member_required
def dashboard_ajax_data(request):
    """AJAX endpoint for dashboard data"""
    data_type = request.GET.get('type', 'revenue')
    
    if data_type == 'revenue':
        today = timezone.now()
        last_7_days = today - timedelta(days=7)
        
        daily_revenue = (
            Order.objects.filter(
                created_at__gte=last_7_days,
                payment_status='paid'
            )
            .annotate(day=TruncDay('created_at'))
            .values('day')
            .annotate(total=Sum('total', output_field=DecimalField()))
            .order_by('day')
        )
        
        chart_dates = []
        chart_revenues = []
        
        for i in range(8):
            date = (today - timedelta(days=7-i)).date()
            chart_dates.append(date.strftime('%b %d'))
            
            revenue = next(
                (float(item['total']) for item in daily_revenue if item['day'].date() == date),
                0
            )
            chart_revenues.append(revenue)
        
        return JsonResponse({
            'dates': chart_dates,
            'revenues': chart_revenues,
        })
    
    elif data_type == 'products_list':
        filter_type = request.GET.get('filter', 'all')
    
    if filter_type == 'low_stock':
        # Get variants that are low stock
        variants = ProductVariant.objects.filter(
            is_active=True,
            quantity__gte=1,
            quantity__lte=5
        ).select_related('product')
        
        products_list = []
        for variant in variants:
            product = variant.product
            image_url = None
            if product.primary_image:
                try:
                    image_url = product.primary_image.url
                except:
                    image_url = None
            
            products_list.append({
                'id': product.id,
                'name': f"{product.name} ({variant.size} - {variant.color})",
                'sku': variant.sku or product.sku,
                'quantity': variant.quantity,
                'low_stock_threshold': 5,
                'image_url': image_url,
                'is_variant': True,
                'variant_id': variant.id
            })
    elif filter_type == 'out_of_stock':
        # Get variants that are out of stock
        variants = ProductVariant.objects.filter(
            is_active=True,
            quantity=0
        ).select_related('product')
        
        products_list = []
        for variant in variants:
            product = variant.product
            image_url = None
            if product.primary_image:
                try:
                    image_url = product.primary_image.url
                except:
                    image_url = None
            
            products_list.append({
                'id': product.id,
                'name': f"{product.name} ({variant.size} - {variant.color})",
                'sku': variant.sku or product.sku,
                'quantity': variant.quantity,
                'low_stock_threshold': 5,
                'image_url': image_url,
                'is_variant': True,
                'variant_id': variant.id
            })
    else:
        # Get all active products
        products = Product.objects.filter(status='active')[:20]
        products_list = []
        for product in products:
            image_url = None
            if product.primary_image:
                try:
                    image_url = product.primary_image.url
                except:
                    image_url = None
            
            products_list.append({
                'id': product.id,
                'name': product.name,
                'sku': product.sku,
                'quantity': product.total_stock,
                'low_stock_threshold': product.low_stock_threshold,
                'image_url': image_url,
                'is_variant': False,
            })
    
    return JsonResponse({
        'products': products_list,
        'count': len(products_list)
    })
    
    return JsonResponse({'error': 'Invalid request'}, status=400)


@staff_member_required
def remaining_stock_view(request):
    """View to show all products with variant stock details"""
    products = Product.objects.filter(status='active').prefetch_related('variants')
    
    # Get filter parameters
    product_id = request.GET.get('product_id')
    low_stock_only = request.GET.get('low_stock', False)
    out_of_stock_only = request.GET.get('out_of_stock', False)
    
    if product_id:
        products = products.filter(id=product_id)
    
    # Prepare stock data
    stock_data = []
    for product in products:
        variants = product.variants.filter(is_active=True)
        total_quantity = variants.aggregate(total=models.Sum('quantity'))['total'] or 0
        
        variant_details = []
        for variant in variants:
            status = 'in_stock'
            if variant.quantity == 0:
                status = 'out_of_stock'
            elif variant.quantity <= 5:
                status = 'low_stock'
            
            variant_details.append({
                'id': variant.id,
                'size': variant.size or 'N/A',
                'color': variant.color or 'N/A',
                'quantity': variant.quantity,
                'status': status,
                'price': float(variant.price) if variant.price else float(product.price),
            })
        
        # Apply filters
        if low_stock_only and total_quantity > 5:
            continue
        if out_of_stock_only and total_quantity > 0:
            continue
            
        stock_data.append({
            'id': product.id,
            'name': product.name,
            'sku': product.sku,
            'primary_image': product.primary_image.url if product.primary_image else None,
            'total_quantity': total_quantity,
            'variants': variant_details,
            'status': 'out_of_stock' if total_quantity == 0 else ('low_stock' if total_quantity <= 5 else 'in_stock'),
        })
    
    context = {
        'stock_data': stock_data,
        'total_products': len(stock_data),
        'total_items': sum(p['total_quantity'] for p in stock_data),
    }
    return render(request, 'admin/remaining_stock.html', context)

