from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework import generics, permissions, status
from rest_framework.response import Response

from userservice.models import Users

from .models import KYC
from .serializers import KYCSerializer


@method_decorator(csrf_exempt, name="dispatch")
class RetrieveMerchantKyc(generics.ListAPIView):
    """View class to retrieve merchant kyc details"""

    queryset = Users.objects.all()
    serializer_class = KYCSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs) -> Response:
        try:
            user = Users.objects.get(id=request.user.id)
        except Users.DoesNotExist:
            return Response(
                {"status": "error", "response": "Invalid user"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        kyc_record = KYC.objects.filter(user=user).first()

        if kyc_record:
            serializer = self.get_serializer(kyc_record)
            return Response(
                {"status": "success", "response": serializer.data},
                status=status.HTTP_200_OK,
            )
        else:
            return Response(
                {"status": "error", "response": "KYC record not found"},
                status=status.HTTP_404_NOT_FOUND,
            )


@method_decorator(csrf_exempt, name="dispatch")
class UpdateMerchantKyc(generics.RetrieveUpdateAPIView):
    """View class to update user kyc details"""

    serializer_class = KYCSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if self.request.user.is_authenticated:
            return KYC.objects.filter(user=self.request.user)
        return KYC.objects.none()

    def update(self, request, *args, **kwargs) -> Response:
        """Update a user account with the supplied KYC details"""
        email = request.data.get("email")
        # Check if user already exists
        try:
            user = Users.objects.get(email=email)
        except Users.DoesNotExist:
            user = None

        # If user does not exist, return an error
        if user is None:
            return Response(
                {
                    "status": "error",
                    "response": "User does not exist.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        else:
            request.data["user"] = user.id
            kyc_record = KYC.objects.filter(user=user).first()
            serializer = self.get_serializer(kyc_record, data=request.data, partial=True)
            if serializer.is_valid():
                self.perform_update(serializer)
                return Response(
                    {
                        "status": "success",
                        "response": serializer.data,
                    },
                    status=status.HTTP_200_OK,
                )
            else:
                return Response(
                    {"status": "error", "response": serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST,
                )
