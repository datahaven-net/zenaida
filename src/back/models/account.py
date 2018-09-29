from django.db import models
from django.contrib.auth.models import BaseUserManager
from django.contrib.auth.models import AbstractUser
  
  
class UserManager(BaseUserManager):

    def create_user(self, email, password=None, **kwargs):
        """
        Creates and saves a User with the given email and password.
        """
        if not email:
            raise ValueError('Users must have an email address')

        user = self.model(
            email=self.normalize_email(email),
        )
        user.is_active = False
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_staffuser(self, email, password, **kwargs):
        """
        Creates and saves a staff user with the given email and password.
        """
        user = self.create_user(
            email,
            password=password,
        )
        user.is_active = True
        user.is_staff = True
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password, **kwargs):
        """
        Creates and saves a superuser with the given email and password.
        """
        user = self.create_user(
            email,
            password=password,
        )
        user.is_active = True
        user.is_staff = True
        user.is_superuser = True
        user.save(using=self._db)
        return user


class Account(AbstractUser):

    users = UserManager()

    class Meta:
        app_label = 'back'
        base_manager_name = 'users'
        default_manager_name = 'users'

    EMAIL_FIELD = 'email'
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []
    
    # related fields:
    # profile -> back.models.profile.Profile

    email = models.EmailField(
        verbose_name='email address',
        max_length=255,
        unique=True,
        null=False,
        blank=False,
        help_text='user email address',
    )

    def __str__(self):
        return 'Account({})'.format(self.email)

    @property
    def username(self):
        """
        Field `username` is disabled.
        """
        return self.email

    @property
    def first_name(self):
        """
        Field `first_name` is disabled.
        """
        return self.email

    @property
    def last_name(self):
        """
        Field `last_name` is disabled.
        """
        return self.email
