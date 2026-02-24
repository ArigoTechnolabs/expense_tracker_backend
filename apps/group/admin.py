from django.contrib import admin
from apps.group.models import Group, Person, GroupTransaction


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ("name", "user", "created_at", "updated_at")
    list_filter = ("created_at", "user")
    search_fields = ("name", "user__email")
    readonly_fields = ("created_at", "updated_at")


@admin.register(Person)
class PersonAdmin(admin.ModelAdmin):
    list_display = ("name", "group", "created_at")
    list_filter = ("group", "created_at")
    search_fields = ("name", "group__name")
    readonly_fields = ("created_at", "updated_at")


@admin.register(GroupTransaction)
class GroupTransactionAdmin(admin.ModelAdmin):
    list_display = ("group", "person", "type", "amount", "date", "user")
    list_filter = ("type", "date", "group", "user")
    search_fields = ("group__name", "person__name", "user__email")
    readonly_fields = ("created_at", "updated_at", "user")
