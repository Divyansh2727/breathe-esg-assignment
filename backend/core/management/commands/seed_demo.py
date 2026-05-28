from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from core.models import DataSource, Organization, OrganizationMembership, PlantLookup
from core.services.ingestion import run_ingestion

User = get_user_model()
SAMPLE_DIR = Path(__file__).resolve().parents[4] / "sample_data"


class Command(BaseCommand):
    help = "Seed demo tenant, analyst user, and sample ingestions"

    def handle(self, *args, **options):
        org, _ = Organization.objects.get_or_create(
            slug="acme-corp",
            defaults={"name": "Acme Corporation (Demo)"},
        )
        user, created = User.objects.get_or_create(
            username="analyst",
            defaults={"email": "analyst@demo.local", "is_staff": True},
        )
        if created:
            user.set_password("demo-analyst-2025")
            user.save()
            self.stdout.write(self.style.SUCCESS("Created user analyst / demo-analyst-2025"))

        OrganizationMembership.objects.get_or_create(
            user=user, organization=org, defaults={"role": "analyst"}
        )

        plants = [
            ("1000", "Berlin HQ", "DE"),
            ("2000", "Munich Plant", "DE"),
            ("US01", "Austin TX Office", "US"),
        ]
        for code, name, country in plants:
            PlantLookup.objects.update_or_create(
                organization=org,
                plant_code=code,
                defaults={"site_name": name, "country": country},
            )

        sources = {}
        for st, label in DataSource.SourceType.choices:
            ds, _ = DataSource.objects.get_or_create(
                organization=org,
                source_type=st,
                name=label,
            )
            sources[st] = ds

        files = {
            DataSource.SourceType.SAP: "sap_fuel_procurement.csv",
            DataSource.SourceType.UTILITY: "utility_electricity.csv",
            DataSource.SourceType.TRAVEL: "concur_travel.json",
        }
        for st, fname in files.items():
            path = SAMPLE_DIR / fname
            if path.exists():
                content = path.read_bytes()
                batch = run_ingestion(
                    organization=org,
                    data_source=sources[st],
                    content=content,
                    filename=fname,
                    user=user,
                )
                self.stdout.write(f"Ingested {fname}: {batch.success_count} ok, {batch.error_count} issues")

        self.stdout.write(self.style.SUCCESS(f"Demo org id={org.id} slug={org.slug}"))
