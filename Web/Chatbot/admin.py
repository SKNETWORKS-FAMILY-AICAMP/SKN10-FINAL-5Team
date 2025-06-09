from django.contrib import admin
from .models import YouthPolicy

# Register your models here.
@admin.register(YouthPolicy)
class YouthPolicyAdmin(admin.ModelAdmin):
    list_display = ('policy_id', 'name', 'main_category', 'region')
    search_fields = ('name', 'keywords', 'description')