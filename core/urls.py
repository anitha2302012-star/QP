from django.urls import path
from . import views as v

urlpatterns = [
    path("", v.home, name="home"),
    path("login/", v.login_view, name="login"),
    path("logout/", v.logout_view, name="logout"),
    path("papers/", v.search, name="search"),
    path("papers/<int:pk>/", v.detail, name="detail"),
    path("papers/<int:pk>/file/", v.download, name="download"),
    path("papers/<int:pk>/delete/", v.delete_paper, name="delete_paper"),
    path("upload/", v.upload, name="upload"),
    path("my-uploads/", v.my_uploads, name="my_uploads"),
    path("manage/papers/", v.all_papers, name="all_papers"),
    path("manage/users/", v.users_list, name="users"),
    path("manage/users/new/", v.user_edit, name="user_new"),
    path("manage/users/<int:pk>/edit/", v.user_edit, name="user_edit"),
    path("manage/users/<int:pk>/delete/", v.user_delete, name="user_delete"),
    path("manage/analytics/", v.analytics, name="analytics"),
]
