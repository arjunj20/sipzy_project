from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
import uuid


class UserManager(BaseUserManager):

    def create_user(self, fullname, email, password=None):
        if not email:
            raise ValueError("Email is required")
        if not fullname:
            raise ValueError("Fullname is required")

        user = self.model(
            email=self.normalize_email(email),
            fullname=fullname,
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, fullname, email, password=None):
        user = self.create_user(
            fullname=fullname,
            email=email,
            password=password,
        )
        user.is_superuser = True
        user.is_staff = True   # REQUIRED BY DJANGO
        user.is_active = True  # REQUIRED
        user.save(using=self._db)
        return user


class CustomUser(AbstractBaseUser, PermissionsMixin):

    fullname = models.CharField(max_length=100, null=True)
    email = models.EmailField(max_length=100, unique=True)

    is_active = models.BooleanField(default=True)
    is_superuser = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    is_loggedin = models.BooleanField(default=False)
    joined_date = models.DateField(auto_now_add=True)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['fullname']


    def __str__(self):
        return self.fullname or self.email or ""
    
class Address(models.Model):

   
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)    

    user =  models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="addresses")
    full_name = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=15)

    address_line1 = models.CharField(max_length=200)
    address_line2 = models.CharField(max_length=200, blank=True, null=True)

    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    country = models.CharField(max_length=100, default="India")
    pincode = models.CharField(max_length=10)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.full_name}"



