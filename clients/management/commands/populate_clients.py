from django.core.management.base import BaseCommand
from clients.models import Client
from faker import Faker
import time

class Command(BaseCommand):
    help = 'Populate database with test clients for performance testing'

    def add_arguments(self, parser):
        parser.add_argument('--count', type=int, default=5000, help='Number of clients to create')

    def handle(self, *args, **options):
        count = options['count']
        fake = Faker('ru_RU')
        
        self.stdout.write(f'Creating {count} test clients...')
        
        start_time = time.time()
        
        # Create clients in batches to avoid memory issues
        batch_size = 1000
        for i in range(0, count, batch_size):
            batch_end = min(i + batch_size, count)
            clients_batch = []
            
            for j in range(i, batch_end):
                client = Client(
                    name=fake.company(),
                    address=fake.address()
                )
                clients_batch.append(client)
            
            Client.objects.bulk_create(clients_batch)
            self.stdout.write(f'Created clients {i+1} to {batch_end}')
        
        end_time = time.time()
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully created {count} clients in {end_time - start_time:.2f} seconds'
            )
        )