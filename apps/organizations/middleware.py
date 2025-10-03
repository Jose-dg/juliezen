import uuid
import logging
from typing import Optional
from urllib.parse import urlparse

from django.conf import settings
from django.core.cache import cache
from django.http import HttpRequest, HttpResponseForbidden
from django.utils.functional import SimpleLazyObject

from .models import Organization

logger = logging.getLogger(__name__)

# --- Stub para el servicio de ERPNext (se implementará más adelante) ---
class ERPNextService:
    @staticmethod
    def check_user_organization_access(user_email: str, organization_id: uuid.UUID) -> bool:
        """
        Simula la llamada a ERPNext para verificar si un usuario tiene acceso a una organización.
        En una implementación real, esto haría una llamada a la API de ERPNext.
        """
        logger.info(
            f"Simulando verificación de acceso en ERPNext para usuario {user_email} "
            f"y organización {organization_id}"
        )
        # Por ahora, siempre devuelve True para permitir el flujo.
        # TODO: Implementar la lógica real de llamada a ERPNext.
        return True

# ----------------------------------------------------------------------


class OrganizationContextMiddleware:
    """
    Adjunta el objeto Organization al request basado en el subdominio
    y valida el acceso del usuario contra ERPNext (con caché).
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest):
        request.organization = SimpleLazyObject(lambda: self._resolve_organization(request))
        response = self.get_response(request)
        return response

    def _resolve_organization(self, request: HttpRequest) -> Optional[Organization]:
        # 1. Obtener el slug de la organización del subdominio
        host = request.get_host().split(':')[0]  # Eliminar el puerto si existe
        domain_parts = host.split('.')

        if len(domain_parts) < 3:  # Ej. localhost, myapp.com (sin subdominio)
            logger.debug(f"No se encontró subdominio para el host: {host}")
            return None

        # Asumimos que el subdominio es la primera parte (ej. 'empresa-a' de 'empresa-a.julizen.com')
        organization_slug = domain_parts[0]

        if organization_slug == "www" or organization_slug == settings.ROOT_DOMAIN_SLUG: # ROOT_DOMAIN_SLUG es un placeholder
            logger.debug(f"Subdominio '{organization_slug}' es un dominio raíz o www, no es una organización.")
            return None

        # 2. Buscar la organización en la base de datos
        try:
            organization = Organization.objects.get(slug=organization_slug, is_active=True)
        except Organization.DoesNotExist:
            logger.warning(f"Organización no encontrada para el slug: {organization_slug}")
            return None

        # 3. Validar acceso si el usuario está autenticado
        user = getattr(request, "user", None)
        if user and user.is_authenticated:
            cache_key = f"user_org_access:{user.id}:{organization.id}"
            has_access = cache.get(cache_key)

            if has_access is None:  # No está en caché, verificar con ERPNext
                has_access = ERPNextService.check_user_organization_access(user.email, organization.id)
                cache.set(cache_key, has_access, timeout=settings.ORGANIZATION_ACCESS_CACHE_TTL) # Cachear por 5 minutos

            if not has_access:
                logger.warning(
                    f"Acceso denegado a la organización {organization.slug} "
                    f"para el usuario {user.email} (verificado por ERPNext/caché)"
                )
                # No devolvemos HttpResponseForbidden aquí, solo None.
                # La vista o un permiso posterior debería manejar el 403.
                return None

        # Adjuntar la organización al request
        return organization