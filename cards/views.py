from django.contrib.auth import get_user_model
from django.core.paginator import Paginator
from django.db.models import F, Q
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, JsonResponse
from django.template.context_processors import request
from typing import Any
from django.template.loader import render_to_string
from .models import Card
from django.http import HttpResponseRedirect
from django.views.decorators.cache import cache_page
from .forms import CardForm, UploadFileForm
import os
from re import search
import time
from django.views import View
from django.views.generic import TemplateView, DetailView
from django.views.generic.list import ListView
from django.core.cache import cache
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin


info = {
    # "menu": ['Главная', 'О проекте', 'Каталог']
    "menu": [
        {"title": "Главная",
         "url": "/",
         "url_name": "index"},
        {"title": "О проекте",
         "url": "/about/",
         "url_name": "about"},
        {"title": "Каталог",
         "url": "/cards/catalog/",
         "url_name": "catalog"},
    ],
}


class MenuMixin:
    """
    Класс-миксин для добавления меню в контекст шаблона
    Добывает и кеширует cards_count, users_count, menu
    """
    timeout = 30

    def get_menu(self):
        menu = cache.get('menu')
        if not menu:
            menu = info['menu']
            cache.set('menu', menu, timeout=self.timeout)

        return menu

    def get_cards_count(self):
        cards_count = cache.get('cards_count')
        if not cards_count:
            cards_count = Card.objects.count()
            cache.set('cards_count', cards_count, timeout=self.timeout)

        return cards_count

    def get_users_count(self):
        users_count = cache.get('users_count')
        if not users_count:
            users_count = get_user_model().objects.count()
            cache.set('users_count', users_count, timeout=self.timeout)

        return users_count

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['menu'] = self.get_menu()
        context['cards_count'] = self.get_cards_count()
        context['users_count'] = self.get_users_count()
        return context


class AboutView(MenuMixin, TemplateView):
    """
    Страница О проекте
    """
    template_name = 'about.html'
    extra_context = {'title': 'О проекте'}


class IndexView(MenuMixin, TemplateView):
    """
    Главная страница
    """
    template_name = 'main.html'


class PageNotFoundView(MenuMixin, TemplateView):
    template_name = '404.html'


class CatalogView(MenuMixin, ListView):
    """
    Страница Каталога
    """
    model = Card  # Указываем модель, данные которой мы хотим отобразить
    template_name = 'cards/catalog.html'  # Путь к шаблону, который будет использоваться для отображения страницы
    context_object_name = 'cards'  # Имя переменной контекста, которую будем использовать в шаблоне
    paginate_by = 30  # Количество объектов на странице

    # Метод для модификации начального запроса к БД
    def get_queryset(self):
        # Получение параметров сортировки из GET-запроса
        sort = self.request.GET.get('sort', 'upload_date')
        order = self.request.GET.get('order', 'desc')
        search_query = self.request.GET.get('search_query', '')

        # Определение направления сортировки
        if order == 'asc':
            order_by = sort
        else:
            order_by = f'-{sort}'

        # Фильтрация карточек по поисковому запросу и сортировка
        if search_query:
            queryset = Card.objects.filter(
                Q(question__iregex=search_query) |
                Q(answer__iregex=search_query) |
                Q(tags__name__iregex=search_query)
            ).select_related('category').prefetch_related('tags').order_by(order_by).distinct()
        else:
            queryset = Card.objects.select_related('category').prefetch_related('tags').order_by(order_by)
        return queryset

    # Метод для добавления дополнительного контекста
    def get_context_data(self, **kwargs):
        # Получение существующего контекста из базового класса
        context = super().get_context_data(**kwargs)
        # Добавление дополнительных данных в контекст
        context['sort'] = self.request.GET.get('sort', 'upload_date')
        context['order'] = self.request.GET.get('order', 'desc')
        context['search_query'] = self.request.GET.get('search_query', '')
        # Добавление статических данных в контекст, если это необходимо
        context['menu'] = info['menu'] # Пример добавления статических данных в контекст
        return context


def get_categories(requests):
    """ Возвращает все категории для представления в каталоге"""
    return HttpResponse('All categories')


def get_cards_by_category(requests, slug):
    """ Возвращает карточки по категории для представления в каталоге """
    return HttpResponse(f'Cards by category {slug}')


def get_cards_by_tag(request, tag_id):
    """ Возвращает карточки по тэгу для представления в каталоге """
    # Добываем карточки из БД по тегу
    cards = Card.objects.filter(tags__id=tag_id)

    # Подготавливаем контекст и отображаем шаблон
    context = {
        'cards': cards,
        'menu': info['menu'],
    }

    return render(request, 'cards/catalog.html', context)


class CardDetailView(MenuMixin, DetailView):
    """
    Детальное представление карточки
    """
    model = Card  # Указываем, что моделью для этого представления является Card
    template_name = 'cards/card_detail.html'  # Указываем путь к шаблону для детального отображения карточки
    context_object_name = 'card'  # Переопределяем имя переменной в контексте шаблона на 'card'

    # Метод для обновления счетчика просмотров при каждом отображении детальной страницы карточки
    def get_object(self, queryset=None):
        # Получаем объект с учетом переданных в URL параметров (в данном случае, pk или id карточки)
        obj = super().get_object(queryset=queryset)
        # Увеличиваем счетчик просмотров на 1 с помощью F-выражения для избежания гонки условий
        Card.objects.filter(pk=obj.pk).update(views=F('views') + 1)
        return obj


def preview_card_ajax(request):
    if request.method == "POST":
        question = request.POST.get('question', '')
        answer = request.POST.get('answer', '')
        category = request.POST.get('category', '')

        # Генерация HTML для предварительного просмотра
        html_content = render_to_string('cards/card_detail.html', {
            'card': {
                'question': question,
                'answer': answer,
                'category': 'Тестовая категория',
                'tags': ['тест', 'тег'],
            }
        }
                                        )

        return JsonResponse({'html': html_content})
    return JsonResponse({'error': 'Invalid request'}, status=400)


class AddCardCreateView(MenuMixin, LoginRequiredMixin, CreateView):
    """
    Добавление карточки
    """
    model = Card  # Указываем модель, с которой работает представление
    form_class = CardForm  # Указываем класс формы для создания карточки
    template_name = 'cards/add_card.html'  # Указываем шаблон, который будет использоваться для отображения формы
    success_url = reverse_lazy('catalog')  # URL для перенаправления после успешного создания карточки
    redirect_field_name = 'next'  # имя параметра запроса, в котором хранится URL-адрес, на который пользователь должен быть перенаправлен после успешного входа в систему.

    def form_valid(self, form):
        # Добавляем автора к карточке перед сохранением
        form.instance.author = self.request.user
        # Логика обработки данных формы перед сохранением объекта
        return super().form_valid(form)


class EditCardUpdateView(MenuMixin, LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = Card  # Указываем модель, с которой работает представление
    form_class = CardForm  # Указываем класс формы для редактирования карточки
    template_name = 'cards/add_card.html'  # Указываем шаблон, который будет использоваться для отображения формы
    context_object_name = 'card'  # Имя переменной контекста для карточки
    success_url = reverse_lazy('catalog')  # URL для перенаправления после успешного редактирования карточки
    permission_required = 'cards.change_card'  # Указываем право, которое должен иметь пользователь для доступа к представлению


class CardDeleteView(DeleteView):
    # Указываем модель, с которой работает представление
    model = Card
    # URL для перенаправления после успешного удаления карточки
    success_url = reverse_lazy('catalog')
    # Указываем шаблон, который будет использоваться для отображения формы подтверждения удаления
    template_name = 'cards/delete_card.html'
