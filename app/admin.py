from django.contrib import admin
from .models import StaffModel,CustomerModel,StaffRecordModel,CustomerRecordModel,StaffPatternModel,CustomerPatternModel,StaffSessionRecordModel,CustomerSessionRecordModel,StaffSessionPatternModel,CustomerSessionPatternModel,TransportRecordModel,TransportPatternModel,PlaceModel,PlaceRemarksModel


admin.site.register(StaffModel)
admin.site.register(CustomerModel)
admin.site.register(StaffRecordModel)
admin.site.register(CustomerRecordModel)
admin.site.register(StaffPatternModel)
admin.site.register(CustomerPatternModel)
admin.site.register(StaffSessionRecordModel)
admin.site.register(CustomerSessionRecordModel)
admin.site.register(StaffSessionPatternModel)
admin.site.register(CustomerSessionPatternModel)
admin.site.register(TransportRecordModel)
admin.site.register(TransportPatternModel)
admin.site.register(PlaceModel)
admin.site.register(PlaceRemarksModel)