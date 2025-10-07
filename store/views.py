# store/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from .models import Product, Category, Cart, CartItem, Order, OrderItem
from .forms import CheckoutForm, AddToCartForm


def home(request):
    featured_products = Product.objects.filter(available=True)[:8]
    categories = Category.objects.all()[:6]
    context = {
        'featured_products': featured_products,
        'categories': categories,
    }
    return render(request, 'store/home.html', context)


def product_list(request):
    products = Product.objects.filter(available=True)
    categories = Category.objects.all()
    
    # Filtrage par catégorie
    category_slug = request.GET.get('category')
    if category_slug:
        category = get_object_or_404(Category, slug=category_slug)
        products = products.filter(category=category)
    
    # Recherche
    query = request.GET.get('q')
    if query:
        products = products.filter(
            Q(name__icontains=query) | Q(description__icontains=query)
        )
    
    context = {
        'products': products,
        'categories': categories,
    }
    return render(request, 'store/product_list.html', context)


def product_detail(request, slug):
    product = get_object_or_404(Product, slug=slug, available=True)
    form = AddToCartForm()
    related_products = Product.objects.filter(
        category=product.category, 
        available=True
    ).exclude(id=product.id)[:4]
    
    context = {
        'product': product,
        'form': form,
        'related_products': related_products,
    }
    return render(request, 'store/product_detail.html', context)


def get_or_create_cart(request):
    """Récupère ou crée un panier pour l'utilisateur"""
    if request.user.is_authenticated:
        cart, created = Cart.objects.get_or_create(user=request.user)
    else:
        session_key = request.session.session_key
        if not session_key:
            request.session.create()
            session_key = request.session.session_key
        cart, created = Cart.objects.get_or_create(session_key=session_key)
    return cart


def add_to_cart(request, slug):
    product = get_object_or_404(Product, slug=slug)
    cart = get_or_create_cart(request)
    
    if request.method == 'POST':
        form = AddToCartForm(request.POST)
        if form.is_valid():
            quantity = form.cleaned_data['quantity']
            
            cart_item, created = CartItem.objects.get_or_create(
                cart=cart,
                product=product,
                defaults={'quantity': quantity}
            )
            
            if not created:
                cart_item.quantity += quantity
                cart_item.save()
            
            messages.success(request, f"{product.name} ajouté au panier !")
            return redirect('store:cart')
    
    return redirect('store:product_detail', slug=slug)


def cart_view(request):
    cart = get_or_create_cart(request)
    context = {
        'cart': cart,
    }
    return render(request, 'store/cart.html', context)


def update_cart(request, item_id):
    cart_item = get_object_or_404(CartItem, id=item_id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'increase':
            cart_item.quantity += 1
            cart_item.save()
        elif action == 'decrease':
            if cart_item.quantity > 1:
                cart_item.quantity -= 1
                cart_item.save()
            else:
                cart_item.delete()
                messages.info(request, "Produit retiré du panier")
        elif action == 'remove':
            cart_item.delete()
            messages.info(request, "Produit retiré du panier")
    
    return redirect('store:cart')


@login_required
def checkout(request):
    cart = get_or_create_cart(request)
    
    if not cart.items.exists():
        messages.warning(request, "Votre panier est vide")
        return redirect('store:product_list')
    
    if request.method == 'POST':
        form = CheckoutForm(request.POST)
        if form.is_valid():
            order = form.save(commit=False)
            order.user = request.user
            order.total = cart.get_total()
            order.save()
            
            # Créer les items de commande
            for item in cart.items.all():
                OrderItem.objects.create(
                    order=order,
                    product=item.product,
                    price=item.product.price,
                    quantity=item.quantity
                )
            
            # Vider le panier
            cart.items.all().delete()
            
            messages.success(request, f"Commande #{order.id} créée avec succès !")
            return redirect('store:order_success', order_id=order.id)
    else:
        # Pré-remplir avec les infos de l'utilisateur
        initial_data = {
            'email': request.user.email,
            'phone': request.user.phone if hasattr(request.user, 'phone') else '',
        }
        form = CheckoutForm(initial=initial_data)
    
    context = {
        'form': form,
        'cart': cart,
    }
    return render(request, 'store/checkout.html', context)


@login_required
def order_success(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    context = {
        'order': order,
    }
    return render(request, 'store/order_success.html', context)


@login_required
def order_history(request):
    orders = Order.objects.filter(user=request.user)
    context = {
        'orders': orders,
    }
    return render(request, 'store/order_history.html', context)