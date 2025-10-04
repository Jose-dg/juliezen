# Arquitectura del Motor de Marketing Automation

## 1. Visión General y Principios

El objetivo de este módulo es crear un sistema de automatización de marketing que utilice los datos transaccionales de ERPNext para ejecutar campañas personalizadas y oportunas. El diseño se rige por tres principios fundamentales:

1.  **ERPNext es la Única Fuente de Verdad (Single Source of Truth - SSOT):** Toda la información maestra sobre clientes, productos, ventas, números de serie y fechas de expiración reside y se gestiona exclusivamente en ERPNext. Nuestro motor solo **lee** esta información.
2.  **Cero Duplicación de Datos Maestros:** El motor de marketing NO almacenará su propia copia de clientes o productos. Almacenará únicamente la lógica de marketing (campañas, reglas) y los logs de ejecución.
3.  **Eficiencia y Escalabilidad:** Las operaciones serán asíncronas y optimizadas para no sobrecargar la API de ERPNext, utilizando tareas programadas (`celery`) para procesos en lote.

## 2. Arquitectura de Componentes

El sistema consta de tres partes principales:

```
                                      +--------------------------------+
           (Lee datos vía API)        |   Motor de Marketing           |      (Envía emails, etc.)
[ ERPNext ] <----------------------- |   (Nuestra App Django)         | ------------------------> [ Servicios Externos ]
(Fuente de Verdad)                    |                                |                           (SendGrid, Mailchimp...)
                                      | - Modelos: Campañas, Triggers  |
                                      | - Lógica: Tareas Celery        |
                                      +--------------------------------+
```

1.  **ERPNext:** Contiene todos los datos operativos. No se realizarán modificaciones a su esquema base.
2.  **Motor de Marketing (Nueva App `marketing_automation`):** El cerebro del sistema. Es una nueva app dentro de nuestro proyecto Django que contiene la lógica para definir y ejecutar las campañas.
3.  **Servicios Externos:** APIs de terceros (ej. proveedores de email) que ejecutan la acción final de comunicación.

## 3. Modelo de Datos en ERPNext (Sin Modificaciones)

Para el caso de uso de "pines de suscripción", aprovecharemos los doctypes estándar de ERPNext:

*   **Producto (`Item`):** Un pin es un `Item` en ERPNext, con la casilla "Has Serial No" activada. Se puede agrupar bajo un `Item Group` llamado "Suscripciones Digitales".
*   **Número de Serie (`Serial No`):** Cada pin único vendido tiene un `Serial No`. De forma crucial, el doctype `Serial No` tiene un campo estándar: **`Expiry Date`**. Aquí es donde se almacenará la fecha de vencimiento de la suscripción.
*   **Venta (`Sales Invoice`):** Cuando se vende un pin, se genera una `Sales Invoice` que asocia un `Customer` con un `Serial No` específico.

Este modelo nos da toda la información que necesitamos sin añadir un solo campo personalizado a ERPNext: qué cliente compró qué suscripción y cuándo expira.

## 4. El Motor de Marketing (Nueva App Django `marketing_automation`)

Esta nueva app contendrá los siguientes modelos:

*   `Campaign(name, description, is_active)`: La campaña general. Ej: "Campaña de Renovación de Suscripciones".
*   `Trigger(campaign, name, trigger_type, days_offset)`: La regla que dispara la acción.
    *   `trigger_type`: Ej: `BEFORE_EXPIRATION`.
    *   `days_offset`: Ej: `30` (para 30 días antes).
*   `Action(trigger, name, action_type, email_template)`: La acción a realizar.
    *   `action_type`: Ej: `SEND_EMAIL`.
*   `EmailTemplate(name, subject, body)`: La plantilla del correo, con variables como `{{customer_name}}`, `{{item_name}}`, `{{expiry_date}}`.
*   `ExecutionLog(customer, campaign, action, status, executed_at)`: Un registro de cada acción ejecutada para evitar envíos duplicados y para auditoría.

## 5. Flujo de Trabajo Detallado (Ejemplo: Renovación de Suscripción)

Este es el flujo de trabajo para notificar a un cliente 30 días antes de que su suscripción expire.

1.  **Configuración (Única vez):**
    *   Un usuario de marketing crea una `Campaign`: "Renovación de Suscripciones".
    *   Crea un `Trigger`: "Notificar 30 días antes", con `trigger_type='BEFORE_EXPIRATION'` y `days_offset=30`.
    *   Crea una `EmailTemplate` con el texto de la oferta de renovación.
    *   Crea una `Action`: "Enviar Email de Renovación", que une el `Trigger` con la `EmailTemplate`.

2.  **Ejecución (Automática y Diaria):**
    *   Una tarea de Celery (`check_expiring_subscriptions`) se ejecuta todas las noches a la 1 AM.
    *   **Paso 1 (Consulta a ERPNext):** La tarea hace una llamada a la API de ERPNext para solicitar: "Todos los `Serial No` cuyo `Expiry Date` sea exactamente dentro de 30 días".
    *   **Paso 2 (Obtener Contexto):** Por cada `Serial No` devuelto, la tarea hace una consulta adicional a ERPNext para obtener el `Customer` asociado a la `Sales Invoice` de ese `Serial No`.
    *   **Paso 3 (Verificar y Ejecutar):** Para cada `Serial No` encontrado:
        *   El motor busca en su `ExecutionLog` para asegurarse de que no se ha enviado ya una notificación para este cliente y esta campaña.
        *   Si no hay registro, renderiza la `EmailTemplate` con los datos del cliente y la suscripción.
        *   Llama a la API del servicio de email (ej. SendGrid) para enviar el correo.
        *   Crea un registro en `ExecutionLog` marcando la acción como "Completada".

## 6. Mejores Prácticas y Siguientes Pasos

*   **Abstracción de Servicios:** Utilizar librerías como `django-anymail` para que el `Action` no dependa de un proveedor de email específico. Podríamos cambiar de SendGrid a Mailgun con una sola línea de configuración.
*   **Consultas Eficientes:** Optimizar la consulta a la API de ERPNext para obtener todos los datos necesarios en el menor número de llamadas posible.
*   **Interfaz de Usuario:** Construir vistas de Django para que el equipo de marketing pueda gestionar las Campañas, Triggers y Plantillas sin tocar el código.
*   **Prueba de Concepto (PoC):** El primer paso de desarrollo sería implementar este flujo específico de renovación de suscripciones para validar la arquitectura antes de añadir triggers más complejos (ej. basados en comportamiento).
