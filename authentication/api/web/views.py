from datetime import datetime
from authentication.permissions import HasCustomPermission
from authentication.utils import auth_utils, email_utils
from .serializers import *
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from ..utils.auth_utils import validated_merchant_user, process_code
from ..utils.jwt_utils import generate_tokens, verify_jwt_token
from authentication.models import User, Merchant, Role, Permission, RolePermission
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.contrib.auth import authenticate
from rest_framework import status
from rest_framework import viewsets
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from rest_framework.generics import UpdateAPIView
from rest_framework.permissions import AllowAny
from django.shortcuts import get_object_or_404
from rest_framework.generics import UpdateAPIView
from django_filters.rest_framework import DjangoFilterBackend
from Config.utils.pagination import PageNumberPagination

from django.db.models import Q
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample
from rest_framework.parsers import MultiPartParser, FormParser

from django.utils.decorators import method_decorator
from security.decorators import login_attempt_limit
from authentication.api.mobile.utils.auth_utils import validated_user_account, updateLastLoginInfo
from authentication.api.utils.auth_utils import verify_confirmation, validated_merchant_user
from django.apps import apps
from drf_spectacular.types import OpenApiTypes
from rest_framework import mixins
from django.contrib.auth.hashers import make_password
from utils.common_import_utils import *
from utils.cloudflare_minio_utils import compress_and_upload_to_r2, upload_file_to_r2
from PIL import Image
import os
import uuid
from rest_framework import status
from rest_framework.response import Response


class UserAPI(viewsets.ModelViewSet):
    queryset = User.objects.all().order_by('-created_at')
    serializer_class = UserSerializer
    lookup_field = 'slug'
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend,SearchFilter]
    search_fields = ['name','email','phone',]
    DYNAMIC_PERMISSION_CODE = 'user'
    filterset_fields = ['role','user_id','gender','is_active']
    pagination_class = PageNumberPagination

    def get_queryset(self):
        emails = ['rakib@admin.com','admin@admin.com','inventory@admin.com','salmansadi165324@gmail.com']
        return super().get_queryset().exclude(email__in=emails)
        
    
    def destroy(self, request, *args, **kwargs):
        current_user = request.user
        user = self.get_object()
        if current_user.id == user.id:
            return Response({"detail": "You cannot delete your own account"}, status=status.HTTP_400_BAD_REQUEST)
        return super().destroy(request, *args, **kwargs)


# Define your views here
class WebUserLoginView(APIView):
    authentication_classes = []
    permission_classes = []

    @extend_schema(
        request=LoginRequestSerializer,
        responses={
            200: OpenApiTypes.OBJECT,
            400: OpenApiTypes.OBJECT,
        },
        examples=[
            OpenApiExample(
                'Request',
                value={"email": "user@example.com", "password": "123456"},
                request_only=True
            ),
            OpenApiExample(
                'Success',
                value={
                    "id": 1,
                    "profile_image": "https://cdn.example.com/u.png",
                    "name": "User",
                    "email": "user@example.com",
                    "phone": "+8801...",
                    "access_token": "<jwt>",
                    "refresh_token": "<jwt>",
                    "user_slug": "user-slug",
                },
                status_codes=['200'],
                response_only=True
            ),
            OpenApiExample(
                'Invalid credentials',
                value={"detail": "Invalid Email or Password"},
                status_codes=['400'],
                response_only=True
            )
        ],
        tags=['Authentication & Authorization']
    )
    def post(self, request):
        context = {}
        mid_info = request.data.get('mid')
        email = request.data.get('email')
        password = request.data.get('password')
        account = validated_user_account(email)
        if not account:
            context['detail'] = 'No Valid Account Found'
            return Response(context,status = status.HTTP_400_BAD_REQUEST)
        user_info = authenticate(email=email, password=password)

        if user_info:
            if not user_info.is_active:
                context['detail'] = 'User is disabled, please contact admin'
                return Response(context,status = status.HTTP_400_BAD_REQUEST)
            updateLastLoginInfo(request,user_info)
            context['id'] = account.pk
            context['profile_image'] = user_info.image_url  
            context['username'] = user_info.name
            context['email'] = user_info.email
            context['phone'] = user_info.phone
            access_token, refresh_token = generate_tokens({'user_id':user_info.id,'user_name':user_info.name,'role':'3','role_title':'merchant'})
            context['access_token'] = access_token
            context['refresh_token'] = refresh_token
            context['user_slug'] = user_info.slug
            return Response(context)
        else:
            context['detail'] = 'Invalid Email or Password'
            return Response(context,status = status.HTTP_400_BAD_REQUEST)

