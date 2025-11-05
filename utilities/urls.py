from django.urls import path

from utilities.views import AddTestTypes

app_name = "utilities"

urlpatterns = [  # Get Test Types
    path(
        "add-test-types",
        AddTestTypes.as_view(),
        name="add-test-types",
    ),
]
