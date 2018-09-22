from django.db import models
from django.contrib.auth.models import BaseUserManager
from django.contrib.auth.models import AbstractBaseUser
  
  
class UserManager(BaseUserManager):

    def create_user(self, email, password=None):
        """
        Creates and saves a User with the given email and password.
        """
        if not email:
            raise ValueError('Users must have an email address')

        user = self.model(
            email=self.normalize_email(email),
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_staffuser(self, email, password):
        """
        Creates and saves a staff user with the given email and password.
        """
        user = self.create_user(
            email,
            password=password,
        )
        user.staff = True
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password):
        """
        Creates and saves a superuser with the given email and password.
        """
        user = self.create_user(
            email,
            password=password,
        )
        user.staff = True
        user.admin = True
        user.save(using=self._db)
        return user


class Account(AbstractBaseUser):

    class Meta:
        app_label = 'back'

    USERNAME_FIELD = 'email'

    REQUIRED_FIELDS = []

    users = UserManager()

    email = models.EmailField(
        verbose_name='email address',
        max_length=255,
        unique=True,
        help_text='user email address',
    )

    active = models.BooleanField(default=True, help_text='account is active')

    staff = models.BooleanField(default=False, help_text='administrator permissions')

    admin = models.BooleanField(default=False, help_text='superuser permissions')
 

    def get_full_name(self):
        return self.email
 
    def get_short_name(self):
        return self.email
 
    def __str__(self):
        return self.email
 
    def has_perm(self, perm, obj=None):
        return True
 
    def has_module_perms(self, app_label):
        return True
 
    @property
    def is_staff(self):
        return self.staff
 
    @property
    def is_admin(self):
        return self.admin
    
    @property
    def is_superuser(self):
        return self.admin
 
    @property
    def is_active(self):
        return self.active

