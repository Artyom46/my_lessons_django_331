"""
URL configuration for anki project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
#  Подключаем файл urls.py из приложения cards через include

from django.contrib import admin
from django.urls import path, include
from anki import settings
from cards import views, urls
from django.views.decorators.cache import cache_page
from django.conf.urls.static import static
from django.conf import settings


# Настраиваем заголовки админ-панели
# Текст в шапке
admin.site.site_header = "Управление моим сайтом"
# Текст в тайтле
admin.site.site_title = "Административный сайт"
# Текст на главной странице
admin.site.index_title = "Добро пожаловать в панель управления"


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', cache_page(60 * 15)(views.IndexView.as_view()), name='index'),
    path('about/', cache_page(60 * 15)(views.AboutView.as_view()), name='about'),
    path('cards/', include('cards.urls')),
    path('users/', include('users.urls', namespace='users')),
]

if settings.DEBUG:
    import debug_toolbar

    urlpatterns = [
                      path('__debug__/', include(debug_toolbar.urls)),
                      # другие URL-паттерны
                  ] + urlpatterns

    # Добавляем обработку медиафайлов
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


# Кастомный обработчик ошибки 404
handler404 = views.PageNotFoundView.as_view()
