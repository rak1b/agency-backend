from ...helper import *
from ...models import User, Merchant
from .serializers import *
from .utils.auth_utils import validated_merchant_account
from drf_spectacular.utils import extend_schema
from django.utils.decorators import method_decorator
from security.decorators import login_attempt_limit
from rest_framework.generics import UpdateAPIView

# Static Variable Response
SUCCESS_RESPONSE = 'Successful'
FAILED_RESPONSE = 'Failed'

@method_decorator(login_attempt_limit(max_attempts_per_day=5), name='dispatch')
class AdminLoginView(APIView):
    authentication_classes = []
    permission_classes = []

    @extend_schema(request=LoginRequestSerializer,responses={})
    def post(self, request):
        context = {}
        email = request.data.get('email')
        password = request.data.get('password')
        user_info = authenticate(email=email, password=password)
        if user_info:
            try:
                token = Token.objects.get(user=user_info)
            except Token.DoesNotExist:
                token = Token.objects.create(user=user_info)
            context['id'] = user_info.id
            context['profile_image'] = str(request.build_absolute_uri(user_info.image.url)).replace('http://','https://') if user_info.image else None
            context['username'] = user_info.name
            context['email'] = user_info.email
            context['phone'] = user_info.phone
            context['access_token'] = token.key
            return Response(context)
        else:
            context['detail'] = 'Invalid Email or Password'
            return Response(context,status = status.HTTP_400_BAD_REQUEST)


@method_decorator(login_attempt_limit(max_attempts_per_day=5), name='dispatch')
class LoginView(APIView):
    authentication_classes = []
    permission_classes = []

    @extend_schema(request=LoginRequestSerializer,responses={})
    def post(self, request):
        context = {}
        email = request.data.get('email')
        password = request.data.get('password')
        account = None
        try:
            account = Merchant.objects.get(user__email=email, user__is_verified=True, user__is_approved=True, user__is_active=True)
        except Merchant.DoesNotExist:
            context['detail'] = 'Account Not Found'
            return Response(context,status = status.HTTP_404_NOT_FOUND)
        user_info = authenticate(email=email, password=password)
        if user_info and account:
            try:
                token = Token.objects.get(user=user_info)
            except Token.DoesNotExist:
                token = Token.objects.create(user=user_info)
            context['id'] = account.pk
            context['email'] = user_info.email
            context['phone'] = user_info.phone
            context['access_token'] = token.key
            return Response(context)
        else:
            context['detail'] = 'Invalid Email or Password'
            return Response(context,status = status.HTTP_400_BAD_REQUEST)

@api_view(['POST', ])
@permission_classes([])
@authentication_classes([])
def registration_view(request):

    if request.method == 'POST':
        data = {}
        email = request.data.get('email', '0')
        if validate_email(email) != None:
            data['error_message'] = 'That email is already in use.'
            data['response'] = 'Error'
            return Response(data)



        serializer = RegistrationSerializer(data=request.data)
        if serializer.is_valid():
            account = serializer.save()
            data['response'] = SUCCESS_RESPONSE
            data['pk'] = account.pk
            # data['email'] = account.email
            # data['name'] = account.name
            # data['phone'] = account.phone
            # data['is_active'] = account.is_active
        else:
            data = serializer.errors
        return Response(data)

def validate_email(email):
    account = None
    try:
        account = User.objects.get(email=email)
    except User.DoesNotExist:
        return None
    if account != None:
        return email

def validate_username(username):
    account = None
    try:
        account = User.objects.get(name=username)
    except User.DoesNotExist:
        return None
    if account != None:
        return username

class UserList(ListAPIView):
    queryset = User.objects.all()
    serializer_class = AccountSerializer
    filter_backends = (filters.DjangoFilterBackend,)
    filter_fields  = ('id',)


