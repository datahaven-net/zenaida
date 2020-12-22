import os

from django.db import models


class CSVFileSync(models.Model):

    executions = models.Manager()

    class Meta:
        app_label = 'board'
        base_manager_name = 'executions'
        default_manager_name = 'executions'

    created_at = models.DateTimeField(auto_now_add=True)

    input_filename = models.CharField(max_length=255, db_index=True)

    dry_run = models.BooleanField(default=True)

    status = models.CharField(
        max_length=10,
        choices=(
            ('started', 'STARTED', ),
            ('finished', 'FINISHED', ),
            ('failed', 'FAILED', ),
        ),
        default='started',
    )

    output_log = models.TextField(blank=True)

    processed_count = models.IntegerField(default=0)

    @property
    def filename(self):
        return os.path.basename(self.input_filename)

    def __str__(self):
        return 'CSVFileSync({}:{})'.format(self.filename, self.status)

    def __repr__(self):
        return 'CSVFileSync({}:{})'.format(self.filename, self.status)
