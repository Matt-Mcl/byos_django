import base64
import random
import re
import shutil
import string
import tempfile

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from playwright.sync_api import sync_playwright
from wand.image import Image


class Device(models.Model):
    friendly_id = models.CharField(max_length=6, unique=True, null=False, blank=False)
    device_name = models.CharField(max_length=50)
    mac_address = models.CharField(max_length=17, unique=True, null=False, blank=False)
    api_key = models.CharField(max_length=32, unique=True, null=False, blank=False)
    user = models.ForeignKey(
        "auth.User", on_delete=models.CASCADE, null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True, null=False, blank=False)
    updated_at = models.DateTimeField(auto_now=True, null=False, blank=False)
    last_seen_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    refreshes = models.IntegerField(default=0)
    refresh_rate = models.IntegerField(default=900)

    def __str__(self):
        return f"{self.device_name} ({self.friendly_id})"

    def clean(self):
        # Validate MAC Address format
        self.mac_address = self.mac_address.upper()
        if not re.match(r"^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$", self.mac_address):
            raise ValidationError({"mac_address": "Invalid MAC address format."})

    def save(self, *args, **kwargs):
        # Generate a random API key on first create
        if not self.mac_address:
            # refuse to save the model if the MAC address is missing
            raise ValidationError({"mac_address": "MAC address is required."})
        if not self.api_key:
            self.api_key = "".join(random.choices(string.ascii_letters, k=32))
        # Generate a random friendly ID on first create
        if not self.friendly_id:
            self.friendly_id = "".join(
                random.choices(string.ascii_uppercase + string.digits, k=6)
            )

        self.clean()

        super().save(*args, **kwargs)

    def get_screen(self, update_last_seen=False):
        screen = self.screen_set.order_by("-created_at").first()
        if update_last_seen:
            self.last_seen_at = timezone.now()
            self.refreshes += 1
            self.save()

        if screen:
            return screen

        return None


class DeviceLog(models.Model):
    device = models.ForeignKey(Device, on_delete=models.CASCADE)
    message = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True, null=False, blank=False)


class Screen(models.Model):
    device = models.ForeignKey(Device, on_delete=models.CASCADE)
    html = models.TextField()
    url = models.TextField()
    screen = models.BinaryField()
    created_at = models.DateTimeField(auto_now_add=True, null=False, blank=False)
    generated = models.BooleanField(default=False)

    def generate_screen(self):
        # get random file name
        folder = tempfile.mkdtemp()

        with sync_playwright() as p:
            if settings.PW_SERVER:
                browser = p.firefox.connect(ws_endpoint=settings.PW_SERVER)
            else:
                browser = p.firefox.launch(
                    headless=True,
                    args=["--window-size=800,480", "--disable-web-security"],
                )
            page = browser.new_page()
            page.set_viewport_size({"width": 800, "height": 480})

            if self.url is not None:
                page.goto(self.url, timeout=60000)
            else:
                page.set_content(self.html)

            page.wait_for_timeout(3000)

            page.evaluate(
                'document.getElementsByTagName("html")[0].style.overflow = "hidden";'
                'document.getElementsByTagName("body")[0].style.overflow = "hidden";'
            )
            page.screenshot(path=f"/{folder}/screen.png")
            browser.close()

        with Image(filename=f"/{folder}/screen.png") as img:
            img.posterize(2, dither="floyd_steinberg")
            amap = Image(width=img.width, height=img.height, pseudo="pattern:gray50")
            amap.composite(img, 0, 0)
            img = amap
            img.quantize(2, colorspace_type="gray")
            img.depth = 1
            img.strip()
            img.save(filename=f"bmp3:/{folder}/screen.bmp")

        with open(f"/{folder}/screen.bmp", "rb") as f:
            self.screen = f.read()
            self.generated = True
            self.save()

        # clean up
        shutil.rmtree(folder, ignore_errors=True)

    @property
    def image_as_base64(self):
        return f"data:image/bmp;base64,{base64.b64encode(self.screen).decode()}"

    @property
    def image_as_url_for_device(self):
        device_api_key = self.device.api_key
        return f"/api/v1/media/{self.device.friendly_id}-{self.id}.bmp?api_key={device_api_key}"

    @property
    def image_as_url_for_device_filename(self):
        return f"{self.device.friendly_id}-{self.id}.bmp"


class APIKey(models.Model):
    name = models.CharField(max_length=50, null=False, blank=False)
    key = models.CharField(max_length=32, unique=True, null=False, blank=False)
    user = models.ForeignKey(
        "auth.User", on_delete=models.CASCADE, null=False, blank=False
    )
    created_at = models.DateTimeField(auto_now_add=True, null=False, blank=False)

    def save(self, *args, **kwargs):
        # Generate a random API key on first create
        if not self.key:
            self.key = "".join(random.choices(string.ascii_letters, k=32))
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} (Owner: {self.user.username})"
