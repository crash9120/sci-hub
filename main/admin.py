from django.contrib import admin
from . import models

class ArcticleAdmin(admin.ModelAdmin):
    list_display = ('id','title', 'category', 'date_created', 'user_name','description')
    search_fields = ('title', 'category__name', 'user_name')
    list_filter = ('category', 'date_created')
    list_display_links = ('title','category', 'date_created', 'user_name')

class CommentAdmin(admin.ModelAdmin):
    list_display = ('id', 'article_comment', 'user', 'comment', 'date_comment')

class LikeAdmin(admin.ModelAdmin):
    list_display = ('id', 'article_like', 'user', 'date_like')

class ReadAdmin(admin.ModelAdmin):
    list_display = ('id', 'article_read', 'user', 'date_read')


admin.site.register(models.ArticleCategory)
admin.site.register(models.Arcticle,ArcticleAdmin)
admin.site.register(models.Article_like,LikeAdmin)
admin.site.register(models.Article_read,ReadAdmin)
admin.site.register(models.Article_comment,CommentAdmin)