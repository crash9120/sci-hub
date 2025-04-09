from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('article/', views.article_list, name='article'),
    path('article/<int:category_id>/', views.article_by_category, name='article'),
    path('article_search/', views.search_article, name='search_article'),
    path('liked/<int:article_id>', views.liked, name='liked'),
    path('go_to_login/', views.login_required, name='go_to_login'),
    path('article_detail/<int:article_id>', views.article_detail, name='article_detail'),
    path('article_comment/<int:article_id>', views.article_comment, name='article_comment'),
    # path('http404/', views.http404, name='http404'),
    path('contact/', views.contact, name='contact'),
    path('about/', views.about, name='about'),
    path('profile/', views.profile, name='profile'),
    path('add_article/', views.add_article, name='add_article'),
    path('base/', views.base, name='base'),
    path('about1/', views.about1, name='about_new'),
    path('register/', views.register, name='register'),
    path('article/category/<int:category_id>/', views.article_by_category, name='article_by_category')

    
]
