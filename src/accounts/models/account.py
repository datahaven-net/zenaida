from django.db import models

from django.contrib.auth.models import BaseUserManager
from django.contrib.auth.models import AbstractUser


class UserManager(BaseUserManager):

    def create_user(self, email, password=None, is_active=False, **kwargs):
        """
        Creates and saves a User with the given email and password.
        """
        if not email:
            raise ValueError('Users must have an email address')

        user = self.model(
            email=self.normalize_email(email),
        )
        user.is_active = is_active
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
        app_label = 'accounts'
        base_manager_name = 'users'
        default_manager_name = 'users'

    EMAIL_FIELD = 'email'
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    # related fields:
    # activations -> accounts.models.activation.Activation
    # notifications -> accounts.models.notification.Notification
    # profile -> back.models.profile.Profile
    # domains -> back.models.domain.Domain
    # contacts -> back.models.contact.Contact
    # registrants -> back.models.contact.Registrant
    # payments -> billing.models.payment.Payment
    # orders -> billing.models.order.Order

    email = models.EmailField(
        verbose_name='email address',
        max_length=255,
        unique=True,
        null=False,
        blank=False,
        help_text='user email address',
    )

    balance = models.FloatField(null=False, blank=False, default=0.0)
    notes = models.TextField(
        null=True,
        blank=True,
        default=None,
        help_text='any note regarding this account such as manual balance changes.'
    )

    def __str__(self):
        return 'Account({} {})'.format(self.email, self.balance)

    def __repr__(self):
        return 'Account({} {})'.format(self.email, self.balance)

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
