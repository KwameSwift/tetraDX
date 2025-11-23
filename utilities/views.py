from django.http import JsonResponse
from rest_framework import status
from rest_framework.views import APIView

from utilities.serializers import TestTypeSerializer


class AddTestTypes(APIView):
    # permission_classes = [IsAuthenticated]
    # authentication_classes = [JWTAuthentication]

    def post(self, request, *args, **kwargs):
        # user = request.user
        data = request.data

        # if user.user_type != UserType.LAB_TECHNICIAN.value:
        #     raise api_exception(
        #         "Unauthorized: Only Lab Technicians can add test types.",
        #     )

        serializer = TestTypeSerializer(data=data, context={"facility": None})
        if serializer.is_valid():
            serializer.save()

            # data = {
            #     "test_type": test_data.name,
            #     "tests": [
            #         {"id": test.id, "name": test.name} for test in test_data.tests.all()
            #     ],
            # }

            return JsonResponse(
                {
                    "status": "success",
                    "message": "Test type added successfully",
                    # "data": data,
                },
                status=status.HTTP_200_OK,
            )
        return JsonResponse(serializer.errors, status=400)
