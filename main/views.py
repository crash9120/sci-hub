from django.shortcuts import render, redirect
from . import models
from django.http import Http404, HttpResponseRedirect, HttpResponse
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from .forms import ArticleForm
from django.db.models import Count
from django.core.paginator import Paginator
from random import sample

def get_most_liked_articles(num_articles=5):
    most_liked_articles = models.Article_like.objects.values('article_like') \
        .annotate(like_count=Count('id')) \
        .order_by('-like_count')[:num_articles]
    
    article_ids = [item['article_like'] for item in most_liked_articles]
    most_liked_articles = models.Arcticle.objects.filter(id__in=article_ids)

    return most_liked_articles

def index(request):
    # Проверяем, аутентифицирован ли пользователь
    if request.user.is_authenticated:
        read_articles_count = models.Article_read.objects.filter(user=request.user).count()
        articles = models.Arcticle.objects.filter(user_name__icontains=request.user.username)  # Предположим, что user_name — это поле в модели
    else:
        read_articles_count = 0
        articles = models.Arcticle.objects.all()  # Для анонимного пользователя показываем все статьи

    # Получаем количество пользователей и статей
    user_count = User.objects.count()
    article_count = models.Arcticle.objects.count()

    articles = models.Arcticle.objects.all()
    random_articles = sample(list(articles), min(len(articles), 30))
# kategoriya uçin
    categories = models.ArticleCategory.objects.annotate(article_count=Count('arcticle'))

    context = {
        'user_count': user_count,
        'article_count': article_count,
        'random_articles': random_articles,
        'read_articles_count': read_articles_count,
        'categories': categories
    }
    
    return render(request, 'index.html', context)




def article_list(request):
    article_list = None
    if request.method == 'POST':
        article = request.POST['article']
        article_list = models.Arcticle.objects.filter(title__icontains=article)
    else:
        article_list = models.Arcticle.objects.all()

    paginator = Paginator(article_list, 6)  # Show 6 articles per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    categories = models.ArticleCategory.objects.all()

    context = {
        'article_list': page_obj,  # Pass the page_obj instead of the raw list
        'categories': categories
    }
    return render(request, 'article.html', context)

def article_by_category(request, category_id):
    articles= models.Arcticle.objects.filter(category_id=category_id)
    categories = models.ArticleCategory.objects.all()
    context = {'article_list': articles, 'categories': categories}
    return render(request, 'article.html', context)
    
@login_required
def liked(request, article_id):
    article = models.Arcticle.objects.filter(id=article_id).first()
    if not article:
        return redirect('error')

    user = request.user
    like = models.Article_like.objects.filter(article_like=article, user=user).first()

    if like:
        like.delete()  # Если лайк уже есть, удаляем его (дизлайк)
    else:
        models.Article_like.objects.create(article_like=article, user=user)

    return redirect('article_detail', article_id=article_id)

  
def go_to_login(request):   
    return render(request, 'login_required.html')

def base(request):   
    return render(request, 'base.html')

def about1(request):   
    return render(request, 'about1.html')

def search_article(request):
    if request.method == 'POST':
        article = request.POST['makala']
        articles = models.Arcticle.objects.filter(title__icontains=article)
        categories = models.ArticleCategory.objects.all()
        context = {'article_list': articles, 'categories': categories}
        return render(request,'article.html', context)

def article_detail(request, article_id):
    article = models.Arcticle.objects.filter(id=article_id).first()
    if not article:
        raise Http404("Статья не найдена")

    # Увеличиваем счетчик прочтений (если метод существует)
    if hasattr(article, 'increment_read'):
        article.increment_read()

    # Если пользователь аутентифицирован, создаём запись о прочтении статьи
    if request.user.is_authenticated:
        # Проверяем, существует ли запись о том, что пользователь прочитал статью
        read_record, created = models.Article_read.objects.get_or_create(user=request.user, article_read=article)
        
        if created:
            # Если запись о прочтении только что создана, увеличиваем счётчик прочтённых статей
            read_articles_count = models.Article_read.objects.filter(user=request.user).count()
        else:
            read_articles_count = models.Article_read.objects.filter(user=request.user).count()
    else:
        read_articles_count = 0  # Для анонимных пользователей счётчик 0

    article_comments = models.Article_comment.objects.filter(article_comment__id=article_id)
    context = {
        'article': article,
        'article_id': article_id,
        'article_comments': article_comments,
        'read_articles_count': read_articles_count  # Передаем количество прочитанных статей в контекст
    }
    
    return render(request, 'article_detail.html', context)


@login_required
def article_comment(request, article_id):
    if request.method == 'POST':
        article = models.Arcticle.objects.filter(id=article_id).first()
        user = request.user
        comment = request.POST['comment']
        models.Article_comment.objects.create(article_comment=article, user=user, comment=comment)

    return redirect('article_detail', article_id=article_id)

# def http404(request):
#     return render(request, 'http404.html')


def contact(request):
    if request.method == 'POST':
        title = request.POST['title']
        message = request.POST['message']
        user = request.user
        result = models.Contact.objects.create(title=title, message=message, user=user)
        if result:
           message = messages.success(request, 'Habar üçin sagboluň!.')
        else:
            message = messages.error(request, 'Näsazlyk ýüze çykdy.')
        return render(request, 'contact.html', {'message': message})

    return render(request, 'contact.html')

def about(request):
    return render(request, 'about.html')


def profile(request):
     # Фильтруем статьи по имени пользователя
    articles = models.Arcticle.objects.filter(user_name__icontains=request.user.username)
    
    # Создаем пагинатор: например, 6 статей на странице
    paginator = Paginator(articles, 6)  # Показываем по 6 статей на странице
    
    # Получаем номер текущей страницы из GET-запроса
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Получаем все категории
    categories = models.ArticleCategory.objects.all()
    
    # Форму можно оставить как есть
    form = ArticleForm()

    # Передаем в контекст пагинированные статьи
    context = {'categories': categories, 'form': form, 'page_obj': page_obj}
    
    return render(request, 'profile.html', context)

@login_required
def add_article(request):
    if request.method == 'POST':
        form = ArticleForm(request.POST, request.FILES)
        if form.is_valid():
            article = form.save(commit=False)
            article.user_name = request.user.username
            article.save()
            return redirect('profile')
    else:
        form = ArticleForm()

    return render(request, 'add_article.html', {'form': form})

def register(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.save()
            messages.success(request, 'Registration successful.')
            return redirect('login')  # Переход на страницу логина после успешной регистрации
    else:
        form = RegistrationForm()

    return render(request, 'register.html', {'form': form})