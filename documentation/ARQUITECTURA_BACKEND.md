# Arquitectura Backend: API Gateway

## 1. Visión General

Este documento describe la arquitectura del backend de Django. El rol principal de esta aplicación es actuar como un **API Gateway (Puerta de Enlace de API)** seguro y eficiente.

Su función es sentarse entre los frontends de los clientes y sus respectivas instancias de ERPNext, gestionando la identidad de los usuarios y redirigiendo las peticiones de forma segura.

### Principios Fundamentales:

1.  **ERPNext es la Fuente Única de Verdad (SSoT):** ERPNext gestiona todos los datos del negocio y, crucialmente, los **permisos de los usuarios** sobre qué compañías pueden acceder.
2.  **Este Backend es el Proveedor de Identidad (IdP):** La aplicación Django gestiona las credenciales de los usuarios (email/contraseña) y el proceso de login/autenticación. Determina **quién es** un usuario.
3.  **Este Backend es un Proxy de Autorización:** La aplicación no gestiona roles ni permisos. Delega las decisiones de autorización a ERPNext preguntando en tiempo real: "¿Este usuario tiene acceso a esta compañía?".
4.  **Múltiples Frontends, Un Solo Backend:** El sistema está diseñado para dar servicio a múltiples frontends personalizados (uno por cada compañía cliente) desde una única base de código de backend.

## 2. Componentes y Flujo de Datos

### a) Identificación de la Compañía

La aplicación identifica a qué compañía se está intentando acceder a través del **subdominio** en la URL de la petición.

*   **Ejemplo:** Una petición a `https://empresa-a.julizen.com/api/facturas` le indica al backend que el contexto es la compañía cuyo `slug` es `empresa-a`.

### b) Flujo de una Petición Autenticada

Este es el ciclo de vida de una petición de un usuario ya logueado:

1.  **Petición del Cliente:** El frontend (ej. `empresa-a.julizen.com`) realiza una llamada a la API del backend (ej. `GET /api/facturas`) incluyendo el token de autenticación del usuario.
2.  **Autenticación (Django):** El backend utiliza el token para identificar al usuario (`request.user`).
3.  **Identificación de Compañía (Middleware):** El `CompanyContextMiddleware` extrae el `slug` de la compañía ("empresa-a") del subdominio de la petición.
4.  **Proxy de Autorización (Middleware):**
    *   El middleware comprueba primero un **caché local (Redis)** para ver si ya ha verificado recientemente el acceso de este usuario a esta compañía.
    *   **Si no está en caché**, realiza una llamada a la API de ERPNext preguntando: "¿El usuario `X` tiene acceso a la compañía `Y`?".
    *   **Si la respuesta es "Sí"**, guarda el resultado en el caché con un TTL (tiempo de vida) corto (ej. 5 minutos) y permite que la petición continúe.
    *   **Si la respuesta es "No"**, bloquea la petición con un error `403 Forbidden`.
5.  **Proxy de API (Vista):**
    *   La petición, ya validada, llega a la vista de Django.
    *   La vista actúa como un proxy: utiliza las credenciales de la compañía para realizar la petición original a la API de ERPNext (ej. obtener las facturas).
    *   La respuesta de ERPNext se devuelve directamente al frontend.

## 3. Cambios Arquitectónicos a Implementar

Para adoptar este modelo, se realizarán los siguientes cambios:

*   **Modelo `Company`:** Se mantiene, pero se asegura de que contenga los datos de conexión para la API de ERPNext de esa compañía (URL, credenciales cifradas).
*   **Modelo `CompanyMembership`:** **Será eliminado.** La relación entre usuario y compañía ya no se almacena en nuestra base de datos; se valida en tiempo real contra ERPNext.
*   **Middleware `CompanyContextMiddleware`:** Será reescrito por completo para implementar la lógica de identificación por subdominio y el proxy de autorización con caché.
*   **Vistas:** Se simplificarán para eliminar toda la lógica de comprobación de roles (ej. `is_admin`). Su única función será la de actuar como proxies hacia ERPNext.
*   **Caché:** Se integrará Redis para cachear las respuestas de autorización y mejorar el rendimiento.

## 4. Justificación y Beneficios

*   **Centralización de Permisos:** La gestión de acceso de usuarios se realiza en un único lugar (ERPNext), simplificando la administración para los clientes.
*   **Backend Ligero y Escalable:** La lógica de negocio compleja reside en el ERP. Nuestro backend se enfoca en la seguridad, el rendimiento y el enrutamiento, tareas en las que es muy eficiente.
*   **Desacoplamiento Real:** Permite que los frontends y el ERP evolucionen de forma independiente, con el backend actuando como un traductor y garante de seguridad estable.

Pendientes:
1. Enviar la factura electronica y guardar la respuesta y enviarle a el ERPNetxt una notificacion de que esa venta ya tiene factura electronica. En el caso de que el usuario de el ERP quiera reenviar la factura lo puede hacer 
2. Recibir el json con la venta de shopify y nosotros controlar la creacion el ERP hasta la entrega del pin y si fu exitosa la entrega al ERPNext considerar la informacion
3. Mejorar y cada copania hacerle email que correponda al tipo de tienda.


