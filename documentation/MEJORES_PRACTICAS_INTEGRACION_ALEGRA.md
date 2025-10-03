# Reprocesar mensajes de Alegra

- Cada webhook o request se almacena como un `IntegrationMessage`. No se sobrescriben registros.
- Usa el admin (Integrations → Integration messages) para filtrar por `status` o `external_reference`. Selecciona uno o varios y utiliza la acción "Reenviar mensajes seleccionados"; esto encola nuevamente la tarea `process_integration_message`.
- Desde el shell también puedes forzar un reenvío:
  ```python
  from apps.integrations.tasks import process_integration_message
  process_integration_message.delay("MESSAGE_UUID")
  ```
- Los registros nuevos se crean con `status = received`. Celery intentará procesarlos y, si fallan, podrás ver `error_code` y `error_message` en el mismo registro.
- Para distinguir intentos, revisa los timestamps (`received_at`) y los campos `direction`/`event_type`. Cada intento tendrá su propio UUID.
