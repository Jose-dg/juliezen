# Reprocesar mensajes de Alegra

- Cada webhook o request se almacena como un `IntegrationMessage`. No se sobrescriben registros.
- Usa el admin (Integrations → Integration messages) para filtrar por `status` o `external_reference`. Selecciona uno o varios y utiliza la acción "Reenviar mensajes seleccionados"; esto encola nuevamente la tarea `process_integration_message`.
- Desde el shell también puedes forzar un reenvío:
  ```python
  from apps.integrations.tasks import process_integration_message
  process_integration_message.delay("MESSAGE_UUID")
  ```
- El payload de ERPNext debe incluir `customer.custom_alegra_id` cuando exista, `customer.identification` y `customer.identification_type`; el servicio usa esos campos para consultar directamente en Alegra y evita crear duplicados. Si sólo se envía `customer` como string, el backend usa `customer_name`, `contact_email` y `customer_phone` como respaldo. El handler procesa `POS Invoice` y `Sales Invoice`; otros doctypes quedan marcados como `skipped`. Se aprovechan campos opcionales (`due_date`, `remarks`, `is_pos`, `naming_series`) para poblar la factura en Alegra.
- Si la creación del contacto falla porque ya existe, el flujo intenta recuperarlo usando `custom_alegra_id`, identificación, email o código; así la factura continúa construyéndose y enviándose.
- Configura en `AlegraCredential.metadata` los mapas `payment_account_map` (modo de pago → ID de cuenta) y `payment_method_map` (modo de pago → clave `paymentMethod` de Alegra) para que cada entrada de `payload.payments` se transforme correctamente. Los valores por defecto (`default_payment_account_id`, `default_payment_method`, `default_payment_method_key`) se usan si no hay coincidencias.
- Si ya tienes productos dados de alta en Alegra, agrega un `item_map` en la metadata (`{"item_code": alegra_item_id}`) o envía `items[].alegra_id` en el payload; de esa forma cada línea se manda con el mismo ID que registra Alegra.
- Si manejas numeración manual, puedes definir `number_template_id`, `number_template_prefix` y `number_template_next` en la metadata para enviar `{id, prefix, number}` dentro de `numberTemplate`.
- Los registros nuevos se crean con `status = received`. Celery intenta hasta 3 veces por defecto para errores recuperables (p. ej. `network_error`, `server_error`, `rate_limited`). Los errores no recuperables (`validation_error`, `authentication_error`, `credential_error`, etc.) dejan el mensaje original en `processed` con un resumen liviano en `response_payload` (sin detalles sensibles) y no se reintentan automáticamente; corrige los datos en ERPNext y vuelve a enviar. Cada reintento automático genera un nuevo `IntegrationMessage` (misma dirección) con su propio UUID.
- Para ver los detalles completos del error, revisa el `IntegrationMessage` correspondiente a la dirección `outbound`; allí quedan guardados el payload enviado a Alegra, la respuesta exacta y los códigos HTTP.
- Puedes definir en la metadata de la credencial (`AlegraCredential.metadata`) el campo `generic_identification_type` para indicar qué tipo de identificación usar cuando el número no sea puramente numérico (por defecto se envía `OTHER`).
- Para distinguir intentos, revisa los timestamps (`received_at`) y los campos `direction`/`event_type`. Cada intento tendrá su propio UUID.
