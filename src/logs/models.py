from django.db import models


class RequestLog(models.Model):
    timestamp = models.DateTimeField(help_text="Time of the request", auto_now_add=True, db_index=True)
    ip_address = models.GenericIPAddressField(help_text="IP address of the requestor", blank=True, null=True, db_index=True)
    user = models.CharField(help_text="If captured, the name of the user who sent the request",
                            max_length=255, blank=True, default="", db_index=True)
    method = models.CharField(help_text="HTTP method", max_length=16, blank=True, default="", db_index=True)
    path = models.CharField(help_text="Request path", max_length=255, blank=True, default="", db_index=True)
    request = models.TextField(help_text="Request body", null=True, default="")
    status_code = models.IntegerField(help_text="Response HTTP status code", null=True, blank=True, default=None, db_index=True)
    exception = models.TextField(help_text="Exception info", blank=True, null=True, default=None)
    duration = models.FloatField(help_text="Duration of the response", default=0.0)

    @staticmethod
    def erase_old_records(num_records):
        RequestLog.objects.filter(
            pk__in=RequestLog.objects.order_by('timestamp').all().values_list('pk')[:num_records],
        ).delete()