@method_decorator(login_attempt_limit(max_attempts_per_day=5), name='dispatch')
class WebLoginView(APIView):
    authentication_classes = []
    permission_classes = []

    @extend_schema(
        request=LoginRequestSerializer,
        responses={
            200: OpenApiTypes.OBJECT,
            400: OpenApiTypes.OBJECT,
        },
        examples=[
            OpenApiExample('Request', value={"email": "rakib@admin.com", "password": "Rakibrk1"}, request_only=True),
            OpenApiExample('Success', value={"access_token": "<jwt>", "refresh_token": "<jwt>"}, status_codes=['200'], response_only=True),
            OpenApiExample('Invalid credentials', value={"detail": "Invalid Email or Password"}, status_codes=['400'], response_only=True)
        ],
        tags=['Authentication & Authorization']
    )
    def post(self, request):
        context = {}
        mid_info = request.data.get('mid')
        email = request.data.get('email')
        password = request.data.get('password')
        account = validated_user_account(email)
        if not account:
            context['detail'] = 'No Valid Account Found'
            return Response(context,status = status.HTTP_400_BAD_REQUEST)
        # verified = validate_mid_account(mid_info,account.merchant_identifier)
        # if not verified:
        #     return Response({"detail":"Invalid MID! Please contact your service provider."},status = status.HTTP_400_BAD_REQUEST)
        user_info = authenticate(email=email, password=password)
        if user_info:
            updateLastLoginInfo(request,user_info)
            # context['id'] = account.pk
            # context['client_id'] = account.merchant_identifier
            # context['profile_image'] = request.build_absolute_uri(user_info.image.url) if user_info.image else None
            # context['designation'] = account.designation
            # context['username'] = user_info.name
            # context['email'] = user_info.email
            # context['phone'] = user_info.phone
            access_token, refresh_token = generate_tokens({'user_id':account.user.id,'user_name':user_info.name,'role':'3','role_title':'merchant'})
            context['access_token'] = access_token
            context['refresh_token'] = refresh_token
            return Response(context)
        else:
            context['detail'] = 'Invalid Email or Password'
            return Response(context,status = status.HTTP_400_BAD_REQUEST)

class WebRefreshTokenView(APIView):
    authentication_classes =[]
    permission_classes = []
    
    @extend_schema(
        request=RefreshTokenReqeustSerializer,
        responses={
            200: OpenApiTypes.OBJECT,
            400: OpenApiTypes.OBJECT,
            401: OpenApiTypes.OBJECT,
        },
        examples=[
            OpenApiExample('Request', value={"refresh_token": "<jwt>"}, request_only=True),
            OpenApiExample('Success', value={"access_token": "<jwt>"}, status_codes=['200'], response_only=True),
            OpenApiExample('Invalid payload', value={"detail": "Invalid payload data"}, status_codes=['400'], response_only=True),
            OpenApiExample('Invalid token', value={"error": "Invalid or expired refresh token"}, status_codes=['401'], response_only=True)
        ],
        tags=['Authentication & Authorization']
    )
    def post(self, request):
        refresh_token = request.data.get('refresh_token')
        if not refresh_token:
            return Response({'detail': 'Invalid payload data'}, status=400)
        decoded_data = verify_jwt_token(refresh_token, token_type='refresh')
        
        if decoded_data:
            access_token, _ = generate_tokens({'user_id': decoded_data['user_id'], 'role': decoded_data['role']})
            return Response({"access_token":access_token})
        else:
            return Response({'error': 'Invalid or expired refresh token'}, status=401)


class PasswordChangeView(APIView):
    permission_classes = []
    authentication_classes = []
    serializer_class = ForgetPasswordRequestSerializer
    
    @extend_schema(request=ForgetPasswordRequestSerializer,tags=['Account-Util-API'])
    def post(self, request):
        serializer = ForgetPasswordRequestSerializer(data=request.data)
        if serializer.is_valid():
            email_or_phone = serializer.validated_data['email_or_phone']
            user = auth_utils.validated_user(email_or_phone)
            if user:
                import re
                regex = re.compile(r'([A-Za-z0-9]+[.-_])*[A-Za-z0-9]+@[A-Za-z0-9-]+(\.[A-Z|a-z]{2,})+')
                if re.fullmatch(regex, email_or_phone):
                    data = auth_utils.process_code(user.email)
                    email_utils.send_forget_password_email(user.email, data)
                    return Response({"detail":"An OTP has been sent to your email."},status=status.HTTP_200_OK)
                else:
                    confirmation = auth_utils.create_user_confirmation(user.phone)
                    # sms_utils.send_single_sms(confirmation.identifier,confirmation.code)
                    return Response({"detail":"An OTP has been sent to your phone."},status=status.HTTP_200_OK)
            return Response({"data":{"email_or_phone":["No valid account found"]}},status=status.HTTP_400_BAD_REQUEST)
        return Response({"data":serializer.errors},status=status.HTTP_400_BAD_REQUEST)

