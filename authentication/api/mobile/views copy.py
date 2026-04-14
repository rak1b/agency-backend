from ...helper import *
from ...models import User
from .serializers import *
from drf_spectacular.utils import extend_schema
from django.utils.decorators import method_decorator
from security.decorators import login_attempt_limit

# Static Variable Response
SUCCESS_RESPONSE = 'Successful'
FAILED_RESPONSE = 'Failed'

# @login_attempt_limit(max_attempts_per_day=10)
@method_decorator(login_attempt_limit(max_attempts_per_day=5), name='dispatch')
class LoginView(APIView):
    authentication_classes = []
    permission_classes = []

    @extend_schema(request=LoginRequestSerializer,responses={})
    def post(self, request):
        context = {}
        email = request.data.get('email')
        password = request.data.get('password')
        try:
            user = User.objects.get(email = email)
        except User.DoesNotExist:
            context['detail'] = 'User Not Found'
            return Response(context,status = status.HTTP_404_NOT_FOUND)
        account = authenticate(email=email, password=password)
        if account:
            try:
                token = Token.objects.get(user=account)
            except Token.DoesNotExist:
                token = Token.objects.create(user=account)
            context['code'] = '200'
            context['response'] = SUCCESS_RESPONSE
            context['user_id'] = account.pk
            context['token'] = token.key
            return Response(context)
        else:
            context['code'] = '401'
            context['status'] = FAILED_RESPONSE
            context['msg'] = 'Invalid Email or Password'
            return Response(context,status = status.HTTP_401_UNAUTHORIZED)


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

        username = request.data.get('username', '0')
        if validate_username(username) != None:
            data['error_message'] = 'That username is already in use.'
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


# @permission_classes([])
# @authentication_classes([])
class UserList(ListAPIView):
    queryset = User.objects.all()
    serializer_class = AccountSerializer
    filter_backends = (filters.DjangoFilterBackend,)
    filter_fields  = ('id',)


# Account update properties
# Response: https://gist.github.com/mitchtabian/72bb4c4811199b1d303eb2d71ec932b2
# Url: https://<your-domain>/api/account/properties/update
# Headers: Authorization: Token <token>
@api_view(['PUT', ])
@permission_classes((IsAuthenticated, ))
def update_account_view(request):
    try:
        account = request.user
    except User.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    if request.method == 'PUT':
        serializer = AccountPropertiesSerializer(account, data=request.data)
        data = {}
        if serializer.is_valid():
            serializer.save()
            data['response'] = 'Account update success'
            return Response(data=data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class PersonalDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = User.objects.all()
    serializer_class = OnlyAccountSerializer

    def retrieve(self, request, *args, **kwargs):
        super(PersonalDetailView, self).retrieve(request, args, kwargs)
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        data = serializer.data
        response = {"status_code": status.HTTP_200_OK,
                    "message": "successfully retrieved",
                    "result": data}
        return Response(response)

class PasswordChangeView(APIView):
    
    def post(self, request):
        serializer = PasswordChangeSerializer(data=request.data)
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






# class ChangePasswordView(UpdateAPIView):
#     serializer_class = ChangePasswordSerializer
#     model = Account
#     permission_classes = (IsAuthenticated,)
#     authentication_classes = (TokenAuthentication,)

#     def get_object(self, queryset=None):
#         obj = self.request.user
#         return obj

#     def update(self, request, *args, **kwargs):
#         self.object = self.get_object()
#         serializer = self.get_serializer(data=request.data)

#         if serializer.is_valid():
#             # Check old password
#             if not self.object.check_password(serializer.data.get("old_password")):
#                 return Response({"old_password": ["Wrong password."]}, status=status.HTTP_400_BAD_REQUEST)

#             # confirm the new passwords match
#             new_password = serializer.data.get("new_password")
#             confirm_new_password = serializer.data.get("confirm_new_password")
#             if new_password != confirm_new_password:
#                 return Response({"new_password": ["New passwords must match"]}, status=status.HTTP_400_BAD_REQUEST)

#             # set_password also hashes the password that the user will get
#             self.object.set_password(serializer.data.get("new_password"))
#             self.object.save()
#             return Response({"response":"successfully changed password"}, status=status.HTTP_200_OK)

#         return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)