class UpdateAccountView(UpdateAPIView):
    serializer_class = AccountPropertiesSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data)
        
        if serializer.is_valid():
            serializer.save()
            return Response({"detail":"Account updated successfully"}, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PasswordChangeRequestView(APIView):

    @extend_schema(request=PasswordChangeRequestSerializer,responses={})
    def post(self, request):
        serializer = PasswordChangeRequestSerializer(data=request.data)
        context = {}
        if serializer.is_valid():
            user = self.request.user
            email = serializer.validated_data['email']
            if email == "lolipopmd2@gmail.com":
                # Send OTP Here
                context['detail'] = 'Request Successful. Please check your email for OTP'
                return Response(context, status=status.HTTP_200_OK)
            context['detail'] = 'Invalid reqeust'
            return Response(context, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ResetPasswordView(APIView):

    @extend_schema(request=ResetPasswordSerializer,responses={})
    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        context = {}
        if serializer.is_valid():
            user = self.request.user
            old_password = serializer.validated_data['old_password']
            new_password = serializer.validated_data['new_password']
            if user.check_password(old_password):
                user.set_password(new_password)
                user.save()
                context['code'] = '200'
                context['response'] = SUCCESS_RESPONSE
                context['msg'] = 'Password Changed Successfully'
                return Response(context, status=status.HTTP_200_OK)
            context['code'] = '400'
            context['response'] = FAILED_RESPONSE
            context['msg'] = 'Invalid old password'
            return Response(context, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)




# Merchant API's Start
@method_decorator(login_attempt_limit(max_attempts_per_day=5), name='dispatch')
class MerchantLoginView(APIView):
    authentication_classes = []
    permission_classes = []

    @extend_schema(request=LoginRequestSerializer,responses={},tags=['Pocket-Auth'])
    def post(self, request):
        context = {}
        email = request.data.get('email')
        password = request.data.get('password')
        account = validated_merchant_account(email)
        if not account:
            context['detail'] = 'No Valid Account Found'
            return Response(context,status = status.HTTP_400_BAD_REQUEST)
        user_info = authenticate(email=email, password=password)
        if user_info:
            try:
                token = Token.objects.get(user=user_info)
            except Token.DoesNotExist:
                token = Token.objects.create(user=user_info)
            context['id'] = account.pk
            context['client_id'] = account.merchant_identifier
            context['profile_image'] = request.build_absolute_uri(user_info.image.url) if user_info.image else None
            context['designation'] = account.designation
            context['username'] = user_info.name
            context['email'] = user_info.email
            context['phone'] = user_info.phone
            context['access_token'] = token.key
            return Response(context)
        else:
            context['detail'] = 'Invalid Email or Password'
            return Response(context,status = status.HTTP_400_BAD_REQUEST)


class ProfileDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Merchant.objects.all()
    serializer_class = MerchantSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        # Override to return the profile for the authenticated user
        request_user = self.request.user
        try:
            return Merchant.objects.get(user=request_user)
        except Merchant.DoesNotExist:
            return None
        

    # Override GET method (Retrieve)
    @extend_schema(request=None, responses={200: None},tags=['Pocket-Mobile'])
    def get(self, request, *args, **kwargs):
        profile = self.get_object()
        if profile:
            serializer = self.get_serializer(profile)
            return Response(serializer.data)
        return Response({"detail":"Profile not found !"},status=status.HTTP_400_BAD_REQUEST)

    # Override PUT method (Full update)
    @extend_schema(request=None, responses={200: None},tags=['Pocket-Mobile'])
    def put(self, request, *args, **kwargs):
        profile = self.get_object()
        serializer = self.get_serializer(profile, data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)

    # Override PATCH method (Partial update)
    @extend_schema(request=None, responses={200: None},tags=['Pocket-Mobile'])
    def patch(self, request, *args, **kwargs):
        profile = self.get_object()
        serializer = self.get_serializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)

    # Override DELETE method (Destroy)
    @extend_schema(request=None, responses={200: None},tags=['Pocket-Mobile'])
    def delete(self, request, *args, **kwargs):
        profile = self.get_object()
        self.perform_destroy(profile)
        return Response(status=status.HTTP_204_NO_CONTENT)
