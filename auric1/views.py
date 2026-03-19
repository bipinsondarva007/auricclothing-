from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, UserChangeForm
from django.contrib.auth import login, logout, authenticate
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from datetime import timedelta

from .models import Product, Order, OrderItem
from .forms import CustomUserCreationForm

# ================== PUBLIC VIEWS ==================
def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, "Registration successful! Please log in.")
            return redirect('login')
        else:
            print("REGISTRATION ERRORS:", form.errors)
            messages.error(request, "Please correct the errors below.")
    else:
        form = CustomUserCreationForm()
    return render(request, 'auric1/register.html', {'form': form})

def user_login(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                next_page = request.GET.get('next') or request.POST.get('next') or 'home'
                return redirect(next_page)
        messages.error(request, "Invalid username or password.")
    else:
        form = AuthenticationForm()
    return render(request, 'auric1/login.html', {'form': form})

def user_logout(request):
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect('login')

# ================== PROTECTED VIEWS ==================

def home(request):
    products = Product.objects.all()[:8]
    return render(request, 'auric1/home.html', {'products': products})

@login_required
def shop(request):
    category = request.GET.get('category')
    if category and category != 'all':
        products = Product.objects.filter(category=category)
    else:
        products = Product.objects.all()
    return render(request, 'auric1/shop.html', {'products': products, 'current_category': category})

@login_required
def product_detail(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    return render(request, 'auric1/product_detail.html', {'product': product})

@login_required
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    quantity = int(request.POST.get('quantity', 1))
    size = request.POST.get('size')
    cart = request.session.get('cart', [])
    found = False
    for item in cart:
        if item['product_id'] == product_id and item.get('size') == size:
            item['quantity'] += quantity
            found = True
            break
    if not found:
        cart.append({
            'product_id': product_id,
            'name': product.name,
            'price': str(product.price),
            'quantity': quantity,
            'size': size,
        })
    request.session['cart'] = cart
    messages.success(request, f'{product.name} ({size}) added to cart.')
    return redirect('cart_view')

@login_required
def buy_now(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    quantity = int(request.POST.get('quantity', 1))
    size = request.POST.get('size')
    cart = request.session.get('cart', [])
    found = False
    for item in cart:
        if item['product_id'] == product_id and item.get('size') == size:
            item['quantity'] += quantity
            found = True
            break
    if not found:
        cart.append({
            'product_id': product_id,
            'name': product.name,
            'price': str(product.price),
            'quantity': quantity,
            'size': size,
        })
    request.session['cart'] = cart
    return redirect('checkout')

@login_required
def cart_view(request):
    cart = request.session.get('cart', [])
    total = sum(float(item['price']) * item['quantity'] for item in cart)
    return render(request, 'auric1/cart.html', {'cart': cart, 'total': total})

@login_required
def remove_from_cart(request, product_id):
    size = request.GET.get('size')
    cart = request.session.get('cart', [])
    cart = [item for item in cart if not (item['product_id'] == product_id and item.get('size') == size)]
    request.session['cart'] = cart
    messages.info(request, 'Item removed from cart.')
    return redirect('cart_view')

@login_required
def checkout(request):
    cart = request.session.get('cart', [])
    if not cart:
        return redirect('cart_view')
    total = sum(float(item['price']) * item['quantity'] for item in cart)
    return render(request, 'auric1/checkout.html', {'cart': cart, 'total': total})

@login_required
def place_order(request):
    if request.method == 'POST':
        cart = request.session.get('cart', [])
        address = request.session.get('address')
        if not cart or not address:
            return redirect('checkout')
        total = sum(float(item['price']) * item['quantity'] for item in cart)
        est_delivery = timezone.now().date() + timedelta(days=7)
        order = Order.objects.create(
            user=request.user,
            customer_name=address['name'],
            customer_email=address['email'],
            customer_phone=address['phone'],
            customer_address=address['address'],
            total_amount=total,
            payment_method=request.POST.get('payment_method'),
            payment_status='pending',
            order_status='pending',
            estimated_delivery_date=est_delivery,
        )
        for item in cart:
            OrderItem.objects.create(
                order=order,
                product_id=item['product_id'],
                quantity=item['quantity'],
                size=item.get('size', ''),
            )
        request.session['cart'] = []
        if 'address' in request.session:
            del request.session['address']
        subject = f"Order Confirmation #{order.id}"
        message = f"""
        Dear {order.customer_name},
        Thank you for your order! Your order #{order.id} has been placed successfully.
        Order Details:
        Total Amount: ₹{order.total_amount}
        Payment Method: {order.get_payment_method_display()}
        Estimated Delivery: {order.estimated_delivery_date}
        We will notify you once your order ships.
        Thanks for shopping with AURIC!
        """
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [order.customer_email],
            fail_silently=False,
        )
        if request.POST.get('payment_method') == 'online':
            request.session['pending_order_id'] = order.id
            return redirect('mock_payment')
        else:
            messages.success(request, 'Order placed successfully! You will pay on delivery.')
            return redirect('order_confirmation', order_id=order.id)
    return redirect('checkout')

@login_required
def mock_payment(request):
    order_id = request.session.get('pending_order_id')
    if not order_id:
        return redirect('cart_view')
    try:
        order = Order.objects.get(id=order_id)
    except Order.DoesNotExist:
        return redirect('cart_view')
    return render(request, 'auric1/mock_payment.html', {'order': order})

@login_required
def payment_success(request):
    order_id = request.session.get('pending_order_id')
    if order_id:
        try:
            order = Order.objects.get(id=order_id)
            order.payment_status = 'paid'
            order.order_status = 'confirmed'
            order.save()
            request.session['cart'] = []
            request.session.pop('pending_order_id', None)
            messages.success(request, 'Payment successful! Your order is confirmed.')
            return redirect('order_confirmation', order_id=order.id)
        except Order.DoesNotExist:
            pass
    return redirect('shop')

@login_required
def payment_cancel(request):
    order_id = request.session.get('pending_order_id')
    if order_id:
        try:
            order = Order.objects.get(id=order_id)
            order.order_status = 'cancelled'
            order.save()
        except Order.DoesNotExist:
            pass
        request.session.pop('pending_order_id', None)
        messages.warning(request, 'Payment was cancelled.')
    return redirect('cart_view')

@login_required
def order_confirmation(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    return render(request, 'auric1/order_confirmation.html', {'order': order})

@login_required
def profile(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'auric1/profile.html', {'orders': orders})

@login_required
def update_cart_item(request, product_id):
    if request.method == 'POST':
        action = request.POST.get('action')
        size = request.POST.get('size')
        cart = request.session.get('cart', [])
        for item in cart:
            if item['product_id'] == product_id and item.get('size') == size:
                if action == 'inc':
                    item['quantity'] += 1
                elif action == 'dec' and item['quantity'] > 1:
                    item['quantity'] -= 1
                break
        request.session['cart'] = cart
    return redirect('cart_view')

@login_required
def save_address(request):
    if request.method == 'POST':
        request.session['address'] = {
            'name': request.POST.get('name'),
            'email': request.POST.get('email'),
            'phone': request.POST.get('phone'),
            'address': request.POST.get('address'),
        }
        return redirect('payment_page')
    return redirect('checkout')

@login_required
def payment_page(request):
    cart = request.session.get('cart', [])
    address = request.session.get('address')
    if not cart or not address:
        return redirect('checkout')
    total = sum(float(item['price']) * item['quantity'] for item in cart)
    return render(request, 'auric1/payment_page.html', {
        'cart': cart,
        'total': total,
        'address': address,
    })

@login_required
def edit_profile(request):
    if request.method == 'POST':
        form = UserChangeForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully.')
            return redirect('profile')
    else:
        form = UserChangeForm(instance=request.user)
    return render(request, 'auric1/edit_profile.html', {'form': form})