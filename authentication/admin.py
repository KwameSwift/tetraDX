from django.contrib import admin

from authentication.models import User


# User administration
@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "full_name",
        "phone_number",
        "user_type_display",
        "date_joined",
    )
    search_fields = ("full_name", "phone_number", "user_type")
    ordering = ("-date_joined",)

    def user_type_display(self, obj):
        return obj.get_user_type_display()

    user_type_display.short_description = "User Type"
