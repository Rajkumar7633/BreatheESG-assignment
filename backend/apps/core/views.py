from rest_framework import viewsets, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from .models import Organization, User
from .serializers import OrganizationSerializer, UserSerializer, UserProfileSerializer


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def me(request):
    serializer = UserProfileSerializer(request.user)
    return Response(serializer.data)


class OrganizationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = OrganizationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if request := self.request:
            if request.user.is_superuser:
                return Organization.objects.all()
            if request.user.organization:
                return Organization.objects.filter(id=request.user.organization.id)
        return Organization.objects.none()
