from django.db import models
from django import forms
from djongo import models as djongo_models
from djongo.models import CharField, EmbeddedField, ArrayField, ObjectIdField, IntegerField, DjongoManager

LOCATION_LENGTH = 100
COMMENT_LENGTH = 1000

# Create your models here.
class LogEntry(models.Model):
    station_id = models.CharField(max_length=50)
    timestamp = models.DateTimeField()
    metrics = models.JSONField()
    result = models.CharField(max_length=10)
    filename = models.CharField(max_length=200, unique=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.station_id} - {self.timestamp} - {self.result}"



class Summary(models.Model):
    total = IntegerField(default = 0)
    passed = IntegerField(default = 0)
    error = IntegerField(default = 0)
    failed = IntegerField(default = 0)
    banner = CharField(max_length = 10, default = "NULL")
    css = CharField(max_length = 10, default = "null")

    def __getitem__(self, name):
        return getattr(self, name)

    class Meta:
        abstract = True


class Test_Outcome(models.Model):
    test_name = CharField(max_length = 20, null = False)
    #if this works, probably want to replace this with IntegerField or something similar to make sure it can only ever be [-1, 0, 1]
    passed = CharField(max_length = 4, null = False)
    total = CharField(max_length = 4, null = False)
    failed = CharField(max_length = 4, default = "0")
    anyFailed = CharField(max_length = 1, default = "0")
    anyForced = CharField(max_length = 1, default = "0")
    result = CharField(max_length = 10, default = "")
    get_css_class = CharField(max_length = 10, default = "")
    required = CharField(max_length = 0, default = "1")
    most_recent_date = CharField(max_length=20, default = "")
    objects = DjongoManager()

    class Meta:
        abstract = True
    
class Location(models.Model):
    date_received = CharField(max_length = 30, null = True)
    geo_loc = CharField(max_length=LOCATION_LENGTH, null = False)

    objects = DjongoManager()

    class Meta:
        abstract = True

class Location_Form(forms.ModelForm):
    class Meta:
        model = Location
        fields = ('date_received', 'geo_loc')


class CM_Card(djongo_models.Model):
    _id = djongo_models.ObjectIdField()
    #barcode is the chip number or barcode or whatnot
    barcode = CharField(max_length = 20, default = "NoID")
    ECOND = CharField(max_length = 20, default = "NoEconD")
    ECONT = CharField(max_length = 20, default = "NoEconT")
    #Quick Test summary for easy fast data. Updated by site when card is requested. Might be good to make a manual update script too.
    summary = EmbeddedField(model_container = Summary)#dont know what this is doing 
    #1 for passed, 0 for failed, -1 for skipped
    test_outcomes = ArrayField(
            model_container = Test_Outcome, 
            null = True)

    comments = CharField(max_length=COMMENT_LENGTH, null = True)

    locations = ArrayField(
            model_container = Location,
            default = [])
    def status(self):
        return self.summary["banner"]

    objects = DjongoManager()



class Test(djongo_models.Model):
    _id = djongo_models.ObjectIdField()
    #general info
    test_name = CharField(max_length = 20, default = "NoTest")
    barcode = CharField(max_length = 20, default = "NoID")
    tester = CharField(max_length=20, default = "unknown")
    date_run = CharField(max_length=20, default = "null")
    outcome = CharField(max_length=10, default = "null")
    valid = models.BooleanField(default = True)
    overwrite_pass = models.BooleanField(default=False)
    #eRX and eTX metadata
    eRX_errcounts = models.BinaryField()
    eTX_delays = models.BinaryField()
    eTX_bitcounts = models.BinaryField()
    eTX_errcounts = models.BinaryField()
    #error log
    longrepr = models.TextField(max_length = 2000, null = True)
    #failure logs
    stdout = models.TextField(max_length = 2000, null = True)
    crashpath = models.TextField(max_length = 2000, null = True)
    crashmsg = models.TextField(max_length = 2000, null = True)
    #more specific test info
    filename = CharField(max_length = 50, unique = True)
    branch = CharField(max_length = 20, default = "NO_BRANCH")
    commit_hash = CharField(max_length = 30, default = "NO_COMMIT_HASH")
    remote_url = CharField(max_length = 50, default = "NO_URL")
    status = CharField(max_length = 50, default = "NO_STATUS")
    firmware_name = CharField(max_length = 30, default = "NO_FIRMWARE_NAME")
    firmware_git_desc =  CharField(max_length = 20, default = "NO_GIT_DESC")
    ECON_TYPE = CharField(max_length=10, default = "Unknown")

    comments = CharField(max_length=COMMENT_LENGTH, null = True)

    objects = DjongoManager()

    class Meta:
        ordering = ('date_run',)

class Test_Type(models.Model):
    test_name = CharField(max_length = 30, default = "")
    number_passed = IntegerField()
    number_failed = IntegerField()
    number_total = IntegerField()
    required = models.BooleanField(default = True)
    class Meta:
        abstract = True

class Test_Type_Form(forms.ModelForm):
    class Meta:
        model = Test_Type
        fields = ('test_name','number_passed','number_failed','number_total')
class Overall_Summary(djongo_models.Model):
    _id = djongo_models.ObjectIdField()
    test_types = ArrayField(model_container = Test_Type, model_form_class = Test_Type_Form, default=list)
    passedcards = djongo_models.IntegerField(default = 0)
    failedcards = djongo_models.IntegerField(default = 0)
    totalcards = djongo_models.IntegerField(default = 0)

    objects = DjongoManager()


class TestStation(models.Model):
    station_id = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    location = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    calibration_date = models.DateField()

    def __str__(self):
        return f"{self.station_id} - {self.name}"
