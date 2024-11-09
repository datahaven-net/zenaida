from django.utils.translation import gettext_lazy as _
from django.urls import reverse

from grappelli.dashboard import modules, Dashboard


class CustomIndexDashboard(Dashboard):

    def init_with_context(self, context):
        self.children.append(modules.AppList(
            _('Database tables'),
            collapsible=True,
            column=1,
            css_classes=('collapse closed', ),
        ))

        self.children.append(modules.LinkList(
            _('Management'),
            column=2,
            children=[
                {
                    'title': _('Account balance adjustment'),
                    'url': reverse('balance_adjustment'),
                    'external': False,
                },
                {
                    'title': _('Account 2FA reset'),
                    'url': reverse('two_factor_reset'),
                    'external': False,
                },
                {
                    'title': _('Financial Report'),
                    'url': reverse('financial_report'),
                    'external': False,
                },
                {
                    'title': _('Domain synchronization'),
                    'url': reverse('not_existing_domain_sync'),
                    'external': False,
                },
                {
                    'title': _('CSV file synchronization'),
                    'url': reverse('csv_file_sync'),
                    'external': False,
                },
                {
                    'title': _('Send a testing e-mail'),
                    'url': reverse('sending_single_email'),
                    'external': False,
                },
            ]
        ))

        self.children.append(modules.RecentActions(
            _('Recent actions'),
            limit=20,
            collapsible=False,
            column=3,
        ))
