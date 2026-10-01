from django.urls import path
from . import views

urlpatterns = [
    path("addTask/new/", views.add_task_page, name="add_task_page"),
    path("addTask/", views.addTask, name="addTask"),
    path("mark_as_done/<int:pk>/", views.mark_as_done, name="mark_as_done"),
    path("mark_as_undone/<int:pk>/", views.mark_as_undone, name="mark_as_undone"),
    path("edit_task/<int:pk>/", views.edit_task, name="edit_task"),
    path("task/<int:pk>/", views.task_detail, name="task_detail"),
    path("delete_task/<int:pk>/", views.delete_task, name="delete_task"),
    path("toggle_favorite/<int:pk>/", views.toggle_favorite, name="toggle_favorite"),
    path("reorder/", views.reorder_tasks, name="reorder_tasks"),
    path("profile-picture/", views.protected_profile_picture, name="profile_picture"),
    path(
        "background-image/", views.protected_background_image, name="background_image"
    ),
    path("categories/add/", views.add_category, name="add_category"),
    path("categories/<int:pk>/delete/", views.delete_category, name="delete_category"),
]
