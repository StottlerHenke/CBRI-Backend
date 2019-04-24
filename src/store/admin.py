from django.contrib import admin

from .models import *


class MeasurementAdmin(admin.ModelAdmin):
    list_display = ('date', 'repository')


admin.site.register(Organization)
admin.site.register(InsightUser)
admin.site.register(Repository)
admin.site.register(Measurement, MeasurementAdmin)
