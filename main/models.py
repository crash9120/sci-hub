from django.db import models
from django.contrib.auth.models import User
from ckeditor.fields import RichTextField

class ArticleCategory(models.Model):
    name = models.CharField(max_length=200)
        
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = "Makala kategoriýa"
        verbose_name_plural = "Makala kategoriýalary"
        ordering = ['name']
        db_table = 'article_categories'


class Arcticle(models.Model):
    title = models.TextField(max_length=200)
    file = models.FileField(upload_to='documents/',max_length=200)
    img = models.ImageField(upload_to='images/',default='images\Cybersecurity.png', blank=True, null=True)
    description = RichTextField(blank=True, null=True)
    category = models.ForeignKey(ArticleCategory, on_delete=models.CASCADE)
    date_created = models.DateTimeField(auto_now_add=True)
    user_name = models.CharField(max_length=200,default='Admin',blank=True, null=True)
    likes = models.IntegerField(default=0)
    reads = models.IntegerField(default=0)
    def __str__(self):
        return self.title
    def increment_read(self):
        self.reads += 1
        self.save(update_fields=['reads'])

    def increment_like(self):
        self.likes += 1
        self.save(update_fields=['likes'])
    
    class Meta:
        verbose_name = "Makala"
        verbose_name_plural = "Makalalar"
        ordering = ['title']
        db_table = 'articles'

class Article_read(models.Model):
    article_read = models.ForeignKey(Arcticle, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    date_read = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} - {self.article_read}"
    
    class Meta:
        verbose_name = "Makala okan"
        verbose_name_plural = "Makala okanlar"
        ordering = ['date_read']
        db_table = 'article_reads'
        unique_together = ('user', 'article_read')

class Article_like(models.Model):
    article_like = models.ForeignKey(Arcticle, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    date_like = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user} - {self.article_like}"
    
    class Meta:
        verbose_name = "Makala halanan"
        verbose_name_plural = "Makala halanlar"
        db_table = 'article_likes'

class Article_comment(models.Model):
    article_comment = models.ForeignKey(Arcticle, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    comment = RichTextField(blank=True, null=True)
    date_comment = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user} - {self.article_comment}"
    
    class Meta:
        verbose_name = "Makala kommentariýa"
        verbose_name_plural = "Makala kommentariýa"
        db_table = 'article_comments'


class Contact(models.Model):
    message = RichTextField()
    date_created = models.DateTimeField(auto_now_add=True)
    title = models.CharField(max_length=200)
    is_read = models.BooleanField(default=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True)

    def __str__(self):
        return self.title
    
    class Meta:
        verbose_name = "Bildiriş"
        verbose_name_plural = "Bildirişler"
        ordering = ['-date_created']
        db_table = 'contacts'
        