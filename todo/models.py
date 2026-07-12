from django.db import models

class Task(models.Model):
    task = models.CharField(max_length=250)
    is_completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # this is a string representation of the model, it will return the task name when we print the object
    def __str__(self):
        return self.task