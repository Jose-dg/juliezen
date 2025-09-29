# 🏗️ Implementación Técnica - DaydreamShop (Arquitectura Desacoplada)

## 🎯 Principios de Diseño

### Arquitectura Desacoplada
- **Apps independientes**: Cada app no conoce a las otras
- **UUIDs**: Identificadores únicos para evitar colisiones
- **Event Bus**: Única forma de comunicación entre apps
- **Referencias por string**: No imports directos entre apps
- **Escalabilidad**: Cada app puede correr en servidor separado

## 📁 Estructura de Directorios

```

├── apps/
│   ├── core/              # Funcionalidad base
│   ├── users/             # Gestión de usuarios
│   ├── products/          # Catálogo de productos
│   ├── brands/            # Gestión de marcas
│   ├── cart/              # Carrito de compras
│   ├── ai_service/        # Servicios de IA
│   ├── scraping/          # Web scraping
│   ├── recommendations/   # Sistema de recomendaciones
│   ├── notifications/     # Sistema de notificaciones
│   └── events/            # Event Bus central
├── core/          # Configuración del proyecto
└── manage.py
```

## 📊 Modelos Desacoplados con UUIDs

### Core Models (apps/core/models.py)
```python
import uuid
from django.db import models
from django.utils import timezone

class TimeStampedModel(models.Model):
    """Modelo base con timestamps automáticos."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

class SoftDeleteModel(TimeStampedModel):
    """Modelo base con soft delete."""
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

    def soft_delete(self):
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save()

    class Meta:
        abstract = True
```

### User Model (apps/users/models.py)
```python
import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    """Modelo de usuario personalizado."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    style_preferences = models.JSONField(default=dict)
    size_profile = models.JSONField(default=dict)
    shopping_behavior = models.JSONField(default=dict)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    class Meta:
        db_table = 'users_user'

class StylePassport(models.Model):
    """Pasaporte de estilo del usuario."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_id = models.UUIDField()  # Referencia por UUID, no FK
    favorite_colors = models.JSONField(default=list)
    preferred_styles = models.JSONField(default=list)
    size_preferences = models.JSONField(default=dict)
    budget_range = models.CharField(max_length=50, blank=True)
    
    def __str__(self):
        return f"Style Passport de {self.user_id}"
```

### Brand Model (apps/brands/models.py)
```python
import uuid
from apps.core.models import TimeStampedModel
from django.db import models

class Brand(TimeStampedModel):
    """Entidad central para marcas de ropa."""
    name = models.CharField(max_length=200, unique=True)
    website_url = models.URLField(blank=True)
    api_config = models.JSONField(default=dict)
    scraping_config = models.JSONField(default=dict)
    commission_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return self.name

class BrandScrapingConfig(models.Model):
    """Configuración de scraping para cada marca."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    brand_id = models.UUIDField()  # Referencia por UUID, no FK
    base_url = models.URLField()
    selectors = models.JSONField(default=dict)
    rate_limit = models.IntegerField(default=1)
    last_scraped = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"Config de {self.brand_id}"
```

### Product Model (apps/products/models.py)
```python
import uuid
from apps.core.models import TimeStampedModel
from django.db import models
from django.contrib.postgres.fields import ArrayField

class Product(TimeStampedModel):
    """Producto principal con datos enriquecidos por IA."""
    brand_id = models.UUIDField()  # Referencia por UUID, no FK
    name = models.CharField(max_length=500)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    original_price = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    currency = models.CharField(max_length=3, default='USD')
    
    # Atributos del producto
    category = models.CharField(max_length=100)
    subcategory = models.CharField(max_length=100, blank=True)
    tags = ArrayField(models.CharField(max_length=50), default=list)
    
    # Datos de IA
    ai_description = models.TextField(blank=True)
    ai_tags = ArrayField(models.CharField(max_length=50), default=list)
    embedding_vector = models.BinaryField(null=True, blank=True)
    
    # Imágenes y variantes
    images = models.JSONField(default=list)
    variants = models.JSONField(default=dict)
    
    # Metadatos
    is_active = models.BooleanField(default=True)
    in_stock = models.BooleanField(default=True)
    stock_quantity = models.IntegerField(default=0)
    
    class Meta:
        indexes = [
            models.Index(fields=['brand_id', 'is_active']),
            models.Index(fields=['category', 'is_active']),
            models.Index(fields=['price']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.name} - {self.brand_id}"
```

