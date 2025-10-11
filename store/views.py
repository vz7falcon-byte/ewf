from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from .models import Product, Category, Cart, CartItem, Order, OrderItem
from .forms import CheckoutForm, AddToCartForm
from django.contrib.auth import get_user_model

User = get_user_model()


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


def get_guest_user():
    """Crée ou récupère l'utilisateur invité pour les paniers anonymes"""
    guest, created = User.objects.get_or_create(
        username="guest",
        defaults={"email": "guest@example.com", "password": "!"}
    )
    return guest


def get_or_create_cart(request):
    """Récupère ou crée un panier selon que l'utilisateur est connecté ou non"""
    if request.user.is_authenticated:
        # Pour les utilisateurs connectés : UN SEUL panier par utilisateur
        # On prend celui qui existe déjà OU on en crée un nouveau
        carts = Cart.objects.filter(user=request.user)
        
        if carts.exists():
            # Prendre le premier panier (ou celui avec des items)
            cart_with_items = carts.filter(items__isnull=False).distinct().first()
            cart = cart_with_items if cart_with_items else carts.first()
            
            # Supprimer les autres paniers vides
            carts.exclude(id=cart.id).filter(items__isnull=True).delete()
        else:
            # Créer un nouveau panier
            cart = Cart.objects.create(user=request.user, session_key=None)
    else:
        # Pour les invités : panier basé sur la session
        guest_user = get_guest_user()
        session_key = request.session.session_key
        if not session_key:
            request.session.create()
            session_key = request.session.session_key
        
        cart = Cart.objects.filter(user=guest_user, session_key=session_key).first()
        if not cart:
            cart = Cart.objects.create(user=guest_user, session_key=session_key)
    
    return cart


def add_to_cart(request, slug):
    """Ajoute un produit au panier (pour utilisateurs connectés et invités)"""
    product = get_object_or_404(Product, slug=slug, available=True)
    
    # Créer ou récupérer le panier (fonctionne pour invités et connectés)
    cart = get_or_create_cart(request)
    
    # Ajouter ou mettre à jour l'article
    cart_item, created = CartItem.objects.get_or_create(
        cart=cart, 
        product=product,
        defaults={'quantity': 1}
    )
    
    if not created:
        cart_item.quantity += 1
        cart_item.save()

    messages.success(request, f"{product.name} ajouté au panier.")
    return redirect('store:cart_detail')


def cart_detail(request):
    """Affiche le détail du panier"""
    cart = get_or_create_cart(request)
    items = cart.items.select_related('product').all()
    total = cart.get_total()
    
    # Debug : afficher dans la console
    print(f"=== DEBUG CART ===")
    print(f"Cart ID: {cart.id}")
    print(f"Cart User: {cart.user.username}")
    print(f"Cart Session: {cart.session_key}")
    print(f"Request User: {request.user}")
    print(f"Is Authenticated: {request.user.is_authenticated}")
    print(f"Items count: {items.count()}")
    for item in items:
        print(f"  - {item}")
    print(f"==================")
    
    context = {
        'cart': cart,
        'items': items,
        'total': total,
    }
    return render(request, 'store/cart.html', context)


def update_cart(request, item_id):
    """Met à jour la quantité d'un article dans le panier"""
    # Récupérer le panier de l'utilisateur
    cart = get_or_create_cart(request)
    cart_item = get_object_or_404(CartItem, id=item_id, cart=cart)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'increase':
            cart_item.quantity += 1
            cart_item.save()
            messages.success(request, "Quantité augmentée.")
        elif action == 'decrease':
            if cart_item.quantity > 1:
                cart_item.quantity -= 1
                cart_item.save()
                messages.success(request, "Quantité diminuée.")
            else:
                cart_item.delete()
                messages.info(request, "Produit retiré du panier.")
        elif action == 'remove':
            cart_item.delete()
            messages.info(request, "Produit retiré du panier.")
    
    return redirect('store:cart_detail')


def remove_from_cart(request, item_id):
    """Retire un article du panier"""
    cart = get_or_create_cart(request)
    cart_item = get_object_or_404(CartItem, id=item_id, cart=cart)
    cart_item.delete()
    messages.info(request, "Produit retiré du panier.")
    return redirect('store:cart_detail')


@login_required
def checkout(request):
    """Processus de commande (nécessite une connexion)"""
    cart = get_or_create_cart(request)
    items = cart.items.select_related('product').all()
    total = cart.get_total()

    # Debug
    print(f"=== DEBUG CHECKOUT ===")
    print(f"Cart ID: {cart.id}")
    print(f"Items count: {items.count()}")
    print(f"Total: {total}")
    print(f"=====================")

    if not items.exists():
        messages.warning(request, "Votre panier est vide.")
        return redirect('store:cart_detail')

    if request.method == 'POST':
        form = CheckoutForm(request.POST)
        if form.is_valid():
            order = form.save(commit=False)
            order.user = request.user
            order.total = total
            order.save()

            # Créer les items de commande
            for item in items:
                OrderItem.objects.create(
                    order=order,
                    product=item.product,
                    price=item.product.price,
                    quantity=item.quantity
                )

            # Vider le panier
            cart.items.all().delete()

            messages.success(request, "Commande passée avec succès!")
            return redirect('store:order_success', order_id=order.id)
    else:
        form = CheckoutForm()

    context = {
        'form': form,
        'total': total,
        'items': items,
        'cart': cart,
    }
    return render(request, 'store/checkout.html', context)


@login_required
def order_success(request, order_id):
    """Page de confirmation de commande"""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    context = {
        'order': order,
    }
    return render(request, 'store/order_success.html', context)


@login_required
def order_history(request):
    """Historique des commandes de l'utilisateur"""
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    context = {
        'orders': orders,
    }
    return render(request, 'store/order_history.html', context)