import requests
import time
from django.core.management.base import BaseCommand
from class.models import School

class Command(BaseCommand):
    help = 'Populate school coordinates using Nominatim geocoding'

    def handle(self, *args, **options):
        schools = School.objects.all()
        total = schools.count()
        updated = 0
        failed = 0

        self.stdout.write(f"Processing {total} schools...")

        for idx, school in enumerate(schools, 1):
            # Skip if already has custom coordinates (not default)
            if school.latitude != 28.7041 or school.longitude != 77.1025:
                self.stdout.write(f"[{idx}/{total}] {school.name} - Already has coordinates")
                continue

            try:
                # Build query: "School Name, Block, District, State, India"
                query = f"{school.name}, {school.block}, {school.district}, {school.state}, India"
                
                # Call Nominatim API
                response = requests.get(
                    'https://nominatim.openstreetmap.org/search',
                    params={
                        'q': query,
                        'format': 'json',
                        'limit': 1
                    },
                    headers={'User-Agent': 'CLAS-School-Locator/1.0'}
                )
                
                if response.status_code == 200 and response.json():
                    data = response.json()[0]
                    lat = float(data['lat'])
                    lng = float(data['lon'])
                    
                    school.latitude = lat
                    school.longitude = lng
                    school.save()
                    
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"[{idx}/{total}] {school.name} - Updated: ({lat:.6f}, {lng:.6f})"
                        )
                    )
                    updated += 1
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            f"[{idx}/{total}] {school.name} - Not found in Nominatim"
                        )
                    )
                    failed += 1
                
                # Rate limiting - Nominatim requests 1 per second
                time.sleep(1)
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f"[{idx}/{total}] {school.name} - Error: {str(e)}"
                    )
                )
                failed += 1
                time.sleep(1)

        self.stdout.write(
            self.style.SUCCESS(
                f"\n✓ Completed: {updated} updated, {failed} failed, {total - updated - failed} skipped"
            )
        )