### Cart Models (apps/cart/models.py)
```python
import uuid
from apps.core.models import TimeStampedModel
from django.db import models

class Cart(TimeStampedModel):
    """Carrito de compras del usuario."""
    user_id = models.UUIDField()  # Referencia por UUID, no FK
    is_active = models.BooleanField(default=True)
    
    def get_total_price(self):
        return sum(item.get_total_price() for item in self.items.all())
    
    def __str__(self):
        return f"Carrito de {self.user_id}"

class CartItem(TimeStampedModel):
    """Items del carrito de usuario."""
    cart_id = models.UUIDField()  # Referencia por UUID, no FK
    product_id = models.UUIDField()  # Referencia por UUID, no FK
    quantity = models.PositiveIntegerField(default=1)
    selected_variant = models.JSONField(default=dict)
    
    def get_total_price(self):
        # Obtener precio del producto desde el Event Bus
        # No hay FK directo, se obtiene por eventos
        return 0  # Placeholder
    
    def __str__(self):
        return f"{self.quantity}x {self.product_id}"
```

## 🔄 Event Bus Completamente Desacoplado

### Event Bus Core (apps/events/bus.py)
```python
import json
import redis
from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder
from django.utils import timezone
from typing import Dict, Any, Callable
import logging

logger = logging.getLogger(__name__)

class EventBus:
    """Event Bus completamente desacoplado usando Redis."""
    
    def __init__(self):
        self.redis_client = redis.Redis.from_url(settings.REDIS_URL)
        self.pubsub = self.redis_client.pubsub()
        self.handlers = {}
    
    def publish(self, event_type: str, event_data: Dict[str, Any]):
        """Publica un evento en el bus."""
        event = {
            'id': str(uuid.uuid4()),
            'type': event_type,
            'data': event_data,
            'timestamp': timezone.now().isoformat(),
            'version': '1.0',
            'source': 'unknown'  # Cada app define su source
        }
        
        try:
            self.redis_client.publish(
                f"events:{event_type}",
                json.dumps(event, cls=DjangoJSONEncoder)
            )
            logger.info(f"Evento publicado: {event_type} - {event['id']}")
        except Exception as e:
            logger.error(f"Error publicando evento {event_type}: {e}")
    
    def subscribe(self, event_type: str, handler: Callable):
        """Suscribe un handler a un tipo de evento."""
        if event_type not in self.handlers:
            self.handlers[event_type] = []
        self.handlers[event_type].append(handler)
        logger.info(f"Handler suscrito a {event_type}")
    
    def process_events(self):
        """Procesa eventos pendientes."""
        for event_type, handlers in self.handlers.items():
            self.pubsub.subscribe(f"events:{event_type}")
            
            for message in self.pubsub.listen():
                if message['type'] == 'message':
                    try:
                        event_data = json.loads(message['data'])
                        for handler in handlers:
                            handler(event_data)
                    except Exception as e:
                        logger.error(f"Error procesando evento: {e}")

# Instancia global del Event Bus
event_bus = EventBus()
```

