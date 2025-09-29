# 🚀 API Endpoints - DaydreamShop

Esta documentación describe todos los endpoints disponibles para el frontend de DaydreamShop. La API está construida con Django REST Framework y utiliza autenticación JWT.

## 📋 Tabla de Contenidos

- [Configuración Base](#configuración-base)
- [Autenticación](#autenticación)
- [Usuarios](#usuarios)
- [Productos](#productos)
- [Carrito de Compras](#carrito-de-compras)
- [Servicios de IA](#servicios-de-ia)
- [Marcas](#marcas)
- [Notificaciones](#notificaciones)
- [Recomendaciones](#recomendaciones)
- [Eventos](#eventos)
- [Códigos de Error](#códigos-de-error)

## 🔧 Configuración Base

### URL Base
```
http://localhost:8000/api/v1/
```

### Headers Requeridos
```http
Content-Type: application/json
Authorization: Bearer <jwt_token>
```

### Formato de Respuesta
```json
{
  "data": {},
  "message": "string",
  "status": "success|error",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

## 🔐 Autenticación

### POST /auth/register/
Registra un nuevo usuario en el sistema.

**Request Body:**
```json
{
  "email": "usuario@ejemplo.com",
  "username": "usuario123",
  "password": "contraseña123",
  "first_name": "Juan",
  "last_name": "Pérez"
}
```

**Response (201):**
```json
{
  "data": {
    "user": {
      "id": "uuid",
      "email": "usuario@ejemplo.com",
      "username": "usuario123",
      "first_name": "Juan",
      "last_name": "Pérez"
    },
    "tokens": {
      "access": "jwt_access_token",
      "refresh": "jwt_refresh_token"
    }
  },
  "message": "Usuario registrado exitosamente",
  "status": "success"
}
```

### POST /auth/login/
Inicia sesión con email y contraseña.

**Request Body:**
```json
{
  "email": "usuario@ejemplo.com",
  "password": "contraseña123"
}
```

**Response (200):**
```json
{
  "data": {
    "user": {
      "id": "uuid",
      "email": "usuario@ejemplo.com",
      "username": "usuario123",
      "first_name": "Juan",
      "last_name": "Pérez"
    },
    "tokens": {
      "access": "jwt_access_token",
      "refresh": "jwt_refresh_token"
    }
  },
  "message": "Login exitoso",
  "status": "success"
}
```

### POST /auth/refresh/
Renueva el token de acceso usando el refresh token.

**Request Body:**
```json
{
  "refresh": "jwt_refresh_token"
}
```

**Response (200):**
```json
{
  "data": {
    "access": "new_jwt_access_token"
  },
  "message": "Token renovado exitosamente",
  "status": "success"
}
```

### POST /auth/logout/
Cierra sesión invalidando el refresh token.

**Request Body:**
```json
{
  "refresh": "jwt_refresh_token"
}
```

**Response (200):**
```json
{
  "message": "Logout exitoso",
  "status": "success"
}
```

## 👤 Usuarios

### GET /users/profile/
Obtiene el perfil del usuario autenticado.

**Headers:** `Authorization: Bearer <token>`

**Response (200):**
```json
{
  "data": {
    "id": "uuid",
    "email": "usuario@ejemplo.com",
    "username": "usuario123",
    "first_name": "Juan",
    "last_name": "Pérez",
    "style_preferences": {
      "colors": ["azul", "negro"],
      "styles": ["casual", "formal"]
    },
    "size_profile": {
      "height": 175,
      "weight": 70,
      "shirt_size": "M",
      "pants_size": "32"
    },
    "shopping_behavior": {
      "preferred_brands": ["nike", "adidas"],
      "budget_range": "100-500"
    }
  },
  "status": "success"
}
```

### PUT /users/profile/
Actualiza el perfil del usuario.

**Request Body:**
```json
{
  "first_name": "Juan Carlos",
  "last_name": "Pérez García",
  "style_preferences": {
    "colors": ["azul", "negro", "blanco"],
    "styles": ["casual", "deportivo"]
  },
  "size_profile": {
    "height": 180,
    "weight": 75,
    "shirt_size": "L",
    "pants_size": "34"
  }
}
```

**Response (200):**
```json
{
  "data": {
    "id": "uuid",
    "email": "usuario@ejemplo.com",
    "username": "usuario123",
    "first_name": "Juan Carlos",
    "last_name": "Pérez García",
    "style_preferences": {
      "colors": ["azul", "negro", "blanco"],
      "styles": ["casual", "deportivo"]
    },
    "size_profile": {
      "height": 180,
      "weight": 75,
      "shirt_size": "L",
      "pants_size": "34"
    }
  },
  "message": "Perfil actualizado exitosamente",
  "status": "success"
}
```

### GET /users/style-passport/
Obtiene el pasaporte de estilo del usuario.

**Response (200):**
```json
{
  "data": {
    "id": "uuid",
    "user_id": "uuid",
    "favorite_colors": ["azul", "negro", "blanco"],
    "preferred_styles": ["casual", "deportivo", "formal"],
    "size_preferences": {
      "shirt": "L",
      "pants": "34",
      "shoes": "42"
    },
    "budget_range": "100-500",
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z"
  },
  "status": "success"
}
```

## 🛍️ Productos

### GET /products/
Obtiene la lista de productos con filtros y paginación.

**Query Parameters:**
- `page`: Número de página (default: 1)
- `page_size`: Tamaño de página (default: 20, max: 100)
- `category`: Filtrar por categoría
- `brand_id`: Filtrar por marca
- `min_price`: Precio mínimo
- `max_price`: Precio máximo
- `in_stock`: Solo productos en stock (true/false)
- `search`: Búsqueda por texto

**Example:**
```
GET /products/?category=camisetas&min_price=20&max_price=100&in_stock=true&page=1
```

**Response (200):**
```json
{
  "data": {
    "results": [
      {
        "id": "uuid",
        "name": "Camiseta Nike Dri-FIT",
        "description": "Camiseta deportiva de alta calidad",
        "price": "29.99",
        "original_price": "39.99",
        "currency": "USD",
        "category": "camisetas",
        "subcategory": "deportivas",
        "tags": ["nike", "deportivo", "dri-fit"],
        "ai_description": "Camiseta deportiva ideal para entrenamientos intensos",
        "ai_tags": ["deportivo", "transpirable", "cómodo"],
        "images": [
          "https://example.com/image1.jpg",
          "https://example.com/image2.jpg"
        ],
        "variants": {
          "colors": ["azul", "negro", "blanco"],
          "sizes": ["S", "M", "L", "XL"]
        },
        "in_stock": true,
        "stock_quantity": 50,
        "created_at": "2024-01-01T00:00:00Z"
      }
    ],
    "count": 150,
    "next": "http://localhost:8000/api/v1/products/?page=2",
    "previous": null,
    "page": 1,
    "total_pages": 8
  },
  "status": "success"
}
```

### GET /products/{id}/
Obtiene los detalles de un producto específico.

**Response (200):**
```json
{
  "data": {
    "id": "uuid",
    "name": "Camiseta Nike Dri-FIT",
    "description": "Camiseta deportiva de alta calidad con tecnología Dri-FIT",
    "price": "29.99",
    "original_price": "39.99",
    "currency": "USD",
    "category": "camisetas",
    "subcategory": "deportivas",
    "tags": ["nike", "deportivo", "dri-fit"],
    "ai_description": "Camiseta deportiva ideal para entrenamientos intensos con tecnología de secado rápido",
    "ai_tags": ["deportivo", "transpirable", "cómodo", "secado-rápido"],
    "images": [
      "https://example.com/image1.jpg",
      "https://example.com/image2.jpg",
      "https://example.com/image3.jpg"
    ],
    "variants": {
      "colors": [
        {
          "name": "azul",
          "hex": "#0066CC",
          "images": ["https://example.com/blue1.jpg"]
        },
        {
          "name": "negro",
          "hex": "#000000",
          "images": ["https://example.com/black1.jpg"]
        }
      ],
      "sizes": [
        {
          "size": "S",
          "stock": 10
        },
        {
          "size": "M",
          "stock": 25
        },
        {
          "size": "L",
          "stock": 15
        }
      ]
    },
    "in_stock": true,
    "stock_quantity": 50,
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z"
  },
  "status": "success"
}
```

### POST /products/search/
Búsqueda semántica de productos usando IA.

**Request Body:**
```json
{
  "query": "camiseta cómoda para correr",
  "filters": {
    "category": "camisetas",
    "max_price": 50,
    "brand_id": "uuid"
  },
  "limit": 20
}
```

**Response (200):**
```json
{
  "data": {
    "query": "camiseta cómoda para correr",
    "results": [
      {
        "id": "uuid",
        "name": "Camiseta Nike Dri-FIT",
        "price": "29.99",
        "relevance_score": 0.95,
        "ai_match_reason": "Camiseta deportiva con tecnología transpirable ideal para correr"
      }
    ],
    "total": 15,
    "search_time": "0.234s"
  },
  "status": "success"
}
```

### GET /products/categories/
Obtiene todas las categorías disponibles.

**Response (200):**
```json
{
  "data": [
    {
      "name": "camisetas",
      "display_name": "Camisetas",
      "subcategories": [
        {
          "name": "deportivas",
          "display_name": "Deportivas"
        },
        {
          "name": "casual",
          "display_name": "Casual"
        }
      ],
      "product_count": 150
    },
    {
      "name": "pantalones",
      "display_name": "Pantalones",
      "subcategories": [
        {
          "name": "jeans",
          "display_name": "Jeans"
        },
        {
          "name": "deportivos",
          "display_name": "Deportivos"
        }
      ],
      "product_count": 89
    }
  ],
  "status": "success"
}
```

## 🛒 Carrito de Compras

### GET /cart/
Obtiene el carrito activo del usuario.

**Headers:** `Authorization: Bearer <token>`

**Response (200):**
```json
{
  "data": {
    "id": "uuid",
    "items": [
      {
        "id": "uuid",
        "product_id": "uuid",
        "product_name": "Camiseta Nike Dri-FIT",
        "product_price": "29.99",
        "product_image": "https://example.com/image1.jpg",
        "quantity": 2,
        "selected_variant": {
          "color": "azul",
          "size": "M"
        },
        "total_price": "59.98",
        "created_at": "2024-01-01T00:00:00Z"
      }
    ],
    "total_price": "59.98",
    "items_count": 1,
    "created_at": "2024-01-01T00:00:00Z"
  },
  "status": "success"
}
```

### POST /cart/add-item/
Agrega un producto al carrito.

**Request Body:**
```json
{
  "product_id": "uuid",
  "quantity": 2,
  "selected_variant": {
    "color": "azul",
    "size": "M"
  }
}
```

**Response (201):**
```json
{
  "data": {
    "id": "uuid",
    "product_id": "uuid",
    "quantity": 2,
    "selected_variant": {
      "color": "azul",
      "size": "M"
    },
    "total_price": "59.98"
  },
  "message": "Producto agregado al carrito",
  "status": "success"
}
```

### PUT /cart/items/{item_id}/
Actualiza la cantidad de un item en el carrito.

**Request Body:**
```json
{
  "quantity": 3
}
```

**Response (200):**
```json
{
  "data": {
    "id": "uuid",
    "product_id": "uuid",
    "quantity": 3,
    "selected_variant": {
      "color": "azul",
      "size": "M"
    },
    "total_price": "89.97"
  },
  "message": "Item actualizado exitosamente",
  "status": "success"
}
```

### DELETE /cart/items/{item_id}/
Elimina un item del carrito.

**Response (200):**
```json
{
  "message": "Item eliminado del carrito",
  "status": "success"
}
```

### POST /cart/checkout/
Procesa el checkout del carrito.

**Request Body:**
```json
{
  "shipping_address": {
    "street": "Calle Principal 123",
    "city": "Madrid",
    "postal_code": "28001",
    "country": "España"
  },
  "payment_method": "credit_card",
  "payment_details": {
    "card_number": "**** **** **** 1234",
    "expiry_date": "12/25"
  }
}
```

**Response (200):**
```json
{
  "data": {
    "order_id": "uuid",
    "total": "89.97",
    "items_count": 1,
    "shipping_address": {
      "street": "Calle Principal 123",
      "city": "Madrid",
      "postal_code": "28001",
      "country": "España"
    },
    "estimated_delivery": "2024-01-05T00:00:00Z",
    "tracking_number": "TRK123456789"
  },
  "message": "Checkout completado exitosamente",
  "status": "success"
}
```

### DELETE /cart/clear/
Limpia todo el carrito.

**Response (200):**
```json
{
  "message": "Carrito limpiado exitosamente",
  "status": "success"
}
```

## 🤖 Servicios de IA

### POST /ai/recommendations/
Obtiene recomendaciones personalizadas basadas en IA.

**Request Body:**
```json
{
  "user_id": "uuid",
  "context": "homepage|product_page|cart",
  "limit": 10,
  "filters": {
    "category": "camisetas",
    "max_price": 100
  }
}
```

**Response (200):**
```json
{
  "data": {
    "recommendations": [
      {
        "product_id": "uuid",
        "product_name": "Camiseta Adidas ClimaLite",
        "product_price": "24.99",
        "product_image": "https://example.com/image1.jpg",
        "relevance_score": 0.92,
        "reason": "Basado en tu preferencia por marcas deportivas y estilo casual"
      }
    ],
    "total": 10,
    "context": "homepage",
    "generated_at": "2024-01-01T00:00:00Z"
  },
  "status": "success"
}
```

### POST /ai/style-analysis/
Analiza el estilo del usuario basado en sus preferencias.

**Request Body:**
```json
{
  "user_id": "uuid",
  "preferences": {
    "colors": ["azul", "negro"],
    "styles": ["casual", "deportivo"],
    "budget_range": "50-200"
  }
}
```

**Response (200):**
```json
{
  "data": {
    "style_profile": {
      "primary_style": "casual-deportivo",
      "confidence": 0.87,
      "color_palette": ["azul", "negro", "blanco", "gris"],
      "recommended_brands": ["nike", "adidas", "puma"],
      "style_tips": [
        "Prefieres prendas cómodas y funcionales",
        "Te gustan los colores neutros y clásicos",
        "Valoras la calidad sobre la cantidad"
      ]
    },
    "generated_at": "2024-01-01T00:00:00Z"
  },
  "status": "success"
}
```

### POST /ai/product-description/
Genera una descripción mejorada de un producto usando IA.

**Request Body:**
```json
{
  "product_id": "uuid",
  "style": "formal|casual|deportivo",
  "target_audience": "joven|adulto|profesional"
}
```

**Response (200):**
```json
{
  "data": {
    "enhanced_description": "Esta camiseta deportiva Nike Dri-FIT es perfecta para el atleta moderno que busca comodidad y rendimiento. Con tecnología de secado rápido y diseño ergonómico, te mantendrá fresco y cómodo durante tus entrenamientos más intensos.",
    "key_features": [
      "Tecnología Dri-FIT para secado rápido",
      "Diseño ergonómico para máximo confort",
      "Material transpirable y ligero"
    ],
    "style_tags": ["deportivo", "funcional", "moderno"],
    "generated_at": "2024-01-01T00:00:00Z"
  },
  "status": "success"
}
```

## 🏷️ Marcas

### GET /brands/
Obtiene la lista de marcas disponibles.

**Response (200):**
```json
{
  "data": [
    {
      "id": "uuid",
      "name": "Nike",
      "website_url": "https://nike.com",
      "logo_url": "https://example.com/nike-logo.png",
      "product_count": 150,
      "is_active": true
    },
    {
      "id": "uuid",
      "name": "Adidas",
      "website_url": "https://adidas.com",
      "logo_url": "https://example.com/adidas-logo.png",
      "product_count": 89,
      "is_active": true
    }
  ],
  "status": "success"
}
```

### GET /brands/{id}/
Obtiene los detalles de una marca específica.

**Response (200):**
```json
{
  "data": {
    "id": "uuid",
    "name": "Nike",
    "website_url": "https://nike.com",
    "logo_url": "https://example.com/nike-logo.png",
    "description": "Just Do It - Nike es una marca líder en calzado y ropa deportiva",
    "product_count": 150,
    "categories": ["calzado", "ropa", "accesorios"],
    "is_active": true,
    "created_at": "2024-01-01T00:00:00Z"
  },
  "status": "success"
}
```

## 🔔 Notificaciones

### GET /notifications/
Obtiene las notificaciones del usuario.

**Query Parameters:**
- `page`: Número de página
- `unread_only`: Solo notificaciones no leídas (true/false)

**Response (200):**
```json
{
  "data": {
    "results": [
      {
        "id": "uuid",
        "type": "product_available",
        "title": "Producto disponible",
        "message": "La camiseta Nike que tenías en tu wishlist ya está disponible",
        "data": {
          "product_id": "uuid",
          "product_name": "Camiseta Nike Dri-FIT"
        },
        "is_read": false,
        "created_at": "2024-01-01T00:00:00Z"
      }
    ],
    "count": 5,
    "unread_count": 2,
    "next": null,
    "previous": null
  },
  "status": "success"
}
```

### PUT /notifications/{id}/read/
Marca una notificación como leída.

**Response (200):**
```json
{
  "message": "Notificación marcada como leída",
  "status": "success"
}
```

### PUT /notifications/mark-all-read/
Marca todas las notificaciones como leídas.

**Response (200):**
```json
{
  "message": "Todas las notificaciones marcadas como leídas",
  "status": "success"
}
```

## 🎯 Recomendaciones

### GET /recommendations/
Obtiene recomendaciones personalizadas para el usuario.

**Query Parameters:**
- `type`: Tipo de recomendación (trending|personalized|similar)
- `limit`: Número de recomendaciones (default: 10)

**Response (200):**
```json
{
  "data": {
    "recommendations": [
      {
        "product_id": "uuid",
        "product_name": "Camiseta Nike Dri-FIT",
        "product_price": "29.99",
        "product_image": "https://example.com/image1.jpg",
        "relevance_score": 0.92,
        "reason": "Basado en tu historial de compras"
      }
    ],
    "type": "personalized",
    "total": 10,
    "generated_at": "2024-01-01T00:00:00Z"
  },
  "status": "success"
}
```

### GET /recommendations/similar/{product_id}/
Obtiene productos similares a uno específico.

**Response (200):**
```json
{
  "data": {
    "similar_products": [
      {
        "product_id": "uuid",
        "product_name": "Camiseta Adidas ClimaLite",
        "product_price": "24.99",
        "similarity_score": 0.89,
        "similarity_reasons": ["mismo estilo", "precio similar", "misma categoría"]
      }
    ],
    "base_product": {
      "id": "uuid",
      "name": "Camiseta Nike Dri-FIT"
    },
    "total": 8
  },
  "status": "success"
}
```

## 📊 Eventos

### GET /events/
Obtiene eventos recientes del sistema (para debugging).

**Query Parameters:**
- `type`: Tipo de evento
- `limit`: Número de eventos (default: 50)

**Response (200):**
```json
{
  "data": {
    "events": [
      {
        "id": "uuid",
        "type": "product.viewed",
        "data": {
          "product_id": "uuid",
          "user_id": "uuid"
        },
        "timestamp": "2024-01-01T00:00:00Z",
        "source": "products"
      }
    ],
    "total": 50
  },
  "status": "success"
}
```

## ❌ Códigos de Error

### Errores HTTP Comunes

| Código | Descripción | Ejemplo |
|--------|-------------|---------|
| 400 | Bad Request | Datos de entrada inválidos |
| 401 | Unauthorized | Token JWT inválido o expirado |
| 403 | Forbidden | Sin permisos para acceder al recurso |
| 404 | Not Found | Recurso no encontrado |
| 429 | Too Many Requests | Límite de rate limiting excedido |
| 500 | Internal Server Error | Error interno del servidor |

### Formato de Error
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Los datos proporcionados no son válidos",
    "details": {
      "email": ["Este campo es requerido"],
      "password": ["La contraseña debe tener al menos 8 caracteres"]
    }
  },
  "status": "error",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

### Códigos de Error Específicos

| Código | Descripción |
|--------|-------------|
| `INVALID_CREDENTIALS` | Email o contraseña incorrectos |
| `TOKEN_EXPIRED` | Token JWT expirado |
| `TOKEN_INVALID` | Token JWT inválido |
| `USER_NOT_FOUND` | Usuario no encontrado |
| `PRODUCT_NOT_FOUND` | Producto no encontrado |
| `CART_EMPTY` | Carrito vacío |
| `INSUFFICIENT_STOCK` | Stock insuficiente |
| `PAYMENT_FAILED` | Error en el procesamiento del pago |

## 🔄 Rate Limiting

La API implementa rate limiting para prevenir abuso:

- **Autenticación**: 5 intentos por minuto por IP
- **Búsquedas**: 100 requests por minuto por usuario
- **General**: 1000 requests por hora por usuario

### Headers de Rate Limiting
```http
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1640995200
```

## 📱 Ejemplos de Uso

### Flujo Completo de Compra

1. **Registro/Login**
```javascript
// Registro
const registerResponse = await fetch('/api/v1/auth/register/', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    email: 'usuario@ejemplo.com',
    username: 'usuario123',
    password: 'contraseña123',
    first_name: 'Juan',
    last_name: 'Pérez'
  })
});

// Login
const loginResponse = await fetch('/api/v1/auth/login/', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    email: 'usuario@ejemplo.com',
    password: 'contraseña123'
  })
});

const { data } = await loginResponse.json();
const token = data.tokens.access;
```

2. **Buscar Productos**
```javascript
const searchResponse = await fetch('/api/v1/products/search/', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`
  },
  body: JSON.stringify({
    query: 'camiseta deportiva',
    filters: { max_price: 50 },
    limit: 20
  })
});
```

3. **Agregar al Carrito**
```javascript
const addToCartResponse = await fetch('/api/v1/cart/add-item/', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`
  },
  body: JSON.stringify({
    product_id: 'uuid-del-producto',
    quantity: 2,
    selected_variant: {
      color: 'azul',
      size: 'M'
    }
  })
});
```

4. **Procesar Checkout**
```javascript
const checkoutResponse = await fetch('/api/v1/cart/checkout/', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`
  },
  body: JSON.stringify({
    shipping_address: {
      street: 'Calle Principal 123',
      city: 'Madrid',
      postal_code: '28001',
      country: 'España'
    },
    payment_method: 'credit_card',
    payment_details: {
      card_number: '**** **** **** 1234',
      expiry_date: '12/25'
    }
  })
});
```

## 🔧 Configuración del Cliente

### Variables de Entorno
```javascript
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api/v1';
const API_TIMEOUT = 10000; // 10 segundos
```

### Interceptor de Axios
```javascript
import axios from 'axios';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: API_TIMEOUT,
});

// Interceptor para agregar token automáticamente
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Interceptor para manejar errores de token
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      // Token expirado, intentar renovar
      const refreshToken = localStorage.getItem('refresh_token');
      if (refreshToken) {
        try {
          const response = await api.post('/auth/refresh/', {
            refresh: refreshToken
          });
          const newToken = response.data.data.access;
          localStorage.setItem('access_token', newToken);
          
          // Reintentar request original
          error.config.headers.Authorization = `Bearer ${newToken}`;
          return api.request(error.config);
        } catch (refreshError) {
          // Refresh falló, redirigir a login
          localStorage.removeItem('access_token');
          localStorage.removeItem('refresh_token');
          window.location.href = '/login';
        }
      }
    }
    return Promise.reject(error);
  }
);
```

---

## 📞 Soporte

Para soporte técnico o preguntas sobre la API, contacta al equipo de desarrollo:

- **Email**: dev@daydreamshop.com
- **Documentación**: [docs.daydreamshop.com](https://docs.daydreamshop.com)
- **GitHub**: [github.com/daydreamshop/api](https://github.com/daydreamshop/api)

---

*Última actualización: Enero 2024*
*Versión de la API: 1.0.0*
