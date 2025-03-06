from django import forms
from . import models
from django.contrib.auth.models import User

class Article_CommentForm(forms.Form):
    class Meta:
        model = models.Article_comment
        fields = ['comment']

class ArticleForm(forms.ModelForm):
    class Meta:
        model = models.Arcticle
        fields = '__all__'
        exclude = ['user_name']

        widgets = {
            'title': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    }
                ),
            'description': forms.Textarea(
                attrs={
                    'class': 'form-control',
    
                }), 
            }
class RegistrationForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput())
    password_confirm = forms.CharField(widget=forms.PasswordInput())

    class Meta:
        model = User
        fields = ['username', 'email', 'password']

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        password_confirm = cleaned_data.get("password_confirm")
        
        if password != password_confirm:
            raise forms.ValidationError("Passwords do not match.")
        return 
        
class UploadFileForm(forms.ModelForm):
    file = forms.FileField()