### Event Handlers Desacoplados (apps/events/handlers.py)
```python
from apps.events.bus import event_bus
import logging

logger = logging.getLogger(__name__)

# User Events - No conoce otras apps
@event_bus.subscribe('user.registered')
def handle_user_registered(event_data):
    """Maneja registro de usuario."""
    try:
        user_id = event_data['data']['user_id']
        # Crear style passport inicial
        # Enviar email de bienvenida
        logger.info(f"Usuario registrado: {user_id}")
        
        # Publicar evento de follow-up
        event_bus.publish('user.style_passport_created', {
            'user_id': user_id,
            'timestamp': event_data['timestamp']
        })
    except Exception as e:
        logger.error(f"Error en user.registered: {e}")

@event_bus.subscribe('user.profile_updated')
def handle_user_profile_updated(event_data):
    """Maneja actualización de perfil."""
    try:
        user_id = event_data['data']['user_id']
        # Recalcular recomendaciones
        event_bus.publish('recommendations.user_updated', {
            'user_id': user_id,
            'timestamp': event_data['timestamp']
        })
        logger.info(f"Perfil actualizado: {user_id}")
    except Exception as e:
        logger.error(f"Error en user.profile_updated: {e}")

# Product Events - No conoce otras apps
@event_bus.subscribe('product.scraped')
def handle_product_scraped(event_data):
    """Maneja producto recién scrapeado."""
    try:
        product_id = event_data['data']['product_id']
        # Generar embeddings
        event_bus.publish('ai.embeddings_requested', {
            'product_id': product_id,
            'timestamp': event_data['timestamp']
        })
        logger.info(f"Producto scrapeado: {product_id}")
    except Exception as e:
        logger.error(f"Error en product.scraped: {e}")

@event_bus.subscribe('product.availability_changed')
def handle_product_availability_changed(event_data):
    """Maneja cambio de disponibilidad."""
    try:
        product_id = event_data['data']['product_id']
        is_available = event_data['data']['is_available']
        
        if is_available:
            # Notificar usuarios con producto en wishlist
            event_bus.publish('notifications.product_available', {
                'product_id': product_id,
                'timestamp': event_data['timestamp']
            })
        
        logger.info(f"Disponibilidad cambiada: {product_id}")
    except Exception as e:
        logger.error(f"Error en product.availability_changed: {e}")

# Cart Events - No conoce otras apps
@event_bus.subscribe('cart.item_added')
def handle_cart_item_added(event_data):
    """Maneja item agregado al carrito."""
    try:
        user_id = event_data['data']['user_id']
        product_id = event_data['data']['product_id']
        
        # Actualizar preferencias del usuario
        event_bus.publish('recommendations.user_preference_updated', {
            'user_id': user_id,
            'product_id': product_id,
            'action': 'added_to_cart',
            'timestamp': event_data['timestamp']
        })
        
        logger.info(f"Item agregado al carrito: {product_id}")
    except Exception as e:
        logger.error(f"Error en cart.item_added: {e}")

@event_bus.subscribe('cart.checkout_completed')
def handle_cart_checkout_completed(event_data):
    """Maneja checkout completado."""
    try:
        user_id = event_data['data']['user_id']
        cart_total = event_data['data']['total']
        
        # Procesar comisiones
        event_bus.publish('brands.commission_processed', {
            'user_id': user_id,
            'total': cart_total,
            'timestamp': event_data['timestamp']
        })
        
        # Actualizar historial de compras
        event_bus.publish('users.purchase_completed', {
            'user_id': user_id,
            'total': cart_total,
            'timestamp': event_data['timestamp']
        })
        
        logger.info(f"Checkout completado: {user_id}")
    except Exception as e:
        logger.error(f"Error en cart.checkout_completed: {e}")
```

