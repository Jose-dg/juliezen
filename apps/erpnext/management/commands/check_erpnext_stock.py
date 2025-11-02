import json
from django.core.management.base import BaseCommand, CommandError

from apps.erpnext.models import ERPNextCredential
from apps.erpnext.services.client import ERPNextClient, ERPNextClientError
from apps.organizations.models import Organization


class Command(BaseCommand):
    help = "Checks available 'Serial No' for a given item in a specific warehouse and company in ERPNext."

    def add_arguments(self, parser):
        parser.add_argument("item_code", type=str, help="The Item Code to check in ERPNext.")
        parser.add_argument(
            "--warehouse",
            type=str,
            required=True,
            help="The exact name of the Warehouse to check.",
        )
        parser.add_argument(
            "--company",
            type=str,
            required=True,
            help="The exact name of the Company that owns the warehouse.",
        )
        parser.add_argument(
            "--org",
            type=str,
            help="The Organization ID. If not provided, the first organization will be used.",
        )
        parser.add_argument("--limit", type=int, default=20, help="Number of serials to fetch.")

    def handle(self, *args, **options):
        item_code = options["item_code"]
        warehouse = options["warehouse"]
        company = options["company"]
        org_id = options["org"]
        limit = options["limit"]

        self.stdout.write(
            self.style.SUCCESS(
                f"--- Buscando {limit} seriales para el item '{item_code}' en el almacén '{warehouse}' de la compañía '{company}' ---"
            )
        )

        try:
            # 1. Obtener organización
            if org_id:
                organization = Organization.objects.get(id=org_id)
            else:
                organization = Organization.objects.first()
                if not organization:
                    raise CommandError("No organizations found in the database.")
            self.stdout.write(f"Usando la organización: {organization.name} ({organization.id})")

            # 2. Obtener credenciales
            credential = ERPNextCredential.objects.for_company(
                organization_id=organization.id, company=company
            )
            if not credential:
                raise CommandError(
                    f"No se encontraron credenciales de ERPNext para la compañía '{company}' en la organización seleccionada."
                )
            self.stdout.write(f"Usando la credencial de ERPNext: {credential.api_key[:5]}...\n")

            # 3. Crear cliente
            client = ERPNextClient(credential)

            # 4. MÉTODO CORRECTO: Buscar seriales según documentación oficial
            self.stdout.write("Consultando API de ERPNext...\n")
            
            serials = client.list_serial_numbers(
                item_code=item_code,
                warehouse=warehouse,
                status="Active",  # Opciones: Active, Inactive, Delivered, Expired
                limit=limit,
            )

            if not serials:
                self.stdout.write(
                    self.style.WARNING("--- RESULTADO: No se encontró NINGÚN número de serie disponible. ---")
                )
                self.stdout.write("Posibles razones:")
                self.stdout.write("  1. El Item Code no tiene seriales en ese warehouse")
                self.stdout.write("  2. El warehouse name no coincide exactamente (sensible a mayúsculas)")
                self.stdout.write("  3. Todos los seriales están con status diferente a 'Active'")
                self.stdout.write(f"  4. El item '{item_code}' no existe o no es serializado\n")
                
                # Debugging: Verificar si el item existe
                self._debug_item_info(client, item_code, warehouse)
                return

            # 5. Mostrar resultados
            self.stdout.write(self.style.SUCCESS(f"--- RESULTADO: Se encontraron {len(serials)} seriales disponibles: ---"))
            self.stdout.write(json.dumps(serials, indent=2))

        except Organization.DoesNotExist:
            raise CommandError(f"La organización con ID '{org_id}' no existe.")
        except ERPNextClientError as e:
            self.stderr.write(self.style.ERROR(f"Error en la comunicación con ERPNext: {e}"))
            self.stderr.write("\nVerifica:")
            self.stderr.write("  1. Credenciales de API correctas")
            self.stderr.write("  2. URL de ERPNext accesible")
            self.stderr.write("  3. Permisos de usuario en ERPNext")
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Ha ocurrido un error inesperado: {e}"))
            import traceback
            self.stderr.write(traceback.format_exc())

    def _debug_item_info(self, client, item_code, warehouse):
        """Helper para debug cuando no se encuentran seriales"""
        try:
            self.stdout.write("\n--- DEBUG: Verificando información del item ---")
            
            # Verificar si el item existe
            item = client.get_doc("Item", item_code)
            if item:
                self.stdout.write(f"✓ Item encontrado: {item.get('item_name')}")
                self.stdout.write(f"  - Has Serial No: {item.get('has_serial_no')}")
                self.stdout.write(f"  - Item Group: {item.get('item_group')}")
            
            # Verificar stock en el warehouse
            stock_info = client.get_stock_balance(item_code, warehouse)
            self.stdout.write(f"\n✓ Stock actual en warehouse '{warehouse}': {stock_info}")
            
            # Listar TODOS los seriales del item (sin filtro de warehouse)
            all_serials = client.list_serial_numbers(
                item_code=item_code,
                limit=5
            )
            if all_serials:
                self.stdout.write(f"\n✓ Se encontraron {len(all_serials)} seriales en OTROS warehouses:")
                for serial in all_serials[:3]:
                    self.stdout.write(f"  - {serial.get('name')} en warehouse: {serial.get('warehouse')}")
            
        except Exception as e:
            self.stdout.write(f"  ✗ Error en debug: {e}")
