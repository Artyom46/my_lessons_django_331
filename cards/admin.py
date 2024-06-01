from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from .models import Card


class CardCodeFilter(SimpleListFilter):
    title = 'Наличие кода'
    parameter_name = 'has_code'

    def lookups(self, request, model_admin):
        return (
            ('yes', 'Да'),
            ('no', 'Нет'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.filter(answer__contains='```')
        elif self.value() == 'no':
            return queryset.exclude(answer__contains='```')


@admin.register(Card)
class CardAdmin(admin.ModelAdmin):
    # Поля в админке
    list_display = ('id', 'question', 'category', 'views', 'upload_date', 'status', 'brief_info')
    # Поля - ссылки в админке
    list_display_links = ('id',)
    # Поиск по полям
    search_fields = ('question', 'answer')
    # Фильтр по полям
    list_filter = ('category', 'upload_date', 'status', CardCodeFilter)
    # Сортировка
    ordering = ('-upload_date',)
    # Количество карточек на странице
    list_per_page = 15
    # Редактируемые поля (либо list_display_links, либо list_editable)
    list_editable = ('views', 'question', 'status')
    actions = ['set_checked', 'set_unchecked']
    # fields = ('question', 'answer', 'category', 'status')  # Без этого и так всё видно, кроме 'tags'
    change_form_template = 'admin/cards/change_form_custom.html'

    @admin.action(description="Пометить как проверенное")
    def set_checked(self, request, queryset):
        updated_count = queryset.update(status=Card.Status.CHECKED)
        self.message_user(request, f"{updated_count} записей было помечено как проверенное")

    @admin.action(description="Пометить как не проверенное")
    def set_unchecked(self, request, queryset):
        updated_count = queryset.update(status=Card.Status.UNCHECKED)
        self.message_user(request, f"{updated_count} записей было помечено как непроверенное", 'warning')

    # Определение метода для отображения краткой информации о карточке
    @admin.display(description="Наличие кода", ordering='answer')
    # ordering по полю answer, так как точного поля для сортировки по краткому описанию нет
    def brief_info(self, card):
        # Проверяем наличие кода
        has_code = 'Да' if '```' in card.answer else 'Нет'
        return f"Код: {has_code}"