### Event Publishers en Models (Sin Dependencias)
```python
# En apps/products/models.py
from apps.events.bus import event_bus

class Product(TimeStampedModel):
    # ... campos existentes ...
    
    def save(self, *args, **kwargs):
        is_new = self.pk is None
        old_stock = None
        
        if not is_new:
            try:
                old_instance = Product.objects.get(pk=self.pk)
                old_stock = old_instance.stock_quantity
            except Product.DoesNotExist:
                pass
        
        super().save(*args, **kwargs)
        
        # Publicar eventos - No conoce otras apps
        if is_new:
            event_bus.publish('product.created', {
                'product_id': str(self.id),
                'brand_id': str(self.brand_id),
                'category': self.category,
                'timestamp': timezone.now().isoformat()
            })
        else:
            # Verificar cambio de disponibilidad
            if old_stock is not None and old_stock != self.stock_quantity:
                is_available = self.stock_quantity > 0
                event_bus.publish('product.availability_changed', {
                    'product_id': str(self.id),
                    'is_available': is_available,
                    'old_stock': old_stock,
                    'new_stock': self.stock_quantity,
                    'timestamp': timezone.now().isoformat()
                })

# En apps/cart/models.py
class CartItem(TimeStampedModel):
    # ... campos existentes ...
    
    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        if is_new:
            event_bus.publish('cart.item_added', {
                'user_id': str(self.cart.user_id),
                'product_id': str(self.product_id),
                'quantity': self.quantity,
                'timestamp': timezone.now().isoformat()
            })
    
    def delete(self, *args, **kwargs):
        event_bus.publish('cart.item_removed', {
            'user_id': str(self.cart.user_id),
            'product_id': str(self.product_id),
            'timestamp': timezone.now().isoformat()
        })
        super().delete(*args, **kwargs)
```

## 🎯 API Views Completamente Desacopladas

### Product Views (apps/products/views.py)
```python
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from django_filters.rest_framework import DjangoFilterBackend
from django.core.cache import cache
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page

from .models import Product
from .serializers import ProductSerializer, ProductSearchSerializer
from .filters import ProductFilter
from apps.events.bus import event_bus

class ProductViewSet(viewsets.ModelViewSet):
    """ViewSet para productos - Completamente desacoplado."""
    queryset = Product.objects.filter(is_active=True)
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_class = ProductFilter
    
    @action(detail=False, methods=['post'])
    def search(self, request):
        """Búsqueda semántica de productos."""
        serializer = ProductSearchSerializer(data=request.data)
        if serializer.is_valid():
            query = serializer.validated_data['query']
            filters = serializer.validated_data.get('filters', {})
            
            # Publicar evento de búsqueda
            event_bus.publish('search.query_received', {
                'query': query,
                'filters': filters,
                'user_id': str(request.user.id) if request.user.is_authenticated else None,
                'timestamp': timezone.now().isoformat()
            })
            
            # Implementar búsqueda con embeddings
            results = self.perform_semantic_search(query, filters)
            
            return Response({
                'query': query,
                'results': results,
                'total': len(results)
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @method_decorator(cache_page(60 * 15))  # 15 minutos
    def list(self, request, *args, **kwargs):
        """Lista de productos con cache."""
        return super().list(request, *args, **kwargs)
    
    def perform_semantic_search(self, query, filters):
        """Realiza búsqueda semántica usando embeddings."""
        # TODO: Implementar búsqueda vectorial con pgvector
        # Por ahora retorna búsqueda básica
        return Product.objects.filter(
            name__icontains=query,
            is_active=True
        )[:20]
```

