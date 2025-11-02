from django.contrib import admin

from authentication.models import User


# User administration
@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("id", "full_name", "phone_number", "user_type", "date_joined")
    search_fields = ("full_name", "phone_number", "user_type")
    ordering = ("-date_joined",)