class PasswordChangeConfirmView(APIView):
    permission_classes = []
    authentication_classes = []
    serializer_class = ForgetPasswordConfirmSerializer
    
    @extend_schema(request=ForgetPasswordConfirmSerializer,tags=['Account-Util-API'])
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            email_or_phone = serializer.validated_data['email_or_phone']
            otp = serializer.validated_data['otp']
            new_password = serializer.validated_data['new_password']
            confirmation = auth_utils.verify_confirmation(email_or_phone,otp)
            if confirmation:
                confirmation.is_used = True
                confirmation.save()
                user = auth_utils.validated_user(email_or_phone)
                user.set_password(new_password)
                user.save()
                return Response({"detail":"Password reset successfully done."},status=status.HTTP_200_OK)
            return Response({"data":{"identifier":['Invalid otp or identifier']}},status=status.HTTP_400_BAD_REQUEST)
        return Response({"data":serializer.errors},status=status.HTTP_400_BAD_REQUEST)

class WebResetPasswordAPIView(APIView):
    permission_classes = [AllowAny]
    serializer_class = ResetPasswordRequestSerializer
    
    @extend_schema(request=ResetPasswordRequestSerializer,tags=['Account-Util-API'])
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            user = request.user
            old_password = serializer.validated_data['old_password']
            user_info = authenticate(email=user.email, password=old_password)
            if user_info:
                new_password = serializer.validated_data['new_password']
                user.set_password(new_password)
                user.save()
                return Response({"detail":"Password reset successfully done."},status=status.HTTP_200_OK)
            return Response({"detail": "Invalid old password"},status=status.HTTP_400_BAD_REQUEST)
        return Response({"data":serializer.errors},status=status.HTTP_400_BAD_REQUEST)





class UserPermissionsView(APIView):
    # authentication_classes = []
    # permission_classes = []
    permission_classes = [AllowAny]
    serializer_class = RolePermissionSerializer
    
    @extend_schema(request=RolePermissionSerializer,tags=['Authentication & Authorization'])
    def get(self, request, *args, **kwargs):
        user = request.user
        # user= User.objects.get(id=2)
        if user != "AnonymousUser":
            # Assuming user.roles is the related name for the M2M relationship
            roles = user.role.all()

            # Get all permissions from the roles
            role_permissions = RolePermission.objects.filter(role__in=roles).prefetch_related('permissions')

            # Gather all permission instances
            permissions = set()
            for rp in role_permissions:
                permissions.update(rp.permissions.all())

            # Optionally serialize permissions if needed
            permission_data = [perm.code for perm in permissions]  # Adjust fields as necessary

            # Include account details as well
            account_serializer = AccountDetailsSerializer(user, context={'request': request})

            response = {
                'data': {
                    # 'account': account_serializer.data,
                    'permissions': permission_data,
                },
                'detail': 'Account permissions retrieved successfully'
            }
            return Response(response, status=status.HTTP_200_OK)
        return Response({"data":{"account":["Account Not Found"]}},status=status.HTTP_400_BAD_REQUEST)
    
class SectionWiseUserPermissionAPI(viewsets.GenericViewSet,mixins.ListModelMixin):
    serializer_class = SectionWiseUserPermissionSerializer
    queryset = Section.objects.all()
    permission_classes = [AllowAny]
    CUSTOM_PERMISSION_CODE = 'view_all_permissions_section_wise'
    def get_queryset(self):
        user = self.request.user
        roles = user.role.all()
        role_permissions = RolePermission.objects.filter(role__in=roles).values_list('permissions',flat=True)
        sections = Section.objects.filter(permission_of_section__in=role_permissions).distinct()
        return sections
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['user'] = self.request.user
        context['request'] = self.request
        return context

class RoleViewSet(viewsets.GenericViewSet,mixins.ListModelMixin):
    """
    ViewSet for managing roles and their permissions.
    """
    queryset = Role.objects.all()
    serializer_class = AccountRoleSerializer
    filter_backends = [DjangoFilterBackend,SearchFilter]
    permission_classes = [AllowAny]
    DYNAMIC_PERMISSION_CODE = 'role'
    search_fields = ['name','description']
    