### Cart Views (apps/cart/views.py)
```python
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import transaction

from .models import Cart, CartItem
from .serializers import CartSerializer, CartItemSerializer
from apps.events.bus import event_bus

class CartViewSet(viewsets.ModelViewSet):
    """ViewSet para carrito de compras - Completamente desacoplado."""
    serializer_class = CartSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Cart.objects.filter(user_id=self.request.user.id, is_active=True)
    
    @action(detail=False, methods=['post'])
    def add_item(self, request):
        """Agrega item al carrito."""
        serializer = CartItemSerializer(data=request.data)
        if serializer.is_valid():
            with transaction.atomic():
                cart, created = Cart.objects.get_or_create(
                    user_id=request.user.id,
                    defaults={'is_active': True}
                )
                
                cart_item = serializer.save(cart_id=cart.id)
                
                # Publicar evento - No conoce otras apps
                event_bus.publish('cart.item_added', {
                    'user_id': str(request.user.id),
                    'product_id': str(cart_item.product_id),
                    'quantity': cart_item.quantity,
                    'timestamp': timezone.now().isoformat()
                })
                
                return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def checkout(self, request):
        """Procesa checkout del carrito."""
        cart = self.get_queryset().first()
        if not cart or not cart.items.exists():
            return Response(
                {'error': 'Carrito vacío'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        with transaction.atomic():
            # Procesar compra
            total = cart.get_total_price()
            
            # Publicar evento de checkout - No conoce otras apps
            event_bus.publish('cart.checkout_completed', {
                'user_id': str(request.user.id),
                'cart_id': str(cart.id),
                'total': float(total),
                'items_count': cart.items.count(),
                'timestamp': timezone.now().isoformat()
            })
            
            # Marcar carrito como inactivo
            cart.is_active = False
            cart.save()
            
            return Response({
                'message': 'Checkout completado',
                'total': float(total)
            })
```

## 🔧 Serializers Desacoplados

### Product Serializers (apps/products/serializers.py)
```python
from rest_framework import serializers
from .models import Product

class ProductSerializer(serializers.ModelSerializer):
    # No incluir brand_name - cada app maneja sus propios datos
    
    class Meta:
        model = Product
        fields = [
            'id', 'name', 'description', 'price', 'original_price',
            'currency', 'category', 'subcategory', 'tags',
            'ai_description', 'ai_tags', 'images', 'variants',
            'is_active', 'in_stock', 'stock_quantity',
            'created_at'
        ]

class ProductSearchSerializer(serializers.Serializer):
    query = serializers.CharField(max_length=500)
    filters = serializers.DictField(required=False)
    limit = serializers.IntegerField(default=20, min_value=1, max_value=100)
```

### Cart Serializers (apps/cart/serializers.py)
```python
from rest_framework import serializers
from .models import Cart, CartItem

class CartItemSerializer(serializers.ModelSerializer):
    # No incluir product_name o product_price - se obtienen por eventos
    
    class Meta:
        model = CartItem
        fields = ['id', 'product_id', 'quantity', 'selected_variant']
    
    def validate(self, data):
        # Validar que el producto esté disponible
        # Esto se puede hacer por eventos o cache local
        return data

class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    total_price = serializers.SerializerMethodField()
    
    class Meta:
        model = Cart
        fields = ['id', 'items', 'total_price', 'created_at']
    
    def get_total_price(self, obj):
        return obj.get_total_price()
```

## 🚀 Ventajas de la Arquitectura Desacoplada

### 1. **Escalabilidad Horizontal**
- Cada app puede correr en servidor separado
- Event Bus centralizado con Redis cluster
- Load balancing por app

### 2. **Independencia de Desarrollo**
- Equipos pueden trabajar en paralelo
- No hay dependencias de imports
- Testing aislado por app

### 3. **Migración Fácil**
- AI Service puede extraerse a FastAPI
- Solo cambiar Event Bus implementation
- APIs externas pueden consumir eventos

### 4. **Mantenibilidad**
- Cambios en una app no afectan otras
- Eventos como contratos estables
- Debugging más simple

## 🎯 Próximos Pasos de Implementación

1. **Crear estructura de directorios** con apps/ separadas
2. **Implementar modelos base** con UUIDs
3. **Configurar Event Bus** centralizado
4. **Implementar Event Handlers** por app
5. **Crear APIs independientes** por app
6. **Configurar Celery workers** por app
7. **Implementar búsqueda vectorial** con pgvector
8. **Configurar sistema de logging** centralizado
9. **Implementar tests unitarios** por app
10. **Configurar CI/CD pipeline** con tests aislados

Esta arquitectura permite que DaydreamShop escale horizontalmente sin límites, con cada app funcionando de forma completamente independiente.
