from django.urls import path
from . import views

urlpatterns = [
    # Login page is the root
    path('', views.user_login, name='login'),

    # Home (after login)
    path('home/', views.home, name='home'),

    # Shop and products
    path('shop/', views.shop, name='shop'),
    path('product/<int:product_id>/', views.product_detail, name='product_detail'),

    # Cart actions
    path('add-to-cart/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('buy-now/<int:product_id>/', views.buy_now, name='buy_now'),
    path('remove-from-cart/<int:product_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('cart/', views.cart_view, name='cart_view'),
    path('update-cart-item/<int:product_id>/', views.update_cart_item, name='update_cart_item'),

    # Checkout & Payment
    path('checkout/', views.checkout, name='checkout'),
    path('save-address/', views.save_address, name='save_address'),
    path('payment-page/', views.payment_page, name='payment_page'),
    path('place-order/', views.place_order, name='place_order'),
    path('mock-payment/', views.mock_payment, name='mock_payment'),
    path('payment-success/', views.payment_success, name='payment_success'),
    path('payment-cancel/', views.payment_cancel, name='payment_cancel'),
    path('order-confirmation/<int:order_id>/', views.order_confirmation, name='order_confirmation'),

    # Profile
    path('profile/', views.profile, name='profile'),
    path('edit-profile/', views.edit_profile, name='edit_profile'),

    # Authentication
    path('register/', views.register, name='register'),
    path('login/', views.user_login, name='login'),   # optional alias
    path('logout/', views.user_logout, name='logout'),
]