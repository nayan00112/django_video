from django.db import models

class VideoModel(models.Model):
    title = models.CharField(max_length=200)
    original_file = models.FileField(upload_to='original_videos/')
    hls_folder = models.CharField(max_length=255, blank=True)  # folder where HLS is saved

    def __str__(self):
        return self.title