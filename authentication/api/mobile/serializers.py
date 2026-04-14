from rest_framework import serializers
from ...models import User, Merchant
from django.core.files.storage import default_storage
from django.core.files.storage import FileSystemStorage


class LoginRequestSerializer(serializers.Serializer):
    email = serializers.CharField()
    password = serializers.CharField()

class RegistrationSerializer(serializers.ModelSerializer):

    password2 = serializers.CharField(
        style={'input_type': 'password'}, write_only=True)

    class Meta:
        model = User
        fields = ['email', 'name', 'password', 'password2','gender','address',
                  'phone', 'image','dob']
        extra_kwargs = {
            'password': {'write_only': True},
        }

    def save(self):

        account = User(
            email=self.validated_data['email'],
            name=self.validated_data['name'],
            phone=self.validated_data['phone'],
            # image=self.validated_data['image'],
            gender=self.validated_data['gender'],
            address=self.validated_data['address'],
            dob=self.validated_data['dob'],
            is_verified = True,
            is_approved = True
        )
        password = self.validated_data['password']
        password2 = self.validated_data['password2']
        if password != password2:
            raise serializers.ValidationError(
                {'password': 'Passwords must match.'})
        account.set_password(password)
        account.save()
        return account

class AccountSerializer(serializers.ModelSerializer):
    #sender_info=PostSerializerUser(many=True)
    #order_list=OrderSerializer(many=True)
    #checkout_list=OrderSerializer(many=True)
    # user_address = AccountAddressSerializer(many=True)
    class Meta:
        model = User
        fields = ['pk','email','name', 'phone','image',
        'last_login_ip','is_staff','is_superuser','is_verified','is_approved','is_active']
        depth = 1

class PasswordChangeRequestSerializer(serializers.Serializer):
    email = serializers.CharField()

    def validate(self, data):
        """
        Check that the start is before the stop.
        """
        try:
            q_user = User.objects.get(email=data['email'], is_active=True)
        except User.DoesNotExist:
            raise serializers.ValidationError({"email":"Invalid Email Provided"})
        
        return data

class ResetPasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField()
    new_password = serializers.CharField()
    confirm_new_password = serializers.CharField()

    def validate(self, attrs):
        new_password = attrs['new_password']
        confirm_new_password = attrs['confirm_new_password']
        if new_password != confirm_new_password:
            raise serializers.ValidationError({'confirm_new_password': ['Password does not match', ]})
        if len(new_password) < 6:
            raise serializers.ValidationError({'new_password': ['Password must be at least 6 digit', ]})
        return attrs

class AccountPropertiesSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = ['name','image']

class OnlyAccountSerializer(serializers.ModelSerializer):
   
    class Meta:
        model = User
        fields = ('pk','email','name', 'phone','image',
        'last_login_ip','is_staff','is_superuser','is_verified','is_approved','is_active')

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('image','name','email','phone','gender','address','is_active')

class MerchantSerializer(serializers.ModelSerializer):
    user = UserSerializer(many=False)
    class Meta:
        model = Merchant
        fields = ('uuid','merchant_identifier','designation','user')