from django.contrib import admin

from nested_admin import NestedModelAdmin  # @UnresolvedImport

from board.models.csv_file_sync import CSVFileSync


class CSVFileSyncAdmin(NestedModelAdmin):
    pass


admin.site.register(CSVFileSync, CSVFileSyncAdmin)
