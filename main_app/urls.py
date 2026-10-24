from django.urls import path
from . import views

urlpatterns = [
    # Main pages
    path("", views.home, name="home"),
    path("shop/", views.shop, name="shop"), 
    path("product/<slug:slug>/", views.product_detail, name="product_detail"),
    path("cart/", views.cart, name="cart"),
    path("compare/", views.compare, name="compare"),
    # Checkout
    path("checkout/", views.checkout, name="checkout"),
    path('order-confirmation/<int:order_id>/', views.order_confirmation, name='order_confirmation'),
    # Static pages
    path("about-us/", views.about_us, name="about_us"),
    path("contact-us/", views.contact_us, name="contact_us"),
    path("faqs/", views.faqs, name="faqs"),
    # Product actions
    path("quick-view/<int:product_id>/", views.quick_view_product, name="quick_view"),
    path("search/", views.product_search, name="product_search"), 
    path('get-variant-sizes/', views.get_variant_sizes, name='get_variant_sizes'),
    path('get-variant-id/', views.get_variant_id, name='get_variant_id'),
    path('submit-review/', views.submit_review, name='submit_review'),
    # Cart actions
    path("cart/add/", views.add_to_cart, name="add_to_cart"),
    path("cart/update/", views.update_cart, name="update_cart"),
    path("cart/remove/", views.remove_from_cart, name="remove_from_cart"),
    path('get-cart-data/', views.get_cart_data, name='get_cart_data'),
    path('calculate-shipping/', views.calculate_shipping, name='calculate_shipping'),
    # Wishlist actions
    path(
        "wishlist/add/<int:product_id>/", views.add_to_wishlist, name="add_to_wishlist"
    ),
    path(
        "wishlist/remove/<int:product_id>/",
        views.remove_from_wishlist,
        name="remove_from_wishlist",
    ),
    # Compare actions
    path("compare/get-items/", views.get_compare_items, name="get_compare_items"),
    path("compare/remove-ajax/", views.remove_from_compare_ajax, name="remove_from_compare_ajax"),
    path("compare/add/<int:product_id>/", views.add_to_compare, name="add_to_compare"),
    path(
        "compare/remove/<int:product_id>/",
        views.remove_from_compare,
        name="remove_from_compare",
    ),
    # Order
    path(
        "order-confirmation/<int:order_id>/",
        views.order_confirmation,
        name="order_confirmation",
    ),
    # Newsletter
    path("subscribe/", views.subscribe_newsletter, name="subscribe_newsletter"),
    # Whishlist
    path("wishlist/", views.wishlist, name="wishlist"),
    path("wishlist/remove-ajax/", views.remove_from_wishlist_ajax, name="remove_from_wishlist_ajax"),
    # Logout
    path('logout/', views.custom_logout, name='logout'),
    # Login and Register
    path('login/', views.user_login, name='login'),
    path('register/', views.user_register, name='register'),
    # Order Tracking
    path("track-order/", views.track_order, name="track_order"),
    path("track-order/<str:order_number>/", views.track_order_result, name="track_order_result"),
    path("cancel-order/<str:order_number>/", views.cancel_order_tracking, name="cancel_order_tracking"),
    # My account
    path("my-account/", views.my_account, name="my_account"),
]
