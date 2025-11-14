from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin


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

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['fullname']

    def __str__(self):
        return self.fullname
