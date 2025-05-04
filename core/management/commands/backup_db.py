import os
import datetime
import subprocess
from django.core.management.base import BaseCommand
from django.conf import settings

class Command(BaseCommand):
    help = 'Backup the PostgreSQL database to a file'

    def add_arguments(self, parser):
        parser.add_argument(
            '--filename',
            default=None,
            help='Specify a filename for the backup (defaults to flood_monitoring_backup_YYYY-MM-DD_HHMMSS.sql)',
        )

    def handle(self, *args, **options):
        # Generate a default filename if not provided
        filename = options['filename']
        if not filename:
            timestamp = datetime.datetime.now().strftime('%Y-%m-%d_%H%M%S')
            filename = f'flood_monitoring_backup_{timestamp}.sql'
        
        # Ensure the backups directory exists
        backups_dir = os.path.join(settings.BASE_DIR, 'backups')
        os.makedirs(backups_dir, exist_ok=True)
        
        # Full path for the backup file
        backup_path = os.path.join(backups_dir, filename)
        
        # Get database credentials from environment variables
        db_name = os.environ.get('PGDATABASE')
        db_user = os.environ.get('PGUSER')
        db_password = os.environ.get('PGPASSWORD')
        db_host = os.environ.get('PGHOST')
        db_port = os.environ.get('PGPORT')
        
        # Create backup command
        pg_dump_cmd = ['pg_dump']
        
        if db_host:
            pg_dump_cmd.extend(['-h', db_host])
        if db_port:
            pg_dump_cmd.extend(['-p', db_port])
        if db_user:
            pg_dump_cmd.extend(['-U', db_user])
            
        # Always specify format as plain SQL
        pg_dump_cmd.extend(['-F', 'p'])
        
        # Add database name
        if db_name:
            pg_dump_cmd.append(db_name)
            
        # Redirect output to file
        pg_dump_cmd.extend(['-f', backup_path])
        
        # Set PGPASSWORD environment variable for the subprocess
        env = os.environ.copy()
        if db_password:
            env['PGPASSWORD'] = db_password
            
        try:
            # Execute pg_dump command
            self.stdout.write(f"Running: {' '.join(pg_dump_cmd)}")
            result = subprocess.run(
                pg_dump_cmd,
                env=env,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            
            # Check if backup file was created and has content
            if os.path.exists(backup_path) and os.path.getsize(backup_path) > 0:
                self.stdout.write(self.style.SUCCESS(
                    f'Successfully backed up database to {backup_path}'
                ))
            else:
                self.stdout.write(self.style.ERROR(
                    f'Backup file was created but appears to be empty.'
                ))
                
        except subprocess.CalledProcessError as e:
            self.stdout.write(self.style.ERROR(
                f'Failed to backup database: {e}\n'
                f'Error output: {e.stderr.decode()}'
            ))
        except Exception as e:
            self.stdout.write(self.style.ERROR(
                f'Unexpected error during backup: {str(e)}'
            ))