class AllSectionWisePermissionAPI(viewsets.GenericViewSet,mixins.ListModelMixin):
    queryset = Section.objects.all()
    serializer_class = AllSectionWisePermissionSerializer
    pagination_class = None
    permission_classes = [AllowAny]
    CUSTOM_PERMISSION_CODE = 'view_all_permissions_section_wise'
    
class AssignPermissionToRoleAPI(viewsets.ModelViewSet):
    serializer_class = AssignPermissionToRoleSerializer
    queryset = RolePermission.objects.all().order_by('-created_at')
    permission_classes = [AllowAny]
    DYNAMIC_PERMISSION_CODE = 'role'
    filter_backends = [DjangoFilterBackend,SearchFilter]
    search_fields = ['role__name']
    filterset_fields = ['role']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return RolePermissionListSerializer
        return self.serializer_class
    


def get_model_examples():
    model_examples = []
    for app_config in apps.get_app_configs():
        for model in app_config.get_models():
            if hasattr(model, 'history'):
                model_examples.append(
                    OpenApiExample(
                        f'{model._meta.verbose_name}',
                        value=f'{app_config.label}.{model.__name__}',
                        description=f'Example for {model._meta.verbose_name} model'
                    )
                )
    return model_examples

class HistoryViewSet(viewsets.ViewSet):
    permission_classes = [AllowAny]
    serializer_class = HistorySerializer
    pagination_class = PageNumberPagination
    CUSTOM_PERMISSION_CODE = 'view_history'
    

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='model',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Model name in format "app_name.ModelName"',
                examples=get_model_examples()
            ),
            OpenApiParameter(
                name='id',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='ID of the object to get history for',
                examples=[
                    OpenApiExample(
                        'Example ID',
                        value=123,
                        description='Example ID value'
                    )
                ]
            ),
            OpenApiParameter(
                name='start_date',
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
                description='Filter history records starting from this date'
            ),
            OpenApiParameter(
                name='end_date',
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
                description='Filter history records up to this date'
            )
        ],
        responses={
            200: HistorySerializer(many=True),
            400: {'detail': 'Model name and object ID are required.'},
            404: {'detail': 'Object not found.'}
        }
    )
    def list(self, request, *args, **kwargs):
        model_name = request.query_params.get('model')
        object_id = request.query_params.get('id')
        
        if not model_name or not object_id:
            return Response(
                {'detail': 'Model name and object ID are required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Get the model class
            model = apps.get_model(model_name)
            instance = model.objects.get(id=object_id)
            start_date = request.query_params.get('start_date')
            end_date = request.query_params.get('end_date')
            # Get history records with user prefetch to avoid N+1 queries
            history_records = instance.get_history(start_date, end_date).select_related('history_user')
            
            # Paginate the results
            paginator = self.pagination_class()
            page = paginator.paginate_queryset(history_records, request)
            
            if page is not None:
                serializer = self.serializer_class(page, many=True)
                return paginator.get_paginated_response(serializer.data)
            
            serializer = self.serializer_class(history_records, many=True)
            return Response(serializer.data)
            
        except LookupError:
            return Response(
                {'detail': 'Model not found.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        except model.DoesNotExist:
            return Response(
                {'detail': 'Object not found.'},
                status=status.HTTP_404_NOT_FOUND
            )


class CloudflareUploadAPI(APIView):
    permission_classes = [AllowAny, ]
    
    @extend_schema(
        request={
            'multipart/form-data': {
                'type': 'object',
                'properties': {
                    'file': {
                        'type': 'string',
                        'format': 'binary',
                        'description': 'Image file to upload (supported formats: JPG, PNG, WEBP)'
                    },
                    'width': {
                        'type': 'integer',
                        'description': 'Width to resize the image to (optional, default: 700)'
                    },
                    'height': {
                        'type': 'integer',
                        'description': 'Height to resize the image to (optional, default: 700)'
                    },
                    'quality': {
                        'type': 'integer',
                        'description': 'Image quality (1-100, optional, default: 100)'
                    },
                    'previous_file_url': {
                        'type': 'string',
                        'description': 'Previous file URL to delete (optional)'
                    }
                }
            }
        },
        responses={
            200: OpenApiTypes.OBJECT,
            400: OpenApiTypes.OBJECT,
            500: OpenApiTypes.OBJECT
        },
        examples=[
            OpenApiExample(
                'Success Response',
                value={
                    "message": "File uploaded successfully",
                    "file_url": "https://dwa.rakib.cloud/example_20240321123456_abc12.webp"
                },
                status_codes=['200']
            ),
            OpenApiExample(
                'Error Response',
                value={
                    "error": "No file provided"
                },
                status_codes=['400']
            )
        ],
        description='Upload an image file to Cloudflare R2 storage. The image will be compressed and converted to WebP format. You can specify custom width, height, and quality parameters.'
    )
    def post(self, request):
        try:
            file = request.data.get('file')
            if not file:
                return Response({"error": "No file provided"}, status=status.HTTP_400_BAD_REQUEST)
            
            # Get optional parameters with defaults
            width = request.data.get('width', 700)
            height = request.data.get('height', 700)
            quality = request.data.get('quality', 100)
            previous_file_url = request.data.get('previous_file_url', None)
            
            # Convert to integers if provided
            try:
                width = int(width) if width else None
                height = int(height) if height else None
                quality = int(quality) if quality else 100
            except (ValueError, TypeError):
                return Response({
                    "error": "Width, height, and quality must be valid integers"
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Validate quality range
            if quality < 1 or quality > 100:
                return Response({
                    "error": "Quality must be between 1 and 100"
                }, status=status.HTTP_400_BAD_REQUEST)
            
            image = Image.open(file)
            file_name = os.path.splitext(file.name)[0]
            file_url = compress_and_upload_to_r2(
                image=image,
                file_name=file_name,
                quality=quality,
                width=width,
                height=height
            )
            if previous_file_url:
                from utils.cloudflare_minio_utils import delete_image_from_r2
                delete_image_from_r2(previous_file_url)
                
            if file_url:
                return Response({
                    "message": "File uploaded successfully",
                    "file_url": file_url
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    "error": "Failed to upload file"
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
        except Exception as e:
            return Response({
                "error": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            

class CloudflareFileUploadAPI(APIView):
    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(
        request={
            'multipart/form-data': {
                'type': 'object',
                'properties': {
                    'file': {
                        'type': 'string',
                        'format': 'binary',
                        'description': 'Any file to upload without optimization (image, pdf, doc, etc.)'
                    },
                    'previous_file_url': {
                        'type': 'string',
                        'description': 'Previous file URL to delete after successful upload (optional)'
                    }
                },
                'required': ['file']
            }
        },
        responses={
            200: OpenApiTypes.OBJECT,
            400: OpenApiTypes.OBJECT,
            500: OpenApiTypes.OBJECT
        },
        examples=[
            OpenApiExample(
                'Success Response',
                value={
                    "message": "File uploaded successfully",
                    "file_url": "https://media-inventory.paymentsave.co.uk/file_20260414123456_a1b2c.pdf"
                },
                status_codes=['200']
            ),
            OpenApiExample(
                'Error Response',
                value={"error": "No file provided"},
                status_codes=['400']
            )
        ],
        description='Upload any file to Cloudflare R2 without resizing, compression, or image optimization.'
    )
    def post(self, request):
        try:
            uploaded_file = request.data.get('file')
            if not uploaded_file:
                return Response({"error": "No file provided"}, status=status.HTTP_400_BAD_REQUEST)

            previous_file_url = request.data.get('previous_file_url')

            original_name, original_extension = os.path.splitext(uploaded_file.name)
            timestamp_value = datetime.now().strftime("%Y%m%d%H%M%S")
            short_unique_id = uuid.uuid4().hex[:5]
            uploaded_file.name = f"{original_name}_{timestamp_value}_{short_unique_id}{original_extension}"

            file_url = upload_file_to_r2(uploaded_file)

            if previous_file_url:
                from utils.cloudflare_minio_utils import delete_image_from_r2
                delete_image_from_r2(previous_file_url)

            if file_url:
                return Response(
                    {"message": "File uploaded successfully", "file_url": file_url},
                    status=status.HTTP_200_OK
                )

            return Response({"error": "Failed to upload file"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as error:
            return Response({"error": str(error)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# class CloudflareDeleteAPI(APIView):
#     permission_classes = [AllowAny, ]
    
#     @extend_schema(request=CloudflareDeleteSerializer,responses={})
#     def post(self, request):
#         from utils.cloudflare_minio_utils import delete_image_from_r2
#         serializer = CloudflareDeleteSerializer(data=request.data)
#         if serializer.is_valid():
#             file_url = serializer.validated_data['file_url']
#             delete_image_from_r2(file_url)
#             return Response({"message": "File deleted successfully"}, status=status.HTTP_200_OK)
#         return Response({"data":serializer.errors},status=status.HTTP_400_BAD_REQUEST)
