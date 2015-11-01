#  -*- coding: utf-8 -*-
"""Admin models for impersonate app."""
import logging

from django.contrib import admin
from django.conf import settings

from impersonate.models import ImpersonationLog

logger = logging.getLogger(__name__)

MAX_FILTER_SIZE = getattr(settings, 'IMPERSONATE_MAX_FILTER_SIZE', 100)


def friendly_name(user):
    """Return proper name if exists, else username."""
    if user.get_full_name() != '':
        return user.get_full_name()
    else:
        return user.username


class SessionStateFilter(admin.SimpleListFilter):

    """Custom admin filter based on the session state.

    Provides two filter values - 'complete' and 'incomplete'. A session
    that has no session_ended_at timestamp is considered incomplete. This
    field is set from the session_end signal receiver.

    """

    title = 'session state'
    parameter_name = 'session'

    def lookups(self, request, model_admin):
        return (
            ('incomplete', "Incomplete"),
            ('complete', "Complete")
        )

    def queryset(self, request, queryset):
        if self.value() == 'incomplete':
            return queryset.filter(session_ended_at__isnull=True)
        if self.value() == 'complete':
            return queryset.filter(session_ended_at__isnull=False)
        else:
            return queryset


class ImpersonatorFilter(admin.SimpleListFilter):

    """Custom admin filter based on the impersonator.

    Provides a set of users who have impersonated at some point. It is
    assumed that this is a small list of users - a subset of staff and
    superusers. There is no corresponding filter for users who have been
    impersonated, as this could be a very large set of users.
    
    If the number of unique impersonators exceeds MAX_FILTER_SIZE, then
    the filter is removed (shows only 'All').

    """

    title = 'impersonator'
    parameter_name = 'impersonator'

    def lookups(self, request, model_admin):
        """Return list of unique users who have been an impersonator."""
        # the queryset containing the ImpersonationLog objects
        qs = model_admin.get_queryset(request).order_by('impersonator__first_name')
        # dedupe the impersonators
        impersonators = set([q.impersonator for q in qs])
        if len(impersonators) > MAX_FILTER_SIZE:
            logger.debug(
                "Hiding admin list filter as number of impersonators "
                "exceeds MAX_FILTER_SIZE [%s]",
                len(impersonators),
                MAX_FILTER_SIZE
            )
            return

        for i in impersonators:
            yield (i.id, friendly_name(i))

    def queryset(self, request, queryset):
        if self.value() in (None, ''):
            return queryset
        else:
            return queryset.filter(impersonator_id=self.value())


class ImpersonationLogAdmin(admin.ModelAdmin):
    list_display = (
        'impersonator_',
        'impersonating_',
        'session_key',
        'session_started_at',
        'duration'
    )
    readonly_fields = (
        'impersonator',
        'impersonating',
        'session_key',
        'session_started_at',
        'session_ended_at',
        'duration'
    )
    list_filter = (SessionStateFilter, ImpersonatorFilter, 'session_started_at')

    def impersonator_(self, obj):
        return friendly_name(obj.impersonator)

    def impersonating_(self, obj):
        return friendly_name(obj.impersonating)

admin.site.register(ImpersonationLog, ImpersonationLogAdmin)
